# CryptoLab — Project Instructions

## BACKTESTING RULES — MANDATORY, NO EXCEPTIONS

These rules exist because violations have repeatedly produced misleading results. Every backtesting script MUST follow all of these. If any rule cannot be satisfied, STOP and ask before proceeding.

### Rule 1: Warmup data MUST come from BEFORE the test window, NEVER from within it

- If a strategy needs N bars of warmup (for indicators, rolling windows, PCA fits, OU estimation, etc.), those N bars MUST be loaded from BEFORE the test window start date.
- Example: Holdout starts 2025-07-01. Donchian needs 396 bars warmup. Data loading MUST start from 2025-07-01 minus 396 bars worth of calendar time (roughly 2025-02-18 for 8H bars), NOT from 2025-06-15.
- NEVER allow warmup to consume bars inside the test window. If the data available before the test window is insufficient for warmup, STOP and report which strategies cannot be tested, do not silently truncate the test window.

### Rule 2: Zero positions at test window start

- Every strategy MUST start the test window with zero positions and full cash.
- Warmup period: indicators are computed, NO trades are executed, NO positions are opened.
- The first bar of the test window is the first bar where trading is allowed.
- Print the position state at the first bar of the test window to confirm zero positions, as a sanity check.

### Rule 3: All strategies in a comparison MUST cover the exact same bars

- When comparing multiple strategies in one test, every strategy MUST start trading on the same date and end on the same date.
- The common trading window is determined by the strategy with the LONGEST warmup requirement.
- Print the first and last trading bar index and date for every strategy, and verify they match, before computing any metrics.

### Rule 4: Combo strategies MUST pass sanity checks

- For any weighted combination like A × w1 + B × w2, the combo return MUST equal the weighted average of the individual returns within floating point tolerance.
- Print the sanity check explicitly for every combo in every test output.
- If a sanity check fails, STOP and debug, do not proceed.

### Rule 5: Any new holdout or walk-forward test MUST reproduce previous known-good results

- Before trusting results from a new test script, verify at least one strategy produces the same number as a previous known-good run on the same time window.
- If results differ, STOP and find the discrepancy before proceeding to interpret new results.

### Rule 6: Report data coverage explicitly

- Every test output MUST include: data load start date, warmup end date, test window start date, test window end date, total trading bars in the test window.
- This is to make Rule 1 and Rule 3 violations immediately visible.

### Rule 7: Phase averaging must preserve test window coverage

- When running phase-averaged backtests, every phase MUST cover the full test window.
- Phase shift is achieved by adjusting which bar within the warmup period the strategy "activates", NOT by loading less data.
- For every phase, verify that the first trading bar is on or before the test window start date.

---

## Workflow
- At the start of each conversation, read `master-plan.md` from memory to understand current progress
- All backtest experiments auto-record to RESEARCH_LOG.md
- Architecture changes record to CHANGELOG.md
- Before modifying code, run existing tests to confirm nothing breaks
- Use Chinese for explanations when the user writes in Chinese

## Environment
- WSL is only used for tmux to keep sessions alive; actual dev environment is Windows
- Run code via `cmd.exe /c "cd /d C:\Users\n1rva\projects\cryptolab && python ..."`
- Run tests via `cmd.exe /c "cd /d C:\Users\n1rva\projects\cryptolab && python -m pytest tests/ -x -q"`

## Conventions
- Python 3.12, 1H base timeframe (features computed from 1H OHLCV)
- Strategy parameters go in Config dataclass (`cryptolab/config.py`)
- New strategies inherit BaseStrategy ABC (`cryptolab/strategy/base.py`)
- IS: 2021-2023, OOS: 2024-2026 — always validate on OOS before adopting changes
- Never commit .env, model weights, or files with secrets

## Architecture (v2.0 — ML-Driven)

### Core Pipeline
```
OKX 1H OHLCV → FeaturePipeline (~97 features) → QuantileGBM → PortfolioOptimizer → MLStrategy → BacktestEngine/Execution
```

### Key Packages
| Package | Role |
|---------|------|
| `features/` | Feature engineering: 7 blocks (technical, donchian, microstructure, cross_asset, temporal, volatility, momentum) |
| `ml/` | QuantileGBM model, WalkForwardSplitter, Trainer, Predictor, DriftDetector |
| `portfolio/` | Kelly position sizing, risk budgeting |
| `strategy/` | BaseStrategy ABC, DonchianMTF (legacy + feature input), MLStrategy (ML adapter) |
| `backtest/` | Engine, metrics, telemetry, bias audit |
| `data/` | DataManager, ParquetCache, OKX/Binance/HL fetchers |
| `execution/` | Hyperliquid client, position manager, kill switch |

### Critical Red Lines
- **LeakageGuard**: All features must use `.shift(1)` — no current-bar data in features
- **WalkForwardSplitter**: KFold is FORBIDDEN for time-series. Use walk-forward CV with embargo
- **Targets are NOT features**: `fwd_return_*` columns are training labels only, never in feature matrix
- **Drift detection**: Monitor directional accuracy; WARNING at 2σ, CRITICAL at 3σ

### Key Scripts
| Script | Purpose |
|--------|---------|
| `scripts/seed_cache.py` | Download 1H OHLCV data from OKX |
| `scripts/train_ml.py` | Train QuantileGBM with walk-forward CV |
| `scripts/evaluate_features.py` | Inspect feature matrix quality |
| `scripts/run_backtest.py` | Rule-based strategy backtest (DonchianMTF) |
| `scripts/run_portfolio.py` | Multi-symbol portfolio backtest |

## Current Status
- **v2.0 ML architecture**: Implemented (features, ml, portfolio, ml_strategy)
- **Legacy strategy**: DonchianMTF preserved as feature input to ML
- **Data**: Need to seed 1H data (run `seed_cache.py --interval 1h`)
- **Next step**: Seed 1H data → train first ML model → ML backtest
