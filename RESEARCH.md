# CryptoLab: A Multi-Timeframe Donchian Breakout System for Cryptocurrency Futures

**Author**: Xinyu Wang, UC Irvine
**Date**: March 2026
**Tools**: Python 3.12, Claude Code (AI pair-programmer), Hyperliquid DEX

---

## 1. Introduction

This document describes the design, backtest methodology, and production engineering of **CryptoLab** — a systematic trend-following strategy for cryptocurrency perpetual futures. The system trades 4-hour candles on a portfolio of BTC, SOL, ADA, and XRP via the Hyperliquid decentralized exchange.

The strategy is a **multi-timeframe Donchian channel breakout** with dynamic position sizing governed by volatility targeting and drawdown scaling. The system was developed iteratively using Claude Code (Anthropic's AI coding agent) as a pair-programmer running in a WSL tmux session, which I monitored and directed from my phone via SSH — enabling a rapid research-to-code feedback loop.

This report is structured in two halves: **quantitative methodology** and **production engineering**, reflecting the reality that in live trading, robust infrastructure is as critical as a good signal.

---

## 2. Strategy: Multi-Timeframe Donchian Breakout (DonchianMTF)

### 2.1 Signal Generation

The core signal is a Donchian channel breakout evaluated across three timeframes simultaneously. For each timeframe $i$ with lookback period $L_i$, the Donchian channel at bar $T$ is computed using data up to bar $T-1$ (strict shift(1) to prevent look-ahead bias):

$$
\text{Upper}_i(T) = \max_{t \in [T-L_i, T-1]} H_t, \quad \text{Lower}_i(T) = \min_{t \in [T-L_i, T-1]} L_t
$$

Each timeframe maintains a **persistent trend state** $s_i \in \{-1, 0, +1\}$:

$$
s_i = \begin{cases} +1 & \text{if } C_T > \text{Upper}_i \\ -1 & \text{if } C_T < \text{Lower}_i \\ s_i^{\text{prev}} & \text{otherwise} \end{cases}
$$

The combined agreement score is a weighted sum:

$$
\text{combined} = \sum_{i=1}^{3} w_i \cdot s_i
$$

For our portfolio, we use two lookback configurations:
- **Combo G**: $L = [24, 72, 168]$ (4-day, 12-day, 28-day) — for BTC, SOL, ADA
- **Combo F**: $L = [48, 168, 504]$ (8-day, 28-day, 84-day) — for XRP

With equal weights $w = [0.33, 0.34, 0.33]$.

### 2.2 Entry and Exit Rules

**Entry**: A long (short) position is opened when the close price breaks above (below) the medium-timeframe Donchian upper (lower) band AND the combined score is positive (negative) AND exceeds a deadzone threshold of 0.05.

**Exit**: Positions are closed when either:
1. **ATR trailing stop** is hit: the stop ratchets in the direction of profit, initialized at $C - 2 \times \text{ATR}_{14}$ for longs.
2. **Opposite breakout**: close crosses the opposite Donchian band on the medium timeframe.

**Execution**: All signals generated at bar $T$ are executed at bar $T+1$'s open price plus simulated slippage (15 bps), using taker fees of 3.5 bps.

### 2.3 Position Sizing

Position size is determined by three multiplicative factors:

**Base position** from risk budgeting:

$$
\text{base} = \frac{\text{equity} \times r}{\text{ATR} / C} \times \text{leverage}
$$

where $r = 0.02$ (2% risk per trade), leverage = 3x.

**Volatility scalar** (vol-targeting):

$$
\sigma_{\text{ann}} = \frac{\text{ATR}}{C} \times \sqrt{2190}, \quad v_s = \text{clip}\left(\frac{0.15}{\sigma_{\text{ann}}}, \ 0.5, \ 2.0\right)
$$

This scales position size inversely with realized volatility, targeting 15% annualized.

**Drawdown scalar** (risk reduction during drawdowns):

$$
d_s = \begin{cases} 0.25 & \text{if } \text{DD} \geq 30\% \\ 1 - 0.75 \times \frac{\text{DD}}{0.30} & \text{otherwise} \end{cases}
$$

**Final position**:

$$
\text{position} = \min\left(\text{base} \times |\text{combined}| \times v_s \times d_s, \ \text{equity} \times \text{leverage}\right)
$$

---

## 3. Backtest Methodology

### 3.1 Data and Periods

| | In-Sample (IS) | Out-of-Sample (OOS) |
|---|---|---|
| **Period** | 2021-01-01 to 2023-12-31 | 2024-01-01 to 2026-02-28 |
| **Purpose** | Parameter selection | Validation |
| **4H bars per symbol** | ~6,500 | ~4,740 |

Data source: OKX historical candles, cached locally for reproducibility.

### 3.2 Fill Model

The backtest engine enforces a strict **next-bar-open fill** model:

1. Signal is generated at bar $T$ using all data $\leq T$ (strategy sees close of bar $T$).
2. Signal is executed at bar $T+1$'s open price $\pm$ 15 bps slippage.
3. Gap stops: if bar $T+1$ opens beyond the stop level, the position is closed at the open price (worst-case fill on gaps).

This eliminates close-price execution bias, which is the most common source of inflated backtest returns.

### 3.3 Look-Ahead Bias Prevention

Three layers of protection:

1. **Indicator level**: `compute_donchian(highs[:-1], lows[:-1], period)` — the `[:-1]` slice explicitly excludes the current bar from channel computation, equivalent to `shift(1)`.
2. **Engine level**: the signal-then-execute loop guarantees one bar of delay between signal generation and order fill.
3. **Automated audit** (`bias_audit.py`): a post-backtest check that verifies every trade's fill price is consistent with the bar's open (not close), catching any future regressions.

### 3.4 Overfitting Controls

- **Bootstrap Sharpe CI**: Resample returns 2,000 times to compute 95% confidence interval on Sharpe ratio.
- **Deflated Sharpe Ratio** (Bailey & López de Prado, 2014): accounts for multiple testing across 16 parameter combinations (8 lookback combos × 2 weight sets).
- **Regime-split Sharpe**: separate Sharpe in bull (close > SMA200) vs bear regimes to detect regime dependence.
- **IS/OOS separation**: parameters were chosen on IS data; OOS was never touched during development.

---

## 4. Results

### 4.1 Portfolio Performance

| Metric | In-Sample (2021–2023) | Out-of-Sample (2024–2026) |
|--------|:---------------------:|:-------------------------:|
| **Total Return** | +70.05% | +21.12% |
| **Max Drawdown** | 9.76% | 10.85% |
| **Sharpe** | 1.40 | 0.82 |
| **Sortino** | 1.45 | 0.73 |
| **Calmar** | 1.99 | 0.85 |
| **Bootstrap Sharpe 95% CI** | [0.29, 2.52] | [-0.45, 2.22] |

The IS-to-OOS Sharpe degradation from 1.40 to 0.82 (41% drop) is within the typical range for trend-following strategies, and the portfolio maintains positive returns with controlled drawdowns.

### 4.2 Per-Symbol Breakdown

**In-Sample (2021–2023)**:

| Symbol | Combo | Return | Max DD | Sharpe | Sortino | Calmar | Trades | Win Rate | PF |
|--------|-------|--------|--------|--------|---------|--------|--------|----------|-----|
| BTC | G | +87.92% | 19.95% | 1.10 | 0.94 | 1.17 | 154 | 20.1% | 1.77 |
| SOL | G | +123.42% | 18.54% | 1.26 | 1.15 | 1.70 | 184 | 21.2% | 2.04 |
| ADA | G | +47.04% | 27.87% | 0.77 | 0.64 | 0.49 | 188 | 16.0% | 1.47 |
| XRP | F | +21.82% | 15.36% | 0.48 | 0.26 | 0.44 | 84 | 17.9% | 1.47 |

**Out-of-Sample (2024–2026)**:

| Symbol | Combo | Return | Max DD | Sharpe | Sortino | Calmar | Trades | Win Rate | PF |
|--------|-------|--------|--------|--------|---------|--------|--------|----------|-----|
| BTC | G | +11.58% | 26.32% | 0.42 | 0.28 | 0.20 | 140 | 17.1% | 1.18 |
| SOL | G | +9.12% | 16.33% | 0.31 | 0.24 | 0.25 | 126 | 20.6% | 1.17 |
| ADA | G | +18.28% | 15.45% | 0.50 | 0.38 | 0.52 | 128 | 25.0% | 1.33 |
| XRP | F | +45.50% | 15.37% | 1.16 | 0.61 | 1.23 | 58 | 15.5% | 2.40 |

### 4.3 Key Observations

1. **Win rate is consistently 15–25%** — this is characteristic of trend-following: most trades are small losses during choppy periods, while a few large winners during sustained trends drive profitability. Profit factors of 1.2–2.4x confirm the fat-tailed win distribution.

2. **Regime dependence**: IS data shows clear bull-regime bias (BTC bull Sharpe 2.12 vs bear -0.39). However, OOS data is more balanced — XRP in particular shows positive Sharpe in both regimes, which is why it's the strongest OOS contributor.

3. **Portfolio diversification works**: individual symbol max drawdowns are 15–28%, but portfolio max DD is only 10–11% in both IS and OOS, demonstrating meaningful decorrelation across the four assets.

4. **OOS Sharpe CI includes zero** [-0.45, 2.22] — the strategy is profitable but we cannot reject the null hypothesis of zero skill at 95% confidence with this sample size. This is the honest reality of a ~2-year OOS window.

---

## 5. Production Engineering

### 5.1 System Architecture

```
┌────────────────────────────────────────────────────────┐
│                    CryptoLab System                     │
├──────────────┬──────────────┬──────────────────────────┤
│  Data Layer  │  Strategy    │  Execution Layer          │
│  ───────────│  ──────────  │  ──────────────────────── │
│  OKX/Binance │  DonchianMTF │  Hyperliquid SDK          │
│  HL fetchers │  BaseStrategy│  PositionManager          │
│  Cache/Valid.│  Config      │  KillSwitch               │
├──────────────┴──────────────┴──────────────────────────┤
│                 Observability Layer                      │
│  Decision Telemetry │ Bias Audit │ Regime Monitor       │
│  Worst-Offender     │ Visualizer │ JSONL Logging        │
└────────────────────────────────────────────────────────┘
```

### 5.2 Decision Telemetry

Every bar during backtesting (and planned for live trading) generates a **complete decision snapshot** serialized as JSONL. Each snapshot contains ~29 fields:

- Bar context: timestamp, OHLCV, bar index
- Account state: equity, current position USD
- Signal output: signal type, target position, confidence, stop price
- Strategy internals: `combined_score`, `vol_scalar`, `dd_scalar`, `ann_vol`, `current_dd_pct`
- Per-TF state: trend direction, upper/lower bands for each of the 3 timeframes
- ATR, momentum score, exit reason (if applicable)

Two output files are generated:
- `telemetry_*.jsonl` — every bar (full decision chain reconstruction)
- `actions_*.jsonl` — entries, exits, and pyramid adds only (quick review)

**Why this matters for live trading**: When a trade goes wrong at 3 AM, I need to reconstruct exactly what the system "saw" at the moment it made the decision. A simple "bought BTC at $X" log is useless. The telemetry captures the complete internal state, making it possible to distinguish between "the signal was correct but the market reversed" vs "the volatility scalar was miscalculated because ATR was stale."

### 5.3 Interactive Visualizer

A Plotly-based tool (`scripts/visualize_backtest.py`) renders:
- Candlestick chart with all 3 TF Donchian channels overlaid
- Trade markers (entry/exit arrows)
- **Tooltip on hover**: displays the full decision snapshot JSON from telemetry

This provides a rapid visual debugging workflow — I can scan the chart for suspicious entries and immediately see the exact internal state without digging through log files.

### 5.4 Worst-Offender Analysis

Post-backtest diagnostic module that automatically identifies:
1. **Worst N trades by absolute loss** — where did the most capital go?
2. **Maximum Adverse Excursion (MAE) survivors** — trades that experienced deep drawdown but weren't stopped out. These reveal whether the trailing stop is set too loose.
3. **Missed moves** — periods where price moved significantly but `combined_score` was in the deadzone. These reveal structural blind spots in the signal model.

### 5.5 Look-Ahead Bias Audit

An automated post-backtest check (`bias_audit.py`) that verifies:
- Every trade's fill price is consistent with the execution bar's open price (not close)
- No signal references future bar data

This runs as part of the test suite (83 tests, all passing), ensuring that future code changes cannot silently introduce look-ahead bias.

### 5.6 Regime & Drift Monitor

Continuously monitors two indicators:
- **Rolling 14-day ADX**: when ADX drops below 20, the market is in a choppy/ranging regime where trend-following strategies are expected to underperform.
- **Rolling 14-day Sharpe**: when this turns negative, the strategy is actively losing money in recent history.

Warnings are emitted on **state transitions** (entering a bad regime), not every bar, to avoid log flooding. These warnings are cross-referenced with the `dd_scalar` values in telemetry to verify that the drawdown scaling mechanism is actually engaging when it should.

### 5.7 Kill Switch & Graceful Degradation

The most critical production component. A state machine with three modes:

```
NORMAL ──[3x API failure / NaN data / sentinel file]──> REDUCE_ONLY
REDUCE_ONLY ──[30min cooldown + success]──> NORMAL
NORMAL ──[sentinel file]──> HALTED (manual reset required)
```

**Trigger conditions**:
1. **3 consecutive API timeouts or 5xx errors** from Hyperliquid
2. **NaN values detected in fetched candle data** (data corruption)
3. **Sentinel file** (`KILL_SWITCH` file in project root) — manual emergency stop

**Emergency procedure** (when triggered):
1. Cancel all open orders
2. Market-close all positions (emergency flatten)
3. Enter `REDUCE_ONLY` mode — can close existing positions but cannot open new ones
4. Auto-recover after 30-minute cooldown if API health is restored

**Why not just retry?** In crypto markets, silent failures are more dangerous than loud crashes. If the exchange API is returning errors, the correct response is NOT to keep retrying and hoping — it's to reduce exposure immediately and figure out what's wrong. The `hl_info_post()` function now raises typed `APIError` exceptions that distinguish between timeouts, connection errors, and 5xx server errors, giving the kill switch precise information about the failure mode.

---

## 6. Development Workflow

This project was built using **Claude Code** (Anthropic's AI coding agent) as a pair-programmer. The workflow:

1. I run Claude Code inside a **tmux session on WSL**, which I connect to via **SSH from my phone**. This means I can review Claude's progress, approve tool calls, and steer the conversation from anywhere — the session never drops.

2. I describe what I want in natural language (often in Chinese); Claude reads the relevant source files, writes code, runs the backtest on Windows Python (via `cmd.exe` from WSL), and iterates until tests pass.

3. **Quality control**: Claude runs the full test suite (83 tests) after every change and does not proceed if any test fails. The look-ahead bias audit is part of this suite, so it's impossible to accidentally introduce future data leaks.

4. The entire observability + defensive guardrails layer (6 modules, ~800 lines of code, 22 dedicated tests) was implemented in a single session with zero regressions to the existing 61 tests.

This is not "AI wrote my code and I didn't understand it." I specify the architecture, review every module, question design decisions, and direct the implementation. Claude is a force multiplier — it handles the boilerplate and catches edge cases while I focus on strategy logic and system design.

---

## 7. Known Limitations & Open Questions

1. **Regime dependence**: The strategy has a clear trend-following bias. In-sample bull regime Sharpe is 2x the bear regime Sharpe. The `dd_scalar` mechanism mitigates losses during drawdowns but does not avoid them. **Question: Beyond drawdown scaling, are there regime-switching overlays (e.g., hidden Markov models, or simpler ADX-based gating) that you've seen work in practice for crypto?**

2. **Statistical significance**: The OOS portfolio Sharpe 95% CI includes zero [-0.45, 2.22]. With ~2 years of OOS data at 4H frequency, we have ~4,700 observations, yet the CI is wide. **Question: For a strategy with this profile (~20% win rate, high profit factor), is there a more appropriate statistical test than bootstrap Sharpe CI? Perhaps something that accounts for the non-normality of trend-following returns?**

3. **Volatility scalar bounds**: The vol-targeting scalar is clamped to [0.5, 2.0]. The upper bound was chosen heuristically. **Question: Is there a theoretically grounded way to set these bounds, perhaps based on Kelly criterion or drawdown constraints?**

4. **Portfolio construction**: Currently using equal-weight capital allocation with per-symbol lookback combo selection. **Question: Would a risk-parity allocation (equalizing marginal risk contribution) materially improve portfolio Sharpe, or is the added complexity not worth it for a 4-asset portfolio?**

5. **Kill switch recovery**: The current auto-recovery is time-based (30-minute cooldown). **Question: In your industry experience, what additional conditions should gate recovery beyond "the API is responding again"? I'm concerned about scenarios like exchange partial outages where the API returns data but it's stale or incorrect.**

6. **Live execution gap**: The backtest assumes IOC fills at open + slippage. In practice, Hyperliquid's orderbook may have liquidity gaps, especially for altcoins during volatile periods. **Question: What's a realistic approach to modeling execution quality beyond constant slippage — should I simulate orderbook impact?**

---

## 8. Repository Structure

```
cryptolab/
├── backtest/
│   ├── engine.py          # Next-bar-open backtest engine
│   ├── metrics.py         # Performance metrics + worst-offender analysis
│   ├── telemetry.py       # Decision snapshot JSONL recorder
│   ├── bias_audit.py      # Look-ahead bias verification
│   └── regime_monitor.py  # ADX/Sharpe drift detection
├── strategy/
│   ├── base.py            # BaseStrategy ABC
│   ├── donchian.py        # Single-TF Donchian (baseline)
│   └── donchian_mtf.py    # Multi-TF Donchian (production)
├── indicators/
│   ├── core.py            # ATR, RSI, ADX, EMA, TSMOM, etc.
│   └── donchian.py        # Donchian channel computation
├── execution/
│   ├── hl_client.py       # Hyperliquid API wrapper + typed errors
│   ├── position_manager.py# Order execution + CSV logging
│   └── kill_switch.py     # Emergency flatten + mode state machine
├── data/                  # Fetchers (OKX/Binance/HL), cache, validation
├── config.py              # All parameters in one Config dataclass
└── scripts/
    ├── run_backtest.py    # CLI: single/multi/portfolio/sweep backtests
    └── visualize_backtest.py  # Plotly interactive chart
```

**Test coverage**: 83 tests covering strategy logic, backtest engine, indicators, telemetry, bias audit, regime monitor, and kill switch. All passing.
