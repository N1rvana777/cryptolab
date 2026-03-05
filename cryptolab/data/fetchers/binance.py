"""Binance Vision spot klines fetcher (cross-validation source)."""

import time
import logging
import requests
import pandas as pd

from cryptolab.data.fetchers.base import BaseFetcher
from cryptolab.data.types import BINANCE_SYMBOL_MAP, BINANCE_INTERVAL_MAP, validate_ohlcv_schema

logger = logging.getLogger(__name__)

BINANCE_VISION_URL = "https://data-api.binance.vision"
MAX_CANDLES_PER_REQUEST = 1000


class BinanceFetcher(BaseFetcher):
    source_name = "binance"

    def __init__(self, base_url: str = BINANCE_VISION_URL):
        self.base_url = base_url

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> pd.DataFrame:
        bn_symbol = BINANCE_SYMBOL_MAP.get(symbol)
        if not bn_symbol:
            raise ValueError(f"Unknown symbol for Binance: {symbol}")
        bn_interval = BINANCE_INTERVAL_MAP.get(interval.lower())
        if not bn_interval:
            raise ValueError(f"Unknown interval for Binance: {interval}")

        all_rows = []
        cursor = start_ms

        while cursor < end_ms:
            params = {
                "symbol": bn_symbol,
                "interval": bn_interval,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": MAX_CANDLES_PER_REQUEST,
            }
            try:
                resp = requests.get(
                    f"{self.base_url}/api/v3/klines",
                    params=params,
                    timeout=15,
                )
                resp.raise_for_status()
                rows = resp.json()
            except Exception as e:
                logger.error(f"Binance fetch error for {symbol}: {e}")
                break

            if not rows:
                break

            # Each row: [openTime, o, h, l, c, vol, closeTime, quoteVol, trades, takerBuyBase, takerBuyQuote, ignore]
            for row in rows:
                ts_ms = int(row[0])
                all_rows.append({
                    "timestamp": pd.Timestamp(ts_ms, unit="ms", tz="UTC"),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                })

            # Move cursor past the last candle
            last_ts = int(rows[-1][0])
            if last_ts <= cursor:
                break
            cursor = last_ts + 1

            time.sleep(0.1)

        if not all_rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(all_rows)
        df = df.sort_values("timestamp").drop_duplicates(subset="timestamp").reset_index(drop=True)
        return validate_ohlcv_schema(df)
