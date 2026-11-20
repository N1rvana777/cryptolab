"""Hyperliquid API封装。所有HL相关的网络请求都经过这里。

提供两层接口:
1. SDK层: init_hl_sdk() 初始化官方SDK，用于下单和账户查询
2. 裸API层: hl_info_post() 直接POST到/info端点，用于获取K线、funding rate等公开数据

凭证从.env文件加载: HL_PRIVATE_KEY（私钥）和HL_MAIN_ADDR（账户地址）。
"""

import os
import time
import logging
import requests
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

HL_BASE_URL = "https://api.hyperliquid.xyz"


def _load_env():
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        # Walk up to find .env
        d = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            env_path = os.path.join(d, ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                return
            d = os.path.dirname(d)
    except ImportError:
        pass


def get_hl_credentials() -> tuple:
    """Return (private_key, account_address) from environment. Raises if missing."""
    _load_env()
    pk = os.environ.get("HL_PRIVATE_KEY", "").strip()
    addr = os.environ.get("HL_MAIN_ADDR", "").strip()
    if not pk:
        raise EnvironmentError("HL_PRIVATE_KEY not set in environment or .env file")
    if not addr:
        raise EnvironmentError("HL_MAIN_ADDR not set in environment or .env file")
    return pk, addr


def init_hl_sdk():
    """Initialize and return (exchange, info, account_address) from hyperliquid SDK."""
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from eth_account import Account

    pk, addr = get_hl_credentials()
    wallet = Account.from_key(pk)
    info = Info(HL_BASE_URL, skip_ws=True)
    exchange = Exchange(wallet, HL_BASE_URL, account_address=addr)
    return exchange, info, addr


# --- Raw API helpers (no SDK dependency) ---

class APIError(Exception):
    """Raised when HL API returns a retriable error (5xx, timeout)."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def hl_info_post(base_url: str, payload: dict, timeout: int = 10) -> Any:
    try:
        r = requests.post(f"{base_url}/info", json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        raise APIError(f"Timeout after {timeout}s: {payload.get('type', '')}", status_code=0)
    except requests.exceptions.ConnectionError as e:
        raise APIError(f"Connection error: {e}", status_code=0)

    if r.status_code >= 500:
        raise APIError(f"Server error {r.status_code}: {r.text[:200]}", status_code=r.status_code)

    r.raise_for_status()
    return r.json()


def fetch_meta_and_asset_ctxs(base_url: str = HL_BASE_URL):
    resp = hl_info_post(base_url, {"type": "metaAndAssetCtxs"})
    if not isinstance(resp, list) or len(resp) != 2:
        raise ValueError(f"metaAndAssetCtxs bad shape: {type(resp)}")
    return resp[0], resp[1]


def build_perp_maps(meta: dict, asset_ctxs: list):
    universe = meta.get("universe", [])
    universe_map, ctx_map = {}, {}
    for i, u in enumerate(universe):
        name = u.get("name")
        if not name:
            continue
        universe_map[name] = u
        if i < len(asset_ctxs):
            ctx_map[name] = asset_ctxs[i]
    return universe_map, ctx_map


def get_closed_candles(info, symbol: str, interval: str, lookback: int) -> list:
    """Fetch closed OHLC candles from Hyperliquid (info.candles_snapshot)."""
    from cryptolab.utils import interval_to_ms
    now_ms = int(time.time() * 1000)
    iv_ms = interval_to_ms(interval)
    start_ms = now_ms - (lookback + 5) * iv_ms
    candles = info.candles_snapshot(symbol, interval, start_ms, now_ms)
    closed = [c for c in candles if int(c["t"]) + iv_ms <= now_ms - 1000]
    return closed[-lookback:]


def get_equity_from_state(state: dict) -> float:
    if not state or not isinstance(state, dict):
        return 0.0
    for key in ("crossMarginSummary", "marginSummary"):
        summary = state.get(key) or {}
        v = summary.get("accountValue")
        if v is not None:
            try:
                fv = float(v)
                if fv > 0:
                    return fv
            except (TypeError, ValueError):
                continue
    v = state.get("withdrawable")
    if v is not None:
        try:
            return max(0.0, float(v))
        except (TypeError, ValueError):
            pass
    return 0.0


def get_position_from_state(state: dict, symbol: str) -> Optional[dict]:
    if not state or not isinstance(state, dict):
        return None
    for p in state.get("assetPositions", []):
        pos = p.get("position", {})
        if pos.get("coin") == symbol:
            szi = pos.get("szi")
            if szi is not None and float(szi) != 0.0:
                return pos
    return None


def get_all_positions(state: dict) -> Dict[str, dict]:
    result = {}
    if not state or not isinstance(state, dict):
        return result
    for p in state.get("assetPositions", []):
        pos = p.get("position", {})
        coin = pos.get("coin")
        szi = pos.get("szi")
        if coin and szi is not None and float(szi) != 0.0:
            result[coin] = pos
    return result
