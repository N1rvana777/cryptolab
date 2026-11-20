# Changelog

## v2.0 — ML-Driven Signal System (2026-03-14)

**Why:** Professor feedback identified the biggest gap vs industry: lack of large-scale Machine Learning.
The v1 rule-based approach (hand-coded Donchian breakout) cannot scale — every new strategy requires
manual coding, parameter tuning, and trial-and-error backtesting. ML automates signal discovery
across hundreds of features simultaneously.

**Architecture Changes:**
- New `features/` package: 7 feature blocks producing ~97 features (technical, Donchian, microstructure, cross-asset, temporal, volatility, momentum)
- New `ml/` package: QuantileGBM (LightGBM/XGBoost quantile regression), Walk-Forward CV with embargo, drift detection, feature importance analysis
- New `portfolio/` package: Kelly-criterion position sizing from ML quantile predictions, portfolio-level risk budgeting
- New `strategy/ml_strategy.py`: MLStrategy(BaseStrategy) adapter — plugs ML into existing BacktestEngine and PositionManager with zero modifications
- LeakageGuard ported from RetailLab: prevents look-ahead bias with correlation checks, train/test temporal validation, embargo enforcement
- Base timeframe: 4H → 1H (4× more training data: ~790K samples vs ~200K)
- Data strategy: OKX 1H for ML training, Hyperliquid for live execution

**What's Preserved:**
- DonchianMTF strategy → now a feature input to the ML model (dc_mtf_agreement + 12 other Donchian features)
- BacktestEngine, PositionManager, execution layer — all unchanged
- All 83 original tests still passing

**Key Decisions:**
- Quantile regression (not point prediction): predicts return distribution, enabling risk-aware position sizing
- Walk-forward CV with embargo (not random KFold): prevents temporal leakage in time-series data
- MLStrategy inherits BaseStrategy: architectural compatibility, no rewrites needed

**Test Coverage:** 121 tests (83 original + 38 new)

---

## v1.0 — Rule-Based Trend Following (2026-03-05)

**What:** Built from scratch as a clean rewrite of the old crypto project.

**Components:**
- DonchianMTF strategy: multi-timeframe Donchian channel breakout with ATR trailing stops
- Multi-source data pipeline: OKX (primary historical), Binance (cross-validation), Hyperliquid (live)
- Backtest engine: next-bar-open fills, 3-layer look-ahead bias prevention, bootstrap Sharpe CI
- Live execution: Hyperliquid SDK integration, position manager, kill switch

**Results:**
- 4-coin portfolio (BTC/SOL/ADA/XRP): OOS Sharpe 0.86, MaxDD 6.06%, Return +12.89%
- Walk-forward validation: IS 2021-2023, OOS 2024-2026
- 10-coin screening → 4 survivors

**Test Coverage:** 83 tests
