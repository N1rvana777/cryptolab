"""Binance USDT-M perpetual klines fetcher (cross-validation source).

Tries Futures API (fapi) first; falls back to spot (api) if geo-restricted.
"""

import time
import logging
import requests
import pandas as pd

from cryptolab.data.fetchers.base import BaseFetcher
from cryptolab.data.types import BINANCE_SYMBOL_MAP, BINANCE_INTERVAL_MAP, validate_ohlcv_schema

logger = logging.getLogger(__name__)

# Preferred: USDT-M Futures. Fallback: spot (for geo-restricted regions).
BINANCE_FUTURES_URL = "https://fapi.binance.com"
BINANCE_SPOT_URL = "https://data-api.binance.vision"
MAX_CANDLES_PER_REQUEST = 1000


class BinanceFetcher(BaseFetcher):
    source_name = "binance"

    def __init__(self):
        self.base_url = None  # auto-detect on first call
        self.endpoint = None

    def _detect_endpoint(self, bn_symbol: str, bn_interval: str) -> None:
        """Try futures first, fall back to spot if 451/403."""
        params = {"symbol": bn_symbol, "interval": bn_interval, "limit": 1}
        try:
            resp = requests.get(
                f"{BINANCE_FUTURES_URL}/fapi/v1/klines",
                params=params, timeout=10,
            )
            if resp.status_code == 200:
                self.base_url = BINANCE_FUTURES_URL
                self.endpoint = "/fapi/v1/klines"
                logger.info("Binance: using Futures API (perp data)")
                return
        except Exception:
            pass

        self.base_url = BINANCE_SPOT_URL
        self.endpoint = "/api/v3/klines"
        logger.warning("Binance Futures API blocked (geo-restricted). Falling back to spot data.")

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

        if self.base_url is None:
            self._detect_endpoint(bn_symbol, bn_interval)

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
                    f"{self.base_url}{self.endpoint}",
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
