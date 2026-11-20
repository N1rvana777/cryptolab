"""Portfolio Manager: regime-based strategy allocation across coins.

Sits between Strategy layer and Execution layer. For each coin, reads ADX
to determine regime (trending vs ranging), then routes capital to the
appropriate strategy.

Hysteresis logic prevents frequent switching:
- Trending -> Ranging: ADX must drop below 18 (not 20)
- Ranging -> Trending: ADX must rise above 27 (not 25)
- Minimum 10 bars (80h) before re-switching
- On switch: existing positions held until natural exit (stop/signal)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.strategy.donchian_mtf import _compute_adx

logger = logging.getLogger(__name__)


@dataclass
class CoinAllocation:
    """Per-coin regime detection and strategy allocation result."""
    symbol: str
    adx: Optional[float]
    regime: str            # "trending", "ranging"
    donchian_weight: float # 0.0 or 1.0
    meanrev_weight: float  # 0.0 or 1.0
    per_coin_equity: float # USD allocated to this coin
    bars_in_regime: int = 0
    switched: bool = False # True if regime changed this bar


@dataclass
class PMDecision:
    """Full PM decision for one cycle."""
    timestamp: str
    total_equity: float
    allocations: Dict[str, CoinAllocation]
    targets: Dict[str, float]       # final target positions per coin
    strategy_sources: Dict[str, str] # which strategy generated each target


class PortfolioManager:
    """Regime-based multi-strategy portfolio manager with hysteresis.

    Hysteresis thresholds (prevents whipsaw):
    - To enter trending: ADX must cross ABOVE adx_enter_trending (27)
    - To enter ranging:  ADX must cross BELOW adx_enter_ranging (18)
    - ADX between 18-27: keep current regime (no change)
    - Minimum hold: min_regime_bars (10) bars before allowing switch

    On regime switch, existing strategy positions are NOT force-closed.
    The old strategy continues to manage its open position (exits on
    stop/signal), while the new strategy starts accepting entry signals.
    """

    def __init__(
        self,
        cfg: Config,
        coins: List[str],
        donchian_strategies: Dict[str, BaseStrategy],
        meanrev_strategies: Dict[str, BaseStrategy],
        adx_enter_trending: float = 27.0,
        adx_enter_ranging: float = 18.0,
        min_regime_bars: int = 10,
        max_coin_pct: float = 0.15,
    ):
        self.cfg = cfg
        self.coins = coins
        self.donchian = donchian_strategies
        self.meanrev = meanrev_strategies
        self.adx_enter_trending = adx_enter_trending
        self.adx_enter_ranging = adx_enter_ranging
        self.min_regime_bars = min_regime_bars
        self.max_coin_pct = max_coin_pct

        # Per-coin regime state (persistent across calls)
        self._regime: Dict[str, str] = {c: "trending" for c in coins}
        self._bars_in_regime: Dict[str, int] = {c: 999 for c in coins}

    def _update_regime(self, coin: str, adx_val: Optional[float]) -> tuple[str, bool]:
        """Update regime for a coin with hysteresis.

        Returns (new_regime, switched_this_bar).
        """
        current = self._regime[coin]
        bars = self._bars_in_regime[coin]

        if adx_val is None:
            self._bars_in_regime[coin] = bars + 1
            return current, False

        switched = False

        if current == "trending":
            # Need ADX < enter_ranging AND held for min bars to switch
            if adx_val < self.adx_enter_ranging and bars >= self.min_regime_bars:
                self._regime[coin] = "ranging"
                self._bars_in_regime[coin] = 0
                switched = True
            else:
                self._bars_in_regime[coin] = bars + 1
        else:  # ranging
            # Need ADX > enter_trending AND held for min bars to switch
            if adx_val > self.adx_enter_trending and bars >= self.min_regime_bars:
                self._regime[coin] = "trending"
                self._bars_in_regime[coin] = 0
                switched = True
            else:
                self._bars_in_regime[coin] = bars + 1

        return self._regime[coin], switched

    def _compute_adx(self, df: pd.DataFrame) -> Optional[float]:
        """Compute current ADX from OHLCV data."""
        if df is None or len(df) < 60:
            return None
        highs = df["high"].tolist()
        lows = df["low"].tolist()
        closes = df["close"].tolist()
        return _compute_adx(highs, lows, closes, self.cfg.mtf_adx_period)

    def allocate(
        self,
        total_equity: float,
        market_data: Dict[str, pd.DataFrame],
        timestamp: str = "",
    ) -> PMDecision:
        """Determine regime and allocate capital for each coin.

        On regime switch, both strategies run: the old one manages its
        existing position (can only exit), the new one can open new positions.
        """
        n_coins = len(self.coins)
        base_per_coin = total_equity / n_coins if n_coins > 0 else 0
        max_per_coin = total_equity * self.max_coin_pct

        allocations: Dict[str, CoinAllocation] = {}
        targets: Dict[str, float] = {}
        strategy_sources: Dict[str, str] = {}

        for coin in self.coins:
            df = market_data.get(coin)
            adx_val = self._compute_adx(df)
            regime, switched = self._update_regime(coin, adx_val)
            per_coin_eq = min(base_per_coin, max_per_coin)

            if regime == "trending":
                don_w, mr_w = 1.0, 0.0
            else:
                don_w, mr_w = 0.0, 1.0

            allocations[coin] = CoinAllocation(
                symbol=coin, adx=adx_val, regime=regime,
                donchian_weight=don_w, meanrev_weight=mr_w,
                per_coin_equity=per_coin_eq,
                bars_in_regime=self._bars_in_regime[coin],
                switched=switched,
            )

            # Generate signals from strategies
            target = 0.0
            source = "HOLD"

            if df is not None and len(df) > 0:
                don_target = 0.0
                mr_target = 0.0

                # Active strategy gets full equity for new entries
                # Inactive strategy still runs to manage existing positions
                # (generate_signal will return HOLD or CLOSE for exits)

                if coin in self.donchian:
                    don_eq = per_coin_eq if don_w > 0 else per_coin_eq
                    try:
                        don_sig = self.donchian[coin].generate_signal(coin, df, don_eq)
                        if don_w > 0:
                            # Active: accept all signals
                            don_target = don_sig.target_position
                        else:
                            # Inactive: only accept exit signals (CLOSE)
                            if don_sig.signal == "CLOSE":
                                don_target = 0.0  # close position
                            elif don_sig.target_position != 0:
                                don_target = don_sig.target_position  # hold existing
                    except Exception as e:
                        logger.warning("[PM] %s donchian error: %s", coin, e)

                if coin in self.meanrev:
                    mr_eq = per_coin_eq if mr_w > 0 else per_coin_eq
                    try:
                        mr_sig = self.meanrev[coin].generate_signal(coin, df, mr_eq)
                        if mr_w > 0:
                            mr_target = mr_sig.target_position
                        else:
                            if mr_sig.signal == "CLOSE":
                                mr_target = 0.0
                            elif mr_sig.target_position != 0:
                                mr_target = mr_sig.target_position
                    except Exception as e:
                        logger.warning("[PM] %s meanrev error: %s", coin, e)

                target = don_target + mr_target

                if don_target != 0 and mr_target != 0:
                    source = "BOTH"
                elif don_target != 0:
                    source = "DON"
                elif mr_target != 0:
                    source = "MR"

            targets[coin] = target
            strategy_sources[coin] = source

            logger.info(
                "[PM] %s: ADX=%.1f regime=%s%s don_w=%.0f mr_w=%.0f "
                "target=$%.2f source=%s bars=%d",
                coin, adx_val or 0, regime,
                " [SWITCHED]" if switched else "",
                don_w, mr_w, target, source,
                self._bars_in_regime[coin],
            )

        return PMDecision(
            timestamp=timestamp,
            total_equity=total_equity,
            allocations=allocations,
            targets=targets,
            strategy_sources=strategy_sources,
        )

    def log_summary(self, decision: PMDecision) -> str:
        """Generate a human-readable summary of PM decision."""
        lines = [f"[PM] Equity=${decision.total_equity:.2f}, {len(decision.allocations)} coins"]
        n_trend = sum(1 for a in decision.allocations.values() if a.regime == "trending")
        n_range = sum(1 for a in decision.allocations.values() if a.regime == "ranging")
        switched = [a.symbol for a in decision.allocations.values() if a.switched]
        lines.append(f"[PM] Regimes: {n_trend} trending, {n_range} ranging")
        if switched:
            lines.append(f"[PM] Regime switches: {', '.join(switched)}")

        active = {k: v for k, v in decision.targets.items() if abs(v) > 0.01}
        if active:
            lines.append(f"[PM] Active positions: {len(active)}")
            for sym, tgt in sorted(active.items(), key=lambda x: abs(x[1]), reverse=True):
                src = decision.strategy_sources.get(sym, "?")
                alloc = decision.allocations.get(sym)
                adx_s = f"{alloc.adx:.1f}" if alloc and alloc.adx else "?"
                lines.append(f"[PM]   {sym}: ${tgt:+.2f} ({src}, ADX={adx_s})")

        return "\n".join(lines)
