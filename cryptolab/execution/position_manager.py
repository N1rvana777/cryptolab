"""Unified position management and execution.
The ONLY module allowed to call order functions.
"""

import time
import math
import logging
from typing import Dict, Optional
from dataclasses import dataclass

from cryptolab.utils import utc_ts, round_size, csv_append
from cryptolab.execution.hl_client import (
    get_equity_from_state, get_position_from_state, get_all_positions,
)

logger = logging.getLogger(__name__)


@dataclass
class OrderRecord:
    ts_utc: str
    symbol: str
    side: str
    size: float
    ref_px: float
    limit_px: float
    slippage_bps: float
    reduce_only: bool
    dry_run: bool
    status: str = ""
    fill_size: float = 0.0
    avg_fill_px: float = 0.0
    fees: float = 0.0
    order_id: str = ""
    error: str = ""


class PositionManager:
    """
    Unified position manager.
    - Reads current positions
    - Computes delta (target vs actual)
    - Executes IOC limit orders
    - Logs all orders to CSV
    """

    def __init__(self, cfg, exchange, info, account_address: str, run_dir: str):
        self.cfg = cfg
        self.exchange = exchange
        self.info = info
        self.account_address = account_address
        self.run_dir = run_dir

        self._cached_state: Optional[dict] = None
        self._cached_equity: float = 0.0
        self._sz_decimals: Dict[str, int] = {}
        self._leverage_map: Dict[str, float] = {}
        self._ctx_map: Dict[str, dict] = {}

        self._entry_prices: Dict[str, float] = {}
        self._last_fail_ts: Dict[str, float] = {}

        import os
        self._orders_csv = os.path.join(run_dir, "orders.csv")
        self._fills_csv = os.path.join(run_dir, "fills.csv")

    # --- Initialization ---

    def init_asset_info(self, universe_map: dict, ctx_map: dict):
        cfg = self.cfg
        for sym in cfg.symbols:
            if sym not in universe_map:
                logger.error(f"[PM] {sym} not found in universe!")
                continue
            self._sz_decimals[sym] = int(universe_map[sym].get("szDecimals", 0))
            max_lev = float(universe_map[sym].get("maxLeverage", 1))
            target_lev = cfg.max_leverage.get(sym, cfg.leverage)
            self._leverage_map[sym] = min(float(target_lev), max_lev)
        self._ctx_map = ctx_map

    def setup_leverage(self):
        for sym, lev in self._leverage_map.items():
            try:
                lev_int = max(1, int(lev))
                self.exchange.update_leverage(leverage=lev_int, name=sym, is_cross=True)
                logger.info(f"[PM] Leverage set: {sym} = {lev_int}x (cross)")
            except Exception as e:
                logger.warning(f"[PM] update_leverage {sym} failed: {e}")

    # --- State reading ---

    def refresh_state(self) -> bool:
        try:
            self._cached_state = self.info.user_state(self.account_address)
            self._cached_equity = get_equity_from_state(self._cached_state)
            return True
        except Exception as e:
            logger.error(f"[PM] refresh_state failed: {e}")
            return False

    def update_ctx_map(self, ctx_map: dict):
        self._ctx_map = ctx_map

    @property
    def equity(self) -> float:
        return self._cached_equity

    @property
    def state(self) -> Optional[dict]:
        return self._cached_state

    def get_position(self, symbol: str) -> Optional[dict]:
        return get_position_from_state(self._cached_state, symbol)

    def get_position_size(self, symbol: str) -> float:
        pos = self.get_position(symbol)
        if pos is None:
            return 0.0
        return float(pos.get("szi", 0))

    def get_position_usd(self, symbol: str) -> float:
        return self.get_position_size(symbol) * self._get_mark_px(symbol)

    def get_entry_px(self, symbol: str) -> Optional[float]:
        pos = self.get_position(symbol)
        if pos and pos.get("entryPx"):
            px = float(pos["entryPx"])
            self._entry_prices[symbol] = px
            return px
        return self._entry_prices.get(symbol)

    def get_all_position_usd(self) -> Dict[str, float]:
        result = {}
        if self._cached_state:
            positions = get_all_positions(self._cached_state)
            for coin, pos in positions.items():
                szi = float(pos.get("szi", 0))
                result[coin] = szi * self._get_mark_px(coin)
        return result

    # --- Target execution ---

    def execute_targets(
        self,
        targets: Dict[str, float],
        reasons: Optional[Dict[str, str]] = None,
        order_types: Optional[Dict[str, str]] = None,
    ) -> Dict[str, OrderRecord]:
        if not self._cached_state:
            logger.error("[PM] execute_targets called without refreshed state")
            return {}

        reasons = reasons or {}
        order_types = order_types or {}
        results: Dict[str, OrderRecord] = {}
        now_s = int(time.time())

        for symbol, target_usd in targets.items():
            if (now_s - self._last_fail_ts.get(symbol, 0)) < self.cfg.fail_cooldown_sec:
                continue

            mark = self._get_mark_px(symbol)
            if mark <= 0:
                logger.warning(f"[PM] {symbol} mark_px=0, skip")
                continue

            current_size = self.get_position_size(symbol)
            current_usd = current_size * mark
            delta_usd = target_usd - current_usd
            is_closing = (target_usd == 0 and abs(current_size) > 0)

            if not is_closing:
                tolerance = max(self.cfg.min_notional_usd, abs(target_usd) * 0.03)
                if abs(delta_usd) < tolerance:
                    continue

            if not is_closing:
                lev = self._leverage_map.get(symbol, float(self.cfg.leverage))
                max_notional = self._cached_equity * lev
                if abs(target_usd) > max_notional * 1.05:
                    target_usd = max_notional if target_usd > 0 else -max_notional
                    delta_usd = target_usd - current_usd

            sz_dec = self._sz_decimals.get(symbol, 0)
            if is_closing:
                delta_size = round_size(abs(current_size), sz_dec)
            else:
                delta_size = round_size(abs(delta_usd) / mark, sz_dec)
            if delta_size <= 0:
                continue

            is_buy = delta_usd > 0
            reduce_only = False

            if current_size > 0 and not is_buy:
                reduce_only = True
                delta_size = min(delta_size, abs(current_size))
            elif current_size < 0 and is_buy:
                reduce_only = True
                delta_size = min(delta_size, abs(current_size))

            if not is_closing:
                notional = delta_size * mark
                if notional < self.cfg.min_notional_usd:
                    continue

            reason = reasons.get(symbol, "target_exec")
            otype = order_types.get(symbol, "taker")

            record = self._send_order(
                symbol, is_buy, delta_size, mark,
                reduce_only=reduce_only, reason=reason, order_type=otype,
            )
            results[symbol] = record

            if record.fill_size > 0 and not reduce_only and record.status in ("ok", "dry_run"):
                fill_px = record.avg_fill_px if record.avg_fill_px > 0 else mark
                old_entry = self._entry_prices.get(symbol)
                old_size = abs(current_size)
                if old_entry and old_size > 0:
                    new_total = old_size + record.fill_size
                    self._entry_prices[symbol] = (old_entry * old_size + fill_px * record.fill_size) / new_total
                else:
                    self._entry_prices[symbol] = fill_px

            if is_closing and record.fill_size > 0 and record.status in ("ok", "dry_run"):
                if not self.cfg.dry_run:
                    time.sleep(0.3)
                    self.refresh_state()
                    remaining = abs(self.get_position_size(symbol))
                    if remaining > 0:
                        retry = self._send_order(
                            symbol, current_size < 0, round_size(remaining, sz_dec),
                            self._get_mark_px(symbol), reduce_only=True,
                            reason="dust_cleanup", order_type="taker",
                        )
                        if retry.fill_size > 0:
                            logger.info(f"[DUST_CLEANED] {symbol}")
                self._entry_prices.pop(symbol, None)

        return results

    def close_all(self, reason: str = "close_all") -> Dict[str, OrderRecord]:
        targets = {}
        if self._cached_state:
            positions = get_all_positions(self._cached_state)
            for coin in positions:
                targets[coin] = 0.0
        return self.execute_targets(targets, {c: reason for c in targets})

    # --- Order execution ---

    def _send_order(
        self, symbol: str, is_buy: bool, size: float, ref_px: float,
        reduce_only: bool = False, reason: str = "", order_type: str = "taker",
    ) -> OrderRecord:
        cfg = self.cfg
        side = "BUY" if is_buy else "SELL"

        if order_type == "maker":
            maker_offset_bps = 5.0
            limit_px = ref_px * (1 - maker_offset_bps / 10000.0) if is_buy else ref_px * (1 + maker_offset_bps / 10000.0)
            slippage = maker_offset_bps
        else:
            slippage = cfg.slippage_bps
            limit_px = ref_px * (1 + slippage / 10000.0) if is_buy else ref_px * (1 - slippage / 10000.0)
        limit_px = self._round_px(limit_px)

        record = OrderRecord(
            ts_utc=utc_ts(), symbol=symbol, side=side, size=size,
            ref_px=ref_px, limit_px=limit_px, slippage_bps=slippage,
            reduce_only=reduce_only, dry_run=cfg.dry_run,
        )

        if cfg.dry_run:
            logger.info(f"[DRY_RUN] {side} {symbol} size={size} px~{limit_px:.4f} reason={reason}")
            record.status = "dry_run"
            record.fill_size = size
            record.avg_fill_px = ref_px
        else:
            try:
                order_params = {"limit": {"tif": "Alo" if order_type == "maker" else "Ioc"}}
                out = self.exchange.order(
                    symbol, is_buy, size, limit_px, order_params, reduce_only=reduce_only,
                )
                if out.get("status") == "ok":
                    statuses = out.get("response", {}).get("data", {}).get("statuses", [])
                    if statuses and isinstance(statuses[0], dict) and "filled" in statuses[0]:
                        filled = statuses[0]["filled"]
                        record.status = "ok"
                        record.fill_size = float(filled.get("totalSz", 0))
                        record.avg_fill_px = float(filled.get("avgPx", 0))
                        record.order_id = str(filled.get("oid", ""))
                    elif statuses and isinstance(statuses[0], dict) and "resting" in statuses[0]:
                        record.status = "resting"
                        record.order_id = str(statuses[0]["resting"].get("oid", ""))
                    elif statuses and isinstance(statuses[0], str):
                        record.status = "error"
                        record.error = statuses[0]
                        self._last_fail_ts[symbol] = int(time.time())
                    else:
                        record.status = "unknown"
                else:
                    err = out.get("response", {}).get("data", {}).get("statuses", [{}])
                    record.status = "error"
                    record.error = err[0].get("error", str(out)) if err else str(out)
                    self._last_fail_ts[symbol] = int(time.time())
            except Exception as e:
                record.status = "exception"
                record.error = str(e)
                self._last_fail_ts[symbol] = int(time.time())

        self._log_order(record)
        if record.status in ("ok", "dry_run") and record.fill_size > 0:
            self._log_fill(record, ref_px, order_type=order_type)

        return record

    # --- CSV logging ---

    def _log_order(self, r: OrderRecord):
        csv_append(
            self._orders_csv,
            ["ts_utc", "symbol", "side", "size", "ref_px", "limit_px",
             "slippage_bps", "reduce_only", "dry_run", "status", "error"],
            [r.ts_utc, r.symbol, r.side, f"{r.size}", f"{r.ref_px:.6f}",
             f"{r.limit_px:.6f}", f"{r.slippage_bps}", r.reduce_only,
             r.dry_run, r.status, r.error],
        )

    def _log_fill(self, r: OrderRecord, mid_px: float, order_type: str = "taker"):
        slippage_realized = abs(r.avg_fill_px - mid_px) / mid_px * 10000 if mid_px > 0 else 0
        fee_rate = 0.0001 if order_type == "maker" else 0.00035
        est_fees = r.fill_size * r.avg_fill_px * fee_rate
        csv_append(
            self._fills_csv,
            ["ts_utc", "symbol", "side", "filled_size", "avg_fill_px",
             "mid_px", "slippage_bps_realized", "est_fees_usd", "order_id", "status"],
            [r.ts_utc, r.symbol, r.side, f"{r.fill_size}",
             f"{r.avg_fill_px:.6f}", f"{mid_px:.6f}",
             f"{slippage_realized:.2f}", f"{est_fees:.4f}", r.order_id, r.status],
        )

    # --- Helpers ---

    @staticmethod
    def _round_px(px: float, sig_figs: int = 5) -> float:
        if px <= 0:
            return px
        magnitude = math.floor(math.log10(abs(px)))
        decimals = max(0, sig_figs - 1 - magnitude)
        return round(px, decimals)

    def _get_mark_px(self, symbol: str) -> float:
        ctx = self._ctx_map.get(symbol, {})
        try:
            return float(ctx.get("markPx", 0))
        except (TypeError, ValueError):
            return 0.0

    def get_leverage(self, symbol: str) -> float:
        return self._leverage_map.get(symbol, float(self.cfg.leverage))
