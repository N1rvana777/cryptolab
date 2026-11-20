# CryptoLab Architecture

## Overview

Quantitative cryptocurrency trading system with rule-based and ML strategy pipelines. Currently live-trading a Donchian Breakout strategy with regime detection on Hyperliquid across 22 crypto perpetual contracts.

```
                    ┌──────────────────────────────────────────────┐
                    │           Data Layer                         │
                    │  OKX/Binance/HL APIs → DataManager → Cache  │
                    │  Reddit/Orderbook → DataCollector → SQLite   │
                    └─────────────────┬────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              v                       v                       v
     ┌────────────────┐    ┌──────────────────┐    ┌──────────────────┐
     │  ML Pipeline   │    │  Rule-Based      │    │  Research        │
     │  (experimental)│    │  Strategy        │    │  Framework       │
     │                │    │  (production)    │    │                  │
     │  138 features  │    │  DonchianMTF     │    │  Walk-Forward CV │
     │  QuantileGBM   │    │  + Regime Filter │    │  Parameter Sweep │
     │  Walk-Forward  │    │  8H frequency    │    │  Cross-Asset     │
     └────────────────┘    └────────┬─────────┘    └──────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    v               v               v
             ┌───────────┐  ┌────────────┐  ┌────────────────┐
             │ Backtest   │  │ Live       │  │ Observability  │
             │ Engine     │  │ Trading    │  │ & Review       │
             │            │  │            │  │                │
             │ T+1 fills  │  │ Orchestr.  │  │ Equity curves  │
             │ Fees/slip  │  │ KillSwitch │  │ Slippage audit │
             │ Telemetry  │  │ HL SDK     │  │ Plotly charts  │
             └───────────┘  └────────────┘  └────────────────┘
```

---

## Production System (Live Trading)

### Strategy: DonchianMTF + Regime Filter (B0)

**Signal generation** (every 8H candle close):
1. Compute Donchian channels at 3 timeframes (12d / 20d / 112d lookback)
2. Score multi-timeframe agreement: weighted average of per-TF breakout signals
3. Apply regime filter (ADX + volatility contraction) to suppress choppy markets
4. Size position using volatility targeting and drawdown scaling

**Regime Filter** (reduces false breakout losses):
- ADX(20) >= 25 → full position (trending market)
- ADX(20) 20-25 → half position (uncertain)
- ADX(20) < 20 → no new positions (choppy)
- Vol contraction (10d std < 30d std × 0.7) → no new positions
- Only affects entries; exits (trailing stop, opposite breakout) are unaffected

**Position sizing**:
- Base: `equity × leverage × agreement_score`
- Vol scalar: `target_vol / realized_vol`, clamped to [0.5, 2.0]
- DD scalar: linearly reduces from 1.0 to 0.25 as drawdown approaches 30%
- Per-coin capital: equity / 22 coins

**Exit rules**:
- ATR trailing stop (2× ATR distance, updated each bar)
- Opposite Donchian breakout

### Execution Architecture

```
┌─────────────────────────────────────────────────────────┐
│  LiveOrchestrator (scripts/live_donchian.py)             │
│                                                          │
│  Main loop: poll every 30s, execute at 4H boundaries     │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ DonchianMTF │  │ PositionMgr  │  │ KillSwitch       │  │
│  │ Strategy  │  │              │  │                   │  │
│  │           │──>│ Execute      │  │ NORMAL            │  │
│  │ Signal +  │  │ targets via  │  │  → REDUCE_ONLY    │  │
│  │ Regime    │  │ HL SDK       │  │  → HALTED          │  │
│  │ Filter    │  │ CSV logging  │  │                   │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
│                                                          │
│  Safety: crash recovery on restart (check stops only,    │
│          don't re-run strategy with incomplete candles)   │
└─────────────────────────────────────────────────────────┘
```

**Crash recovery**: On restart, if open positions exist, only check if stop prices are breached. Does NOT re-run strategy signal (which would use incomplete candle data and could generate false signals).

### Portfolio Manager (Regime-Based Strategy Allocation)

The PM sits between Strategy and Execution layers, routing per-coin capital to the appropriate strategy based on ADX regime detection:

```
For each coin, each 8H bar:
  ADX > 25 (trending)  -> 100% capital to DonchianMTF
  ADX < 20 (ranging)   -> 100% capital to MeanReversionZScore
  ADX 20-25 (gray)     -> 50% each strategy
```

Regime is per-coin, not global. BTC may be trending while ETH is ranging simultaneously.

