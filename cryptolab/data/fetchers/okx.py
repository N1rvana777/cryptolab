"""OKX perpetual swap klines fetcher (primary historical source)."""

import time
import logging
import requests
import pandas as pd

from cryptolab.data.fetchers.base import BaseFetcher
from cryptolab.data.types import OKX_SYMBOL_MAP, OKX_INTERVAL_MAP, validate_ohlcv_schema

logger = logging.getLogger(__name__)

OKX_BASE_URL = "https://www.okx.com"
MAX_CANDLES_PER_REQUEST = 300


class OKXFetcher(BaseFetcher):
    source_name = "okx"

    def __init__(self, base_url: str = OKX_BASE_URL):
        self.base_url = base_url

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> pd.DataFrame:
        inst_id = OKX_SYMBOL_MAP.get(symbol)
        if not inst_id:
            raise ValueError(f"Unknown symbol for OKX: {symbol}")
        okx_interval = OKX_INTERVAL_MAP.get(interval.lower())
        if not okx_interval:
            raise ValueError(f"Unknown interval for OKX: {interval}")

        all_rows = []
        # OKX history-candles returns candles BEFORE the `after` timestamp, newest first.
        # We paginate backward from end_ms.
        cursor = end_ms

        while cursor > start_ms:
            params = {
                "instId": inst_id,
                "bar": okx_interval,
                "after": str(cursor),
                "limit": str(MAX_CANDLES_PER_REQUEST),
            }
            try:
                resp = requests.get(
                    f"{self.base_url}/api/v5/market/history-candles",
                    params=params,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"OKX fetch error for {symbol}: {e}")
                break

            if data.get("code") != "0":
                logger.error(f"OKX API error: {data.get('msg', data.get('code'))}")
                break

            rows = data.get("data", [])
            if not rows:
                break

            # Each row: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            for row in rows:
                ts_ms = int(row[0])
                if ts_ms < start_ms:
                    continue
                all_rows.append({
                    "timestamp": pd.Timestamp(ts_ms, unit="ms", tz="UTC"),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                })

            # Oldest candle in this batch — move cursor
            oldest_ts = int(rows[-1][0])
            if oldest_ts >= cursor:
                break  # no progress
            cursor = oldest_ts

            # Rate limit: OKX allows 20 req/2s for market endpoints
            time.sleep(0.15)

        if not all_rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(all_rows)
        df = df.sort_values("timestamp").drop_duplicates(subset="timestamp").reset_index(drop=True)
        return validate_ohlcv_schema(df)
