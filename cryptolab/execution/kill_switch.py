"""实盘交易熔断机制（Kill Switch）。

三级状态:
- NORMAL: 正常交易
- REDUCE_ONLY: 只允许平仓，不允许开新仓（API连续失败3次触发）
- HALTED: 紧急平仓所有仓位，完全停止（手动kill文件触发）

触发条件:
- 连续3次API超时或5xx错误 → REDUCE_ONLY
- K线数据包含NaN → REDUCE_ONLY
- 在项目根目录创建 KILL 文件 → HALTED（紧急用，手动创建即可）

自动恢复: REDUCE_ONLY状态下，如果连续30分钟API正常，自动恢复到NORMAL。
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cryptolab.execution.position_manager import PositionManager

logger = logging.getLogger(__name__)


class SystemMode(Enum):
    NORMAL = "NORMAL"
    REDUCE_ONLY = "REDUCE_ONLY"
    HALTED = "HALTED"


@dataclass
class HealthState:
    """Tracks API health and failure counts."""
    consecutive_api_failures: int = 0
    consecutive_data_errors: int = 0
    total_api_failures: int = 0
    total_data_errors: int = 0
    last_failure_time: float = 0.0
    last_failure_reason: str = ""
    mode: SystemMode = SystemMode.NORMAL
    mode_changed_at: float = 0.0
    emergency_flatten_attempted: bool = False


class KillSwitch:
    """Monitors system health and triggers emergency procedures.

    Usage:
        ks = KillSwitch(position_manager, max_api_failures=3)

        # Wrap every API call:
        try:
            data = api_call()
            ks.record_success()
        except Exception as e:
            ks.record_api_failure(str(e))

        # Check before trading:
        if not ks.is_trading_allowed():
            continue  # skip this cycle

        # Validate candle data:
        ks.validate_candles(df)
    """

    def __init__(
        self,
        position_manager: Optional["PositionManager"] = None,
        max_api_failures: int = 3,
        max_data_errors: int = 2,
        sentinel_path: Optional[str] = None,
        cooldown_minutes: int = 30,
    ):
        self.pm = position_manager
        self.max_api_failures = max_api_failures
        self.max_data_errors = max_data_errors
        self.sentinel_path = sentinel_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "KILL_SWITCH"
        )
        self.cooldown_seconds = cooldown_minutes * 60
        self.health = HealthState()

    @property
    def mode(self) -> SystemMode:
        return self.health.mode

    def is_trading_allowed(self) -> bool:
        """Check if new trades are allowed (not in REDUCE_ONLY or HALTED)."""
        # Check file sentinel
        if os.path.exists(self.sentinel_path):
            if self.health.mode == SystemMode.NORMAL:
                logger.critical("[KILL_SWITCH] Sentinel file detected — entering HALTED mode")
                self._enter_mode(SystemMode.HALTED, "sentinel_file")
                self._emergency_flatten("sentinel_file_detected")
            return False

        return self.health.mode == SystemMode.NORMAL

    def is_reduce_only(self) -> bool:
        """Check if system is in REDUCE_ONLY mode (can close but not open)."""
        return self.health.mode == SystemMode.REDUCE_ONLY

    def record_success(self):
        """Record a successful API call — resets consecutive failure counter."""
        self.health.consecutive_api_failures = 0
        self.health.consecutive_data_errors = 0

        # Auto-recover from REDUCE_ONLY after cooldown
        if self.health.mode == SystemMode.REDUCE_ONLY:
            elapsed = time.time() - self.health.mode_changed_at
            if elapsed >= self.cooldown_seconds:
                logger.info(
                    f"[KILL_SWITCH] Cooldown elapsed ({elapsed:.0f}s), "
                    f"recovering to NORMAL mode"
                )
                self._enter_mode(SystemMode.NORMAL, "cooldown_recovery")

    def record_api_failure(self, reason: str = ""):
        """Record an API failure (timeout, 5xx, connection error)."""
        self.health.consecutive_api_failures += 1
        self.health.total_api_failures += 1
        self.health.last_failure_time = time.time()
        self.health.last_failure_reason = reason
        logger.warning(
            f"[KILL_SWITCH] API failure #{self.health.consecutive_api_failures}: {reason}"
        )

        if self.health.consecutive_api_failures >= self.max_api_failures:
            self._trigger_emergency(f"api_failures_x{self.health.consecutive_api_failures}: {reason}")

    def validate_candles(self, candles_df) -> bool:
        """Validate candle data for NaN/missing values. Returns True if clean."""
        import pandas as pd
        import numpy as np

        if candles_df is None or (isinstance(candles_df, pd.DataFrame) and candles_df.empty):
            self.health.consecutive_data_errors += 1
            self.health.total_data_errors += 1
            logger.error("[KILL_SWITCH] Empty candle data received")
            if self.health.consecutive_data_errors >= self.max_data_errors:
                self._trigger_emergency("empty_candle_data")
            return False

        if isinstance(candles_df, pd.DataFrame):
            ohlcv_cols = ["open", "high", "low", "close"]
            existing_cols = [c for c in ohlcv_cols if c in candles_df.columns]
            if candles_df[existing_cols].isna().any().any():
                nan_counts = candles_df[existing_cols].isna().sum()
                self.health.consecutive_data_errors += 1
                self.health.total_data_errors += 1
                logger.error(f"[KILL_SWITCH] NaN in candle data: {nan_counts.to_dict()}")
                if self.health.consecutive_data_errors >= self.max_data_errors:
                    self._trigger_emergency("nan_in_candles")
                return False

        elif isinstance(candles_df, list):
            for i, c in enumerate(candles_df):
                for key in ("o", "h", "l", "c"):
                    val = c.get(key)
                    if val is None:
                        self.health.consecutive_data_errors += 1
                        self.health.total_data_errors += 1
                        logger.error(f"[KILL_SWITCH] Missing {key} at candle index {i}")
                        if self.health.consecutive_data_errors >= self.max_data_errors:
                            self._trigger_emergency(f"missing_{key}_in_candle")
                        return False
                    try:
                        fv = float(val)
                        if fv != fv:  # NaN
                            raise ValueError("NaN")
                    except (ValueError, TypeError):
                        self.health.consecutive_data_errors += 1
                        self.health.total_data_errors += 1
                        logger.error(f"[KILL_SWITCH] Invalid {key}={val} at candle index {i}")
                        if self.health.consecutive_data_errors >= self.max_data_errors:
                            self._trigger_emergency(f"invalid_{key}_in_candle")
                        return False

        self.health.consecutive_data_errors = 0
        return True

    def _trigger_emergency(self, reason: str):
        """Trigger emergency flatten and enter REDUCE_ONLY."""
        if self.health.mode != SystemMode.NORMAL:
            return  # already in degraded mode

        logger.critical(f"[KILL_SWITCH] EMERGENCY TRIGGERED: {reason}")
        self._emergency_flatten(reason)
        self._enter_mode(SystemMode.REDUCE_ONLY, reason)

    def _emergency_flatten(self, reason: str):
        """Cancel all orders and market-close all positions."""
        if self.health.emergency_flatten_attempted:
            logger.warning("[KILL_SWITCH] Emergency flatten already attempted this cycle")
            return

        self.health.emergency_flatten_attempted = True
        logger.critical(f"[KILL_SWITCH] EMERGENCY FLATTEN — reason: {reason}")

        if self.pm is None:
            logger.error("[KILL_SWITCH] No PositionManager — cannot flatten!")
            return

        # Step 1: Cancel all open orders
        try:
            if hasattr(self.pm, 'exchange') and hasattr(self.pm.exchange, 'cancel_all_orders'):
                self.pm.exchange.cancel_all_orders()
                logger.info("[KILL_SWITCH] All open orders cancelled")
        except Exception as e:
            logger.error(f"[KILL_SWITCH] Failed to cancel orders: {e}")

        # Step 2: Refresh state and close all positions
        try:
            if self.pm.refresh_state():
                results = self.pm.close_all(reason=f"emergency_{reason}")
                for symbol, record in results.items():
                    if record.status in ("ok", "dry_run"):
                        logger.info(f"[KILL_SWITCH] Closed {symbol}: {record.fill_size} @ {record.avg_fill_px}")
                    else:
                        logger.error(f"[KILL_SWITCH] Failed to close {symbol}: {record.error}")
            else:
                logger.error("[KILL_SWITCH] Cannot refresh state for emergency flatten")
        except Exception as e:
            logger.error(f"[KILL_SWITCH] Emergency flatten failed: {e}")

    def _enter_mode(self, mode: SystemMode, reason: str):
        """Transition to a new system mode."""
        old_mode = self.health.mode
        self.health.mode = mode
        self.health.mode_changed_at = time.time()
        logger.critical(f"[KILL_SWITCH] Mode: {old_mode.value} -> {mode.value} (reason: {reason})")

    def reset(self):
        """Manually reset to NORMAL mode (use after investigating the issue)."""
        logger.info("[KILL_SWITCH] Manual reset to NORMAL")
        self.health = HealthState()

    def status_dict(self) -> dict:
        """Return current health status as a dict for logging/monitoring."""
        return {
            "mode": self.health.mode.value,
            "consecutive_api_failures": self.health.consecutive_api_failures,
            "consecutive_data_errors": self.health.consecutive_data_errors,
            "total_api_failures": self.health.total_api_failures,
            "total_data_errors": self.health.total_data_errors,
            "last_failure_reason": self.health.last_failure_reason,
            "emergency_flatten_attempted": self.health.emergency_flatten_attempted,
        }