**Mean Reversion Strategy** (complements Donchian):
- Entry: Z-score crosses beyond threshold (price far from rolling mean)
- Exit: Z-score reverts to near zero
- Stop: Z-score keeps diverging (trend taking over)
- Inverted regime filter: activates in choppy markets (ADX < 20)
- Walk-forward validated: per-coin optimized params, avg validation Sharpe 0.85

### Dynamic Slippage Model

Replaces fixed-bps slippage with Ludwig's market impact model:
- **Small trades** (< 0.1% ADV): linear slippage = K2 * |trade_size|
- **Large trades** (>= 0.1% ADV): quadratic slippage = (K1/ADV) * trade_size^2
- ADV computed as rolling 20-day average daily USD volume
- Impact: Holdout B0 Sharpe improved +0.065 (better models small-fund reality)

### Current Deployment

| Parameter | Value |
|-----------|-------|
| Exchange | Hyperliquid |
| Coins | 28 (BTC, ETH, LTC, TRX, BCH, DOT, ADA, LINK, XLM, XRP, ETC, ALGO, ATOM, AAVE, SOL, ICP, UNI, FIL, AVAX, NEAR, CRV, DOGE, AXS, YGG, CELO, GALA, SAND, PEOPLE) |
| Frequency | 8H (candle close at UTC 0/4/8/12/16/20) |
| Lookbacks | 36/60/336 bars (12d/20d/112d) |
| Weights | med-heavy [0.25, 0.50, 0.25] |
| Leverage | 3× cross-margin |
| Regime filter | Enabled (ADX period=20, thresholds 20/25) |
| Min notional | $1.00 |
| Fee model | Taker 3.5 bps, slippage 15 bps |

---

## Research Framework

### Walk-Forward Validation

All strategy parameters validated using expanding-window walk-forward cross-validation. KFold is forbidden for time-series (enforced in code via `ForbiddenKFoldError`).

```
Window 1: IS=2021.01-2022.06 → Validation=2022.07-2023.06
Window 2: IS=2021.01-2023.06 → Validation=2023.07-2024.06
Window 3: IS=2021.01-2024.06 → Validation=2024.07-2025.06
Holdout:  2025.07-2026.03 (touched once, after all tuning complete)
```

### Key Experimental Results

| Experiment | Finding |
|-----------|---------|
| **Frequency sweep** (1H/2H/4H/8H/1D × 1070 params) | 8H optimal; 0/1070 params positive in all 3 validation windows |
| **Regime filter A/B test** | +0.077 Sharpe improvement; only effective optimization module |
| **Dynamic lookback** | Negative contribution (-0.090); adds noise |
| **Hurst-weighted portfolios** | Rolling Hurst unstable over time; equal-weight more robust in holdout |
| **TSMOM baseline** | Per-coin optimized TSMOM overfits severely (val +0.10, holdout -0.74) |
| **TSMOM unified params** | Eliminates overfitting but also eliminates alpha |
| **Cross-asset Donchian** (30 trad assets) | 26/30 no positive IS params; Donchian ineffective on low-vol assets |
| **Cross-asset TSMOM** | Works better than Donchian on traditional assets; SPY/QQQ/NVDA most robust |
| **Cross-asset correlation** | Crypto-crypto: 0.60, trad-trad: 0.17, crypto-trad: 0.12 |
| **Dynamic slippage** | +0.065 Sharpe improvement on B0; auto-selects linear for small trades |
| **Mean reversion sweep** | All 22 coins found positive val Sharpe; avg 0.85; per-coin params |
| **Donchian-MR correlation** | Daily return correlation -0.061 (slight negative, good diversification) |
| **Portfolio combinations** | 50/50 equal-weight best: Sharpe 1.232, MaxDD 1.93% (vs 1.006/4.11% Donchian-only) |
| **Regime switching** | Sharpe 0.177 — regime transitions cause excessive trading (2050 trades vs 478) |

### Coin Screening

24 coins selected by: OKX data from 2021+, exclude stablecoins/wrapped tokens, daily volatility > 1%. MANA excluded (not on HL), SAND excluded (volume < $200K/day).

Hurst exponent significantly correlates with Donchian performance (Spearman rho=0.53, p=0.008), but rolling Hurst is too unstable for dynamic weighting.

---

## ML Pipeline (Experimental)

Not in production. CV direction accuracy 60.5% but OOS Sharpe negative.

```
OKX 1H OHLCV → FeaturePipeline (138 features, 10 blocks) → QuantileGBM → MLStrategy
```

**Feature blocks**: technical (40), donchian (13), microstructure (15), cross-asset (10), temporal (12), volatility (18), momentum (16), funding (18), orderbook (18), sentiment/FNG (4)

