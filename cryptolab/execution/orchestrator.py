"""DonchianMTF 实盘交易编排器。

主循环:
1. 等待4H K线收盘（每4小时: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC）
2. 拉取每个币种的最新K线数据
3. 调用 DonchianMTF.generate_signal() 生成信号
4. 通过 PositionManager 执行目标仓位
5. 记录 telemetry 和状态日志

安全机制:
- KillSwitch: API连续失败3次→REDUCE_ONLY, KILL_SWITCH文件→全部平仓
- DonchianMTF 内置: ATR trailing stop + 回撤缩仓 + 波动率目标
- Portfolio equity cap: 总仓位不超过 equity × leverage
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.donchian_mtf import DonchianMTF
from cryptolab.strategy.mean_reversion import MeanReversionZScore
from cryptolab.execution.portfolio_manager import PortfolioManager as StrategyPM
from cryptolab.backtest.telemetry import TelemetryRecorder, TelemetrySnapshot
from cryptolab.execution.hl_client import (
    init_hl_sdk,
    fetch_meta_and_asset_ctxs,
    build_perp_maps,
    get_closed_candles,
    HL_BASE_URL,
)
from cryptolab.execution.position_manager import PositionManager
from cryptolab.execution.kill_switch import KillSwitch, SystemMode
from cryptolab.utils import utc_ts, csv_append

logger = logging.getLogger(__name__)

# 4H candle boundaries (UTC hours)
CANDLE_HOURS_4H = {0, 4, 8, 12, 16, 20}
INTERVAL_SEC = 4 * 3600  # 4 hours


@dataclass
class SymbolConfig:
    """Per-symbol strategy config override."""
    symbol: str
    combo: str  # "G", "F", "B0", etc.
    lookbacks: list[int]
    # Mean reversion params (None = disabled)
    mr_lookback: int | None = None
    mr_entry_z: float = 2.0
    mr_exit_z: float = 0.25
    mr_stop_z: float = 3.5


# Combo definitions (same as run_backtest.py)
MTF_COMBO_MAP = {
    "A": [18, 48, 168],
    "B": [24, 72, 252],
    "C": [36, 96, 252],
    "D": [36, 72, 336],
    "E": [48, 120, 336],
    "F": [48, 168, 504],
    "G": [24, 72, 168],
    "H": [36, 120, 504],
    "B0": [36, 60, 336],  # 12d/20d/112d at 8H — B0 regime filter combo
}


class LiveOrchestrator:
    """实盘交易编排器。管理多币种 DonchianMTF 策略的完整生命周期。"""

    def __init__(
        self,
        cfg: Config,
        symbol_configs: list[SymbolConfig],
        run_dir: str,
        poll_interval_sec: int = 30,
        enable_pm: bool = False,
    ):
        self.cfg = cfg
        self.symbol_configs = {sc.symbol: sc for sc in symbol_configs}
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval_sec
        self.enable_pm = enable_pm

        # Per-symbol strategy instances
        self._strategies: Dict[str, DonchianMTF] = {}
        self._mr_strategies: Dict[str, MeanReversionZScore] = {}
        self._strategy_pm: Optional[StrategyPM] = None
        self._telemetry: Dict[str, TelemetryRecorder] = {}
        self._bar_counts: Dict[str, int] = {}

        # State
        self._last_candle_ts: Dict[str, int] = {}
        self._cycle_count = 0
        self._start_time = time.time()
        self._active_stops: Dict[str, float] = {}  # symbol -> stop price
        self._stop_triggered: Dict[str, bool] = {}  # prevent 4H cycle from re-opening

        # Logging
        self._state_csv = str(self.run_dir / "state_log.csv")
        self._equity_csv = str(self.run_dir / "equity_log.csv")

    def init(self):
        """Initialize SDK, position manager, kill switch, strategies."""
        logger.info("[ORCH] Initializing live trading system...")

        # SDK
        exchange, info, addr = init_hl_sdk()
        self._info = info

        # Position manager
        self.pm = PositionManager(
            self.cfg, exchange, info, addr, str(self.run_dir)
        )

        # Fetch universe info
        meta, ctxs = fetch_meta_and_asset_ctxs()
        universe_map, ctx_map = build_perp_maps(meta, ctxs)
        self.pm.init_asset_info(universe_map, ctx_map)
        self.pm.setup_leverage()

        # Kill switch
        self.ks = KillSwitch(
            position_manager=self.pm,
            max_api_failures=3,
            max_data_errors=2,
        )

        # Per-symbol strategies
        symbols = list(self.symbol_configs.keys())
        for sym, sc in self.symbol_configs.items():
            sym_cfg = replace(
                self.cfg,
                mtf_lookbacks=sc.lookbacks,
                mtf_weights=[0.33, 0.34, 0.33],
            )
            self._strategies[sym] = DonchianMTF(sym_cfg)
            self._telemetry[sym] = TelemetryRecorder()
            self._bar_counts[sym] = 0

            # Mean reversion strategy (if params provided)
            if sc.mr_lookback is not None:
                mr_cfg = replace(
                    self.cfg,
                    mr_zscore_lookback=sc.mr_lookback,
                    mr_entry_z=sc.mr_entry_z,
                    mr_exit_z=sc.mr_exit_z,
                    mr_stop_z=sc.mr_stop_z,
                )
                self._mr_strategies[sym] = MeanReversionZScore(mr_cfg)

        # Portfolio Manager (regime-based strategy allocation)
        if self.enable_pm and self._mr_strategies:
            self._strategy_pm = StrategyPM(
                cfg=self.cfg,
                coins=symbols,
                donchian_strategies=self._strategies,
                meanrev_strategies=self._mr_strategies,
            )
            logger.info("[ORCH] PM enabled: %d coins with MR strategies",
                        len(self._mr_strategies))

        # Refresh state
        if not self.pm.refresh_state():
            raise RuntimeError("Cannot connect to Hyperliquid — check credentials")

        equity = self.pm.equity
        positions = self.pm.get_all_position_usd()
        logger.info(
            "[ORCH] Initialized: equity=$%.2f, symbols=%s, positions=%s",
            equity, symbols, positions,
        )

        # Save run config
        run_info = {
            "start_time": utc_ts(),
            "symbols": {s: {"combo": sc.combo, "lookbacks": sc.lookbacks}
                        for s, sc in self.symbol_configs.items()},
            "leverage": self.cfg.leverage,
            "dry_run": self.cfg.dry_run,
            "initial_equity": equity,
        }
        (self.run_dir / "run_config.json").write_text(json.dumps(run_info, indent=2))

    def run_forever(self):
        """Main loop: poll for candle closes, generate signals, execute."""
        logger.info("[ORCH] Starting main loop (dry_run=%s)...", self.cfg.dry_run)

        # CRASH RECOVERY: if we have open positions, run a cycle immediately
        # to check stop losses — don't wait for next 4H candle
        self._crash_recovery_check()

        while True:
            try:
                now = datetime.now(timezone.utc)

                # Check if we just passed a 4H boundary
                if self._is_candle_close(now):
                    self._run_cycle()

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("[ORCH] Keyboard interrupt — shutting down")
                self._shutdown()
                break
            except Exception as e:
                logger.error("[ORCH] Unexpected error in main loop: %s", e, exc_info=True)
                self.ks.record_api_failure(f"main_loop: {e}")
                time.sleep(60)  # wait before retrying

    def _is_candle_close(self, now: datetime) -> bool:
        """Check if we're within 2 minutes after a 4H candle close."""
        if now.hour not in CANDLE_HOURS_4H:
            return False
        if now.minute > 2:
            return False

        # Prevent duplicate execution for same candle
        candle_key = f"{now.date()}_{now.hour}"
        if hasattr(self, '_last_candle_key') and self._last_candle_key == candle_key:
            return False
        self._last_candle_key = candle_key
        return True

    def _run_cycle(self):
        """Execute one trading cycle for all symbols."""
        self._cycle_count += 1
        cycle_ts = utc_ts()
        logger.info("[ORCH] === Cycle %d at %s ===", self._cycle_count, cycle_ts)

        # Refresh market data
        try:
            meta, ctxs = fetch_meta_and_asset_ctxs()
            _, ctx_map = build_perp_maps(meta, ctxs)
            self.pm.update_ctx_map(ctx_map)
            self.ks.record_success()
        except Exception as e:
            logger.error("[ORCH] Failed to fetch meta: %s", e)
            self.ks.record_api_failure(f"meta_fetch: {e}")
            return

        # Refresh account state
        if not self.pm.refresh_state():
            self.ks.record_api_failure("refresh_state_failed")
            return
        self.ks.record_success()

        equity = self.pm.equity
        per_symbol_equity = equity / len(self.symbol_configs)
        logger.info("[ORCH] Equity: $%.2f, per-symbol: $%.2f", equity, per_symbol_equity)

        # Check kill switch
        if not self.ks.is_trading_allowed():
            logger.warning("[ORCH] Trading not allowed (mode=%s)", self.ks.mode.value)
            self._log_equity(cycle_ts, equity, "BLOCKED")
            return

        # Generate signals and execute for each symbol
        targets: Dict[str, float] = {}
        reasons: Dict[str, str] = {}

        if self._strategy_pm is not None:
            # PM mode: fetch all candle data, let PM allocate
            market_data: Dict[str, pd.DataFrame] = {}
            for sym in self.symbol_configs:
                df = self._fetch_candles(sym)
                if df is not None:
                    market_data[sym] = df

            decision = self._strategy_pm.allocate(
                equity, market_data, cycle_ts)
            summary = self._strategy_pm.log_summary(decision)
            logger.info(summary)

            targets = decision.targets
            reasons = {sym: decision.strategy_sources.get(sym, "PM")
                       for sym in targets}

            # Log PM allocations to CSV
            pm_csv = str(self.run_dir / "pm_allocations.csv")
            for sym, alloc in decision.allocations.items():
                csv_append(
                    pm_csv,
                    ["timestamp", "symbol", "adx", "regime",
                     "don_weight", "mr_weight", "target_usd"],
                    [cycle_ts, sym, f"{alloc.adx:.1f}" if alloc.adx else "",
                     alloc.regime, alloc.donchian_weight, alloc.meanrev_weight,
                     f"{targets.get(sym, 0):.2f}"],
                )
        else:
            # Legacy mode: Donchian only
            for sym, sc in self.symbol_configs.items():
                try:
                    signal = self._generate_signal(sym, per_symbol_equity)
                    if signal is None:
                        continue

                    targets[sym] = signal.target_position
                    reasons[sym] = signal.signal

                    # Record stop price for inter-cycle monitoring
                    if signal.suggested_stop_px and signal.target_position != 0:
                        self._active_stops[sym] = signal.suggested_stop_px
                    elif signal.target_position == 0:
                        self._active_stops.pop(sym, None)

                    logger.info(
                        "[ORCH] %s: signal=%s, target=$%.2f, stop=%.2f, "
                        "meta=%s",
                        sym, signal.signal, signal.target_position,
                        signal.suggested_stop_px or 0,
                        {k: v for k, v in (signal.metadata or {}).items()
                         if k in ("agreement", "vol_scalar", "dd_scalar", "ann_vol",
                                  "trail_stop", "exit_reason",
                                  "regime_scale", "adx", "vol_10d", "vol_30d")},
                    )
                except Exception as e:
                    logger.error("[ORCH] Signal error for %s: %s", sym, e, exc_info=True)

        # Execute all targets atomically
        if targets:
            try:
                results = self.pm.execute_targets(targets, reasons)
                for sym, rec in results.items():
                    if rec.status in ("ok", "dry_run"):
                        logger.info(
                            "[FILL] %s %s %.4f @ %.4f (fee=$%.4f)",
                            rec.side, sym, rec.fill_size, rec.avg_fill_px, rec.fees,
                        )
                    else:
                        logger.error("[ORDER_FAIL] %s: %s", sym, rec.error)
                        self.ks.record_api_failure(f"order_{sym}: {rec.error}")
                self.ks.record_success()
            except Exception as e:
                logger.error("[ORCH] Execution error: %s", e, exc_info=True)
                self.ks.record_api_failure(f"execute: {e}")

        # Log state
        self._log_equity(cycle_ts, equity, "OK")
        self._log_state(cycle_ts, targets)

    def _fetch_candles(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV candles for a symbol. Returns DataFrame or None."""
        lookback = max(self.symbol_configs[symbol].lookbacks) + 50
        candles_raw = get_closed_candles(self._info, symbol, "4h", lookback)

        if not candles_raw:
            logger.warning("[ORCH] No candles for %s", symbol)
            return None
        if not self.ks.validate_candles(candles_raw):
            return None

        df = pd.DataFrame([{
            "timestamp": pd.Timestamp(int(c["t"]), unit="ms", tz="UTC"),
            "open": float(c["o"]),
            "high": float(c["h"]),
            "low": float(c["l"]),
            "close": float(c["c"]),
            "volume": float(c["v"]),
        } for c in candles_raw])
        return df

    def _generate_signal(self, symbol: str, equity: float):
        """Fetch candles and generate DonchianMTF signal for one symbol."""
        strategy = self._strategies[symbol]

        df = self._fetch_candles(symbol)
        if df is None:
            return None

        # Check for duplicate candle (same as last)
        latest_ts = int(df["timestamp"].iloc[-1].timestamp() * 1000)
        if self._last_candle_ts.get(symbol) == latest_ts:
            logger.debug("[ORCH] %s: same candle as last cycle, skip", symbol)
            return None
        self._last_candle_ts[symbol] = latest_ts

        # Generate signal
        signal = strategy.generate_signal(symbol, df, equity)

        # Record telemetry
        self._bar_counts[symbol] += 1
        bar = df.iloc[-1]
        self._telemetry[symbol].record(
            bar_idx=self._bar_counts[symbol],
            timestamp=str(bar["timestamp"]),
            symbol=symbol,
            bar_data=bar.to_dict(),
            equity=equity,
            position_usd=self.pm.get_position_usd(symbol),
            signal=signal,
        )

        return signal

    def _log_equity(self, ts: str, equity: float, status: str):
        """Append equity snapshot to CSV."""
        positions = self.pm.get_all_position_usd()
        pos_str = json.dumps({k: round(v, 2) for k, v in positions.items()})
        csv_append(
            self._equity_csv,
            ["timestamp", "equity", "positions", "status", "mode"],
            [ts, f"{equity:.2f}", pos_str, status, self.ks.mode.value],
        )

    def _log_state(self, ts: str, targets: Dict[str, float]):
        """Append cycle state to CSV."""
        csv_append(
            self._state_csv,
            ["timestamp", "cycle", "targets", "kill_switch"],
            [ts, self._cycle_count,
             json.dumps({k: round(v, 2) for k, v in targets.items()}),
             json.dumps(self.ks.status_dict())],
        )

    def _shutdown(self):
        """Clean shutdown: save telemetry, log final state."""
        logger.info("[ORCH] Shutting down...")

        # Save telemetry
        tel_dir = str(self.run_dir / "telemetry")
        for sym, recorder in self._telemetry.items():
            if recorder._snapshots:
                recorder.save_jsonl(tel_dir, sym, "live", "live")
                logger.info("[ORCH] Saved %d telemetry snapshots for %s",
                            len(recorder._snapshots), sym)

        # Log final state
        if self.pm.refresh_state():
            equity = self.pm.equity
            positions = self.pm.get_all_position_usd()
            logger.info(
                "[ORCH] Final state: equity=$%.2f, positions=%s, "
                "cycles=%d, uptime=%.0fs",
                equity, positions, self._cycle_count,
                time.time() - self._start_time,
            )

    def _check_stop_losses(self):
        """Check mark prices against active stop levels every poll cycle.

        Runs every 30 seconds. If mark price breaches the trailing stop,
        immediately closes the position — no need to wait for 4H cycle.
        """
        if not self._active_stops:
            return

        try:
            meta, ctxs = fetch_meta_and_asset_ctxs()
            _, ctx_map = build_perp_maps(meta, ctxs)
        except Exception:
            return  # silently skip on API error, KillSwitch handles retries

        for sym, stop_px in list(self._active_stops.items()):
            ctx = ctx_map.get(sym)
            if not ctx:
                continue

            mark_px = float(ctx.get("markPx", 0))
            if mark_px <= 0:
                continue

            pos_usd = self.pm.get_position_usd(sym)
            is_long = pos_usd > 0
            is_short = pos_usd < 0

            # Check breach: long stops below mark, short stops above mark
            breached = False
            if is_long and mark_px <= stop_px:
                breached = True
            elif is_short and mark_px >= stop_px:
                breached = True

            if breached:
                logger.critical(
                    "[STOP_LOSS] %s breached! mark=%.2f, stop=%.2f, pos=$%.2f — closing NOW",
                    sym, mark_px, stop_px, pos_usd,
                )

                # Refresh state and close
                try:
                    self.pm.refresh_state()
                    result = self.pm.execute_targets(
                        {sym: 0.0}, {sym: f"stop_loss_mark={mark_px:.2f}"}
                    )
                    rec = result.get(sym)
                    if rec and rec.status in ("ok", "dry_run"):
                        logger.critical(
                            "[STOP_LOSS] %s closed: %s %.4f @ %.4f",
                            sym, rec.side, rec.fill_size, rec.avg_fill_px,
                        )
                    self._active_stops.pop(sym, None)
                    self._stop_triggered[sym] = True
                    self._log_equity(utc_ts(), self.pm.equity, "STOP_LOSS")
                except Exception as e:
                    logger.error("[STOP_LOSS] Failed to close %s: %s", sym, e)

    def _crash_recovery_check(self):
        """On startup, if we have open positions, restore stop levels and check them.

        Does NOT re-run the full strategy (which would use incomplete candle data
        and could generate false signals). Instead:
        1. Detects open positions
        2. Fetches last known candle data to compute stop prices
        3. Registers stops for the 30-second monitor
        4. If stop is already breached, closes immediately
        5. Otherwise, holds position until the next proper 4H cycle
        """
        if not self.pm.refresh_state():
            logger.error("[RECOVERY] Cannot refresh state for crash recovery")
            return

        positions = self.pm.get_all_position_usd()
        if not positions:
            logger.info("[RECOVERY] No open positions -- no recovery needed")
            return

        logger.info(
            "[RECOVERY] Open positions detected: %s -- restoring stop levels",
            {k: f"${v:.2f}" for k, v in positions.items()},
        )

        # Fetch mark prices
        try:
            meta, ctxs = fetch_meta_and_asset_ctxs()
            _, ctx_map = build_perp_maps(meta, ctxs)
        except Exception as e:
            logger.error("[RECOVERY] Cannot fetch market data: %s", e)
            return

        for sym, pos_usd in positions.items():
            if sym not in self.symbol_configs:
                continue

            # Generate signal ONLY to get the stop price, not to trade
            try:
                signal = self._generate_signal(sym, abs(pos_usd))
                if signal and signal.suggested_stop_px:
                    self._active_stops[sym] = signal.suggested_stop_px
                    mark = float(ctx_map.get(sym, {}).get("markPx", 0))

                    # Check if stop is already breached
                    is_long = pos_usd > 0
                    is_short = pos_usd < 0
                    breached = (is_long and mark <= signal.suggested_stop_px) or \
                               (is_short and mark >= signal.suggested_stop_px)

                    if breached:
                        logger.critical(
                            "[RECOVERY] %s stop ALREADY BREACHED (mark=%.2f, stop=%.2f) -- closing",
                            sym, mark, signal.suggested_stop_px,
                        )
                        self.pm.execute_targets({sym: 0.0}, {sym: "recovery_stop_breached"})
                        self._active_stops.pop(sym, None)
                    else:
                        logger.info(
                            "[RECOVERY] %s stop restored: %.2f (mark=%.2f, safe)",
                            sym, signal.suggested_stop_px, mark,
                        )
                else:
                    logger.warning("[RECOVERY] %s: no stop price available, position unmanaged until next cycle", sym)

            except Exception as e:
                logger.error("[RECOVERY] %s signal error: %s", sym, e)

        logger.info("[RECOVERY] Recovery complete -- positions held, stops active")

    def run_once(self):
        """Execute a single cycle immediately (for testing)."""
        self._run_cycle()

    def status(self) -> dict:
        """Return current system status."""
        equity = self.pm.equity if self.pm._cached_state else 0
        return {
            "mode": self.ks.mode.value,
            "equity": equity,
            "cycles": self._cycle_count,
            "uptime_sec": time.time() - self._start_time,
            "positions": self.pm.get_all_position_usd() if self.pm._cached_state else {},
            "kill_switch": self.ks.status_dict(),
            "dry_run": self.cfg.dry_run,
        }
