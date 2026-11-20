# CryptoLab

Quantitative trading research and execution for crypto perpetual swaps.

The project covers data collection, backtesting, machine-learning forecasts and live execution. Its main result is negative: under a strict holdout protocol, all 11 strategies and blends tested lost money.

> **Public snapshot.** This repository is a copy of a private working repository.
> Not included: API keys and wallet credentials (`.env`), market data and the local
> collection database (`data/`), trained model binaries (`models/**/*.joblib`),
> live-trading logs, large interactive chart exports, and a separate course project.
> To run it, copy `.env.example` to `.env` and download data with `scripts/seed_cache.py`.
> Licensed under the MIT License; see `LICENSE`.

## Overview

- **Data.** Hourly OKX perpetual-swap bars (cross-checked against Binance spot), Hyperliquid prices, funding rates and a daily sentiment index (Fear & Greed).
- **Backtester.** Signals at a bar's close fill at the next bar's open, with fees and slippage, and stops gap at the open. Bootstrap Sharpe intervals and regime splits check robustness.
- **Strategies.** Multi-timeframe Donchian trend following with ATR trailing stops and a regime filter. LightGBM and XGBoost quantile models on 138 lagged features in 10 blocks, validated walk-forward with an embargo and sized by fractional Kelly. Research scripts for about 15 other strategy families, including cross-sectional momentum, mean reversion, cointegration pairs, Ornstein-Uhlenbeck, PCA residuals and HMM regime switching.
- **Live execution.** The trend strategy traded real money on Hyperliquid for 11 days (25 March to 5 April 2026), with a kill switch, crash recovery and order logs.

## Findings

- **Coin selection.** Choosing coins with the holdout gave a Sharpe ratio of 4.18. Choosing them on validation data instead gave only 0.38.
- **Rebalance timing.** A cross-sectional momentum strategy's holdout Sharpe ranged from −1.16 to +1.04 across the 21 possible phases of its rebalance schedule.
- **Test rules.** After method bugs contaminated earlier holdout runs, seven rules became mandatory for every test (see `CLAUDE.md`). They include warm-up only before the test window, flat positions at its start and identical bars across compared strategies. Under these rules, all 11 strategies and blends lost money in the final holdout, July 2025 to March 2026 (best Sharpe −0.10).

The full record is in `RESEARCH_LOG.md`. Research closed in April 2026. Claude Code, an AI coding agent, wrote much of the code under my direction.

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