**LeakageGuard** (4 layers): lag correlation check, train/test temporal ordering, embargo gap validation, target-feature separation.

---

## Data Collection

### Historical Data
- **OHLCV**: OKX perpetuals, 1H/4H, 2021-present, Parquet cache
- **Funding rates**: Hyperliquid, 2023-present
- **Fear & Greed Index**: alternative.me, 2018-present (CSV)
- **Traditional assets**: Yahoo Finance daily, 2015-present (for research only)

### Real-Time Collection (data_collector.py)
- **HL Orderbook**: Top 10 bid/ask levels, 22 coins, hourly → SQLite
- **Reddit**: Hot posts from r/cryptocurrency, r/bitcoin, r/ethtrader, hourly → SQLite

---

## Module Reference

| Module | File | Role |
|--------|------|------|
| **Data** | | |
| DataManager | `data/manager.py` | Unified data access with cache-through |
| OKX/Binance/HL Fetchers | `data/fetchers/*.py` | Exchange-specific OHLCV fetching |
| ParquetCache | `data/cache.py` | Local OHLCV storage |
| DataCollector | `scripts/data_collector.py` | Scheduled alternative data collection |
| **Strategy** | | |
| DonchianMTF | `strategy/donchian_mtf.py` | Trend-following: Donchian breakout + regime filter |
| MeanReversionZScore | `strategy/mean_reversion.py` | Mean-reversion: Z-score entry/exit (ranging markets) |
| MLStrategy | `strategy/ml_strategy.py` | ML signal adapter (experimental) |
| BaseStrategy | `strategy/base.py` | ABC defining StrategySignal interface |
| **Features** | | |
| FeaturePipeline | `features/pipeline.py` | Orchestrates 10 feature blocks |
| LeakageGuard | `features/leakage_guard.py` | Look-ahead bias prevention (fatal errors) |
| 10 FeatureBlocks | `features/*.py` | Technical, momentum, volatility, sentiment, etc. |
| **ML** | | |
| QuantileGBM | `ml/model.py` | LightGBM quantile regression (5 quantiles) |
| WalkForwardSplitter | `ml/splitter.py` | Time-series CV with embargo |
| Trainer | `ml/trainer.py` | End-to-end training pipeline |
| DriftDetector | `ml/drift_detector.py` | Performance degradation monitoring |
| **Backtest** | | |
| BacktestEngine | `backtest/engine.py` | T+1 execution, dynamic slippage, gap stops |
| Metrics | `backtest/metrics.py` | Sharpe, Sortino, Calmar, MaxDD, bootstrap CI |
| BiasAudit | `backtest/bias_audit.py` | Fill timing and signal look-ahead verification |
| TelemetryRecorder | `backtest/telemetry.py` | Per-bar decision snapshots (JSONL) |
| **Execution** | | |
| LiveOrchestrator | `execution/orchestrator.py` | Main trading loop, crash recovery |
| PortfolioManager | `execution/portfolio_manager.py` | Regime-based multi-strategy allocation |
| PositionManager | `execution/position_manager.py` | Order execution, CSV logging |
| KillSwitch | `execution/kill_switch.py` | 3-state emergency stop |
| HL Client | `execution/hl_client.py` | Hyperliquid SDK wrapper |
| **Scripts** | | |
| live_donchian.py | `scripts/` | CLI entry point for live trading |
| review_live.py | `scripts/` | Post-trade review dashboard |
| donchian_full_sweep.py | `scripts/` | Full frequency × lookback parameter sweep |
| cross_asset_sweep.py | `scripts/` | Traditional asset Donchian experiment |
| tsmom_experiment.py | `scripts/` | TSMOM baseline comparison |
| data_collector.py | `scripts/` | Scheduled data collection daemon |

---

## Safety Invariants

| Rule | Implementation | Location |
|------|---------------|----------|
| No look-ahead bias | All features use `.shift(1)` on OHLCV | Every FeatureBlock |
| Targets ≠ features | `fwd_return_*` never in feature matrix | LeakageGuard |
| No KFold | `ForbiddenKFoldError` on KFold detection | WalkForwardSplitter |
| T+1 execution | Signal at bar T, fill at bar T+1 open | BacktestEngine |
| API circuit breaker | 3 consecutive failures → REDUCE_ONLY | KillSwitch |
| Crash recovery | Check stops only, don't re-run strategy | Orchestrator |
| Regime filter | ADX + vol contraction suppress choppy markets | DonchianMTF |
