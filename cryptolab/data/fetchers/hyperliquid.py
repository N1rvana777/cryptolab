"""Hyperliquid candleSnapshot fetcher (live/recent data)."""

import logging
import requests
import pandas as pd

from cryptolab.data.fetchers.base import BaseFetcher
from cryptolab.data.types import HL_SYMBOL_MAP, validate_ohlcv_schema

logger = logging.getLogger(__name__)

HL_BASE_URL = "https://api.hyperliquid.xyz"
MAX_CANDLES = 5000


class HyperliquidFetcher(BaseFetcher):
    source_name = "hl"

    def __init__(self, base_url: str = HL_BASE_URL):
        self.base_url = base_url

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> pd.DataFrame:
        hl_symbol = HL_SYMBOL_MAP.get(symbol, symbol)

        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": hl_symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/info",
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            candles = resp.json()
        except Exception as e:
            logger.error(f"HL fetch error for {symbol}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        if not isinstance(candles, list):
            logger.error(f"HL unexpected response type: {type(candles)}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        rows = []
        for c in candles:
            ts_ms = int(c["t"])
            if ts_ms < start_ms or ts_ms >= end_ms:
                continue
            rows.append({
                "timestamp": pd.Timestamp(ts_ms, unit="ms", tz="UTC"),
                "open": float(c["o"]),
                "high": float(c["h"]),
                "low": float(c["l"]),
                "close": float(c["c"]),
                "volume": float(c.get("v", 0) or 0),
            })

        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(rows)
        df = df.sort_values("timestamp").drop_duplicates(subset="timestamp").reset_index(drop=True)
        return validate_ohlcv_schema(df)
