"""Strategy-agnostic single-symbol backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

from cryptolab.config import Config, SlippageConfig
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.backtest.metrics import compute_metrics, drawdown_series, PERIODS_PER_YEAR
from cryptolab.backtest.telemetry import TelemetryRecorder


# ---------------------------------------------------------------------------
# Dynamic slippage model (Ludwig)
# ---------------------------------------------------------------------------

# bars-per-day lookup for ADV window conversion
_BARS_PER_DAY = {"1h": 24, "2h": 12, "4h": 6, "8h": 3, "1d": 1}


def compute_slippage(trade_size_usd: float, adv_usd: float,
                     slippage_cfg: SlippageConfig,
                     fallback_bps: float = 15.0) -> float:
    """Compute slippage in USD for a single trade.

    Args:
        trade_size_usd: absolute USD notional of the trade
        adv_usd: average daily volume in USD (rolling 20-day)
        slippage_cfg: SlippageConfig with model selection
        fallback_bps: used when model="fixed" or ADV unavailable

    Returns:
        slippage in USD (always >= 0)
    """
    if trade_size_usd <= 0:
        return 0.0

    model = slippage_cfg.model

    if model == "fixed":
        return trade_size_usd * fallback_bps / 10_000

    if adv_usd <= 0 or np.isnan(adv_usd):
        # Fallback to fixed when ADV unavailable
        return trade_size_usd * fallback_bps / 10_000

    if model == "auto":
        ratio = trade_size_usd / adv_usd
        if ratio < slippage_cfg.auto_threshold:
            model = "linear"
        else:
            model = "quadratic"

    if model == "linear":
        return trade_size_usd * slippage_cfg.k2_bps / 10_000
    elif model == "quadratic":
        return (slippage_cfg.k1 / adv_usd) * trade_size_usd ** 2
    else:
        return trade_size_usd * fallback_bps / 10_000


def precompute_adv(df: pd.DataFrame, interval: str,
                   adv_window_days: int = 20) -> np.ndarray:
    """Precompute rolling average daily volume in USD from OHLCV DataFrame.

    Returns numpy array of length len(df) with ADV in USD for each bar.
    """
    vol_usd = df["volume"].values * df["close"].values
    bpd = _BARS_PER_DAY.get(interval, 24)
    window_bars = adv_window_days * bpd
    # Sum bars over window, divide by days to get daily average
    adv = pd.Series(vol_usd).rolling(window_bars, min_periods=max(1, bpd)).sum().values / adv_window_days
    return adv


@dataclass
class Trade:
    """单笔交易记录。每次仓位变化都生成一条。

    realized_pnl: 只在减仓/平仓时非零（开仓时为0）。
    计算方式: 减仓数量 × (成交价 - 入场均价) / 入场均价
    """
    bar_idx: int
    timestamp: pd.Timestamp
    symbol: str
    side: str  # "BUY" or "SELL"
    size_usd: float  # absolute USD notional traded
    fill_px: float
    fee: float
    old_position: float  # signed USD before trade
    new_position: float  # signed USD after trade
    realized_pnl: float  # PnL realized on this trade (0 for opens)
    signal: str  # from StrategySignal.signal
    metadata: dict = field(default_factory=dict)


@dataclass
class BacktestResult:
    config: Config
    symbol: str
    start_date: str
    end_date: str
    strategy_name: str
    # Equity
    initial_equity: float
    final_equity: float
    total_return_pct: float
    # Risk
    max_drawdown_pct: float
    max_drawdown_usd: float
    sharpe: float
    sortino: float
    calmar: float
    # Trades
    total_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    # Costs
    total_fees: float
    total_slippage_est: float
    # Time
    time_in_market_pct: float
    avg_trade_duration_bars: float
    # Data
    equity_curve: pd.DataFrame  # columns: timestamp, equity, drawdown_pct
    trades: List[Trade] = field(default_factory=list)
    telemetry: Optional[TelemetryRecorder] = None


class _PositionTracker:
    """单币种仓位追踪器。管理加仓/减仓/翻转的入场均价和已实现盈亏。

    核心逻辑:
    - 加仓: 入场价按USD加权平均（不是简单平均）
    - 减仓: 对减掉的部分按 (成交价-入场价)/入场价 计算已实现盈亏
    - 翻转(多翻空): 先全部平仓（结算盈亏），再以新方向开仓
    - 手续费不在这里处理——由BacktestEngine在外部扣除
    """

    def __init__(self):
        self.position_usd: float = 0.0  # signed USD notional
        self.entry_px: Optional[float] = None

    def unrealized_pnl(self, mark_px: float) -> float:
        if self.position_usd == 0.0 or self.entry_px is None:
            return 0.0
        return self.position_usd * (mark_px - self.entry_px) / self.entry_px

    def execute(self, target_usd: float, fill_px: float) -> tuple[float, float]:
        """Execute a position change. Returns (abs_trade_size_usd, gross_realized_pnl).

        Handles increase/reduce/flip/close following old v9 _do_trade logic.
        Fees are computed and deducted by the engine, not here.
        """
        old_pos = self.position_usd
        trade_size = target_usd - old_pos

        if abs(trade_size) < 0.01:
            return 0.0, 0.0

        # Same direction: increase or reduce
        if (old_pos > 0 and target_usd > 0) or (old_pos < 0 and target_usd < 0):
            if abs(target_usd) > abs(old_pos):
                # Increase: weighted average entry
                add_sz = target_usd - old_pos
                if self.entry_px is not None and self.entry_px > 0:
                    self.entry_px = (old_pos * self.entry_px + add_sz * fill_px) / target_usd
                else:
                    self.entry_px = fill_px
                self.position_usd = target_usd
                return abs(add_sz), 0.0
            else:
                # Reduce: realize gross PnL on reduced portion
                reduced_sz = abs(old_pos) - abs(target_usd)
                realized = 0.0
                if self.entry_px is not None and self.entry_px > 0 and reduced_sz > 0:
                    if old_pos > 0:
                        realized = reduced_sz * (fill_px - self.entry_px) / self.entry_px
                    else:
                        realized = reduced_sz * (self.entry_px - fill_px) / self.entry_px
                if abs(target_usd) < 0.01:
                    self.entry_px = None
                self.position_usd = target_usd
                return reduced_sz, realized

        # Flip or open from flat or close: close fully, then open new
        realized = 0.0

        # Close existing position
        if abs(old_pos) > 0.01 and self.entry_px is not None and self.entry_px > 0:
            sz = abs(old_pos)
            if old_pos > 0:
                realized = sz * (fill_px - self.entry_px) / self.entry_px
            else:
                realized = sz * (self.entry_px - fill_px) / self.entry_px

        self.entry_px = None

        # Open new position if target != 0
        if abs(target_usd) > 0.01:
            self.entry_px = fill_px

        self.position_usd = target_usd
        return abs(trade_size), realized


class BacktestEngine:
    """回测引擎：接收一个策略和OHLCV数据，逐bar模拟交易。

    关键设计:
    - 信号在当前bar收盘价处生成，但在下一bar的开盘价执行（T+1成交，防止未来函数）
    - 权益按复利增长（仓位大小随MTM权益变化）
    - 滑点: 买入时成交价 = 开盘价 × (1+滑点)，卖出时反之
    - 手续费从现金中扣除
    - Gap stop: 如果开盘价直接穿透止损位，按开盘价平仓（模拟跳空）
    """

    def __init__(self, strategy: BaseStrategy, cfg: Config):
        self.strategy = strategy
        self.cfg = cfg

    def run(self, symbol: str, df: pd.DataFrame) -> BacktestResult:
        """主回测循环。

        对每一根K线:
        1. 检查gap stop（开盘价是否穿透止损）
        2. 执行上一根K线的信号（在本bar开盘价+滑点成交）
        3. 更新权益（现金 + 未实现盈亏）
        4. 调用strategy.generate_signal()生成下一bar的信号

        输入: symbol（币种代号）, df（OHLCV DataFrame，至少2根K线）
        输出: BacktestResult（权益曲线、交易列表、绩效指标）
        """
        if len(df) < 2:
            raise ValueError("Need at least 2 bars for backtest")

        initial_equity = self.cfg.initial_capital
        cash = initial_equity
        tracker = _PositionTracker()
        trades: List[Trade] = []
        telemetry = TelemetryRecorder()
        taker_fee = self.cfg.taker_fee_bps / 10_000
        maker_fee = self.cfg.maker_fee_bps / 10_000
        slippage_bps = self.cfg.slippage_bps
        slippage_cfg = self.cfg.slippage
        adv_arr = precompute_adv(df, self.cfg.interval, slippage_cfg.adv_window_days)

        # Equity curve storage
        timestamps = []
        equities = []

        # Bar 0: generate initial signal
        prev_signal = self.strategy.generate_signal(symbol, df.iloc[:1], initial_equity)

        # Record bar 0 equity
        mark_px = df.iloc[0]["close"]
        equity = cash + tracker.unrealized_pnl(mark_px)
        timestamps.append(df.iloc[0]["timestamp"])
        equities.append(equity)

        # Telemetry: record bar 0 signal
        bar0 = df.iloc[0]
        telemetry.record(
            bar_idx=0, timestamp=bar0["timestamp"], symbol=symbol,
            bar_data={"open": bar0["open"], "high": bar0["high"],
                      "low": bar0["low"], "close": bar0["close"],
                      "volume": bar0["volume"]},
            equity=equity, position_usd=tracker.position_usd, signal=prev_signal,
        )

        for bar_idx in range(1, len(df)):
            bar = df.iloc[bar_idx]
            open_px = bar["open"]
            mark_px = bar["close"]

            # 0. Gap stop check: did this bar OPEN beyond the stop level?
            #    Only triggers on true gaps (open beyond stop), not intra-bar wicks.
            #    Strategy's close-based check handles non-gap stop exits.
            stop_triggered = False
            if (prev_signal
                    and prev_signal.suggested_stop_px is not None
                    and abs(tracker.position_usd) > 0.01):
                stop_px = prev_signal.suggested_stop_px
                is_long = tracker.position_usd > 0
                is_short = tracker.position_usd < 0

                if is_long and open_px <= stop_px:
                    fill_px = open_px  # gapped through, fill at open
                    stop_triggered = True
                elif is_short and open_px >= stop_px:
                    fill_px = open_px
                    stop_triggered = True

                if stop_triggered:
                    old_pos = tracker.position_usd
                    trade_size, gross_pnl = tracker.execute(0.0, fill_px)
                    if trade_size > 0:
                        fee = trade_size * taker_fee
                        slippage_usd = abs(fill_px - open_px) / open_px * trade_size if open_px > 0 else 0
                        cash += gross_pnl - fee
                        trades.append(Trade(
                            bar_idx=bar_idx,
                            timestamp=bar["timestamp"],
                            symbol=symbol,
                            side="SELL" if is_long else "BUY",
                            size_usd=trade_size,
                            fill_px=fill_px,
                            fee=fee,
                            old_position=old_pos,
                            new_position=0.0,
                            realized_pnl=gross_pnl - fee,
                            signal="STOP_GAP",
                            metadata={"stop_px": stop_px, "slippage_usd": slippage_usd},
                        ))
                    # Reset strategy state for this symbol
                    self.strategy.reset(symbol)

            # 1. Execute previous bar's signal at this bar's open + slippage
            target_usd = prev_signal.target_position if not stop_triggered else 0.0
            if abs(target_usd - tracker.position_usd) >= 0.01:
                # Determine fill direction for slippage
                buying = target_usd > tracker.position_usd
                trade_notional = abs(target_usd - tracker.position_usd)
                slippage_usd = compute_slippage(
                    trade_notional, adv_arr[bar_idx], slippage_cfg, slippage_bps)
                slip_pct = slippage_usd / trade_notional if trade_notional > 0 else 0
                if buying:
                    fill_px = open_px * (1 + slip_pct)
                else:
                    fill_px = open_px * (1 - slip_pct)

                # Fee rate based on order type
                fee_rate = maker_fee if prev_signal.order_type == "maker" else taker_fee

                old_pos = tracker.position_usd
                trade_size, gross_pnl = tracker.execute(target_usd, fill_px)

                if trade_size > 0:
                    fee = trade_size * fee_rate

                    # Fee and gross PnL both hit cash immediately
                    cash += gross_pnl - fee
                    net_pnl = gross_pnl - fee

                    trades.append(Trade(
                        bar_idx=bar_idx,
                        timestamp=bar["timestamp"],
                        symbol=symbol,
                        side="BUY" if buying else "SELL",
                        size_usd=trade_size,
                        fill_px=fill_px,
                        fee=fee,
                        old_position=old_pos,
                        new_position=tracker.position_usd,
                        realized_pnl=net_pnl,
                        signal=prev_signal.signal,
                        metadata={
                            "slippage_usd": slippage_usd,
                            **prev_signal.metadata,
                        },
                    ))

            # 2. Update MTM equity
            equity = cash + tracker.unrealized_pnl(mark_px)
            timestamps.append(bar["timestamp"])
            equities.append(equity)

            # 3. Generate signal for next bar
            prev_signal = self.strategy.generate_signal(
                symbol, df.iloc[: bar_idx + 1], equity
            )

            # Telemetry: record every signal with full state
            telemetry.record(
                bar_idx=bar_idx, timestamp=bar["timestamp"], symbol=symbol,
                bar_data={"open": bar["open"], "high": bar["high"],
                          "low": bar["low"], "close": bar["close"],
                          "volume": bar["volume"]},
                equity=equity, position_usd=tracker.position_usd, signal=prev_signal,
            )

        # Build equity curve DataFrame
        eq_series = pd.Series(equities, name="equity")
        dd_series = drawdown_series(eq_series)
        equity_curve = pd.DataFrame({
            "timestamp": timestamps,
            "equity": equities,
            "drawdown_pct": dd_series.values,
        })

        # Compute metrics
        m = compute_metrics(equity_curve, trades, initial_equity, interval=self.cfg.interval)

        start_date = str(df.iloc[0]["timestamp"].date()) if hasattr(df.iloc[0]["timestamp"], "date") else str(df.iloc[0]["timestamp"])
        end_date = str(df.iloc[-1]["timestamp"].date()) if hasattr(df.iloc[-1]["timestamp"], "date") else str(df.iloc[-1]["timestamp"])

        return BacktestResult(
            config=self.cfg,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            strategy_name=self.strategy.name,
            initial_equity=initial_equity,
            final_equity=m["final_equity"],
            total_return_pct=m["total_return_pct"],
            max_drawdown_pct=m["max_drawdown_pct"],
            max_drawdown_usd=m["max_drawdown_usd"],
            sharpe=m["sharpe"],
            sortino=m["sortino"],
            calmar=m["calmar"],
            total_trades=m["total_trades"],
            win_rate=m["win_rate"],
            avg_win_pct=m["avg_win_pct"],
            avg_loss_pct=m["avg_loss_pct"],
            profit_factor=m["profit_factor"],
            total_fees=m["total_fees"],
            total_slippage_est=m["total_slippage_est"],
            time_in_market_pct=m["time_in_market_pct"],
            avg_trade_duration_bars=m["avg_trade_duration_bars"],
            equity_curve=equity_curve,
            trades=trades,
            telemetry=telemetry,
        )
