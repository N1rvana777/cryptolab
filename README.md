# CryptoLab

Quantitative trading research and execution for crypto perpetual swaps.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
python scripts/seed_cache.py  # download historical data
```

## Structure

- `cryptolab/` — main package (data, indicators, strategy, backtest, execution)
- `data/cache/` — parquet cache (gitignored)
- `runs/` — backtest outputs (gitignored)
- `scripts/` — utility scripts
- `tests/` — test suite

## Data Sources

- **OKX perps** — primary historical source (perpetual swap klines, 2020+)
- **Binance spot** — cross-validation via Binance Vision API
- **Hyperliquid** — live/recent candle data
