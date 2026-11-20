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
    "XRP": "XRP-USDT-SWAP",
    "ADA": "ADA-USDT-SWAP",
    "DOT": "DOT-USDT-SWAP",
    "NEAR": "NEAR-USDT-SWAP",
    "MATIC": "MATIC-USDT-SWAP",
    "PEPE": "PEPE-USDT-SWAP",
    "OP": "OP-USDT-SWAP",
    "FIL": "FIL-USDT-SWAP",
    "APT": "APT-USDT-SWAP",
    "ATOM": "ATOM-USDT-SWAP",
    "BCH": "BCH-USDT-SWAP",
    "BNB": "BNB-USDT-SWAP",
    "LTC": "LTC-USDT-SWAP",
    "XLM": "XLM-USDT-SWAP",
    "XMR": "XMR-USDT-SWAP",
    "TRX": "TRX-USDT-SWAP",
    "ETC": "ETC-USDT-SWAP",
    "AAVE": "AAVE-USDT-SWAP",
    "UNI": "UNI-USDT-SWAP",
    "CRV": "CRV-USDT-SWAP",
    "EOS": "EOS-USDT-SWAP",
    "SAND": "SAND-USDT-SWAP",
    "MANA": "MANA-USDT-SWAP",
    "AXS": "AXS-USDT-SWAP",
    "FTM": "FTM-USDT-SWAP",
    "ALGO": "ALGO-USDT-SWAP",
    "HBAR": "HBAR-USDT-SWAP",
    "ICP": "ICP-USDT-SWAP",
    # Additional coins for expanded universe
    "FET": "FET-USDT-SWAP",
    "WLD": "WLD-USDT-SWAP",
    "SEI": "SEI-USDT-SWAP",
    "JTO": "JTO-USDT-SWAP",
    "TIA": "TIA-USDT-SWAP",
    "INJ": "INJ-USDT-SWAP",
    "RENDER": "RENDER-USDT-SWAP",
    "WIF": "WIF-USDT-SWAP",
    "JUP": "JUP-USDT-SWAP",
    "PENDLE": "PENDLE-USDT-SWAP",
    "DYDX": "DYDX-USDT-SWAP",
    "PYTH": "PYTH-USDT-SWAP",
    "STRK": "STRK-USDT-SWAP",
    "BLUR": "BLUR-USDT-SWAP",
    "ZRO": "ZRO-USDT-SWAP",
    "ZK": "ZK-USDT-SWAP",
    "RUNE": "RUNE-USDT-SWAP",
    "ONDO": "ONDO-USDT-SWAP",
    "ENA": "ENA-USDT-SWAP",
    "BONK": "BONK-USDT-SWAP",
    "SHIB": "SHIB-USDT-SWAP",
    "FLOKI": "FLOKI-USDT-SWAP",
    "LDO": "LDO-USDT-SWAP",
    "SNX": "SNX-USDT-SWAP",
    "IMX": "IMX-USDT-SWAP",
    "GALA": "GALA-USDT-SWAP",
    "APE": "APE-USDT-SWAP",
    "AR": "AR-USDT-SWAP",
    "STX": "STX-USDT-SWAP",
    "CELO": "CELO-USDT-SWAP",
    "ZEC": "ZEC-USDT-SWAP",
    "DASH": "DASH-USDT-SWAP",
    "GMT": "GMT-USDT-SWAP",
    "MINA": "MINA-USDT-SWAP",
    "SUSHI": "SUSHI-USDT-SWAP",
    "YGG": "YGG-USDT-SWAP",
    "MNT": "MNT-USDT-SWAP",
    "TON": "TON-USDT-SWAP",
    "KAS": "KAS-USDT-SWAP",
    "TAO": "TAO-USDT-SWAP",
    "ORDI": "ORDI-USDT-SWAP",
    "EIGEN": "EIGEN-USDT-SWAP",
    "PEOPLE": "PEOPLE-USDT-SWAP",
    "CAKE": "CAKE-USDT-SWAP",
    "ETHFI": "ETHFI-USDT-SWAP",
    "BSV": "BSV-USDT-SWAP",
    "IOTA": "IOTA-USDT-SWAP",
    "POL": "POL-USDT-SWAP",
    "MOVE": "MOVE-USDT-SWAP",
}

# Binance USDT-M perpetual pairs (Futures API)
BINANCE_SYMBOL_MAP: Dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT",
    "ARB": "ARBUSDT",
    "SUI": "SUIUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOT": "DOTUSDT",
    "NEAR": "NEARUSDT",
    "MATIC": "MATICUSDT",
    "PEPE": "PEPEUSDT",
    "OP": "OPUSDT",
    "FIL": "FILUSDT",
    "APT": "APTUSDT",
    "ATOM": "ATOMUSDT",
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
