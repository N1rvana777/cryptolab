# CryptoLab

Quantitative trading research and execution for crypto perpetual swaps.

> **Public snapshot.** This repository is a copy of a private working repository.
> Not included: API keys and wallet credentials (`.env`), market data and the local
> collection database (`data/`), trained model binaries (`models/**/*.joblib`),
> live-trading logs, large interactive chart exports, and a separate course project.
> To run it, copy `.env.example` to `.env` and download data with `scripts/seed_cache.py`.
> Licensed under the MIT License; see `LICENSE`.

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
