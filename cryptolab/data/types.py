"""Symbol maps and canonical OHLCV schema definitions."""

from typing import Dict
import pandas as pd

# Canonical DataFrame columns — all fetchers must return this exact schema
OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
OHLCV_DTYPES = {
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "volume": "float64",
}

# --- Symbol mapping per exchange ---

# OKX perpetual swap instrument IDs
OKX_SYMBOL_MAP: Dict[str, str] = {
    "BTC": "BTC-USDT-SWAP",
    "ETH": "ETH-USDT-SWAP",
    "SOL": "SOL-USDT-SWAP",
    "DOGE": "DOGE-USDT-SWAP",
    "AVAX": "AVAX-USDT-SWAP",
    "LINK": "LINK-USDT-SWAP",
    "ARB": "ARB-USDT-SWAP",
    "SUI": "SUI-USDT-SWAP",
}

# Binance spot pairs (Vision API)
BINANCE_SYMBOL_MAP: Dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT",
    "ARB": "ARBUSDT",
    "SUI": "SUIUSDT",
}

# Hyperliquid — uses plain coin name
HL_SYMBOL_MAP: Dict[str, str] = {
    "BTC": "BTC",
    "ETH": "ETH",
    "SOL": "SOL",
    "DOGE": "DOGE",
    "AVAX": "AVAX",
    "LINK": "LINK",
    "ARB": "ARB",
    "SUI": "SUI",
}

# OKX interval format mapping
OKX_INTERVAL_MAP: Dict[str, str] = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H",
    "1d": "1D", "1w": "1W",
}

# Binance interval format mapping
BINANCE_INTERVAL_MAP: Dict[str, str] = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h",
    "1d": "1d", "1w": "1w",
}


def validate_ohlcv_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame has correct columns and dtypes."""
    for col in OHLCV_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    for col, dtype in OHLCV_DTYPES.items():
        df[col] = df[col].astype(dtype)
    return df[OHLCV_COLUMNS].copy()
