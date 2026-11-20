# Research Log

## 2026-03-05 — Project Init

- Clean rebuild from old crypto project
- First strategy target: 4H Donchian Channel Breakout + Volatility Sizing
- Data pipeline: OKX perps (primary) + Binance spot (cross-validation) + HL (live)
- Parquet cache for fast local reads

## 2026-03-05 11:13 UTC — Backtest: DonchianBreakout on BTC

- Period: 2022-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -0.47% | Max DD: 54.94%
- Trades: 2666 | Win rate: 25.1% | Profit factor: 1.00
- Fees: $1961.69 | Slippage: $8407.25 | Time in market: 58.6%
- Initial: $10,000 | Final: $9,953.27

## 2026-03-05 11:24 UTC — Backtest: DonchianBreakout on BTC

- Period: 2022-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +31.27% | Max DD: 55.75%
- Trades: 208 | Win rate: 19.7% | Profit factor: 1.07
- Fees: $1570.85 | Slippage: $6732.19 | Time in market: 58.6%
- Initial: $10,000 | Final: $13,126.93

## 2026-03-05 12:18 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=12, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -72.32% | Max DD: 87.87% | Sharpe: -0.17 | Sortino: -0.21 | Calmar: -0.40
- Trades: 414 | Win rate: 16.4% | Profit factor: 0.84
- Fees: $1254.03 | Slippage: $5374.40 | Time in market: 67.9%
- Initial: $10,000 | Final: $2,768.37

## 2026-03-05 12:24 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=12, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -63.68% | Max DD: 83.02% | Sharpe: -0.05 | Sortino: -0.06 | Calmar: -0.35
- Trades: 438 | Win rate: 16.9% | Profit factor: 0.91
- Fees: $1886.83 | Slippage: $8086.43 | Time in market: 68.9%
- Initial: $10,000 | Final: $3,632.39

## 2026-03-05 12:27 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=12, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -8.12% | Max DD: 78.46% | Sharpe: 0.38 | Sortino: 0.51 | Calmar: -0.04
- Trades: 449 | Win rate: 17.4% | Profit factor: 0.98
- Fees: $844.12 | Slippage: $3617.64 | Time in market: 72.1%
- Initial: $10,000 | Final: $9,188.26

## 2026-03-05 12:31 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -32.84% | Max DD: 76.55% | Sharpe: 0.17 | Sortino: 0.19 | Calmar: -0.16
- Trades: 330 | Win rate: 18.8% | Profit factor: 0.92
- Fees: $1127.87 | Slippage: $4833.71 | Time in market: 60.2%
- Initial: $10,000 | Final: $6,716.36

## 2026-03-05 12:35 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -72.09% | Max DD: 76.82% | Sharpe: -0.25 | Sortino: -0.29 | Calmar: -0.45
- Trades: 364 | Win rate: 18.1% | Profit factor: 0.81
- Fees: $920.20 | Slippage: $3943.71 | Time in market: 61.3%
- Initial: $10,000 | Final: $2,791.09

## 2026-03-05 12:39 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +277.92% | Max DD: 57.42% | Sharpe: 0.96 | Sortino: 1.20 | Calmar: 1.00
- Trades: 357 | Win rate: 19.3% | Profit factor: 1.49
- Fees: $1199.81 | Slippage: $5142.04 | Time in market: 62.3%
- Initial: $10,000 | Final: $37,791.63

## 2026-03-05 12:42 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=30, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +28.24% | Max DD: 65.94% | Sharpe: 0.45 | Sortino: 0.46 | Calmar: 0.13
- Trades: 262 | Win rate: 19.1% | Profit factor: 1.07
- Fees: $1170.40 | Slippage: $5016.00 | Time in market: 48.0%
- Initial: $10,000 | Final: $12,824.37

## 2026-03-05 12:46 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=30, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -70.39% | Max DD: 77.13% | Sharpe: -0.27 | Sortino: -0.29 | Calmar: -0.43
- Trades: 310 | Win rate: 18.1% | Profit factor: 0.76
- Fees: $697.60 | Slippage: $2989.73 | Time in market: 51.4%
- Initial: $10,000 | Final: $2,960.62

## 2026-03-05 12:50 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=30, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +430.47% | Max DD: 61.29% | Sharpe: 1.13 | Sortino: 1.31 | Calmar: 1.25
- Trades: 308 | Win rate: 20.1% | Profit factor: 1.55
- Fees: $1604.17 | Slippage: $6875.02 | Time in market: 54.5%
- Initial: $10,000 | Final: $53,047.18

## 2026-03-05 12:53 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=48, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +74.51% | Max DD: 48.17% | Sharpe: 0.61 | Sortino: 0.57 | Calmar: 0.42
- Trades: 206 | Win rate: 19.4% | Profit factor: 1.19
- Fees: $1319.00 | Slippage: $5652.87 | Time in market: 39.2%
- Initial: $10,000 | Final: $17,451.27

## 2026-03-05 12:57 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=48, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -53.20% | Max DD: 70.20% | Sharpe: -0.12 | Sortino: -0.11 | Calmar: -0.32
- Trades: 240 | Win rate: 18.8% | Profit factor: 0.80
- Fees: $654.87 | Slippage: $2806.59 | Time in market: 39.9%
- Initial: $10,000 | Final: $4,679.61

## 2026-03-05 13:01 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=48, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +101.91% | Max DD: 60.38% | Sharpe: 0.69 | Sortino: 0.72 | Calmar: 0.45
- Trades: 252 | Win rate: 19.4% | Profit factor: 1.21
- Fees: $881.31 | Slippage: $3777.03 | Time in market: 43.8%
- Initial: $10,000 | Final: $20,190.51

## 2026-03-05 13:04 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +151.22% | Max DD: 42.90% | Sharpe: 0.84 | Sortino: 0.70 | Calmar: 0.84
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.36
- Fees: $1370.71 | Slippage: $5874.47 | Time in market: 30.7%
- Initial: $10,000 | Final: $25,121.74

## 2026-03-05 13:08 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -31.07% | Max DD: 66.67% | Sharpe: 0.04 | Sortino: 0.04 | Calmar: -0.18
- Trades: 184 | Win rate: 19.0% | Profit factor: 0.88
- Fees: $699.19 | Slippage: $2996.54 | Time in market: 30.4%
- Initial: $10,000 | Final: $6,893.11

## 2026-03-05 13:12 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +486.36% | Max DD: 48.14% | Sharpe: 1.26 | Sortino: 1.22 | Calmar: 1.71
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.81
- Fees: $1244.82 | Slippage: $5334.92 | Time in market: 34.9%
- Initial: $10,000 | Final: $58,636.21

## 2026-03-05 13:15 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=96, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +83.90% | Max DD: 51.96% | Sharpe: 0.65 | Sortino: 0.52 | Calmar: 0.43
- Trades: 138 | Win rate: 19.6% | Profit factor: 1.22
- Fees: $1195.66 | Slippage: $5124.26 | Time in market: 26.6%
- Initial: $10,000 | Final: $18,389.73

## 2026-03-05 13:19 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=96, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -48.13% | Max DD: 64.95% | Sharpe: -0.16 | Sortino: -0.13 | Calmar: -0.30
- Trades: 168 | Win rate: 17.3% | Profit factor: 0.78
- Fees: $494.33 | Slippage: $2118.57 | Time in market: 26.8%
- Initial: $10,000 | Final: $5,186.88

## 2026-03-05 13:23 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=96, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +435.68% | Max DD: 45.62% | Sharpe: 1.24 | Sortino: 1.11 | Calmar: 1.69
- Trades: 164 | Win rate: 23.2% | Profit factor: 1.85
- Fees: $979.98 | Slippage: $4199.92 | Time in market: 30.6%
- Initial: $10,000 | Final: $53,568.01

## 2026-03-05 13:23 UTC — Lookback Sweep: DonchianBreakout (BTC, ETH, SOL)

Lookbacks tested: [12, 20, 30, 48, 72, 96]

| Lookback | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|----------|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| 12 | BTC | -72.32% | 87.87% | -0.17 | -0.21 | -0.40 | 414 | 16.4% | 0.84 |
| 12 | ETH | -63.68% | 83.02% | -0.05 | -0.06 | -0.35 | 438 | 16.9% | 0.91 |
| 12 | SOL | -8.12% | 78.46% | 0.38 | 0.51 | -0.04 | 449 | 17.4% | 0.98 |
| 20 | BTC | -32.84% | 76.55% | 0.17 | 0.19 | -0.16 | 330 | 18.8% | 0.92 |
| 20 | ETH | -72.09% | 76.82% | -0.25 | -0.29 | -0.45 | 364 | 18.1% | 0.81 |
| 20 | SOL | +277.92% | 57.42% | 0.96 | 1.20 | 1.00 | 357 | 19.3% | 1.49 |
| 30 | BTC | +28.24% | 65.94% | 0.45 | 0.46 | 0.13 | 262 | 19.1% | 1.07 |
| 30 | ETH | -70.39% | 77.13% | -0.27 | -0.29 | -0.43 | 310 | 18.1% | 0.76 |
| 30 | SOL | +430.47% | 61.29% | 1.13 | 1.31 | 1.25 | 308 | 20.1% | 1.55 |
| 48 | BTC | +74.51% | 48.17% | 0.61 | 0.57 | 0.42 | 206 | 19.4% | 1.19 |
| 48 | ETH | -53.20% | 70.20% | -0.12 | -0.11 | -0.32 | 240 | 18.8% | 0.80 |
| 48 | SOL | +101.91% | 60.38% | 0.69 | 0.72 | 0.45 | 252 | 19.4% | 1.21 |
| 72 | BTC | +151.22% | 42.90% | 0.84 | 0.70 | 0.84 | 154 | 20.1% | 1.36 |
| 72 | ETH | -31.07% | 66.67% | 0.04 | 0.04 | -0.18 | 184 | 19.0% | 0.88 |
| 72 | SOL | +486.36% | 48.14% | 1.26 | 1.22 | 1.71 | 188 | 21.8% | 1.81 |
| 96 | BTC | +83.90% | 51.96% | 0.65 | 0.52 | 0.43 | 138 | 19.6% | 1.22 |
| 96 | ETH | -48.13% | 64.95% | -0.16 | -0.13 | -0.30 | 168 | 17.3% | 0.78 |
| 96 | SOL | +435.68% | 45.62% | 1.24 | 1.11 | 1.69 | 164 | 23.2% | 1.85 |

## 2026-03-05 21:43 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +57.87% | Max DD: 16.91% | Sharpe: 0.90 | Sortino: 0.75 | Calmar: 0.97
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.51
- Fees: $377.89 | Slippage: $1619.54 | Time in market: 30.7%
- Initial: $10,000 | Final: $15,787.08

## 2026-03-05 21:47 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +107.38% | Max DD: 19.60% | Sharpe: 1.20 | Sortino: 1.14 | Calmar: 1.44
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.85
- Fees: $267.93 | Slippage: $1148.29 | Time in market: 34.9%
- Initial: $10,000 | Final: $20,738.09

## 2026-03-05 21:51 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +86.30% | Max DD: 24.26% | Sharpe: 0.89 | Sortino: 0.74 | Calmar: 0.95
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.47
- Fees: $608.03 | Slippage: $2605.83 | Time in market: 30.7%
- Initial: $10,000 | Final: $18,630.16

## 2026-03-05 21:55 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +182.12% | Max DD: 27.91% | Sharpe: 1.22 | Sortino: 1.16 | Calmar: 1.52
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.84
- Fees: $455.75 | Slippage: $1953.19 | Time in market: 34.9%
- Initial: $10,000 | Final: $28,212.25

## 2026-03-05 21:59 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.0
- Return: +112.27% | Max DD: 31.01% | Sharpe: 0.87 | Sortino: 0.73 | Calmar: 0.92
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.43
- Fees: $856.25 | Slippage: $3669.63 | Time in market: 30.7%
- Initial: $10,000 | Final: $21,227.29

## 2026-03-05 22:02 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.0
- Return: +271.15% | Max DD: 35.38% | Sharpe: 1.23 | Sortino: 1.18 | Calmar: 1.59
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.83
- Fees: $681.78 | Slippage: $2921.91 | Time in market: 34.9%
- Initial: $10,000 | Final: $37,115.28

## 2026-03-05 22:06 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.5
- Return: +134.32% | Max DD: 37.20% | Sharpe: 0.86 | Sortino: 0.72 | Calmar: 0.88
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.40
- Fees: $1113.66 | Slippage: $4772.82 | Time in market: 30.7%
- Initial: $10,000 | Final: $23,431.54

## 2026-03-05 22:10 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.5
- Return: +373.34% | Max DD: 42.10% | Sharpe: 1.25 | Sortino: 1.20 | Calmar: 1.66
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.82
- Fees: $945.63 | Slippage: $4052.69 | Time in market: 34.9%
- Initial: $10,000 | Final: $47,334.37

## 2026-03-05 22:13 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +151.22% | Max DD: 42.90% | Sharpe: 0.84 | Sortino: 0.70 | Calmar: 0.84
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.36
- Fees: $1370.71 | Slippage: $5874.47 | Time in market: 30.7%
- Initial: $10,000 | Final: $25,121.74

## 2026-03-05 22:17 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +486.36% | Max DD: 48.14% | Sharpe: 1.26 | Sortino: 1.22 | Calmar: 1.71
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.81
- Fees: $1244.82 | Slippage: $5334.92 | Time in market: 34.9%
- Initial: $10,000 | Final: $58,636.21

## 2026-03-05 22:17 UTC — Parameter Sweep: DonchianBreakout (BTC, SOL)

Params: leverage=[1.0, 1.5, 2.0, 2.5, 3.0]

| Leverage | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BTC | +57.87% | 16.91% | 0.90 | 0.75 | 0.97 | 154 | 20.1% | 1.51 |
| 1 | SOL | +107.38% | 19.60% | 1.20 | 1.14 | 1.44 | 188 | 21.8% | 1.85 |
| 1.5 | BTC | +86.30% | 24.26% | 0.89 | 0.74 | 0.95 | 154 | 20.1% | 1.47 |
| 1.5 | SOL | +182.12% | 27.91% | 1.22 | 1.16 | 1.52 | 188 | 21.8% | 1.84 |
| 2 | BTC | +112.27% | 31.01% | 0.87 | 0.73 | 0.92 | 154 | 20.1% | 1.43 |
| 2 | SOL | +271.15% | 35.38% | 1.23 | 1.18 | 1.59 | 188 | 21.8% | 1.83 |
| 2.5 | BTC | +134.32% | 37.20% | 0.86 | 0.72 | 0.88 | 154 | 20.1% | 1.40 |
| 2.5 | SOL | +373.34% | 42.10% | 1.25 | 1.20 | 1.66 | 188 | 21.8% | 1.82 |
| 3 | BTC | +151.22% | 42.90% | 0.84 | 0.70 | 0.84 | 154 | 20.1% | 1.36 |
| 3 | SOL | +486.36% | 48.14% | 1.26 | 1.22 | 1.71 | 188 | 21.8% | 1.81 |

## 2026-03-05 23:50 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +57.87% | Max DD: 16.91% | Sharpe: 0.90 | Sortino: 0.75 | Calmar: 0.97
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.51
- Fees: $377.89 | Slippage: $1619.54 | Time in market: 30.7%
- Initial: $10,000 | Final: $15,787.08

## 2026-03-05 23:54 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +107.38% | Max DD: 19.60% | Sharpe: 1.20 | Sortino: 1.14 | Calmar: 1.44
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.85
- Fees: $267.93 | Slippage: $1148.29 | Time in market: 34.9%
- Initial: $10,000 | Final: $20,738.09

## 2026-03-05 23:58 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +86.30% | Max DD: 24.26% | Sharpe: 0.89 | Sortino: 0.74 | Calmar: 0.95
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.47
- Fees: $608.03 | Slippage: $2605.83 | Time in market: 30.7%
- Initial: $10,000 | Final: $18,630.16

## 2026-03-06 00:01 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +182.12% | Max DD: 27.91% | Sharpe: 1.22 | Sortino: 1.16 | Calmar: 1.52
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.84
- Fees: $455.75 | Slippage: $1953.19 | Time in market: 34.9%
- Initial: $10,000 | Final: $28,212.25

## 2026-03-06 00:05 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.0
- Return: +112.27% | Max DD: 31.01% | Sharpe: 0.87 | Sortino: 0.73 | Calmar: 0.92
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.43
- Fees: $856.25 | Slippage: $3669.63 | Time in market: 30.7%
- Initial: $10,000 | Final: $21,227.29

## 2026-03-06 00:07 UTC — Backtest: DonchianBreakout on BTC

- Period: 2023-01-01 to 2023-01-09
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.00% | Max DD: 0.00% | Sharpe: 0.00 | Sortino: 0.00 | Calmar: 0.00
- Trades: 0 | Win rate: 0.0% | Profit factor: 0.00
- Fees: $0.00 | Slippage: $0.00 | Time in market: 0.0%
- Initial: $10,000 | Final: $10,000.00

## 2026-03-06 00:09 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.0
- Return: +271.15% | Max DD: 35.38% | Sharpe: 1.23 | Sortino: 1.18 | Calmar: 1.59
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.83
- Fees: $681.78 | Slippage: $2921.91 | Time in market: 34.9%
- Initial: $10,000 | Final: $37,115.28

## 2026-03-06 00:11 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +57.87% | Max DD: 16.91% | Sharpe: 0.90 | Sortino: 0.75 | Calmar: 0.97
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.51
- Fees: $377.89 | Slippage: $1619.54 | Time in market: 30.7%
- Initial: $10,000 | Final: $15,787.08

## 2026-03-06 00:13 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.5
- Return: +134.32% | Max DD: 37.20% | Sharpe: 0.86 | Sortino: 0.72 | Calmar: 0.88
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.40
- Fees: $1113.66 | Slippage: $4772.82 | Time in market: 30.7%
- Initial: $10,000 | Final: $23,431.54

## 2026-03-06 00:16 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +57.87% | Max DD: 16.91% | Sharpe: 0.90 | Sortino: 0.75 | Calmar: 0.97
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.51
- Fees: $377.89 | Slippage: $1619.54 | Time in market: 30.7%
- Initial: $10,000 | Final: $15,787.08

## 2026-03-06 00:17 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.5
- Return: +373.34% | Max DD: 42.10% | Sharpe: 1.25 | Sortino: 1.20 | Calmar: 1.66
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.82
- Fees: $945.63 | Slippage: $4052.69 | Time in market: 34.9%
- Initial: $10,000 | Final: $47,334.37

## 2026-03-06 00:20 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.0
- Return: +107.38% | Max DD: 19.60% | Sharpe: 1.20 | Sortino: 1.14 | Calmar: 1.44
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.85
- Fees: $267.93 | Slippage: $1148.29 | Time in market: 34.9%
- Initial: $10,000 | Final: $20,738.09

## 2026-03-06 00:21 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +151.22% | Max DD: 42.90% | Sharpe: 0.84 | Sortino: 0.70 | Calmar: 0.84
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.36
- Fees: $1370.71 | Slippage: $5874.47 | Time in market: 30.7%
- Initial: $10,000 | Final: $25,121.74

## 2026-03-06 00:24 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +86.30% | Max DD: 24.26% | Sharpe: 0.89 | Sortino: 0.74 | Calmar: 0.95
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.47
- Fees: $608.03 | Slippage: $2605.83 | Time in market: 30.7%
- Initial: $10,000 | Final: $18,630.16

## 2026-03-06 00:24 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +486.36% | Max DD: 48.14% | Sharpe: 1.26 | Sortino: 1.22 | Calmar: 1.71
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.81
- Fees: $1244.82 | Slippage: $5334.92 | Time in market: 34.9%
- Initial: $10,000 | Final: $58,636.21

## 2026-03-06 00:24 UTC — Parameter Sweep: DonchianBreakout (BTC, SOL)

Params: leverage=[1.0, 1.5, 2.0, 2.5, 3.0]

| Leverage | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BTC | +57.87% | 16.91% | 0.90 | 0.75 | 0.97 | 154 | 20.1% | 1.51 |
| 1 | SOL | +107.38% | 19.60% | 1.20 | 1.14 | 1.44 | 188 | 21.8% | 1.85 |
| 1.5 | BTC | +86.30% | 24.26% | 0.89 | 0.74 | 0.95 | 154 | 20.1% | 1.47 |
| 1.5 | SOL | +182.12% | 27.91% | 1.22 | 1.16 | 1.52 | 188 | 21.8% | 1.84 |
| 2 | BTC | +112.27% | 31.01% | 0.87 | 0.73 | 0.92 | 154 | 20.1% | 1.43 |
| 2 | SOL | +271.15% | 35.38% | 1.23 | 1.18 | 1.59 | 188 | 21.8% | 1.83 |
| 2.5 | BTC | +134.32% | 37.20% | 0.86 | 0.72 | 0.88 | 154 | 20.1% | 1.40 |
| 2.5 | SOL | +373.34% | 42.10% | 1.25 | 1.20 | 1.66 | 188 | 21.8% | 1.82 |
| 3 | BTC | +151.22% | 42.90% | 0.84 | 0.70 | 0.84 | 154 | 20.1% | 1.36 |
| 3 | SOL | +486.36% | 48.14% | 1.26 | 1.22 | 1.71 | 188 | 21.8% | 1.81 |

## 2026-03-06 00:27 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +182.12% | Max DD: 27.91% | Sharpe: 1.22 | Sortino: 1.16 | Calmar: 1.52
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.84
- Fees: $455.75 | Slippage: $1953.19 | Time in market: 34.9%
- Initial: $10,000 | Final: $28,212.25

## 2026-03-06 00:31 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.0
- Return: +112.27% | Max DD: 31.01% | Sharpe: 0.87 | Sortino: 0.73 | Calmar: 0.92
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.43
- Fees: $856.25 | Slippage: $3669.63 | Time in market: 30.7%
- Initial: $10,000 | Final: $21,227.29

## 2026-03-06 00:35 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.0
- Return: +271.15% | Max DD: 35.38% | Sharpe: 1.23 | Sortino: 1.18 | Calmar: 1.59
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.83
- Fees: $681.78 | Slippage: $2921.91 | Time in market: 34.9%
- Initial: $10,000 | Final: $37,115.28

## 2026-03-06 00:39 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.5
- Return: +134.32% | Max DD: 37.20% | Sharpe: 0.86 | Sortino: 0.72 | Calmar: 0.88
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.40
- Fees: $1113.66 | Slippage: $4772.82 | Time in market: 30.7%
- Initial: $10,000 | Final: $23,431.54

## 2026-03-06 00:43 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=2.5
- Return: +373.34% | Max DD: 42.10% | Sharpe: 1.25 | Sortino: 1.20 | Calmar: 1.66
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.82
- Fees: $945.63 | Slippage: $4052.69 | Time in market: 34.9%
- Initial: $10,000 | Final: $47,334.37

## 2026-03-06 00:47 UTC — Backtest: DonchianBreakout on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +151.22% | Max DD: 42.90% | Sharpe: 0.84 | Sortino: 0.70 | Calmar: 0.84
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.36
- Fees: $1370.71 | Slippage: $5874.47 | Time in market: 30.7%
- Initial: $10,000 | Final: $25,121.74

## 2026-03-06 00:51 UTC — Backtest: DonchianBreakout on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +486.36% | Max DD: 48.14% | Sharpe: 1.26 | Sortino: 1.22 | Calmar: 1.71
- Trades: 188 | Win rate: 21.8% | Profit factor: 1.81
- Fees: $1244.82 | Slippage: $5334.92 | Time in market: 34.9%
- Initial: $10,000 | Final: $58,636.21

## 2026-03-06 00:51 UTC — Parameter Sweep: DonchianBreakout (BTC, SOL)

Params: leverage=[1.0, 1.5, 2.0, 2.5, 3.0]

| Leverage | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BTC | +57.87% | 16.91% | 0.90 | 0.75 | 0.97 | 154 | 20.1% | 1.51 |
| 1 | SOL | +107.38% | 19.60% | 1.20 | 1.14 | 1.44 | 188 | 21.8% | 1.85 |
| 1.5 | BTC | +86.30% | 24.26% | 0.89 | 0.74 | 0.95 | 154 | 20.1% | 1.47 |
| 1.5 | SOL | +182.12% | 27.91% | 1.22 | 1.16 | 1.52 | 188 | 21.8% | 1.84 |
| 2 | BTC | +112.27% | 31.01% | 0.87 | 0.73 | 0.92 | 154 | 20.1% | 1.43 |
| 2 | SOL | +271.15% | 35.38% | 1.23 | 1.18 | 1.59 | 188 | 21.8% | 1.83 |
| 2.5 | BTC | +134.32% | 37.20% | 0.86 | 0.72 | 0.88 | 154 | 20.1% | 1.40 |
| 2.5 | SOL | +373.34% | 42.10% | 1.25 | 1.20 | 1.66 | 188 | 21.8% | 1.82 |
| 3 | BTC | +151.22% | 42.90% | 0.84 | 0.70 | 0.84 | 154 | 20.1% | 1.36 |
| 3 | SOL | +486.36% | 48.14% | 1.26 | 1.22 | 1.71 | 188 | 21.8% | 1.81 |

## 2026-03-06 03:12 UTC — Backtest: DonchianBreakout on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +4.46% | Max DD: 45.12% | Sharpe: 0.21 | Sortino: 0.18 | Calmar: 0.04
- Trades: 143 | Win rate: 17.5% | Profit factor: 1.02
- Fees: $630.61 | Slippage: $2702.61 | Time in market: 30.2%
- Initial: $10,000 | Final: $10,445.63

## 2026-03-06 03:14 UTC — Backtest: DonchianBreakout on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +13.67% | Max DD: 22.93% | Sharpe: 0.35 | Sortino: 0.31 | Calmar: 0.26
- Trades: 129 | Win rate: 20.2% | Profit factor: 1.18
- Fees: $266.59 | Slippage: $1142.53 | Time in market: 29.0%
- Initial: $10,000 | Final: $11,366.67

## 2026-03-06 03:14 UTC — Comparison: DonchianBreakout (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | +4.46% | 45.12% | 0.21 | 0.18 | 0.04 | 143 | 17.5% | 1.02 |
| SOL | +13.67% | 22.93% | 0.35 | 0.31 | 0.26 | 129 | 20.2% | 1.18 |

## 2026-03-06 03:16 UTC — Backtest: DonchianBreakout on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +4.08% | Max DD: 44.61% | Sharpe: 0.21 | Sortino: 0.17 | Calmar: 0.04
- Trades: 143 | Win rate: 17.5% | Profit factor: 1.02
- Fees: $630.53 | Slippage: $2702.28 | Time in market: 30.2%
- Initial: $10,000 | Final: $10,407.86

## 2026-03-06 03:19 UTC — Backtest: DonchianBreakout on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.46% | Max DD: 23.20% | Sharpe: 0.30 | Sortino: 0.27 | Calmar: 0.20
- Trades: 131 | Win rate: 21.4% | Profit factor: 1.14
- Fees: $264.39 | Slippage: $1133.08 | Time in market: 29.2%
- Initial: $10,000 | Final: $11,046.28

## 2026-03-06 03:19 UTC — Comparison: DonchianBreakout (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | +4.08% | 44.61% | 0.21 | 0.17 | 0.04 | 143 | 17.5% | 1.02 |
| SOL | +10.46% | 23.20% | 0.30 | 0.27 | 0.20 | 131 | 21.4% | 1.14 |

## 2026-03-06 08:21 UTC — Backtest: DonchianBreakout on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +47.58% | Max DD: 46.13% | Sharpe: 0.48 | Sortino: 0.41 | Calmar: 0.30
- Trades: 152 | Win rate: 16.4% | Profit factor: 1.18
- Fees: $434.10 | Slippage: $1860.41 | Time in market: 23.1%
- Initial: $10,000 | Final: $14,757.66

## 2026-03-06 08:22 UTC — Backtest: DonchianBreakout on ARB

- Period: 2023-07-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -5.08% | Max DD: 21.97% | Sharpe: -0.20 | Sortino: -0.17 | Calmar: -0.45
- Trades: 32 | Win rate: 18.8% | Profit factor: 0.83
- Fees: $75.22 | Slippage: $322.36 | Time in market: 33.2%
- Initial: $10,000 | Final: $9,491.98

## 2026-03-06 08:22 UTC — Backtest: DonchianBreakout on SUI

- Period: 2023-07-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.50% | Max DD: 21.29% | Sharpe: -0.36 | Sortino: -0.32 | Calmar: -0.59
- Trades: 28 | Win rate: 17.9% | Profit factor: 0.70
- Fees: $50.69 | Slippage: $217.26 | Time in market: 35.2%
- Initial: $10,000 | Final: $9,350.42

## 2026-03-06 08:22 UTC — Comparison: DonchianBreakout (ARB, SUI)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| ARB | -5.08% | 21.97% | -0.20 | -0.17 | -0.45 | 32 | 18.8% | 0.83 |
| SUI | -6.50% | 21.29% | -0.36 | -0.32 | -0.59 | 28 | 17.9% | 0.70 |

## 2026-03-06 08:24 UTC — Backtest: DonchianBreakout on AVAX

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +76.34% | Max DD: 34.18% | Sharpe: 0.71 | Sortino: 0.72 | Calmar: 0.61
- Trades: 212 | Win rate: 20.3% | Profit factor: 1.31
- Fees: $554.26 | Slippage: $2375.41 | Time in market: 34.3%
- Initial: $10,000 | Final: $17,633.50

## 2026-03-06 08:25 UTC — Backtest: DonchianBreakout on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -7.92% | Max DD: 42.43% | Sharpe: 0.04 | Sortino: 0.04 | Calmar: -0.06
- Trades: 184 | Win rate: 19.0% | Profit factor: 0.95
- Fees: $419.30 | Slippage: $1797.01 | Time in market: 30.4%
- Initial: $10,000 | Final: $9,207.97

## 2026-03-06 08:28 UTC — Backtest: DonchianBreakout on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -15.18% | Max DD: 41.17% | Sharpe: -0.04 | Sortino: -0.04 | Calmar: -0.13
- Trades: 194 | Win rate: 17.5% | Profit factor: 0.88
- Fees: $290.70 | Slippage: $1245.86 | Time in market: 31.3%
- Initial: $10,000 | Final: $8,481.71

## 2026-03-06 08:28 UTC — Comparison: DonchianBreakout (DOGE, AVAX, LINK)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| DOGE | +47.58% | 46.13% | 0.48 | 0.41 | 0.30 | 152 | 16.4% | 1.18 |
| AVAX | +76.34% | 34.18% | 0.71 | 0.72 | 0.61 | 212 | 20.3% | 1.31 |
| LINK | -15.18% | 41.17% | -0.04 | -0.04 | -0.13 | 194 | 17.5% | 0.88 |

## 2026-03-06 08:31 UTC — Backtest: DonchianBreakout on AVAX

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=72, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -18.92% | Max DD: 41.96% | Sharpe: -0.19 | Sortino: -0.17 | Calmar: -0.22
- Trades: 150 | Win rate: 16.7% | Profit factor: 0.81
- Fees: $215.30 | Slippage: $922.72 | Time in market: 29.8%
- Initial: $10,000 | Final: $8,108.47

## 2026-03-06 08:39 UTC -- Portfolio: BTC_SOL (equal weight)

- Period: 2021-01-01 to 2023-12-30
- Config: lookback=72, leverage=1.5, capital=$10,000 ($5,000/symbol)
- **Portfolio**: Return +134.21% | MaxDD 19.62% | Sharpe 1.26 | Sortino 1.28 | Calmar 1.67

| Symbol | Return | MaxDD | Sharpe | PF |
|--------|--------|-------|--------|----|
| BTC | +86.30% | 24.26% | 0.89 | 1.47 |
| SOL | +182.12% | 27.91% | 1.22 | 1.84 |

## 2026-03-06 08:43 UTC -- Portfolio: BTC_SOL (equal weight)

- Period: 2024-01-01 to 2026-03-04
- Config: lookback=72, leverage=1.5, capital=$10,000 ($5,000/symbol)
- **Portfolio**: Return +9.06% | MaxDD 26.14% | Sharpe 0.29 | Sortino 0.26 | Calmar 0.16

| Symbol | Return | MaxDD | Sharpe | PF |
|--------|--------|-------|--------|----|
| BTC | +4.46% | 45.12% | 0.21 | 1.02 |
| SOL | +13.67% | 22.93% | 0.35 | 1.18 |

## 2026-03-06 09:05 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -19.31% | Max DD: 29.42% | Sharpe: -0.61 | Sortino: -0.68 | Calmar: -0.23
- Trades: 1295 | Win rate: 18.3% | Profit factor: 0.74
- Fees: $303.00 | Slippage: $1298.56 | Time in market: 85.3%
- Initial: $10,000 | Final: $8,068.69

## 2026-03-06 09:09 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +29.65% | Max DD: 33.08% | Sharpe: 0.44 | Sortino: 0.50 | Calmar: 0.28
- Trades: 1896 | Win rate: 20.2% | Profit factor: 1.17
- Fees: $558.74 | Slippage: $2394.60 | Time in market: 84.7%
- Initial: $10,000 | Final: $12,964.97

## 2026-03-06 09:09 UTC — Comparison: DonchianMTF (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | -19.31% | 29.42% | -0.61 | -0.68 | -0.23 | 1295 | 18.3% | 0.74 |
| SOL | +29.65% | 33.08% | 0.44 | 0.50 | 0.28 | 1896 | 20.2% | 1.17 |

## 2026-03-06 09:15 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -19.48% | Max DD: 31.90% | Sharpe: -0.42 | Sortino: -0.47 | Calmar: -0.22
- Trades: 158 | Win rate: 19.6% | Profit factor: 0.55
- Fees: $68.79 | Slippage: $294.83 | Time in market: 87.6%
- Initial: $10,000 | Final: $8,051.57

## 2026-03-06 09:19 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -2.99% | Max DD: 37.28% | Sharpe: 0.16 | Sortino: 0.17 | Calmar: -0.03
- Trades: 339 | Win rate: 29.5% | Profit factor: 0.96
- Fees: $110.78 | Slippage: $474.77 | Time in market: 85.7%
- Initial: $10,000 | Final: $9,700.84

## 2026-03-06 09:19 UTC — Comparison: DonchianMTF (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | -19.48% | 31.90% | -0.42 | -0.47 | -0.22 | 158 | 19.6% | 0.55 |
| SOL | -2.99% | 37.28% | 0.16 | 0.17 | -0.03 | 339 | 29.5% | 0.96 |

## 2026-03-06 09:25 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +28.15% | Max DD: 12.90% | Sharpe: 0.83 | Sortino: 0.65 | Calmar: 0.67
- Trades: 136 | Win rate: 19.9% | Profit factor: 1.56
- Fees: $163.37 | Slippage: $700.16 | Time in market: 25.7%
- Initial: $10,000 | Final: $12,814.65

## 2026-03-06 09:28 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.63% | Max DD: 9.63% | Sharpe: 1.29 | Sortino: 1.10 | Calmar: 1.79
- Trades: 158 | Win rate: 22.8% | Profit factor: 2.08
- Fees: $107.09 | Slippage: $458.95 | Time in market: 29.7%
- Initial: $10,000 | Final: $15,963.13

## 2026-03-06 09:28 UTC — Comparison: DonchianMTF (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | +28.15% | 12.90% | 0.83 | 0.65 | 0.67 | 136 | 19.9% | 1.56 |
| SOL | +59.63% | 9.63% | 1.29 | 1.10 | 1.79 | 158 | 22.8% | 2.08 |

## 2026-03-06 09:30 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.64% | Max DD: 16.74% | Sharpe: 0.08 | Sortino: 0.05 | Calmar: 0.02
- Trades: 117 | Win rate: 19.7% | Profit factor: 1.01
- Fees: $143.96 | Slippage: $616.95 | Time in market: 24.8%
- Initial: $10,000 | Final: $10,063.97

## 2026-03-06 09:33 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.17% | Max DD: 10.36% | Sharpe: 0.34 | Sortino: 0.25 | Calmar: 0.27
- Trades: 109 | Win rate: 17.4% | Profit factor: 1.24
- Fees: $81.21 | Slippage: $348.06 | Time in market: 24.2%
- Initial: $10,000 | Final: $10,616.88

## 2026-03-06 09:33 UTC — Comparison: DonchianMTF (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | +0.64% | 16.74% | 0.08 | 0.05 | 0.02 | 117 | 19.7% | 1.01 |
| SOL | +6.17% | 10.36% | 0.34 | 0.25 | 0.27 | 109 | 17.4% | 1.24 |

## 2026-03-06 09:37 UTC -- Portfolio: BTC_SOL (equal weight)

- Period: 2024-01-01 to 2026-03-04
- Config: lookback=20, leverage=1.5, capital=$10,000 ($5,000/symbol)
- **Portfolio**: Return +3.40% | MaxDD 10.83% | Sharpe 0.24 | Sortino 0.18 | Calmar 0.14

| Symbol | Return | MaxDD | Sharpe | PF |
|--------|--------|-------|--------|----|
| BTC | +0.64% | 16.74% | 0.08 | 1.01 |
| SOL | +6.17% | 10.36% | 0.34 | 1.24 |

## 2026-03-06 09:41 UTC -- Portfolio: BTC_SOL (equal weight)

- Period: 2021-01-01 to 2023-12-30
- Config: lookback=20, leverage=1.5, capital=$10,000 ($5,000/symbol)
- **Portfolio**: Return +43.89% | MaxDD 7.20% | Sharpe 1.35 | Sortino 1.30 | Calmar 1.79

| Symbol | Return | MaxDD | Sharpe | PF |
|--------|--------|-------|--------|----|
| BTC | +28.15% | 12.90% | 0.83 | 1.56 |
| SOL | +59.63% | 9.63% | 1.29 | 2.08 |

## 2026-03-06 09:57 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +47.80% | Max DD: 12.33% | Sharpe: 1.01 | Sortino: 0.98 | Calmar: 1.13
- Trades: 204 | Win rate: 19.6% | Profit factor: 1.61
- Fees: $253.23 | Slippage: $1085.27 | Time in market: 38.8%
- Initial: $10,000 | Final: $14,779.55

## 2026-03-06 10:00 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +28.19% | Max DD: 14.31% | Sharpe: 0.71 | Sortino: 0.72 | Calmar: 0.62
- Trades: 246 | Win rate: 19.1% | Profit factor: 1.38
- Fees: $136.90 | Slippage: $586.69 | Time in market: 42.8%
- Initial: $10,000 | Final: $12,819.24

## 2026-03-06 10:04 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +46.72% | Max DD: 12.31% | Sharpe: 1.01 | Sortino: 0.97 | Calmar: 1.11
- Trades: 204 | Win rate: 19.6% | Profit factor: 1.64
- Fees: $229.46 | Slippage: $983.40 | Time in market: 38.8%
- Initial: $10,000 | Final: $14,671.53

## 2026-03-06 10:08 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +31.78% | Max DD: 14.22% | Sharpe: 0.80 | Sortino: 0.79 | Calmar: 0.69
- Trades: 246 | Win rate: 19.1% | Profit factor: 1.46
- Fees: $129.02 | Slippage: $552.95 | Time in market: 42.8%
- Initial: $10,000 | Final: $13,178.04

## 2026-03-06 10:12 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +32.33% | Max DD: 11.33% | Sharpe: 0.92 | Sortino: 0.74 | Calmar: 0.86
- Trades: 152 | Win rate: 20.4% | Profit factor: 1.58
- Fees: $175.41 | Slippage: $751.76 | Time in market: 29.7%
- Initial: $10,000 | Final: $13,233.47

## 2026-03-06 10:16 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +52.68% | Max DD: 11.55% | Sharpe: 1.17 | Sortino: 1.05 | Calmar: 1.34
- Trades: 180 | Win rate: 21.1% | Profit factor: 1.90
- Fees: $117.59 | Slippage: $503.96 | Time in market: 33.7%
- Initial: $10,000 | Final: $15,267.56

## 2026-03-06 10:19 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +23.37% | Max DD: 11.51% | Sharpe: 0.76 | Sortino: 0.58 | Calmar: 0.63
- Trades: 152 | Win rate: 20.4% | Profit factor: 1.46
- Fees: $154.36 | Slippage: $661.55 | Time in market: 29.7%
- Initial: $10,000 | Final: $12,337.08

## 2026-03-06 10:23 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +51.24% | Max DD: 11.18% | Sharpe: 1.18 | Sortino: 1.04 | Calmar: 1.35
- Trades: 180 | Win rate: 21.1% | Profit factor: 1.95
- Fees: $107.02 | Slippage: $458.65 | Time in market: 33.7%
- Initial: $10,000 | Final: $15,123.80

## 2026-03-06 10:27 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +28.15% | Max DD: 12.90% | Sharpe: 0.83 | Sortino: 0.65 | Calmar: 0.67
- Trades: 136 | Win rate: 19.9% | Profit factor: 1.56
- Fees: $163.37 | Slippage: $700.16 | Time in market: 25.7%
- Initial: $10,000 | Final: $12,814.65

## 2026-03-06 10:31 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.63% | Max DD: 9.63% | Sharpe: 1.29 | Sortino: 1.10 | Calmar: 1.79
- Trades: 158 | Win rate: 22.8% | Profit factor: 2.08
- Fees: $107.09 | Slippage: $458.95 | Time in market: 29.7%
- Initial: $10,000 | Final: $15,963.13

## 2026-03-06 10:35 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +21.87% | Max DD: 12.21% | Sharpe: 0.72 | Sortino: 0.53 | Calmar: 0.56
- Trades: 136 | Win rate: 19.9% | Profit factor: 1.47
- Fees: $146.43 | Slippage: $627.54 | Time in market: 25.7%
- Initial: $10,000 | Final: $12,187.19

## 2026-03-06 10:38 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +60.83% | Max DD: 9.42% | Sharpe: 1.34 | Sortino: 1.12 | Calmar: 1.86
- Trades: 158 | Win rate: 22.8% | Profit factor: 2.20
- Fees: $99.13 | Slippage: $424.84 | Time in market: 29.7%
- Initial: $10,000 | Final: $16,082.52

## 2026-03-06 10:42 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +37.81% | Max DD: 11.85% | Sharpe: 1.02 | Sortino: 0.83 | Calmar: 0.95
- Trades: 150 | Win rate: 20.0% | Profit factor: 1.70
- Fees: $175.96 | Slippage: $754.12 | Time in market: 29.3%
- Initial: $10,000 | Final: $13,780.99

## 2026-03-06 10:46 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.75% | Max DD: 11.57% | Sharpe: 1.29 | Sortino: 1.16 | Calmar: 1.49
- Trades: 178 | Win rate: 21.3% | Profit factor: 2.06
- Fees: $114.61 | Slippage: $491.20 | Time in market: 33.6%
- Initial: $10,000 | Final: $15,975.13

## 2026-03-06 10:50 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +29.55% | Max DD: 12.11% | Sharpe: 0.92 | Sortino: 0.69 | Calmar: 0.74
- Trades: 150 | Win rate: 20.0% | Profit factor: 1.61
- Fees: $154.36 | Slippage: $661.52 | Time in market: 29.3%
- Initial: $10,000 | Final: $12,954.86

## 2026-03-06 10:53 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.90% | Max DD: 11.19% | Sharpe: 1.33 | Sortino: 1.17 | Calmar: 1.55
- Trades: 178 | Win rate: 21.3% | Profit factor: 2.17
- Fees: $102.71 | Slippage: $440.20 | Time in market: 33.6%
- Initial: $10,000 | Final: $15,990.47

## 2026-03-06 10:57 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +37.97% | Max DD: 10.72% | Sharpe: 1.07 | Sortino: 0.77 | Calmar: 1.06
- Trades: 112 | Win rate: 20.5% | Profit factor: 1.88
- Fees: $141.17 | Slippage: $605.03 | Time in market: 21.3%
- Initial: $10,000 | Final: $13,796.91

## 2026-03-06 11:01 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.27% | Max DD: 10.07% | Sharpe: 1.39 | Sortino: 1.12 | Calmar: 1.70
- Trades: 134 | Win rate: 23.9% | Profit factor: 2.38
- Fees: $87.68 | Slippage: $375.76 | Time in market: 26.2%
- Initial: $10,000 | Final: $15,927.28

## 2026-03-06 11:05 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +31.38% | Max DD: 10.61% | Sharpe: 0.99 | Sortino: 0.67 | Calmar: 0.90
- Trades: 112 | Win rate: 20.5% | Profit factor: 1.80
- Fees: $126.53 | Slippage: $542.28 | Time in market: 21.3%
- Initial: $10,000 | Final: $13,137.58

## 2026-03-06 11:09 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.88% | Max DD: 9.54% | Sharpe: 1.43 | Sortino: 1.13 | Calmar: 1.81
- Trades: 134 | Win rate: 23.9% | Profit factor: 2.53
- Fees: $79.41 | Slippage: $340.33 | Time in market: 26.2%
- Initial: $10,000 | Final: $15,988.21

## 2026-03-06 11:12 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +4.11% | Max DD: 11.85% | Sharpe: 0.21 | Sortino: 0.12 | Calmar: 0.11
- Trades: 102 | Win rate: 16.7% | Profit factor: 1.11
- Fees: $104.31 | Slippage: $447.03 | Time in market: 18.0%
- Initial: $10,000 | Final: $10,410.93

## 2026-03-06 11:16 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +61.11% | Max DD: 6.36% | Sharpe: 1.45 | Sortino: 1.03 | Calmar: 2.77
- Trades: 104 | Win rate: 23.1% | Profit factor: 2.86
- Fees: $73.05 | Slippage: $313.07 | Time in market: 20.5%
- Initial: $10,000 | Final: $16,110.95

## 2026-03-06 11:20 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +3.09% | Max DD: 11.17% | Sharpe: 0.17 | Sortino: 0.10 | Calmar: 0.09
- Trades: 102 | Win rate: 16.7% | Profit factor: 1.09
- Fees: $93.81 | Slippage: $402.04 | Time in market: 18.0%
- Initial: $10,000 | Final: $10,309.20

## 2026-03-06 11:24 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +62.00% | Max DD: 6.03% | Sharpe: 1.49 | Sortino: 1.04 | Calmar: 2.96
- Trades: 104 | Win rate: 23.1% | Profit factor: 3.02
- Fees: $69.44 | Slippage: $297.61 | Time in market: 20.5%
- Initial: $10,000 | Final: $16,199.89

## 2026-03-06 11:28 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +61.46% | Max DD: 12.66% | Sharpe: 1.23 | Sortino: 1.11 | Calmar: 1.37
- Trades: 154 | Win rate: 20.1% | Profit factor: 1.97
- Fees: $208.28 | Slippage: $892.65 | Time in market: 30.7%
- Initial: $10,000 | Final: $16,145.76

## 2026-03-06 11:31 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +58.67% | Max DD: 11.52% | Sharpe: 1.21 | Sortino: 1.11 | Calmar: 1.48
- Trades: 184 | Win rate: 21.2% | Profit factor: 1.96
- Fees: $128.16 | Slippage: $549.25 | Time in market: 34.1%
- Initial: $10,000 | Final: $15,867.34

## 2026-03-06 11:35 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +60.06% | Max DD: 12.86% | Sharpe: 1.23 | Sortino: 1.09 | Calmar: 1.32
- Trades: 154 | Win rate: 20.1% | Profit factor: 2.01
- Fees: $193.86 | Slippage: $830.81 | Time in market: 30.7%
- Initial: $10,000 | Final: $16,006.48

## 2026-03-06 11:39 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.46% | Max DD: 11.14% | Sharpe: 1.24 | Sortino: 1.12 | Calmar: 1.54
- Trades: 184 | Win rate: 21.2% | Profit factor: 2.04
- Fees: $120.67 | Slippage: $517.16 | Time in market: 34.1%
- Initial: $10,000 | Final: $15,945.76

## 2026-03-06 11:43 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +33.17% | Max DD: 10.50% | Sharpe: 1.00 | Sortino: 0.70 | Calmar: 0.96
- Trades: 110 | Win rate: 20.9% | Profit factor: 1.81
- Fees: $132.78 | Slippage: $569.06 | Time in market: 21.1%
- Initial: $10,000 | Final: $13,317.12

## 2026-03-06 11:47 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +55.71% | Max DD: 8.45% | Sharpe: 1.35 | Sortino: 1.04 | Calmar: 1.93
- Trades: 130 | Win rate: 23.1% | Profit factor: 2.37
- Fees: $85.26 | Slippage: $365.41 | Time in market: 24.8%
- Initial: $10,000 | Final: $15,570.66

## 2026-03-06 11:50 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +24.68% | Max DD: 10.30% | Sharpe: 0.87 | Sortino: 0.57 | Calmar: 0.74
- Trades: 110 | Win rate: 20.9% | Profit factor: 1.67
- Fees: $116.08 | Slippage: $497.50 | Time in market: 21.1%
- Initial: $10,000 | Final: $12,468.37

## 2026-03-06 11:54 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +57.82% | Max DD: 7.63% | Sharpe: 1.42 | Sortino: 1.08 | Calmar: 2.20
- Trades: 130 | Win rate: 23.1% | Profit factor: 2.57
- Fees: $78.80 | Slippage: $337.69 | Time in market: 24.8%
- Initial: $10,000 | Final: $15,781.83

## 2026-03-06 11:54 UTC — Parameter Sweep: DonchianMTF (BTC, SOL)

Params: combo=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], lookbacks=['18/48/168', '24/72/168', '24/72/252', '36/120/504', '36/72/336', '36/96/252', '48/120/336', '48/168/504'], weights=['equal', 'med-heavy']

| Combo | Lookbacks | Weights | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F | 48/168/504 | equal | SOL | +62.00% | 6.03% | 1.49 | 1.04 | 2.96 | 104 | 23.1% | 3.02 |
| F | 48/168/504 | med-heavy | SOL | +61.11% | 6.36% | 1.45 | 1.03 | 2.77 | 104 | 23.1% | 2.86 |
| E | 48/120/336 | equal | SOL | +59.88% | 9.54% | 1.43 | 1.13 | 1.81 | 134 | 23.9% | 2.53 |
| H | 36/120/504 | equal | SOL | +57.82% | 7.63% | 1.42 | 1.08 | 2.20 | 130 | 23.1% | 2.57 |
| E | 48/120/336 | med-heavy | SOL | +59.27% | 10.07% | 1.39 | 1.12 | 1.70 | 134 | 23.9% | 2.38 |
| H | 36/120/504 | med-heavy | SOL | +55.71% | 8.45% | 1.35 | 1.04 | 1.93 | 130 | 23.1% | 2.37 |
| C | 36/96/252 | equal | SOL | +60.83% | 9.42% | 1.34 | 1.12 | 1.86 | 158 | 22.8% | 2.20 |
| D | 36/72/336 | equal | SOL | +59.90% | 11.19% | 1.33 | 1.17 | 1.55 | 178 | 21.3% | 2.17 |
| C | 36/96/252 | med-heavy | SOL | +59.63% | 9.63% | 1.29 | 1.10 | 1.79 | 158 | 22.8% | 2.08 |
| D | 36/72/336 | med-heavy | SOL | +59.75% | 11.57% | 1.29 | 1.16 | 1.49 | 178 | 21.3% | 2.06 |
| G | 24/72/168 | equal | SOL | +59.46% | 11.14% | 1.24 | 1.12 | 1.54 | 184 | 21.2% | 2.04 |
| G | 24/72/168 | equal | BTC | +60.06% | 12.86% | 1.23 | 1.09 | 1.32 | 154 | 20.1% | 2.01 |
| G | 24/72/168 | med-heavy | BTC | +61.46% | 12.66% | 1.23 | 1.11 | 1.37 | 154 | 20.1% | 1.97 |
| G | 24/72/168 | med-heavy | SOL | +58.67% | 11.52% | 1.21 | 1.11 | 1.48 | 184 | 21.2% | 1.96 |
| B | 24/72/252 | equal | SOL | +51.24% | 11.18% | 1.18 | 1.04 | 1.35 | 180 | 21.1% | 1.95 |
| B | 24/72/252 | med-heavy | SOL | +52.68% | 11.55% | 1.17 | 1.05 | 1.34 | 180 | 21.1% | 1.90 |
| E | 48/120/336 | med-heavy | BTC | +37.97% | 10.72% | 1.07 | 0.77 | 1.06 | 112 | 20.5% | 1.88 |
| D | 36/72/336 | med-heavy | BTC | +37.81% | 11.85% | 1.02 | 0.83 | 0.95 | 150 | 20.0% | 1.70 |
| A | 18/48/168 | equal | BTC | +46.72% | 12.31% | 1.01 | 0.97 | 1.11 | 204 | 19.6% | 1.64 |
| A | 18/48/168 | med-heavy | BTC | +47.80% | 12.33% | 1.01 | 0.98 | 1.13 | 204 | 19.6% | 1.61 |
| H | 36/120/504 | med-heavy | BTC | +33.17% | 10.50% | 1.00 | 0.70 | 0.96 | 110 | 20.9% | 1.81 |
| E | 48/120/336 | equal | BTC | +31.38% | 10.61% | 0.99 | 0.67 | 0.90 | 112 | 20.5% | 1.80 |
| B | 24/72/252 | med-heavy | BTC | +32.33% | 11.33% | 0.92 | 0.74 | 0.86 | 152 | 20.4% | 1.58 |
| D | 36/72/336 | equal | BTC | +29.55% | 12.11% | 0.92 | 0.69 | 0.74 | 150 | 20.0% | 1.61 |
| H | 36/120/504 | equal | BTC | +24.68% | 10.30% | 0.87 | 0.57 | 0.74 | 110 | 20.9% | 1.67 |
| C | 36/96/252 | med-heavy | BTC | +28.15% | 12.90% | 0.83 | 0.65 | 0.67 | 136 | 19.9% | 1.56 |
| A | 18/48/168 | equal | SOL | +31.78% | 14.22% | 0.80 | 0.79 | 0.69 | 246 | 19.1% | 1.46 |
| B | 24/72/252 | equal | BTC | +23.37% | 11.51% | 0.76 | 0.58 | 0.63 | 152 | 20.4% | 1.46 |
| C | 36/96/252 | equal | BTC | +21.87% | 12.21% | 0.72 | 0.53 | 0.56 | 136 | 19.9% | 1.47 |
| A | 18/48/168 | med-heavy | SOL | +28.19% | 14.31% | 0.71 | 0.72 | 0.62 | 246 | 19.1% | 1.38 |
| F | 48/168/504 | med-heavy | BTC | +4.11% | 11.85% | 0.21 | 0.12 | 0.11 | 102 | 16.7% | 1.11 |
| F | 48/168/504 | equal | BTC | +3.09% | 11.17% | 0.17 | 0.10 | 0.09 | 102 | 16.7% | 1.09 |

## 2026-03-06 20:56 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.79% | Max DD: 14.81% | Sharpe: 0.19 | Sortino: 0.11 | Calmar: 0.09
- Trades: 103 | Win rate: 18.4% | Profit factor: 1.09
- Fees: $114.89 | Slippage: $492.37 | Time in market: 21.1%
- Initial: $10,000 | Final: $10,279.07

## 2026-03-06 20:56 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.74% | Max DD: 16.70% | Sharpe: 0.37 | Sortino: 0.25 | Calmar: 0.18
- Trades: 141 | Win rate: 17.0% | Profit factor: 1.17
- Fees: $155.70 | Slippage: $667.30 | Time in market: 29.5%
- Initial: $10,000 | Final: $10,673.86

## 2026-03-06 20:56 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.74% | Max DD: 16.70% | Sharpe: 0.37 | Sortino: 0.25 | Calmar: 0.18
- Trades: 141 | Win rate: 17.0% | Profit factor: 1.17
- Fees: $155.70 | Slippage: $667.30 | Time in market: 29.5%
- Initial: $10,000 | Final: $10,673.86

## 2026-03-06 20:56 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.46% | Max DD: 11.13% | Sharpe: 0.19 | Sortino: 0.12 | Calmar: 0.10
- Trades: 72 | Win rate: 18.1% | Profit factor: 1.12
- Fees: $50.23 | Slippage: $215.27 | Time in market: 15.3%
- Initial: $10,000 | Final: $10,246.41

## 2026-03-06 20:58 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +9.17% | Max DD: 10.14% | Sharpe: 0.49 | Sortino: 0.33 | Calmar: 0.41
- Trades: 93 | Win rate: 18.3% | Profit factor: 1.47
- Fees: $65.02 | Slippage: $278.67 | Time in market: 21.1%
- Initial: $10,000 | Final: $10,917.18

## 2026-03-06 20:58 UTC — Comparison: DonchianMTF (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | +2.79% | 14.81% | 0.19 | 0.11 | 0.09 | 103 | 18.4% | 1.09 |
| SOL | +9.17% | 10.14% | 0.49 | 0.33 | 0.41 | 93 | 18.3% | 1.47 |

## 2026-03-06 20:58 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.88% | Max DD: 9.64% | Sharpe: 0.35 | Sortino: 0.27 | Calmar: 0.32
- Trades: 127 | Win rate: 20.5% | Profit factor: 1.24
- Fees: $90.80 | Slippage: $389.15 | Time in market: 28.8%
- Initial: $10,000 | Final: $10,687.59

## 2026-03-06 20:58 UTC — Comparison: DonchianMTF (BTC, SOL)

| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
|--------|--------|-------|--------|---------|--------|--------|---------|-----|
| BTC | +6.74% | 16.70% | 0.37 | 0.25 | 0.18 | 141 | 17.0% | 1.17 |
| SOL | +6.88% | 9.64% | 0.35 | 0.27 | 0.32 | 127 | 20.5% | 1.24 |

## 2026-03-06 22:11 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -8.19% | Max DD: 18.52% | Sharpe: -0.24 | Sortino: -0.22 | Calmar: -0.15
- Trades: 236 | Win rate: 19.1% | Profit factor: 0.87
- Fees: $159.40 | Slippage: $683.15 | Time in market: 39.7%
- Initial: $10,000 | Final: $9,180.79

## 2026-03-06 22:11 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -5.84% | Max DD: 21.91% | Sharpe: -0.16 | Sortino: -0.15 | Calmar: -0.09
- Trades: 232 | Win rate: 17.7% | Profit factor: 0.90
- Fees: $124.17 | Slippage: $532.16 | Time in market: 40.2%
- Initial: $10,000 | Final: $9,416.15

## 2026-03-06 22:14 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +1.68% | Max DD: 20.49% | Sharpe: 0.11 | Sortino: 0.08 | Calmar: 0.03
- Trades: 200 | Win rate: 18.0% | Profit factor: 1.03
- Fees: $103.46 | Slippage: $443.42 | Time in market: 31.5%
- Initial: $10,000 | Final: $10,168.37

## 2026-03-06 22:14 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +14.10% | Max DD: 11.23% | Sharpe: 0.44 | Sortino: 0.44 | Calmar: 0.40
- Trades: 226 | Win rate: 19.5% | Profit factor: 1.20
- Fees: $120.81 | Slippage: $517.76 | Time in market: 38.1%
- Initial: $10,000 | Final: $11,409.81

## 2026-03-06 22:18 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +90.31% | Max DD: 12.64% | Sharpe: 1.49 | Sortino: 1.51 | Calmar: 1.89
- Trades: 191 | Win rate: 20.4% | Profit factor: 1.93
- Fees: $207.28 | Slippage: $888.36 | Time in market: 35.0%
- Initial: $10,000 | Final: $19,030.70

## 2026-03-06 22:18 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -10.69% | Max DD: 21.70% | Sharpe: -0.34 | Sortino: -0.31 | Calmar: -0.17
- Trades: 234 | Win rate: 17.9% | Profit factor: 0.80
- Fees: $108.84 | Slippage: $466.45 | Time in market: 36.9%
- Initial: $10,000 | Final: $8,930.75

## 2026-03-06 22:22 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -16.40% | Max DD: 27.72% | Sharpe: -0.81 | Sortino: -0.67 | Calmar: -0.21
- Trades: 250 | Win rate: 12.8% | Profit factor: 0.59
- Fees: $73.90 | Slippage: $316.71 | Time in market: 34.2%
- Initial: $10,000 | Final: $8,359.51

## 2026-03-06 22:22 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.38% | Max DD: 18.85% | Sharpe: 0.23 | Sortino: 0.17 | Calmar: 0.11
- Trades: 196 | Win rate: 19.9% | Profit factor: 1.11
- Fees: $137.57 | Slippage: $589.58 | Time in market: 31.0%
- Initial: $10,000 | Final: $10,638.28

## 2026-03-06 22:23 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +18.86% | Max DD: 6.72% | Sharpe: 0.90 | Sortino: 0.93 | Calmar: 1.72
- Trades: 116 | Win rate: 24.1% | Profit factor: 1.63
- Fees: $69.18 | Slippage: $296.48 | Time in market: 39.9%
- Initial: $10,000 | Final: $11,885.81

## 2026-03-06 22:26 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +20.97% | Max DD: 21.14% | Sharpe: 0.58 | Sortino: 0.55 | Calmar: 0.31
- Trades: 230 | Win rate: 16.5% | Profit factor: 1.31
- Fees: $154.13 | Slippage: $660.54 | Time in market: 36.0%
- Initial: $10,000 | Final: $12,097.43

## 2026-03-06 22:27 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -4.99% | Max DD: 21.49% | Sharpe: -0.14 | Sortino: -0.13 | Calmar: -0.08
- Trades: 232 | Win rate: 17.7% | Profit factor: 0.91
- Fees: $114.31 | Slippage: $489.91 | Time in market: 40.2%
- Initial: $10,000 | Final: $9,501.04

## 2026-03-06 22:30 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -8.76% | Max DD: 18.51% | Sharpe: -0.28 | Sortino: -0.24 | Calmar: -0.16
- Trades: 236 | Win rate: 19.1% | Profit factor: 0.85
- Fees: $146.23 | Slippage: $626.68 | Time in market: 39.7%
- Initial: $10,000 | Final: $9,124.24

## 2026-03-06 22:31 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +15.33% | Max DD: 11.01% | Sharpe: 0.48 | Sortino: 0.47 | Calmar: 0.44
- Trades: 226 | Win rate: 19.5% | Profit factor: 1.24
- Fees: $112.75 | Slippage: $483.21 | Time in market: 38.1%
- Initial: $10,000 | Final: $11,533.48

## 2026-03-06 22:34 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.62% | Max DD: 19.96% | Sharpe: 0.13 | Sortino: 0.10 | Calmar: 0.04
- Trades: 200 | Win rate: 18.0% | Profit factor: 1.05
- Fees: $96.19 | Slippage: $412.23 | Time in market: 31.5%
- Initial: $10,000 | Final: $10,261.83

## 2026-03-06 22:35 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +89.10% | Max DD: 13.06% | Sharpe: 1.50 | Sortino: 1.50 | Calmar: 1.81
- Trades: 191 | Win rate: 20.4% | Profit factor: 2.00
- Fees: $189.01 | Slippage: $810.02 | Time in market: 35.0%
- Initial: $10,000 | Final: $18,909.59

## 2026-03-06 22:38 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -10.41% | Max DD: 21.76% | Sharpe: -0.35 | Sortino: -0.31 | Calmar: -0.17
- Trades: 234 | Win rate: 17.9% | Profit factor: 0.79
- Fees: $98.71 | Slippage: $423.05 | Time in market: 36.9%
- Initial: $10,000 | Final: $8,959.05

## 2026-03-06 22:39 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -16.39% | Max DD: 26.65% | Sharpe: -0.83 | Sortino: -0.67 | Calmar: -0.22
- Trades: 250 | Win rate: 12.8% | Profit factor: 0.58
- Fees: $71.70 | Slippage: $307.30 | Time in market: 34.2%
- Initial: $10,000 | Final: $8,360.92

## 2026-03-06 22:40 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +19.03% | Max DD: 6.44% | Sharpe: 0.93 | Sortino: 0.95 | Calmar: 1.81
- Trades: 116 | Win rate: 24.1% | Profit factor: 1.71
- Fees: $63.97 | Slippage: $274.16 | Time in market: 39.9%
- Initial: $10,000 | Final: $11,902.74

## 2026-03-06 22:42 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.50% | Max DD: 18.13% | Sharpe: 0.24 | Sortino: 0.18 | Calmar: 0.12
- Trades: 196 | Win rate: 19.9% | Profit factor: 1.12
- Fees: $128.59 | Slippage: $551.09 | Time in market: 31.0%
- Initial: $10,000 | Final: $10,650.23

## 2026-03-06 22:44 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -10.66% | Max DD: 21.16% | Sharpe: -0.40 | Sortino: -0.33 | Calmar: -0.17
- Trades: 186 | Win rate: 18.8% | Profit factor: 0.77
- Fees: $100.08 | Slippage: $428.93 | Time in market: 32.1%
- Initial: $10,000 | Final: $8,933.78

## 2026-03-06 22:46 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +22.80% | Max DD: 21.73% | Sharpe: 0.64 | Sortino: 0.59 | Calmar: 0.33
- Trades: 230 | Win rate: 16.5% | Profit factor: 1.37
- Fees: $139.81 | Slippage: $599.18 | Time in market: 36.0%
- Initial: $10,000 | Final: $12,280.33

## 2026-03-06 22:48 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +14.52% | Max DD: 11.26% | Sharpe: 0.48 | Sortino: 0.43 | Calmar: 0.41
- Trades: 178 | Win rate: 18.5% | Profit factor: 1.28
- Fees: $93.48 | Slippage: $400.62 | Time in market: 30.5%
- Initial: $10,000 | Final: $11,452.35

## 2026-03-06 22:50 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -7.57% | Max DD: 17.09% | Sharpe: -0.25 | Sortino: -0.19 | Calmar: -0.15
- Trades: 180 | Win rate: 18.9% | Profit factor: 0.86
- Fees: $137.94 | Slippage: $591.17 | Time in market: 29.8%
- Initial: $10,000 | Final: $9,242.57

## 2026-03-06 22:52 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +84.31% | Max DD: 12.19% | Sharpe: 1.66 | Sortino: 1.47 | Calmar: 1.86
- Trades: 141 | Win rate: 23.4% | Profit factor: 2.37
- Fees: $150.35 | Slippage: $644.34 | Time in market: 27.8%
- Initial: $10,000 | Final: $18,431.05

## 2026-03-06 22:54 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.97% | Max DD: 18.35% | Sharpe: -0.02 | Sortino: -0.01 | Calmar: -0.04
- Trades: 150 | Win rate: 16.0% | Profit factor: 0.96
- Fees: $69.59 | Slippage: $298.23 | Time in market: 23.0%
- Initial: $10,000 | Final: $9,802.55

## 2026-03-06 22:55 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -25.19% | Max DD: 26.48% | Sharpe: -1.48 | Sortino: -1.05 | Calmar: -0.35
- Trades: 202 | Win rate: 12.4% | Profit factor: 0.35
- Fees: $64.50 | Slippage: $276.42 | Time in market: 26.1%
- Initial: $10,000 | Final: $7,481.25

## 2026-03-06 22:57 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +11.16% | Max DD: 7.21% | Sharpe: 0.62 | Sortino: 0.58 | Calmar: 0.96
- Trades: 94 | Win rate: 23.4% | Profit factor: 1.44
- Fees: $54.26 | Slippage: $232.54 | Time in market: 31.0%
- Initial: $10,000 | Final: $11,116.07

## 2026-03-06 22:57 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -3.50% | Max DD: 16.93% | Sharpe: -0.07 | Sortino: -0.06 | Calmar: -0.07
- Trades: 188 | Win rate: 18.1% | Profit factor: 0.92
- Fees: $99.26 | Slippage: $425.40 | Time in market: 30.2%
- Initial: $10,000 | Final: $9,649.55

## 2026-03-06 23:00 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -11.30% | Max DD: 21.21% | Sharpe: -0.46 | Sortino: -0.36 | Calmar: -0.18
- Trades: 186 | Win rate: 18.8% | Profit factor: 0.73
- Fees: $88.73 | Slippage: $380.26 | Time in market: 32.1%
- Initial: $10,000 | Final: $8,870.36

## 2026-03-06 23:01 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +8.09% | Max DD: 15.52% | Sharpe: 0.30 | Sortino: 0.23 | Calmar: 0.17
- Trades: 152 | Win rate: 18.4% | Profit factor: 1.18
- Fees: $110.38 | Slippage: $473.05 | Time in market: 24.3%
- Initial: $10,000 | Final: $10,809.11

## 2026-03-06 23:04 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +16.06% | Max DD: 10.82% | Sharpe: 0.53 | Sortino: 0.47 | Calmar: 0.47
- Trades: 178 | Win rate: 18.5% | Profit factor: 1.33
- Fees: $87.56 | Slippage: $375.24 | Time in market: 30.5%
- Initial: $10,000 | Final: $11,605.66

## 2026-03-06 23:05 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -3.66% | Max DD: 18.02% | Sharpe: -0.08 | Sortino: -0.06 | Calmar: -0.07
- Trades: 186 | Win rate: 15.6% | Profit factor: 0.93
- Fees: $115.84 | Slippage: $496.47 | Time in market: 28.0%
- Initial: $10,000 | Final: $9,633.71

## 2026-03-06 23:08 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +78.02% | Max DD: 11.57% | Sharpe: 1.63 | Sortino: 1.41 | Calmar: 1.83
- Trades: 141 | Win rate: 23.4% | Profit factor: 2.44
- Fees: $132.29 | Slippage: $566.97 | Time in market: 27.8%
- Initial: $10,000 | Final: $17,801.74

## 2026-03-06 23:09 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.42% | Max DD: 16.89% | Sharpe: -0.35 | Sortino: -0.26 | Calmar: -0.19
- Trades: 180 | Win rate: 18.9% | Profit factor: 0.81
- Fees: $126.47 | Slippage: $542.03 | Time in market: 29.8%
- Initial: $10,000 | Final: $9,058.34

## 2026-03-06 23:12 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -24.75% | Max DD: 26.05% | Sharpe: -1.47 | Sortino: -1.02 | Calmar: -0.35
- Trades: 202 | Win rate: 12.4% | Profit factor: 0.33
- Fees: $60.94 | Slippage: $261.18 | Time in market: 26.1%
- Initial: $10,000 | Final: $7,525.24

## 2026-03-06 23:13 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.21% | Max DD: 18.16% | Sharpe: 0.00 | Sortino: 0.00 | Calmar: -0.02
- Trades: 150 | Win rate: 16.0% | Profit factor: 0.97
- Fees: $63.99 | Slippage: $274.23 | Time in market: 23.0%
- Initial: $10,000 | Final: $9,878.57

## 2026-03-06 23:13 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +11.21% | Max DD: 7.28% | Sharpe: 0.64 | Sortino: 0.59 | Calmar: 0.95
- Trades: 94 | Win rate: 23.4% | Profit factor: 1.47
- Fees: $50.67 | Slippage: $217.15 | Time in market: 31.0%
- Initial: $10,000 | Final: $11,121.31

## 2026-03-06 23:17 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -2.50% | Max DD: 16.51% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.05
- Trades: 188 | Win rate: 18.1% | Profit factor: 0.94
- Fees: $91.28 | Slippage: $391.20 | Time in market: 30.2%
- Initial: $10,000 | Final: $9,750.28

## 2026-03-06 23:17 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.12% | Max DD: 20.61% | Sharpe: -0.33 | Sortino: -0.26 | Calmar: -0.15
- Trades: 168 | Win rate: 19.0% | Profit factor: 0.78
- Fees: $95.14 | Slippage: $407.76 | Time in market: 27.9%
- Initial: $10,000 | Final: $9,088.25

## 2026-03-06 23:21 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +8.49% | Max DD: 14.94% | Sharpe: 0.31 | Sortino: 0.24 | Calmar: 0.18
- Trades: 152 | Win rate: 18.4% | Profit factor: 1.20
- Fees: $101.94 | Slippage: $436.90 | Time in market: 24.3%
- Initial: $10,000 | Final: $10,849.02

## 2026-03-06 23:21 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +26.78% | Max DD: 9.62% | Sharpe: 0.81 | Sortino: 0.71 | Calmar: 0.86
- Trades: 146 | Win rate: 21.9% | Profit factor: 1.62
- Fees: $87.34 | Slippage: $374.29 | Time in market: 27.4%
- Initial: $10,000 | Final: $12,678.27

## 2026-03-06 23:25 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +83.86% | Max DD: 10.66% | Sharpe: 1.66 | Sortino: 1.36 | Calmar: 2.11
- Trades: 123 | Win rate: 25.2% | Profit factor: 2.56
- Fees: $132.51 | Slippage: $567.89 | Time in market: 23.1%
- Initial: $10,000 | Final: $18,386.13

## 2026-03-06 23:25 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -5.44% | Max DD: 18.72% | Sharpe: -0.15 | Sortino: -0.12 | Calmar: -0.10
- Trades: 186 | Win rate: 15.6% | Profit factor: 0.88
- Fees: $105.58 | Slippage: $452.48 | Time in market: 28.0%
- Initial: $10,000 | Final: $9,456.21

## 2026-03-06 23:29 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -19.45% | Max DD: 21.24% | Sharpe: -0.97 | Sortino: -0.68 | Calmar: -0.33
- Trades: 170 | Win rate: 13.5% | Profit factor: 0.46
- Fees: $68.47 | Slippage: $293.43 | Time in market: 23.4%
- Initial: $10,000 | Final: $8,055.37

## 2026-03-06 23:29 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -10.62% | Max DD: 17.35% | Sharpe: -0.41 | Sortino: -0.30 | Calmar: -0.21
- Trades: 164 | Win rate: 17.1% | Profit factor: 0.79
- Fees: $114.53 | Slippage: $490.84 | Time in market: 26.3%
- Initial: $10,000 | Final: $8,938.00

## 2026-03-06 23:30 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.08% | Max DD: 6.74% | Sharpe: 0.66 | Sortino: 0.59 | Calmar: 1.11
- Trades: 84 | Win rate: 25.0% | Profit factor: 1.50
- Fees: $51.55 | Slippage: $220.95 | Time in market: 26.9%
- Initial: $10,000 | Final: $11,207.63

## 2026-03-06 23:33 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.47% | Max DD: 18.44% | Sharpe: -0.20 | Sortino: -0.12 | Calmar: -0.12
- Trades: 128 | Win rate: 17.2% | Profit factor: 0.84
- Fees: $60.50 | Slippage: $259.29 | Time in market: 19.0%
- Initial: $10,000 | Final: $9,353.48

## 2026-03-06 23:34 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.40% | Max DD: 20.10% | Sharpe: -0.35 | Sortino: -0.27 | Calmar: -0.16
- Trades: 168 | Win rate: 19.0% | Profit factor: 0.76
- Fees: $87.59 | Slippage: $375.39 | Time in market: 27.9%
- Initial: $10,000 | Final: $9,060.15

## 2026-03-06 23:37 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.98% | Max DD: 17.03% | Sharpe: 0.01 | Sortino: 0.01 | Calmar: -0.02
- Trades: 162 | Win rate: 17.3% | Profit factor: 0.97
- Fees: $82.42 | Slippage: $353.23 | Time in market: 24.7%
- Initial: $10,000 | Final: $9,901.58

## 2026-03-06 23:38 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +28.11% | Max DD: 9.30% | Sharpe: 0.86 | Sortino: 0.73 | Calmar: 0.93
- Trades: 146 | Win rate: 21.9% | Profit factor: 1.73
- Fees: $80.47 | Slippage: $344.89 | Time in market: 27.4%
- Initial: $10,000 | Final: $12,810.53

## 2026-03-06 23:41 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +4.97% | Max DD: 15.75% | Sharpe: 0.21 | Sortino: 0.15 | Calmar: 0.10
- Trades: 132 | Win rate: 16.7% | Profit factor: 1.12
- Fees: $96.01 | Slippage: $411.47 | Time in market: 17.9%
- Initial: $10,000 | Final: $10,497.08

## 2026-03-06 23:42 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +80.07% | Max DD: 10.14% | Sharpe: 1.65 | Sortino: 1.32 | Calmar: 2.14
- Trades: 123 | Win rate: 25.2% | Profit factor: 2.68
- Fees: $119.59 | Slippage: $512.55 | Time in market: 23.1%
- Initial: $10,000 | Final: $18,007.49

## 2026-03-06 23:45 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.93% | Max DD: 18.91% | Sharpe: 0.01 | Sortino: 0.01 | Calmar: -0.02
- Trades: 160 | Win rate: 15.6% | Profit factor: 0.98
- Fees: $95.01 | Slippage: $407.20 | Time in market: 24.0%
- Initial: $10,000 | Final: $9,906.70

## 2026-03-06 23:45 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -18.77% | Max DD: 20.54% | Sharpe: -0.95 | Sortino: -0.64 | Calmar: -0.33
- Trades: 170 | Win rate: 13.5% | Profit factor: 0.45
- Fees: $65.19 | Slippage: $279.40 | Time in market: 23.4%
- Initial: $10,000 | Final: $8,122.96

## 2026-03-06 23:47 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.22% | Max DD: 7.07% | Sharpe: 0.69 | Sortino: 0.60 | Calmar: 1.07
- Trades: 84 | Win rate: 25.0% | Profit factor: 1.54
- Fees: $47.84 | Slippage: $205.04 | Time in market: 26.9%
- Initial: $10,000 | Final: $11,221.73

## 2026-03-06 23:49 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -11.06% | Max DD: 17.96% | Sharpe: -0.47 | Sortino: -0.32 | Calmar: -0.21
- Trades: 164 | Win rate: 17.1% | Profit factor: 0.77
- Fees: $105.31 | Slippage: $451.34 | Time in market: 26.3%
- Initial: $10,000 | Final: $8,894.36

## 2026-03-06 23:50 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -11.20% | Max DD: 21.52% | Sharpe: -0.42 | Sortino: -0.34 | Calmar: -0.18
- Trades: 182 | Win rate: 18.7% | Profit factor: 0.75
- Fees: $100.76 | Slippage: $431.84 | Time in market: 31.4%
- Initial: $10,000 | Final: $8,879.67

## 2026-03-06 23:53 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.38% | Max DD: 18.52% | Sharpe: -0.21 | Sortino: -0.12 | Calmar: -0.12
- Trades: 128 | Win rate: 17.2% | Profit factor: 0.83
- Fees: $55.63 | Slippage: $238.40 | Time in market: 19.0%
- Initial: $10,000 | Final: $9,361.54

## 2026-03-06 23:54 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.47% | Max DD: 11.26% | Sharpe: 0.37 | Sortino: 0.33 | Calmar: 0.30
- Trades: 174 | Win rate: 18.4% | Profit factor: 1.20
- Fees: $88.77 | Slippage: $380.43 | Time in market: 30.2%
- Initial: $10,000 | Final: $11,047.49

## 2026-03-06 23:56 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +1.67% | Max DD: 15.90% | Sharpe: 0.11 | Sortino: 0.08 | Calmar: 0.03
- Trades: 162 | Win rate: 17.3% | Profit factor: 1.05
- Fees: $78.16 | Slippage: $334.96 | Time in market: 24.7%
- Initial: $10,000 | Final: $10,166.79

## 2026-03-06 23:58 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +80.65% | Max DD: 12.19% | Sharpe: 1.62 | Sortino: 1.48 | Calmar: 1.79
- Trades: 141 | Win rate: 23.4% | Profit factor: 2.32
- Fees: $148.28 | Slippage: $635.49 | Time in market: 27.8%
- Initial: $10,000 | Final: $18,065.40

## 2026-03-07 00:01 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.42% | Max DD: 15.12% | Sharpe: 0.26 | Sortino: 0.18 | Calmar: 0.14
- Trades: 132 | Win rate: 16.7% | Profit factor: 1.17
- Fees: $90.51 | Slippage: $387.91 | Time in market: 17.9%
- Initial: $10,000 | Final: $10,642.09

## 2026-03-07 00:03 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -24.78% | Max DD: 25.50% | Sharpe: -1.42 | Sortino: -1.03 | Calmar: -0.36
- Trades: 198 | Win rate: 12.6% | Profit factor: 0.37
- Fees: $68.28 | Slippage: $292.63 | Time in market: 25.5%
- Initial: $10,000 | Final: $7,522.04

## 2026-03-07 00:05 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.12% | Max DD: 7.24% | Sharpe: 0.62 | Sortino: 0.56 | Calmar: 0.87
- Trades: 88 | Win rate: 23.9% | Profit factor: 1.44
- Fees: $47.61 | Slippage: $204.03 | Time in market: 29.7%
- Initial: $10,000 | Final: $11,011.93

## 2026-03-07 00:07 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -2.30% | Max DD: 18.64% | Sharpe: -0.05 | Sortino: -0.03 | Calmar: -0.04
- Trades: 160 | Win rate: 15.6% | Profit factor: 0.94
- Fees: $88.03 | Slippage: $377.27 | Time in market: 24.0%
- Initial: $10,000 | Final: $9,769.97

## 2026-03-07 00:13 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -12.20% | Max DD: 21.13% | Sharpe: -0.49 | Sortino: -0.39 | Calmar: -0.20
- Trades: 182 | Win rate: 18.7% | Profit factor: 0.71
- Fees: $91.28 | Slippage: $391.22 | Time in market: 31.4%
- Initial: $10,000 | Final: $8,779.99

## 2026-03-07 00:15 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.75% | Max DD: 17.10% | Sharpe: -0.22 | Sortino: -0.17 | Calmar: -0.13
- Trades: 176 | Win rate: 18.8% | Profit factor: 0.87
- Fees: $135.94 | Slippage: $582.60 | Time in market: 29.5%
- Initial: $10,000 | Final: $9,325.32

## 2026-03-07 00:20 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.97% | Max DD: 10.81% | Sharpe: 0.40 | Sortino: 0.34 | Calmar: 0.33
- Trades: 174 | Win rate: 18.4% | Profit factor: 1.23
- Fees: $82.30 | Slippage: $352.71 | Time in market: 30.2%
- Initial: $10,000 | Final: $11,097.24

## 2026-03-07 00:22 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +3.60% | Max DD: 17.67% | Sharpe: 0.17 | Sortino: 0.11 | Calmar: 0.07
- Trades: 148 | Win rate: 16.2% | Profit factor: 1.08
- Fees: $72.21 | Slippage: $309.49 | Time in market: 22.9%
- Initial: $10,000 | Final: $10,359.72

## 2026-03-07 00:26 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +73.13% | Max DD: 11.57% | Sharpe: 1.58 | Sortino: 1.41 | Calmar: 1.74
- Trades: 141 | Win rate: 23.4% | Profit factor: 2.37
- Fees: $129.12 | Slippage: $553.37 | Time in market: 27.8%
- Initial: $10,000 | Final: $17,313.04

## 2026-03-07 00:28 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.31% | Max DD: 15.12% | Sharpe: 0.06 | Sortino: 0.05 | Calmar: 0.01
- Trades: 184 | Win rate: 17.9% | Profit factor: 1.01
- Fees: $106.83 | Slippage: $457.82 | Time in market: 29.9%
- Initial: $10,000 | Final: $10,030.92

## 2026-03-07 00:33 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -24.29% | Max DD: 24.94% | Sharpe: -1.42 | Sortino: -1.00 | Calmar: -0.36
- Trades: 198 | Win rate: 12.6% | Profit factor: 0.35
- Fees: $64.69 | Slippage: $277.22 | Time in market: 25.5%
- Initial: $10,000 | Final: $7,571.21

## 2026-03-07 00:35 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +8.95% | Max DD: 6.86% | Sharpe: 0.58 | Sortino: 0.51 | Calmar: 0.81
- Trades: 88 | Win rate: 23.9% | Profit factor: 1.42
- Fees: $42.50 | Slippage: $182.15 | Time in market: 29.7%
- Initial: $10,000 | Final: $10,895.26

## 2026-03-07 00:35 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +8.65% | Max DD: 14.06% | Sharpe: 0.32 | Sortino: 0.24 | Calmar: 0.20
- Trades: 150 | Win rate: 18.7% | Profit factor: 1.20
- Fees: $108.99 | Slippage: $467.09 | Time in market: 23.5%
- Initial: $10,000 | Final: $10,865.49

## 2026-03-07 00:42 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -11.69% | Max DD: 18.69% | Sharpe: -0.49 | Sortino: -0.36 | Calmar: -0.22
- Trades: 148 | Win rate: 18.2% | Profit factor: 0.68
- Fees: $84.92 | Slippage: $363.93 | Time in market: 23.2%
- Initial: $10,000 | Final: $8,830.58

## 2026-03-07 00:42 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.29% | Max DD: 16.87% | Sharpe: 0.01 | Sortino: 0.01 | Calmar: -0.03
- Trades: 184 | Win rate: 15.8% | Profit factor: 0.97
- Fees: $118.56 | Slippage: $508.12 | Time in market: 27.8%
- Initial: $10,000 | Final: $9,870.67

## 2026-03-07 00:49 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +27.46% | Max DD: 7.75% | Sharpe: 0.86 | Sortino: 0.71 | Calmar: 1.09
- Trades: 124 | Win rate: 24.2% | Profit factor: 1.75
- Fees: $76.85 | Slippage: $329.34 | Time in market: 25.1%
- Initial: $10,000 | Final: $12,746.19

## 2026-03-07 00:49 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.10% | Max DD: 16.52% | Sharpe: -0.34 | Sortino: -0.25 | Calmar: -0.19
- Trades: 176 | Win rate: 18.8% | Profit factor: 0.81
- Fees: $124.32 | Slippage: $532.82 | Time in market: 29.5%
- Initial: $10,000 | Final: $9,090.32

## 2026-03-07 00:56 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +76.45% | Max DD: 9.42% | Sharpe: 1.62 | Sortino: 1.30 | Calmar: 2.21
- Trades: 109 | Win rate: 27.5% | Profit factor: 2.67
- Fees: $116.39 | Slippage: $498.83 | Time in market: 20.7%
- Initial: $10,000 | Final: $17,644.59

## 2026-03-07 00:56 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +5.83% | Max DD: 17.00% | Sharpe: 0.24 | Sortino: 0.16 | Calmar: 0.11
- Trades: 148 | Win rate: 16.2% | Profit factor: 1.14
- Fees: $66.98 | Slippage: $287.07 | Time in market: 22.9%
- Initial: $10,000 | Final: $10,583.45

## 2026-03-07 01:02 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -20.10% | Max DD: 21.26% | Sharpe: -1.10 | Sortino: -0.71 | Calmar: -0.34
- Trades: 152 | Win rate: 11.8% | Profit factor: 0.43
- Fees: $64.74 | Slippage: $277.48 | Time in market: 20.1%
- Initial: $10,000 | Final: $7,990.04

## 2026-03-07 01:02 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.26% | Max DD: 14.46% | Sharpe: 0.12 | Sortino: 0.11 | Calmar: 0.05
- Trades: 184 | Win rate: 17.9% | Profit factor: 1.05
- Fees: $98.14 | Slippage: $420.59 | Time in market: 29.9%
- Initial: $10,000 | Final: $10,225.69

## 2026-03-07 01:04 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +9.70% | Max DD: 7.66% | Sharpe: 0.62 | Sortino: 0.51 | Calmar: 0.79
- Trades: 68 | Win rate: 23.5% | Profit factor: 1.48
- Fees: $39.63 | Slippage: $169.85 | Time in market: 22.3%
- Initial: $10,000 | Final: $10,970.00

## 2026-03-07 01:10 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +9.13% | Max DD: 12.93% | Sharpe: 0.34 | Sortino: 0.25 | Calmar: 0.23
- Trades: 150 | Win rate: 18.7% | Profit factor: 1.23
- Fees: $99.72 | Slippage: $427.37 | Time in market: 23.5%
- Initial: $10,000 | Final: $10,913.36

## 2026-03-07 01:12 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -11.53% | Max DD: 18.48% | Sharpe: -0.50 | Sortino: -0.35 | Calmar: -0.22
- Trades: 148 | Win rate: 18.2% | Profit factor: 0.66
- Fees: $78.62 | Slippage: $336.94 | Time in market: 23.2%
- Initial: $10,000 | Final: $8,846.95

## 2026-03-07 01:17 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -2.63% | Max DD: 17.25% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.05
- Trades: 184 | Win rate: 15.8% | Profit factor: 0.94
- Fees: $108.71 | Slippage: $465.91 | Time in market: 27.8%
- Initial: $10,000 | Final: $9,737.23

## 2026-03-07 01:19 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +26.28% | Max DD: 7.61% | Sharpe: 0.85 | Sortino: 0.68 | Calmar: 1.06
- Trades: 124 | Win rate: 24.2% | Profit factor: 1.79
- Fees: $70.75 | Slippage: $303.20 | Time in market: 25.1%
- Initial: $10,000 | Final: $12,628.18

## 2026-03-07 01:24 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.28% | Max DD: 16.92% | Sharpe: -0.37 | Sortino: -0.24 | Calmar: -0.19
- Trades: 138 | Win rate: 18.1% | Profit factor: 0.80
- Fees: $106.36 | Slippage: $455.85 | Time in market: 21.8%
- Initial: $10,000 | Final: $9,071.91

## 2026-03-07 01:26 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +70.53% | Max DD: 8.87% | Sharpe: 1.58 | Sortino: 1.25 | Calmar: 2.20
- Trades: 109 | Win rate: 27.5% | Profit factor: 2.70
- Fees: $104.69 | Slippage: $448.66 | Time in market: 20.7%
- Initial: $10,000 | Final: $17,053.31

## 2026-03-07 01:31 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +1.38% | Max DD: 15.84% | Sharpe: 0.10 | Sortino: 0.05 | Calmar: 0.03
- Trades: 108 | Win rate: 17.6% | Profit factor: 1.04
- Fees: $55.83 | Slippage: $239.29 | Time in market: 17.0%
- Initial: $10,000 | Final: $10,137.68

## 2026-03-07 01:33 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -19.54% | Max DD: 20.59% | Sharpe: -1.08 | Sortino: -0.68 | Calmar: -0.34
- Trades: 152 | Win rate: 11.8% | Profit factor: 0.41
- Fees: $62.16 | Slippage: $266.39 | Time in market: 20.1%
- Initial: $10,000 | Final: $8,045.75

## 2026-03-07 01:35 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +9.72% | Max DD: 6.75% | Sharpe: 0.65 | Sortino: 0.52 | Calmar: 0.89
- Trades: 68 | Win rate: 23.5% | Profit factor: 1.54
- Fees: $36.05 | Slippage: $154.50 | Time in market: 22.3%
- Initial: $10,000 | Final: $10,972.26

## 2026-03-07 01:39 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -2.27% | Max DD: 13.97% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.05
- Trades: 138 | Win rate: 17.4% | Profit factor: 0.94
- Fees: $82.70 | Slippage: $354.43 | Time in market: 21.9%
- Initial: $10,000 | Final: $9,772.69

## 2026-03-07 01:42 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.63% | Max DD: 16.93% | Sharpe: -0.44 | Sortino: -0.30 | Calmar: -0.20
- Trades: 122 | Win rate: 19.7% | Profit factor: 0.70
- Fees: $70.91 | Slippage: $303.91 | Time in market: 19.0%
- Initial: $10,000 | Final: $9,037.20

## 2026-03-07 01:46 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +7.74% | Max DD: 9.49% | Sharpe: 0.30 | Sortino: 0.19 | Calmar: 0.27
- Trades: 114 | Win rate: 18.4% | Profit factor: 1.26
- Fees: $87.08 | Slippage: $373.18 | Time in market: 14.7%
- Initial: $10,000 | Final: $10,773.72

## 2026-03-07 01:50 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +29.55% | Max DD: 8.32% | Sharpe: 1.02 | Sortino: 0.78 | Calmar: 1.08
- Trades: 94 | Win rate: 26.6% | Profit factor: 2.25
- Fees: $58.68 | Slippage: $251.48 | Time in market: 20.1%
- Initial: $10,000 | Final: $12,955.29

## 2026-03-07 01:53 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.72% | Max DD: 17.56% | Sharpe: -0.03 | Sortino: -0.02 | Calmar: -0.03
- Trades: 136 | Win rate: 15.4% | Profit factor: 0.95
- Fees: $84.02 | Slippage: $360.09 | Time in market: 20.9%
- Initial: $10,000 | Final: $9,827.84

## 2026-03-07 01:57 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +54.64% | Max DD: 7.25% | Sharpe: 1.40 | Sortino: 1.00 | Calmar: 2.16
- Trades: 83 | Win rate: 28.9% | Profit factor: 2.94
- Fees: $71.65 | Slippage: $307.08 | Time in market: 16.0%
- Initial: $10,000 | Final: $15,463.92

## 2026-03-07 02:00 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.60% | Max DD: 17.03% | Sharpe: -0.41 | Sortino: -0.26 | Calmar: -0.19
- Trades: 138 | Win rate: 18.1% | Profit factor: 0.78
- Fees: $98.12 | Slippage: $420.53 | Time in market: 21.8%
- Initial: $10,000 | Final: $9,039.65

## 2026-03-07 02:04 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -17.05% | Max DD: 18.40% | Sharpe: -1.01 | Sortino: -0.60 | Calmar: -0.33
- Trades: 122 | Win rate: 12.3% | Profit factor: 0.42
- Fees: $53.65 | Slippage: $229.92 | Time in market: 15.8%
- Initial: $10,000 | Final: $8,295.26

## 2026-03-07 02:06 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.46% | Max DD: 8.07% | Sharpe: 0.08 | Sortino: 0.05 | Calmar: 0.04
- Trades: 54 | Win rate: 18.5% | Profit factor: 1.03
- Fees: $27.81 | Slippage: $119.19 | Time in market: 16.6%
- Initial: $10,000 | Final: $10,045.59

## 2026-03-07 02:07 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.71% | Max DD: 14.78% | Sharpe: 0.14 | Sortino: 0.08 | Calmar: 0.06
- Trades: 108 | Win rate: 17.6% | Profit factor: 1.08
- Fees: $51.83 | Slippage: $222.14 | Time in market: 17.0%
- Initial: $10,000 | Final: $10,271.34

## 2026-03-07 02:13 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -8.16% | Max DD: 15.97% | Sharpe: -0.37 | Sortino: -0.25 | Calmar: -0.18
- Trades: 122 | Win rate: 19.7% | Profit factor: 0.72
- Fees: $67.06 | Slippage: $287.41 | Time in market: 19.0%
- Initial: $10,000 | Final: $9,183.99

## 2026-03-07 02:14 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.18% | Max DD: 12.87% | Sharpe: 0.05 | Sortino: 0.04 | Calmar: 0.00
- Trades: 138 | Win rate: 17.4% | Profit factor: 1.01
- Fees: $78.42 | Slippage: $336.07 | Time in market: 21.9%
- Initial: $10,000 | Final: $10,018.22

## 2026-03-07 02:20 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +28.76% | Max DD: 8.04% | Sharpe: 1.02 | Sortino: 0.75 | Calmar: 1.09
- Trades: 94 | Win rate: 26.6% | Profit factor: 2.32
- Fees: $55.72 | Slippage: $238.82 | Time in market: 20.1%
- Initial: $10,000 | Final: $12,876.34

## 2026-03-07 02:21 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +9.23% | Max DD: 9.05% | Sharpe: 0.35 | Sortino: 0.22 | Calmar: 0.33
- Trades: 114 | Win rate: 18.4% | Profit factor: 1.34
- Fees: $80.62 | Slippage: $345.50 | Time in market: 14.7%
- Initial: $10,000 | Final: $10,923.36

## 2026-03-07 02:27 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +51.30% | Max DD: 6.51% | Sharpe: 1.38 | Sortino: 0.97 | Calmar: 2.28
- Trades: 83 | Win rate: 28.9% | Profit factor: 2.96
- Fees: $64.58 | Slippage: $276.75 | Time in market: 16.0%
- Initial: $10,000 | Final: $15,130.26

## 2026-03-07 02:28 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.99% | Max DD: 16.75% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.04
- Trades: 136 | Win rate: 15.4% | Profit factor: 0.94
- Fees: $79.68 | Slippage: $341.50 | Time in market: 20.9%
- Initial: $10,000 | Final: $9,801.43

## 2026-03-07 02:34 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -16.03% | Max DD: 17.25% | Sharpe: -0.96 | Sortino: -0.56 | Calmar: -0.33
- Trades: 122 | Win rate: 12.3% | Profit factor: 0.43
- Fees: $51.84 | Slippage: $222.16 | Time in market: 15.8%
- Initial: $10,000 | Final: $8,397.32

## 2026-03-07 02:35 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.04% | Max DD: 11.65% | Sharpe: 0.12 | Sortino: 0.08 | Calmar: 0.06
- Trades: 112 | Win rate: 20.5% | Profit factor: 1.06
- Fees: $96.13 | Slippage: $411.99 | Time in market: 19.6%
- Initial: $10,000 | Final: $10,204.06

## 2026-03-07 02:36 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +1.53% | Max DD: 7.05% | Sharpe: 0.17 | Sortino: 0.12 | Calmar: 0.14
- Trades: 54 | Win rate: 18.5% | Profit factor: 1.11
- Fees: $25.21 | Slippage: $108.06 | Time in market: 16.6%
- Initial: $10,000 | Final: $10,153.45

## 2026-03-07 02:42 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.27% | Max DD: 16.15% | Sharpe: 0.03 | Sortino: 0.02 | Calmar: -0.01
- Trades: 92 | Win rate: 18.5% | Profit factor: 0.99
- Fees: $49.58 | Slippage: $212.50 | Time in market: 13.9%
- Initial: $10,000 | Final: $9,973.40

## 2026-03-07 02:42 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.57% | Max DD: 21.36% | Sharpe: 0.03 | Sortino: 0.02 | Calmar: -0.01
- Trades: 186 | Win rate: 19.4% | Profit factor: 0.99
- Fees: $115.46 | Slippage: $494.82 | Time in market: 32.9%
- Initial: $10,000 | Final: $9,943.36

## 2026-03-07 02:49 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.57% | Max DD: 14.27% | Sharpe: -0.03 | Sortino: -0.02 | Calmar: -0.04
- Trades: 112 | Win rate: 16.1% | Profit factor: 0.94
- Fees: $60.47 | Slippage: $259.16 | Time in market: 17.2%
- Initial: $10,000 | Final: $9,843.05

## 2026-03-07 02:49 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +17.69% | Max DD: 11.07% | Sharpe: 0.55 | Sortino: 0.51 | Calmar: 0.50
- Trades: 180 | Win rate: 18.9% | Profit factor: 1.32
- Fees: $99.85 | Slippage: $427.95 | Time in market: 31.0%
- Initial: $10,000 | Final: $11,769.38

## 2026-03-07 02:56 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.73% | Max DD: 9.93% | Sharpe: 0.40 | Sortino: 0.22 | Calmar: 0.35
- Trades: 84 | Win rate: 17.9% | Profit factor: 1.41
- Fees: $67.54 | Slippage: $289.45 | Time in market: 10.1%
- Initial: $10,000 | Final: $11,072.60

## 2026-03-07 02:56 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +112.51% | Max DD: 12.58% | Sharpe: 1.78 | Sortino: 1.65 | Calmar: 2.27
- Trades: 145 | Win rate: 23.4% | Profit factor: 2.51
- Fees: $186.73 | Slippage: $800.28 | Time in market: 28.4%
- Initial: $10,000 | Final: $21,250.59

## 2026-03-07 03:03 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.87% | Max DD: 19.25% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.03
- Trades: 112 | Win rate: 16.1% | Profit factor: 0.94
- Fees: $65.75 | Slippage: $281.79 | Time in market: 17.2%
- Initial: $10,000 | Final: $9,812.76

## 2026-03-07 03:03 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -15.93% | Max DD: 27.31% | Sharpe: -0.76 | Sortino: -0.57 | Calmar: -0.21
- Trades: 202 | Win rate: 12.9% | Profit factor: 0.62
- Fees: $72.07 | Slippage: $308.88 | Time in market: 27.0%
- Initial: $10,000 | Final: $8,406.89

## 2026-03-07 03:05 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +13.58% | Max DD: 7.89% | Sharpe: 0.71 | Sortino: 0.67 | Calmar: 1.06
- Trades: 94 | Win rate: 23.4% | Profit factor: 1.54
- Fees: $54.69 | Slippage: $234.38 | Time in market: 31.3%
- Initial: $10,000 | Final: $11,357.72

## 2026-03-07 03:10 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.23% | Max DD: 10.52% | Sharpe: 0.13 | Sortino: 0.08 | Calmar: 0.07
- Trades: 112 | Win rate: 20.5% | Profit factor: 1.07
- Fees: $89.27 | Slippage: $382.57 | Time in market: 19.6%
- Initial: $10,000 | Final: $10,222.79

## 2026-03-07 03:12 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.36% | Max DD: 20.90% | Sharpe: 0.03 | Sortino: 0.03 | Calmar: -0.01
- Trades: 186 | Win rate: 19.4% | Profit factor: 0.99
- Fees: $107.10 | Slippage: $459.01 | Time in market: 32.9%
- Initial: $10,000 | Final: $9,963.79

## 2026-03-07 03:17 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.76% | Max DD: 14.93% | Sharpe: 0.07 | Sortino: 0.04 | Calmar: 0.02
- Trades: 92 | Win rate: 18.5% | Profit factor: 1.03
- Fees: $46.19 | Slippage: $197.96 | Time in market: 13.9%
- Initial: $10,000 | Final: $10,076.21

## 2026-03-07 03:19 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +19.93% | Max DD: 10.62% | Sharpe: 0.61 | Sortino: 0.55 | Calmar: 0.59
- Trades: 180 | Win rate: 18.9% | Profit factor: 1.38
- Fees: $95.00 | Slippage: $407.16 | Time in market: 31.0%
- Initial: $10,000 | Final: $11,992.60

## 2026-03-07 03:24 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +1.68% | Max DD: 12.52% | Sharpe: 0.11 | Sortino: 0.07 | Calmar: 0.04
- Trades: 112 | Win rate: 16.1% | Profit factor: 1.07
- Fees: $57.69 | Slippage: $247.24 | Time in market: 17.2%
- Initial: $10,000 | Final: $10,168.29

## 2026-03-07 03:27 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +109.97% | Max DD: 12.09% | Sharpe: 1.77 | Sortino: 1.62 | Calmar: 2.32
- Trades: 145 | Win rate: 23.4% | Profit factor: 2.62
- Fees: $172.87 | Slippage: $740.88 | Time in market: 28.4%
- Initial: $10,000 | Final: $20,997.25

## 2026-03-07 03:31 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.87% | Max DD: 8.63% | Sharpe: 0.47 | Sortino: 0.25 | Calmar: 0.48
- Trades: 84 | Win rate: 17.9% | Profit factor: 1.53
- Fees: $64.90 | Slippage: $278.15 | Time in market: 10.1%
- Initial: $10,000 | Final: $11,286.55

## 2026-03-07 03:34 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -16.66% | Max DD: 26.89% | Sharpe: -0.83 | Sortino: -0.60 | Calmar: -0.22
- Trades: 202 | Win rate: 12.9% | Profit factor: 0.58
- Fees: $69.09 | Slippage: $296.08 | Time in market: 27.0%
- Initial: $10,000 | Final: $8,334.22

## 2026-03-07 03:36 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +13.91% | Max DD: 7.76% | Sharpe: 0.75 | Sortino: 0.68 | Calmar: 1.10
- Trades: 94 | Win rate: 23.4% | Profit factor: 1.60
- Fees: $50.90 | Slippage: $218.14 | Time in market: 31.3%
- Initial: $10,000 | Final: $11,391.26

## 2026-03-07 03:38 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.74% | Max DD: 18.45% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.03
- Trades: 112 | Win rate: 16.1% | Profit factor: 0.94
- Fees: $63.32 | Slippage: $271.38 | Time in market: 17.2%
- Initial: $10,000 | Final: $9,826.49

## 2026-03-07 03:43 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -7.55% | Max DD: 16.80% | Sharpe: -0.31 | Sortino: -0.23 | Calmar: -0.15
- Trades: 144 | Win rate: 18.8% | Profit factor: 0.78
- Fees: $85.78 | Slippage: $367.61 | Time in market: 22.9%
- Initial: $10,000 | Final: $9,245.43

## 2026-03-07 03:45 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.48% | Max DD: 17.25% | Sharpe: 0.07 | Sortino: 0.06 | Calmar: 0.01
- Trades: 182 | Win rate: 19.2% | Profit factor: 1.01
- Fees: $148.50 | Slippage: $636.44 | Time in market: 30.3%
- Initial: $10,000 | Final: $10,048.22

## 2026-03-07 03:49 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +33.65% | Max DD: 7.59% | Sharpe: 1.03 | Sortino: 0.88 | Calmar: 1.34
- Trades: 120 | Win rate: 24.2% | Profit factor: 1.98
- Fees: $77.73 | Slippage: $333.14 | Time in market: 24.6%
- Initial: $10,000 | Final: $13,364.83

## 2026-03-07 03:52 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.65% | Max DD: 18.98% | Sharpe: 0.04 | Sortino: 0.02 | Calmar: -0.01
- Trades: 152 | Win rate: 16.4% | Profit factor: 0.99
- Fees: $78.35 | Slippage: $335.79 | Time in market: 23.0%
- Initial: $10,000 | Final: $9,934.78

## 2026-03-07 03:56 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +61.09% | Max DD: 9.80% | Sharpe: 1.47 | Sortino: 1.17 | Calmar: 1.76
- Trades: 107 | Win rate: 27.1% | Profit factor: 2.56
- Fees: $98.79 | Slippage: $423.38 | Time in market: 20.2%
- Initial: $10,000 | Final: $16,108.92

## 2026-03-07 03:59 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -5.45% | Max DD: 18.48% | Sharpe: -0.15 | Sortino: -0.13 | Calmar: -0.10
- Trades: 190 | Win rate: 17.9% | Profit factor: 0.88
- Fees: $97.77 | Slippage: $419.00 | Time in market: 30.7%
- Initial: $10,000 | Final: $9,455.05

## 2026-03-07 04:03 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -18.07% | Max DD: 18.79% | Sharpe: -0.95 | Sortino: -0.62 | Calmar: -0.34
- Trades: 148 | Win rate: 12.2% | Profit factor: 0.48
- Fees: $65.61 | Slippage: $281.19 | Time in market: 19.9%
- Initial: $10,000 | Final: $8,193.37

## 2026-03-07 04:05 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.88% | Max DD: 8.52% | Sharpe: 0.24 | Sortino: 0.18 | Calmar: 0.21
- Trades: 62 | Win rate: 22.6% | Profit factor: 1.15
- Fees: $36.49 | Slippage: $156.38 | Time in market: 19.5%
- Initial: $10,000 | Final: $10,287.78

## 2026-03-07 04:06 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +8.78% | Max DD: 15.13% | Sharpe: 0.30 | Sortino: 0.20 | Calmar: 0.19
- Trades: 154 | Win rate: 18.8% | Profit factor: 1.19
- Fees: $115.46 | Slippage: $494.83 | Time in market: 24.5%
- Initial: $10,000 | Final: $10,878.20

## 2026-03-07 04:12 UTC — Backtest: DonchianMTF on DOT

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.86% | Max DD: 15.95% | Sharpe: -0.29 | Sortino: -0.21 | Calmar: -0.15
- Trades: 144 | Win rate: 18.8% | Profit factor: 0.78
- Fees: $79.20 | Slippage: $339.44 | Time in market: 22.9%
- Initial: $10,000 | Final: $9,313.83

## 2026-03-07 04:13 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +27.19% | Max DD: 18.28% | Sharpe: 0.72 | Sortino: 0.62 | Calmar: 0.46
- Trades: 188 | Win rate: 16.0% | Profit factor: 1.45
- Fees: $146.08 | Slippage: $626.07 | Time in market: 29.2%
- Initial: $10,000 | Final: $12,718.96

## 2026-03-07 04:19 UTC — Backtest: DonchianMTF on NEAR

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +34.18% | Max DD: 7.35% | Sharpe: 1.08 | Sortino: 0.89 | Calmar: 1.40
- Trades: 120 | Win rate: 24.2% | Profit factor: 2.12
- Fees: $71.93 | Slippage: $308.28 | Time in market: 24.6%
- Initial: $10,000 | Final: $13,417.54

## 2026-03-07 04:20 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.76% | Max DD: 16.62% | Sharpe: 0.08 | Sortino: 0.06 | Calmar: 0.02
- Trades: 182 | Win rate: 19.2% | Profit factor: 1.01
- Fees: $140.72 | Slippage: $603.10 | Time in market: 30.3%
- Initial: $10,000 | Final: $10,076.41

## 2026-03-07 04:26 UTC — Backtest: DonchianMTF on FIL

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +57.55% | Max DD: 9.35% | Sharpe: 1.46 | Sortino: 1.14 | Calmar: 1.75
- Trades: 107 | Win rate: 27.1% | Profit factor: 2.67
- Fees: $87.36 | Slippage: $374.40 | Time in market: 20.2%
- Initial: $10,000 | Final: $15,755.35

## 2026-03-07 04:27 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -0.39% | Max DD: 18.96% | Sharpe: 0.04 | Sortino: 0.03 | Calmar: -0.01
- Trades: 152 | Win rate: 16.4% | Profit factor: 0.99
- Fees: $75.16 | Slippage: $322.12 | Time in market: 23.0%
- Initial: $10,000 | Final: $9,960.91

## 2026-03-07 04:33 UTC — Backtest: DonchianMTF on ATOM

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -16.81% | Max DD: 17.49% | Sharpe: -0.89 | Sortino: -0.56 | Calmar: -0.34
- Trades: 148 | Win rate: 12.2% | Profit factor: 0.48
- Fees: $62.31 | Slippage: $267.02 | Time in market: 19.9%
- Initial: $10,000 | Final: $8,318.86

## 2026-03-07 04:34 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -5.22% | Max DD: 18.57% | Sharpe: -0.15 | Sortino: -0.12 | Calmar: -0.10
- Trades: 190 | Win rate: 17.9% | Profit factor: 0.88
- Fees: $89.71 | Slippage: $384.49 | Time in market: 30.7%
- Initial: $10,000 | Final: $9,477.67

## 2026-03-07 04:35 UTC — Backtest: DonchianMTF on OP

- Period: 2022-06-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.61% | Max DD: 7.92% | Sharpe: 0.23 | Sortino: 0.17 | Calmar: 0.21
- Trades: 62 | Win rate: 22.6% | Profit factor: 1.15
- Fees: $33.29 | Slippage: $142.67 | Time in market: 19.5%
- Initial: $10,000 | Final: $10,260.59

## 2026-03-07 04:35 UTC — Parameter Sweep: DonchianMTF (ATOM, DOT, FIL, NEAR, OP)

Params: combo=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], lookbacks=['18/48/168', '24/72/168', '24/72/252', '36/120/504', '36/72/336', '36/96/252', '48/120/336', '48/168/504'], weights=['equal', 'med-heavy']

| Combo | Lookbacks | Weights | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G | 24/72/168 | med-heavy | FIL | +112.51% | 12.58% | 1.78 | 1.65 | 2.27 | 145 | 23.4% | 2.51 |
| G | 24/72/168 | equal | FIL | +109.97% | 12.09% | 1.77 | 1.62 | 2.32 | 145 | 23.4% | 2.62 |
| B | 24/72/252 | med-heavy | FIL | +84.31% | 12.19% | 1.66 | 1.47 | 1.86 | 141 | 23.4% | 2.37 |
| C | 36/96/252 | med-heavy | FIL | +83.86% | 10.66% | 1.66 | 1.36 | 2.11 | 123 | 25.2% | 2.56 |
| C | 36/96/252 | equal | FIL | +80.07% | 10.14% | 1.65 | 1.32 | 2.14 | 123 | 25.2% | 2.68 |
| B | 24/72/252 | equal | FIL | +78.02% | 11.57% | 1.63 | 1.41 | 1.83 | 141 | 23.4% | 2.44 |
| D | 36/72/336 | med-heavy | FIL | +80.65% | 12.19% | 1.62 | 1.48 | 1.79 | 141 | 23.4% | 2.32 |
| E | 48/120/336 | med-heavy | FIL | +76.45% | 9.42% | 1.62 | 1.30 | 2.21 | 109 | 27.5% | 2.67 |
| D | 36/72/336 | equal | FIL | +73.13% | 11.57% | 1.58 | 1.41 | 1.74 | 141 | 23.4% | 2.37 |
| E | 48/120/336 | equal | FIL | +70.53% | 8.87% | 1.58 | 1.25 | 2.20 | 109 | 27.5% | 2.70 |
| A | 18/48/168 | equal | FIL | +89.10% | 13.06% | 1.50 | 1.50 | 1.81 | 191 | 20.4% | 2.00 |
| A | 18/48/168 | med-heavy | FIL | +90.31% | 12.64% | 1.49 | 1.51 | 1.89 | 191 | 20.4% | 1.93 |
| H | 36/120/504 | med-heavy | FIL | +61.09% | 9.80% | 1.47 | 1.17 | 1.76 | 107 | 27.1% | 2.56 |
| H | 36/120/504 | equal | FIL | +57.55% | 9.35% | 1.46 | 1.14 | 1.75 | 107 | 27.1% | 2.67 |
| F | 48/168/504 | med-heavy | FIL | +54.64% | 7.25% | 1.40 | 1.00 | 2.16 | 83 | 28.9% | 2.94 |
| F | 48/168/504 | equal | FIL | +51.30% | 6.51% | 1.38 | 0.97 | 2.28 | 83 | 28.9% | 2.96 |
| H | 36/120/504 | equal | NEAR | +34.18% | 7.35% | 1.08 | 0.89 | 1.40 | 120 | 24.2% | 2.12 |
| H | 36/120/504 | med-heavy | NEAR | +33.65% | 7.59% | 1.03 | 0.88 | 1.34 | 120 | 24.2% | 1.98 |
| F | 48/168/504 | equal | NEAR | +28.76% | 8.04% | 1.02 | 0.75 | 1.09 | 94 | 26.6% | 2.32 |
| F | 48/168/504 | med-heavy | NEAR | +29.55% | 8.32% | 1.02 | 0.78 | 1.08 | 94 | 26.6% | 2.25 |
| A | 18/48/168 | equal | OP | +19.03% | 6.44% | 0.93 | 0.95 | 1.81 | 116 | 24.1% | 1.71 |
| A | 18/48/168 | med-heavy | OP | +18.86% | 6.72% | 0.90 | 0.93 | 1.72 | 116 | 24.1% | 1.63 |
| C | 36/96/252 | equal | NEAR | +28.11% | 9.30% | 0.86 | 0.73 | 0.93 | 146 | 21.9% | 1.73 |
| E | 48/120/336 | med-heavy | NEAR | +27.46% | 7.75% | 0.86 | 0.71 | 1.09 | 124 | 24.2% | 1.75 |
| E | 48/120/336 | equal | NEAR | +26.28% | 7.61% | 0.85 | 0.68 | 1.06 | 124 | 24.2% | 1.79 |
| C | 36/96/252 | med-heavy | NEAR | +26.78% | 9.62% | 0.81 | 0.71 | 0.86 | 146 | 21.9% | 1.62 |
| G | 24/72/168 | equal | OP | +13.91% | 7.76% | 0.75 | 0.68 | 1.10 | 94 | 23.4% | 1.60 |
| G | 24/72/168 | med-heavy | OP | +13.58% | 7.89% | 0.71 | 0.67 | 1.06 | 94 | 23.4% | 1.54 |
| C | 36/96/252 | equal | OP | +12.22% | 7.07% | 0.69 | 0.60 | 1.07 | 84 | 25.0% | 1.54 |
| C | 36/96/252 | med-heavy | OP | +12.08% | 6.74% | 0.66 | 0.59 | 1.11 | 84 | 25.0% | 1.50 |
| E | 48/120/336 | equal | OP | +9.72% | 6.75% | 0.65 | 0.52 | 0.89 | 68 | 23.5% | 1.54 |
| B | 24/72/252 | equal | OP | +11.21% | 7.28% | 0.64 | 0.59 | 0.95 | 94 | 23.4% | 1.47 |
| E | 48/120/336 | med-heavy | OP | +9.70% | 7.66% | 0.62 | 0.51 | 0.79 | 68 | 23.5% | 1.48 |
| B | 24/72/252 | med-heavy | OP | +11.16% | 7.21% | 0.62 | 0.58 | 0.96 | 94 | 23.4% | 1.44 |
| D | 36/72/336 | med-heavy | OP | +10.12% | 7.24% | 0.62 | 0.56 | 0.87 | 88 | 23.9% | 1.44 |
| G | 24/72/168 | equal | NEAR | +19.93% | 10.62% | 0.61 | 0.55 | 0.59 | 180 | 18.9% | 1.38 |
| D | 36/72/336 | equal | OP | +8.95% | 6.86% | 0.58 | 0.51 | 0.81 | 88 | 23.9% | 1.42 |
| G | 24/72/168 | med-heavy | NEAR | +17.69% | 11.07% | 0.55 | 0.51 | 0.50 | 180 | 18.9% | 1.32 |
| B | 24/72/252 | equal | NEAR | +16.06% | 10.82% | 0.53 | 0.47 | 0.47 | 178 | 18.5% | 1.33 |
| A | 18/48/168 | equal | NEAR | +15.33% | 11.01% | 0.48 | 0.47 | 0.44 | 226 | 19.5% | 1.24 |
| B | 24/72/252 | med-heavy | NEAR | +14.52% | 11.26% | 0.48 | 0.43 | 0.41 | 178 | 18.5% | 1.28 |
| A | 18/48/168 | med-heavy | NEAR | +14.10% | 11.23% | 0.44 | 0.44 | 0.40 | 226 | 19.5% | 1.20 |
| D | 36/72/336 | equal | NEAR | +10.97% | 10.81% | 0.40 | 0.34 | 0.33 | 174 | 18.4% | 1.23 |
| D | 36/72/336 | med-heavy | NEAR | +10.47% | 11.26% | 0.37 | 0.33 | 0.30 | 174 | 18.4% | 1.20 |
| H | 36/120/504 | med-heavy | OP | +2.88% | 8.52% | 0.24 | 0.18 | 0.21 | 62 | 22.6% | 1.15 |
| H | 36/120/504 | equal | OP | +2.61% | 7.92% | 0.23 | 0.17 | 0.21 | 62 | 22.6% | 1.15 |
| F | 48/168/504 | equal | OP | +1.53% | 7.05% | 0.17 | 0.12 | 0.14 | 54 | 18.5% | 1.11 |
| F | 48/168/504 | med-heavy | OP | +0.46% | 8.07% | 0.08 | 0.05 | 0.04 | 54 | 18.5% | 1.03 |
| G | 24/72/168 | equal | DOT | -0.36% | 20.90% | 0.03 | 0.03 | -0.01 | 186 | 19.4% | 0.99 |
| G | 24/72/168 | med-heavy | DOT | -0.57% | 21.36% | 0.03 | 0.02 | -0.01 | 186 | 19.4% | 0.99 |
| A | 18/48/168 | equal | DOT | -4.99% | 21.49% | -0.14 | -0.13 | -0.08 | 232 | 17.7% | 0.91 |
| A | 18/48/168 | med-heavy | DOT | -5.84% | 21.91% | -0.16 | -0.15 | -0.09 | 232 | 17.7% | 0.90 |
| H | 36/120/504 | equal | DOT | -6.86% | 15.95% | -0.29 | -0.21 | -0.15 | 144 | 18.8% | 0.78 |
| H | 36/120/504 | med-heavy | DOT | -7.55% | 16.80% | -0.31 | -0.23 | -0.15 | 144 | 18.8% | 0.78 |
| C | 36/96/252 | med-heavy | DOT | -9.12% | 20.61% | -0.33 | -0.26 | -0.15 | 168 | 19.0% | 0.78 |
| C | 36/96/252 | equal | DOT | -9.40% | 20.10% | -0.35 | -0.27 | -0.16 | 168 | 19.0% | 0.76 |
| F | 48/168/504 | equal | DOT | -8.16% | 15.97% | -0.37 | -0.25 | -0.18 | 122 | 19.7% | 0.72 |
| B | 24/72/252 | med-heavy | DOT | -10.66% | 21.16% | -0.40 | -0.33 | -0.17 | 186 | 18.8% | 0.77 |
| D | 36/72/336 | med-heavy | DOT | -11.20% | 21.52% | -0.42 | -0.34 | -0.18 | 182 | 18.7% | 0.75 |
| F | 48/168/504 | med-heavy | DOT | -9.63% | 16.93% | -0.44 | -0.30 | -0.20 | 122 | 19.7% | 0.70 |
| B | 24/72/252 | equal | DOT | -11.30% | 21.21% | -0.46 | -0.36 | -0.18 | 186 | 18.8% | 0.73 |
| E | 48/120/336 | med-heavy | DOT | -11.69% | 18.69% | -0.49 | -0.36 | -0.22 | 148 | 18.2% | 0.68 |
| D | 36/72/336 | equal | DOT | -12.20% | 21.13% | -0.49 | -0.39 | -0.20 | 182 | 18.7% | 0.71 |
| E | 48/120/336 | equal | DOT | -11.53% | 18.48% | -0.50 | -0.35 | -0.22 | 148 | 18.2% | 0.66 |
| G | 24/72/168 | med-heavy | ATOM | -15.93% | 27.31% | -0.76 | -0.57 | -0.21 | 202 | 12.9% | 0.62 |
| A | 18/48/168 | med-heavy | ATOM | -16.40% | 27.72% | -0.81 | -0.67 | -0.21 | 250 | 12.8% | 0.59 |
| A | 18/48/168 | equal | ATOM | -16.39% | 26.65% | -0.83 | -0.67 | -0.22 | 250 | 12.8% | 0.58 |
| G | 24/72/168 | equal | ATOM | -16.66% | 26.89% | -0.83 | -0.60 | -0.22 | 202 | 12.9% | 0.58 |
| H | 36/120/504 | equal | ATOM | -16.81% | 17.49% | -0.89 | -0.56 | -0.34 | 148 | 12.2% | 0.48 |
| C | 36/96/252 | equal | ATOM | -18.77% | 20.54% | -0.95 | -0.64 | -0.33 | 170 | 13.5% | 0.45 |
| H | 36/120/504 | med-heavy | ATOM | -18.07% | 18.79% | -0.95 | -0.62 | -0.34 | 148 | 12.2% | 0.48 |
| F | 48/168/504 | equal | ATOM | -16.03% | 17.25% | -0.96 | -0.56 | -0.33 | 122 | 12.3% | 0.43 |
| C | 36/96/252 | med-heavy | ATOM | -19.45% | 21.24% | -0.97 | -0.68 | -0.33 | 170 | 13.5% | 0.46 |
| F | 48/168/504 | med-heavy | ATOM | -17.05% | 18.40% | -1.01 | -0.60 | -0.33 | 122 | 12.3% | 0.42 |
| E | 48/120/336 | equal | ATOM | -19.54% | 20.59% | -1.08 | -0.68 | -0.34 | 152 | 11.8% | 0.41 |
| E | 48/120/336 | med-heavy | ATOM | -20.10% | 21.26% | -1.10 | -0.71 | -0.34 | 152 | 11.8% | 0.43 |
| D | 36/72/336 | equal | ATOM | -24.29% | 24.94% | -1.42 | -1.00 | -0.36 | 198 | 12.6% | 0.35 |
| D | 36/72/336 | med-heavy | ATOM | -24.78% | 25.50% | -1.42 | -1.03 | -0.36 | 198 | 12.6% | 0.37 |
| B | 24/72/252 | equal | ATOM | -24.75% | 26.05% | -1.47 | -1.02 | -0.35 | 202 | 12.4% | 0.33 |
| B | 24/72/252 | med-heavy | ATOM | -25.19% | 26.48% | -1.48 | -1.05 | -0.35 | 202 | 12.4% | 0.35 |

## 2026-03-07 04:42 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +9.07% | Max DD: 14.54% | Sharpe: 0.31 | Sortino: 0.20 | Calmar: 0.20
- Trades: 154 | Win rate: 18.8% | Profit factor: 1.21
- Fees: $108.05 | Slippage: $463.07 | Time in market: 24.5%
- Initial: $10,000 | Final: $10,907.18

## 2026-03-07 04:49 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +29.33% | Max DD: 18.54% | Sharpe: 0.78 | Sortino: 0.66 | Calmar: 0.48
- Trades: 188 | Win rate: 16.0% | Profit factor: 1.53
- Fees: $136.65 | Slippage: $585.62 | Time in market: 29.2%
- Initial: $10,000 | Final: $12,933.44

## 2026-03-07 04:57 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.60% | Max DD: 15.72% | Sharpe: -0.25 | Sortino: -0.17 | Calmar: -0.14
- Trades: 136 | Win rate: 18.4% | Profit factor: 0.85
- Fees: $108.42 | Slippage: $464.65 | Time in market: 21.7%
- Initial: $10,000 | Final: $9,340.00

## 2026-03-07 05:04 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +1.93% | Max DD: 13.83% | Sharpe: 0.12 | Sortino: 0.06 | Calmar: 0.05
- Trades: 108 | Win rate: 17.6% | Profit factor: 1.06
- Fees: $57.88 | Slippage: $248.06 | Time in market: 17.0%
- Initial: $10,000 | Final: $10,193.42

## 2026-03-07 05:11 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.14% | Max DD: 13.95% | Sharpe: 0.05 | Sortino: 0.04 | Calmar: 0.00
- Trades: 136 | Win rate: 17.6% | Profit factor: 1.00
- Fees: $81.86 | Slippage: $350.82 | Time in market: 21.7%
- Initial: $10,000 | Final: $10,014.09

## 2026-03-07 05:19 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.52% | Max DD: 10.00% | Sharpe: 0.39 | Sortino: 0.24 | Calmar: 0.34
- Trades: 112 | Win rate: 18.8% | Profit factor: 1.36
- Fees: $86.10 | Slippage: $368.98 | Time in market: 14.4%
- Initial: $10,000 | Final: $11,052.15

## 2026-03-07 05:27 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.91% | Max DD: 18.28% | Sharpe: -0.04 | Sortino: -0.03 | Calmar: -0.04
- Trades: 134 | Win rate: 15.7% | Profit factor: 0.95
- Fees: $84.67 | Slippage: $362.89 | Time in market: 20.8%
- Initial: $10,000 | Final: $9,809.08

## 2026-03-07 05:35 UTC — Backtest: DonchianMTF on ETH

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -6.60% | Max DD: 15.44% | Sharpe: -0.27 | Sortino: -0.17 | Calmar: -0.15
- Trades: 136 | Win rate: 18.4% | Profit factor: 0.84
- Fees: $100.35 | Slippage: $430.06 | Time in market: 21.7%
- Initial: $10,000 | Final: $9,339.81

## 2026-03-07 05:43 UTC — Backtest: DonchianMTF on DOGE

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +3.59% | Max DD: 12.63% | Sharpe: 0.17 | Sortino: 0.10 | Calmar: 0.09
- Trades: 108 | Win rate: 17.6% | Profit factor: 1.12
- Fees: $54.24 | Slippage: $232.46 | Time in market: 17.0%
- Initial: $10,000 | Final: $10,359.14

## 2026-03-07 05:50 UTC — Backtest: DonchianMTF on LINK

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.74% | Max DD: 12.41% | Sharpe: 0.15 | Sortino: 0.11 | Calmar: 0.07
- Trades: 136 | Win rate: 17.6% | Profit factor: 1.08
- Fees: $77.58 | Slippage: $332.47 | Time in market: 21.7%
- Initial: $10,000 | Final: $10,274.48

## 2026-03-07 05:59 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.59% | Max DD: 9.45% | Sharpe: 0.45 | Sortino: 0.28 | Calmar: 0.43
- Trades: 112 | Win rate: 18.8% | Profit factor: 1.47
- Fees: $80.65 | Slippage: $345.65 | Time in market: 14.4%
- Initial: $10,000 | Final: $11,259.11

## 2026-03-07 06:07 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -2.50% | Max DD: 17.74% | Sharpe: -0.07 | Sortino: -0.05 | Calmar: -0.05
- Trades: 134 | Win rate: 15.7% | Profit factor: 0.93
- Fees: $80.60 | Slippage: $345.41 | Time in market: 20.8%
- Initial: $10,000 | Final: $9,749.55

## 2026-03-07 06:07 UTC — Parameter Sweep: DonchianMTF (ADA, DOGE, ETH, LINK, XRP)

Params: combo=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], lookbacks=['18/48/168', '24/72/168', '24/72/252', '36/120/504', '36/72/336', '36/96/252', '48/120/336', '48/168/504'], weights=['equal', 'med-heavy']

| Combo | Lookbacks | Weights | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G | 24/72/168 | equal | ADA | +29.33% | 18.54% | 0.78 | 0.66 | 0.48 | 188 | 16.0% | 1.53 |
| G | 24/72/168 | med-heavy | ADA | +27.19% | 18.28% | 0.72 | 0.62 | 0.46 | 188 | 16.0% | 1.45 |
| A | 18/48/168 | equal | ADA | +22.80% | 21.73% | 0.64 | 0.59 | 0.33 | 230 | 16.5% | 1.37 |
| A | 18/48/168 | med-heavy | ADA | +20.97% | 21.14% | 0.58 | 0.55 | 0.31 | 230 | 16.5% | 1.31 |
| F | 48/168/504 | equal | XRP | +12.87% | 8.63% | 0.47 | 0.25 | 0.48 | 84 | 17.9% | 1.53 |
| H | 36/120/504 | equal | XRP | +12.59% | 9.45% | 0.45 | 0.28 | 0.43 | 112 | 18.8% | 1.47 |
| F | 48/168/504 | med-heavy | XRP | +10.73% | 9.93% | 0.40 | 0.22 | 0.35 | 84 | 17.9% | 1.41 |
| H | 36/120/504 | med-heavy | XRP | +10.52% | 10.00% | 0.39 | 0.24 | 0.34 | 112 | 18.8% | 1.36 |
| E | 48/120/336 | equal | XRP | +9.23% | 9.05% | 0.35 | 0.22 | 0.33 | 114 | 18.4% | 1.34 |
| D | 36/72/336 | equal | XRP | +9.13% | 12.93% | 0.34 | 0.25 | 0.23 | 150 | 18.7% | 1.23 |
| D | 36/72/336 | med-heavy | XRP | +8.65% | 14.06% | 0.32 | 0.24 | 0.20 | 150 | 18.7% | 1.20 |
| B | 24/72/252 | equal | XRP | +8.49% | 14.94% | 0.31 | 0.24 | 0.18 | 152 | 18.4% | 1.20 |
| G | 24/72/168 | equal | XRP | +9.07% | 14.54% | 0.31 | 0.20 | 0.20 | 154 | 18.8% | 1.21 |
| E | 48/120/336 | med-heavy | XRP | +7.74% | 9.49% | 0.30 | 0.19 | 0.27 | 114 | 18.4% | 1.26 |
| B | 24/72/252 | med-heavy | XRP | +8.09% | 15.52% | 0.30 | 0.23 | 0.17 | 152 | 18.4% | 1.18 |
| G | 24/72/168 | med-heavy | XRP | +8.78% | 15.13% | 0.30 | 0.20 | 0.19 | 154 | 18.8% | 1.19 |
| C | 36/96/252 | equal | XRP | +6.42% | 15.12% | 0.26 | 0.18 | 0.14 | 132 | 16.7% | 1.17 |
| D | 36/72/336 | equal | DOGE | +5.83% | 17.00% | 0.24 | 0.16 | 0.11 | 148 | 16.2% | 1.14 |
| A | 18/48/168 | equal | XRP | +6.50% | 18.13% | 0.24 | 0.18 | 0.12 | 196 | 19.9% | 1.12 |
| A | 18/48/168 | med-heavy | XRP | +6.38% | 18.85% | 0.23 | 0.17 | 0.11 | 196 | 19.9% | 1.11 |
| C | 36/96/252 | med-heavy | XRP | +4.97% | 15.75% | 0.21 | 0.15 | 0.10 | 132 | 16.7% | 1.12 |
| H | 36/120/504 | equal | DOGE | +3.59% | 12.63% | 0.17 | 0.10 | 0.09 | 108 | 17.6% | 1.12 |
| D | 36/72/336 | med-heavy | DOGE | +3.60% | 17.67% | 0.17 | 0.11 | 0.07 | 148 | 16.2% | 1.08 |
| H | 36/120/504 | equal | LINK | +2.74% | 12.41% | 0.15 | 0.11 | 0.07 | 136 | 17.6% | 1.08 |
| E | 48/120/336 | equal | DOGE | +2.71% | 14.78% | 0.14 | 0.08 | 0.06 | 108 | 17.6% | 1.08 |
| F | 48/168/504 | equal | ETH | +2.23% | 10.52% | 0.13 | 0.08 | 0.07 | 112 | 20.5% | 1.07 |
| A | 18/48/168 | equal | DOGE | +2.62% | 19.96% | 0.13 | 0.10 | 0.04 | 200 | 18.0% | 1.05 |
| D | 36/72/336 | equal | LINK | +2.26% | 14.46% | 0.12 | 0.11 | 0.05 | 184 | 17.9% | 1.05 |
| F | 48/168/504 | med-heavy | ETH | +2.04% | 11.65% | 0.12 | 0.08 | 0.06 | 112 | 20.5% | 1.06 |
| H | 36/120/504 | med-heavy | DOGE | +1.93% | 13.83% | 0.12 | 0.06 | 0.05 | 108 | 17.6% | 1.06 |
| F | 48/168/504 | equal | LINK | +1.68% | 12.52% | 0.11 | 0.07 | 0.04 | 112 | 16.1% | 1.07 |
| C | 36/96/252 | equal | LINK | +1.67% | 15.90% | 0.11 | 0.08 | 0.03 | 162 | 17.3% | 1.05 |
| A | 18/48/168 | med-heavy | DOGE | +1.68% | 20.49% | 0.11 | 0.08 | 0.03 | 200 | 18.0% | 1.03 |
| E | 48/120/336 | med-heavy | DOGE | +1.38% | 15.84% | 0.10 | 0.05 | 0.03 | 108 | 17.6% | 1.04 |
| G | 24/72/168 | equal | ETH | +0.76% | 16.62% | 0.08 | 0.06 | 0.02 | 182 | 19.2% | 1.01 |
| F | 48/168/504 | equal | DOGE | +0.76% | 14.93% | 0.07 | 0.04 | 0.02 | 92 | 18.5% | 1.03 |
| G | 24/72/168 | med-heavy | ETH | +0.48% | 17.25% | 0.07 | 0.06 | 0.01 | 182 | 19.2% | 1.01 |
| D | 36/72/336 | med-heavy | LINK | +0.31% | 15.12% | 0.06 | 0.05 | 0.01 | 184 | 17.9% | 1.01 |
| E | 48/120/336 | equal | LINK | +0.18% | 12.87% | 0.05 | 0.04 | 0.00 | 138 | 17.4% | 1.01 |
| H | 36/120/504 | med-heavy | LINK | +0.14% | 13.95% | 0.05 | 0.04 | 0.00 | 136 | 17.6% | 1.00 |
| G | 24/72/168 | equal | DOGE | -0.39% | 18.96% | 0.04 | 0.03 | -0.01 | 152 | 16.4% | 0.99 |
| G | 24/72/168 | med-heavy | DOGE | -0.65% | 18.98% | 0.04 | 0.02 | -0.01 | 152 | 16.4% | 0.99 |
| F | 48/168/504 | med-heavy | DOGE | -0.27% | 16.15% | 0.03 | 0.02 | -0.01 | 92 | 18.5% | 0.99 |
| C | 36/96/252 | med-heavy | ADA | -0.93% | 18.91% | 0.01 | 0.01 | -0.02 | 160 | 15.6% | 0.98 |
| C | 36/96/252 | med-heavy | LINK | -0.98% | 17.03% | 0.01 | 0.01 | -0.02 | 162 | 17.3% | 0.97 |
| D | 36/72/336 | med-heavy | ADA | -1.29% | 16.87% | 0.01 | 0.01 | -0.03 | 184 | 15.8% | 0.97 |
| B | 24/72/252 | equal | DOGE | -1.21% | 18.16% | 0.00 | 0.00 | -0.02 | 150 | 16.0% | 0.97 |
| B | 24/72/252 | med-heavy | DOGE | -1.97% | 18.35% | -0.02 | -0.01 | -0.04 | 150 | 16.0% | 0.96 |
| E | 48/120/336 | med-heavy | ADA | -1.72% | 17.56% | -0.03 | -0.02 | -0.03 | 136 | 15.4% | 0.95 |
| F | 48/168/504 | med-heavy | LINK | -1.57% | 14.27% | -0.03 | -0.02 | -0.04 | 112 | 16.1% | 0.94 |
| E | 48/120/336 | med-heavy | LINK | -2.27% | 13.97% | -0.04 | -0.03 | -0.05 | 138 | 17.4% | 0.94 |
| H | 36/120/504 | med-heavy | ADA | -1.91% | 18.28% | -0.04 | -0.03 | -0.04 | 134 | 15.7% | 0.95 |
| F | 48/168/504 | equal | ADA | -1.74% | 18.45% | -0.04 | -0.03 | -0.03 | 112 | 16.1% | 0.94 |
| B | 24/72/252 | equal | LINK | -2.50% | 16.51% | -0.04 | -0.03 | -0.05 | 188 | 18.1% | 0.94 |
| E | 48/120/336 | equal | ADA | -1.99% | 16.75% | -0.04 | -0.03 | -0.04 | 136 | 15.4% | 0.94 |
| D | 36/72/336 | equal | ADA | -2.63% | 17.25% | -0.04 | -0.03 | -0.05 | 184 | 15.8% | 0.94 |
| F | 48/168/504 | med-heavy | ADA | -1.87% | 19.25% | -0.04 | -0.03 | -0.03 | 112 | 16.1% | 0.94 |
| C | 36/96/252 | equal | ADA | -2.30% | 18.64% | -0.05 | -0.03 | -0.04 | 160 | 15.6% | 0.94 |
| H | 36/120/504 | equal | ADA | -2.50% | 17.74% | -0.07 | -0.05 | -0.05 | 134 | 15.7% | 0.93 |
| B | 24/72/252 | med-heavy | LINK | -3.50% | 16.93% | -0.07 | -0.06 | -0.07 | 188 | 18.1% | 0.92 |
| B | 24/72/252 | med-heavy | ADA | -3.66% | 18.02% | -0.08 | -0.06 | -0.07 | 186 | 15.6% | 0.93 |
| G | 24/72/168 | equal | LINK | -5.22% | 18.57% | -0.15 | -0.12 | -0.10 | 190 | 17.9% | 0.88 |
| G | 24/72/168 | med-heavy | LINK | -5.45% | 18.48% | -0.15 | -0.13 | -0.10 | 190 | 17.9% | 0.88 |
| B | 24/72/252 | equal | ADA | -5.44% | 18.72% | -0.15 | -0.12 | -0.10 | 186 | 15.6% | 0.88 |
| C | 36/96/252 | med-heavy | DOGE | -6.47% | 18.44% | -0.20 | -0.12 | -0.12 | 128 | 17.2% | 0.84 |
| C | 36/96/252 | equal | DOGE | -6.38% | 18.52% | -0.21 | -0.12 | -0.12 | 128 | 17.2% | 0.83 |
| D | 36/72/336 | med-heavy | ETH | -6.75% | 17.10% | -0.22 | -0.17 | -0.13 | 176 | 18.8% | 0.87 |
| A | 18/48/168 | med-heavy | ETH | -8.19% | 18.52% | -0.24 | -0.22 | -0.15 | 236 | 19.1% | 0.87 |
| B | 24/72/252 | med-heavy | ETH | -7.57% | 17.09% | -0.25 | -0.19 | -0.15 | 180 | 18.9% | 0.86 |
| H | 36/120/504 | med-heavy | ETH | -6.60% | 15.72% | -0.25 | -0.17 | -0.14 | 136 | 18.4% | 0.85 |
| H | 36/120/504 | equal | ETH | -6.60% | 15.44% | -0.27 | -0.17 | -0.15 | 136 | 18.4% | 0.84 |
| A | 18/48/168 | equal | ETH | -8.76% | 18.51% | -0.28 | -0.24 | -0.16 | 236 | 19.1% | 0.85 |
| A | 18/48/168 | med-heavy | LINK | -10.69% | 21.70% | -0.34 | -0.31 | -0.17 | 234 | 17.9% | 0.80 |
| D | 36/72/336 | equal | ETH | -9.10% | 16.52% | -0.34 | -0.25 | -0.19 | 176 | 18.8% | 0.81 |
| A | 18/48/168 | equal | LINK | -10.41% | 21.76% | -0.35 | -0.31 | -0.17 | 234 | 17.9% | 0.79 |
| B | 24/72/252 | equal | ETH | -9.42% | 16.89% | -0.35 | -0.26 | -0.19 | 180 | 18.9% | 0.81 |
| E | 48/120/336 | med-heavy | ETH | -9.28% | 16.92% | -0.37 | -0.24 | -0.19 | 138 | 18.1% | 0.80 |
| E | 48/120/336 | equal | ETH | -9.60% | 17.03% | -0.41 | -0.26 | -0.19 | 138 | 18.1% | 0.78 |
| C | 36/96/252 | med-heavy | ETH | -10.62% | 17.35% | -0.41 | -0.30 | -0.21 | 164 | 17.1% | 0.79 |
| C | 36/96/252 | equal | ETH | -11.06% | 17.96% | -0.47 | -0.32 | -0.21 | 164 | 17.1% | 0.77 |

## 2026-03-07 06:19 UTC — Backtest: DonchianMTF on FIL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -7.86% | Max DD: 16.81% | Sharpe: -0.41 | Sortino: -0.28 | Calmar: -0.22
- Trades: 134 | Win rate: 19.4% | Profit factor: 0.74
- Fees: $62.02 | Slippage: $265.81 | Time in market: 30.1%
- Initial: $10,000 | Final: $9,214.42

## 2026-03-07 06:21 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.46% | Max DD: 11.13% | Sharpe: 0.19 | Sortino: 0.12 | Calmar: 0.10
- Trades: 72 | Win rate: 18.1% | Profit factor: 1.12
- Fees: $50.23 | Slippage: $215.27 | Time in market: 15.3%
- Initial: $10,000 | Final: $10,246.41

## 2026-03-07 06:24 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.74% | Max DD: 16.70% | Sharpe: 0.37 | Sortino: 0.25 | Calmar: 0.18
- Trades: 141 | Win rate: 17.0% | Profit factor: 1.17
- Fees: $155.70 | Slippage: $667.30 | Time in market: 29.5%
- Initial: $10,000 | Final: $10,673.86

## 2026-03-07 06:27 UTC — Backtest: DonchianMTF on NEAR

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.50% | Max DD: 10.00% | Sharpe: 0.07 | Sortino: 0.05 | Calmar: 0.02
- Trades: 95 | Win rate: 21.1% | Profit factor: 1.02
- Fees: $45.02 | Slippage: $192.96 | Time in market: 19.3%
- Initial: $10,000 | Final: $10,049.55

## 2026-03-07 06:31 UTC — Backtest: DonchianMTF on OP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.88% | Max DD: 13.27% | Sharpe: 0.18 | Sortino: 0.16 | Calmar: 0.10
- Trades: 168 | Win rate: 18.5% | Profit factor: 1.08
- Fees: $79.87 | Slippage: $342.29 | Time in market: 35.5%
- Initial: $10,000 | Final: $10,288.12

## 2026-03-07 06:34 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.27% | Max DD: 8.88% | Sharpe: 0.54 | Sortino: 0.41 | Calmar: 0.62
- Trades: 128 | Win rate: 25.0% | Profit factor: 1.42
- Fees: $86.02 | Slippage: $368.64 | Time in market: 28.9%
- Initial: $10,000 | Final: $11,226.72

## 2026-03-07 06:38 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +25.68% | Max DD: 8.82% | Sharpe: 1.18 | Sortino: 0.61 | Calmar: 1.26
- Trades: 58 | Win rate: 15.5% | Profit factor: 2.58
- Fees: $44.91 | Slippage: $192.48 | Time in market: 9.1%
- Initial: $10,000 | Final: $12,567.65

## 2026-03-07 06:43 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.88% | Max DD: 9.64% | Sharpe: 0.35 | Sortino: 0.27 | Calmar: 0.32
- Trades: 127 | Win rate: 20.5% | Profit factor: 1.24
- Fees: $90.80 | Slippage: $389.15 | Time in market: 28.8%
- Initial: $10,000 | Final: $10,687.59

## 2026-03-07 06:47 UTC — Backtest: DonchianMTF on NEAR

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.92% | Max DD: 12.20% | Sharpe: 0.09 | Sortino: 0.08 | Calmar: 0.03
- Trades: 137 | Win rate: 21.2% | Profit factor: 1.03
- Fees: $74.17 | Slippage: $317.85 | Time in market: 29.8%
- Initial: $10,000 | Final: $10,092.15

## 2026-03-07 06:51 UTC — Backtest: DonchianMTF on OP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -9.04% | Max DD: 17.19% | Sharpe: -0.55 | Sortino: -0.40 | Calmar: -0.25
- Trades: 142 | Win rate: 17.6% | Profit factor: 0.70
- Fees: $57.43 | Slippage: $246.15 | Time in market: 29.2%
- Initial: $10,000 | Final: $9,096.37

## 2026-03-07 06:56 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +3.61% | Max DD: 15.47% | Sharpe: 0.21 | Sortino: 0.15 | Calmar: 0.11
- Trades: 136 | Win rate: 16.2% | Profit factor: 1.08
- Fees: $96.32 | Slippage: $412.82 | Time in market: 22.5%
- Initial: $10,000 | Final: $10,361.34

## 2026-03-07 21:18 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +60.06% | Max DD: 12.86% | Sharpe: 1.23 | Sortino: 1.09 | Calmar: 1.32
- Trades: 154 | Win rate: 20.1% | Profit factor: 2.01
- Fees: $193.86 | Slippage: $830.81 | Time in market: 30.7%
- Initial: $10,000 | Final: $16,006.48

## 2026-03-07 21:22 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +61.33% | Max DD: 11.14% | Sharpe: 1.26 | Sortino: 1.14 | Calmar: 1.59
- Trades: 184 | Win rate: 21.2% | Profit factor: 2.07
- Fees: $122.00 | Slippage: $519.61 | Time in market: 34.1%
- Initial: $10,000 | Final: $16,133.33

## 2026-03-07 21:26 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +29.33% | Max DD: 18.54% | Sharpe: 0.78 | Sortino: 0.66 | Calmar: 0.48
- Trades: 188 | Win rate: 16.0% | Profit factor: 1.53
- Fees: $136.65 | Slippage: $585.62 | Time in market: 29.2%
- Initial: $10,000 | Final: $12,933.44

## 2026-03-07 21:30 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.87% | Max DD: 8.63% | Sharpe: 0.47 | Sortino: 0.25 | Calmar: 0.48
- Trades: 84 | Win rate: 17.9% | Profit factor: 1.53
- Fees: $64.90 | Slippage: $278.15 | Time in market: 10.1%
- Initial: $10,000 | Final: $11,286.55

## 2026-03-07 21:34 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +50.89% | Max DD: 13.80% | Sharpe: 1.14 | Sortino: 1.35 | Calmar: 1.07
- Trades: 303 | Win rate: 20.1% | Profit factor: 1.66
- Fees: $318.20 | Slippage: $1360.79 | Time in market: 61.5%
- Initial: $10,000 | Final: $15,089.00

## 2026-03-07 21:38 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +71.40% | Max DD: 9.91% | Sharpe: 1.52 | Sortino: 1.77 | Calmar: 2.03
- Trades: 321 | Win rate: 21.5% | Profit factor: 1.83
- Fees: $177.61 | Slippage: $758.38 | Time in market: 63.3%
- Initial: $10,000 | Final: $17,139.96

## 2026-03-07 21:42 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +21.46% | Max DD: 12.65% | Sharpe: 0.63 | Sortino: 0.68 | Calmar: 0.53
- Trades: 339 | Win rate: 18.3% | Profit factor: 1.30
- Fees: $199.24 | Slippage: $853.91 | Time in market: 58.4%
- Initial: $10,000 | Final: $12,146.08

## 2026-03-07 21:46 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +16.96% | Max DD: 14.70% | Sharpe: 0.56 | Sortino: 0.57 | Calmar: 0.37
- Trades: 256 | Win rate: 18.4% | Profit factor: 1.28
- Fees: $152.65 | Slippage: $654.20 | Time in market: 47.2%
- Initial: $10,000 | Final: $11,695.78

## 2026-03-07 21:50 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +40.55% | Max DD: 12.60% | Sharpe: 1.08 | Sortino: 1.25 | Calmar: 0.95
- Trades: 301 | Win rate: 20.6% | Profit factor: 1.60
- Fees: $280.72 | Slippage: $1200.55 | Time in market: 61.6%
- Initial: $10,000 | Final: $14,054.73

## 2026-03-07 21:54 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +70.32% | Max DD: 8.53% | Sharpe: 1.63 | Sortino: 1.91 | Calmar: 2.33
- Trades: 323 | Win rate: 21.7% | Profit factor: 1.92
- Fees: $160.68 | Slippage: $686.26 | Time in market: 63.6%
- Initial: $10,000 | Final: $17,031.53

## 2026-03-07 21:58 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +24.51% | Max DD: 11.21% | Sharpe: 0.76 | Sortino: 0.83 | Calmar: 0.68
- Trades: 343 | Win rate: 18.1% | Profit factor: 1.37
- Fees: $185.56 | Slippage: $795.25 | Time in market: 58.3%
- Initial: $10,000 | Final: $12,451.08

## 2026-03-07 22:02 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +14.69% | Max DD: 13.52% | Sharpe: 0.55 | Sortino: 0.55 | Calmar: 0.35
- Trades: 256 | Win rate: 18.8% | Profit factor: 1.26
- Fees: $137.15 | Slippage: $587.79 | Time in market: 47.3%
- Initial: $10,000 | Final: $11,468.92

## 2026-03-07 22:06 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +31.61% | Max DD: 10.15% | Sharpe: 1.01 | Sortino: 1.16 | Calmar: 0.95
- Trades: 319 | Win rate: 20.7% | Profit factor: 1.55
- Fees: $248.19 | Slippage: $1061.54 | Time in market: 64.6%
- Initial: $10,000 | Final: $13,160.89

## 2026-03-07 22:10 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +68.94% | Max DD: 6.36% | Sharpe: 1.74 | Sortino: 2.05 | Calmar: 3.07
- Trades: 335 | Win rate: 21.2% | Profit factor: 2.03
- Fees: $142.18 | Slippage: $607.40 | Time in market: 64.5%
- Initial: $10,000 | Final: $16,893.54

## 2026-03-07 22:14 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +26.62% | Max DD: 9.80% | Sharpe: 0.89 | Sortino: 0.98 | Calmar: 0.84
- Trades: 355 | Win rate: 18.0% | Profit factor: 1.43
- Fees: $167.37 | Slippage: $717.32 | Time in market: 60.7%
- Initial: $10,000 | Final: $12,661.92

## 2026-03-07 22:18 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +10.01% | Max DD: 14.73% | Sharpe: 0.46 | Sortino: 0.45 | Calmar: 0.22
- Trades: 278 | Win rate: 18.7% | Profit factor: 1.20
- Fees: $120.37 | Slippage: $515.88 | Time in market: 52.2%
- Initial: $10,000 | Final: $11,000.83

## 2026-03-07 22:23 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +18.56% | Max DD: 8.66% | Sharpe: 0.75 | Sortino: 0.81 | Calmar: 0.68
- Trades: 319 | Win rate: 20.4% | Profit factor: 1.37
- Fees: $219.02 | Slippage: $936.91 | Time in market: 63.8%
- Initial: $10,000 | Final: $11,856.20

## 2026-03-07 22:27 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +64.45% | Max DD: 5.95% | Sharpe: 1.76 | Sortino: 2.07 | Calmar: 3.10
- Trades: 321 | Win rate: 22.1% | Profit factor: 2.08
- Fees: $128.94 | Slippage: $551.15 | Time in market: 62.8%
- Initial: $10,000 | Final: $16,444.91

## 2026-03-07 22:31 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +27.54% | Max DD: 10.09% | Sharpe: 0.97 | Sortino: 1.07 | Calmar: 0.84
- Trades: 339 | Win rate: 18.3% | Profit factor: 1.47
- Fees: $153.51 | Slippage: $657.92 | Time in market: 58.9%
- Initial: $10,000 | Final: $12,754.34

## 2026-03-07 22:35 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.96% | Max DD: 13.85% | Sharpe: 0.36 | Sortino: 0.35 | Calmar: 0.16
- Trades: 280 | Win rate: 19.6% | Profit factor: 1.15
- Fees: $110.13 | Slippage: $471.97 | Time in market: 52.8%
- Initial: $10,000 | Final: $10,695.88

## 2026-03-07 22:39 UTC — Backtest: DonchianMTF on BTC

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.61% | Max DD: 9.41% | Sharpe: 0.35 | Sortino: 0.35 | Calmar: 0.23
- Trades: 311 | Win rate: 20.3% | Profit factor: 1.16
- Fees: $186.75 | Slippage: $799.02 | Time in market: 62.4%
- Initial: $10,000 | Final: $10,660.99

## 2026-03-07 22:43 UTC — Backtest: DonchianMTF on SOL

- Period: 2021-01-22 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +59.67% | Max DD: 6.33% | Sharpe: 1.74 | Sortino: 2.00 | Calmar: 2.72
- Trades: 313 | Win rate: 22.4% | Profit factor: 2.12
- Fees: $116.91 | Slippage: $500.04 | Time in market: 61.0%
- Initial: $10,000 | Final: $15,966.74

## 2026-03-07 22:47 UTC — Backtest: DonchianMTF on ADA

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +27.55% | Max DD: 10.79% | Sharpe: 1.00 | Sortino: 1.07 | Calmar: 0.78
- Trades: 329 | Win rate: 18.2% | Profit factor: 1.51
- Fees: $137.87 | Slippage: $590.87 | Time in market: 57.8%
- Initial: $10,000 | Final: $12,754.77

## 2026-03-07 22:51 UTC — Backtest: DonchianMTF on XRP

- Period: 2021-01-01 to 2023-12-30
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.93% | Max DD: 14.44% | Sharpe: 0.18 | Sortino: 0.16 | Calmar: 0.07
- Trades: 280 | Win rate: 19.6% | Profit factor: 1.07
- Fees: $100.13 | Slippage: $429.14 | Time in market: 52.8%
- Initial: $10,000 | Final: $10,293.19

## 2026-03-07 22:51 UTC — Parameter Sweep: DonchianMTF (ADA, BTC, SOL, XRP)

Params: mom_weight=['0.0', '0.2', '0.4', '0.6', '0.8', '1.0']

| Mom_weight | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.8 | SOL | +64.45% | 5.95% | 1.76 | 2.07 | 3.10 | 321 | 22.1% | 2.08 |
| 1 | SOL | +59.67% | 6.33% | 1.74 | 2.00 | 2.72 | 313 | 22.4% | 2.12 |
| 0.6 | SOL | +68.94% | 6.36% | 1.74 | 2.05 | 3.07 | 335 | 21.2% | 2.03 |
| 0.4 | SOL | +70.32% | 8.53% | 1.63 | 1.91 | 2.33 | 323 | 21.7% | 1.92 |
| 0.2 | SOL | +71.40% | 9.91% | 1.52 | 1.77 | 2.03 | 321 | 21.5% | 1.83 |
| 0 | SOL | +61.33% | 11.14% | 1.26 | 1.14 | 1.59 | 184 | 21.2% | 2.07 |
| 0 | BTC | +60.06% | 12.86% | 1.23 | 1.09 | 1.32 | 154 | 20.1% | 2.01 |
| 0.2 | BTC | +50.89% | 13.80% | 1.14 | 1.35 | 1.07 | 303 | 20.1% | 1.66 |
| 0.4 | BTC | +40.55% | 12.60% | 1.08 | 1.25 | 0.95 | 301 | 20.6% | 1.60 |
| 0.6 | BTC | +31.61% | 10.15% | 1.01 | 1.16 | 0.95 | 319 | 20.7% | 1.55 |
| 1 | ADA | +27.55% | 10.79% | 1.00 | 1.07 | 0.78 | 329 | 18.2% | 1.51 |
| 0.8 | ADA | +27.54% | 10.09% | 0.97 | 1.07 | 0.84 | 339 | 18.3% | 1.47 |
| 0.6 | ADA | +26.62% | 9.80% | 0.89 | 0.98 | 0.84 | 355 | 18.0% | 1.43 |
| 0 | ADA | +29.33% | 18.54% | 0.78 | 0.66 | 0.48 | 188 | 16.0% | 1.53 |
| 0.4 | ADA | +24.51% | 11.21% | 0.76 | 0.83 | 0.68 | 343 | 18.1% | 1.37 |
| 0.8 | BTC | +18.56% | 8.66% | 0.75 | 0.81 | 0.68 | 319 | 20.4% | 1.37 |
| 0.2 | ADA | +21.46% | 12.65% | 0.63 | 0.68 | 0.53 | 339 | 18.3% | 1.30 |
| 0.2 | XRP | +16.96% | 14.70% | 0.56 | 0.57 | 0.37 | 256 | 18.4% | 1.28 |
| 0.4 | XRP | +14.69% | 13.52% | 0.55 | 0.55 | 0.35 | 256 | 18.8% | 1.26 |
| 0 | XRP | +12.87% | 8.63% | 0.47 | 0.25 | 0.48 | 84 | 17.9% | 1.53 |
| 0.6 | XRP | +10.01% | 14.73% | 0.46 | 0.45 | 0.22 | 278 | 18.7% | 1.20 |
| 0.8 | XRP | +6.96% | 13.85% | 0.36 | 0.35 | 0.16 | 280 | 19.6% | 1.15 |
| 1 | BTC | +6.61% | 9.41% | 0.35 | 0.35 | 0.23 | 311 | 20.3% | 1.16 |
| 1 | XRP | +2.93% | 14.44% | 0.18 | 0.16 | 0.07 | 280 | 19.6% | 1.07 |

## 2026-03-07 22:54 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.74% | Max DD: 16.70% | Sharpe: 0.37 | Sortino: 0.25 | Calmar: 0.18
- Trades: 141 | Win rate: 17.0% | Profit factor: 1.17
- Fees: $155.70 | Slippage: $667.30 | Time in market: 29.5%
- Initial: $10,000 | Final: $10,673.86

## 2026-03-07 22:56 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.88% | Max DD: 9.64% | Sharpe: 0.35 | Sortino: 0.27 | Calmar: 0.32
- Trades: 127 | Win rate: 20.5% | Profit factor: 1.24
- Fees: $90.80 | Slippage: $389.15 | Time in market: 28.8%
- Initial: $10,000 | Final: $10,687.59

## 2026-03-07 22:58 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +12.27% | Max DD: 8.88% | Sharpe: 0.54 | Sortino: 0.41 | Calmar: 0.62
- Trades: 128 | Win rate: 25.0% | Profit factor: 1.42
- Fees: $86.02 | Slippage: $368.64 | Time in market: 28.9%
- Initial: $10,000 | Final: $11,226.72

## 2026-03-07 23:00 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +25.68% | Max DD: 8.82% | Sharpe: 1.18 | Sortino: 0.61 | Calmar: 1.26
- Trades: 58 | Win rate: 15.5% | Profit factor: 2.58
- Fees: $44.91 | Slippage: $192.48 | Time in market: 9.1%
- Initial: $10,000 | Final: $12,567.65

## 2026-03-07 23:03 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.63% | Max DD: 21.22% | Sharpe: -0.06 | Sortino: -0.05 | Calmar: -0.04
- Trades: 249 | Win rate: 16.5% | Profit factor: 0.96
- Fees: $157.98 | Slippage: $677.06 | Time in market: 54.8%
- Initial: $10,000 | Final: $9,836.61

## 2026-03-07 23:05 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -7.61% | Max DD: 12.25% | Sharpe: -0.40 | Sortino: -0.43 | Calmar: -0.29
- Trades: 273 | Win rate: 15.8% | Profit factor: 0.84
- Fees: $111.66 | Slippage: $476.86 | Time in market: 60.9%
- Initial: $10,000 | Final: $9,238.67

## 2026-03-07 23:07 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +11.24% | Max DD: 11.53% | Sharpe: 0.55 | Sortino: 0.55 | Calmar: 0.44
- Trades: 228 | Win rate: 21.5% | Profit factor: 1.29
- Fees: $99.52 | Slippage: $426.54 | Time in market: 53.9%
- Initial: $10,000 | Final: $11,123.71

## 2026-03-07 23:09 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.71% | Max DD: 17.00% | Sharpe: 0.08 | Sortino: 0.07 | Calmar: 0.02
- Trades: 178 | Win rate: 18.0% | Profit factor: 1.02
- Fees: $79.76 | Slippage: $341.83 | Time in market: 35.6%
- Initial: $10,000 | Final: $10,071.01

## 2026-03-07 23:11 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +0.95% | Max DD: 18.15% | Sharpe: 0.10 | Sortino: 0.09 | Calmar: 0.02
- Trades: 261 | Win rate: 16.9% | Profit factor: 1.02
- Fees: $152.76 | Slippage: $654.69 | Time in market: 56.4%
- Initial: $10,000 | Final: $10,095.23

## 2026-03-07 23:13 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -4.38% | Max DD: 10.04% | Sharpe: -0.23 | Sortino: -0.25 | Calmar: -0.20
- Trades: 275 | Win rate: 16.4% | Profit factor: 0.90
- Fees: $102.45 | Slippage: $436.97 | Time in market: 60.6%
- Initial: $10,000 | Final: $9,561.50

## 2026-03-07 23:16 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +6.54% | Max DD: 10.83% | Sharpe: 0.40 | Sortino: 0.38 | Calmar: 0.27
- Trades: 236 | Win rate: 22.0% | Profit factor: 1.19
- Fees: $80.75 | Slippage: $346.09 | Time in market: 55.2%
- Initial: $10,000 | Final: $10,654.21

## 2026-03-07 23:18 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.66% | Max DD: 15.79% | Sharpe: 0.20 | Sortino: 0.16 | Calmar: 0.08
- Trades: 190 | Win rate: 18.4% | Profit factor: 1.07
- Fees: $72.42 | Slippage: $310.36 | Time in market: 38.1%
- Initial: $10,000 | Final: $10,266.47

## 2026-03-07 23:20 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +2.83% | Max DD: 15.47% | Sharpe: 0.21 | Sortino: 0.19 | Calmar: 0.08
- Trades: 259 | Win rate: 16.6% | Profit factor: 1.07
- Fees: $152.09 | Slippage: $651.82 | Time in market: 54.7%
- Initial: $10,000 | Final: $10,283.31

## 2026-03-07 23:22 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: -1.64% | Max DD: 8.80% | Sharpe: -0.07 | Sortino: -0.08 | Calmar: -0.09
- Trades: 267 | Win rate: 17.2% | Profit factor: 0.96
- Fees: $97.03 | Slippage: $413.39 | Time in market: 59.5%
- Initial: $10,000 | Final: $9,835.71

## 2026-03-07 23:24 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +4.43% | Max DD: 8.48% | Sharpe: 0.31 | Sortino: 0.30 | Calmar: 0.24
- Trades: 232 | Win rate: 21.6% | Profit factor: 1.14
- Fees: $71.73 | Slippage: $307.41 | Time in market: 53.5%
- Initial: $10,000 | Final: $10,443.44

## 2026-03-07 23:26 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-04
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=1.5
- Return: +3.24% | Max DD: 14.74% | Sharpe: 0.24 | Sortino: 0.20 | Calmar: 0.10
- Trades: 190 | Win rate: 18.4% | Profit factor: 1.09
- Fees: $68.43 | Slippage: $293.28 | Time in market: 38.3%
- Initial: $10,000 | Final: $10,323.94

## 2026-03-07 23:26 UTC — Parameter Sweep: DonchianMTF (ADA, BTC, SOL, XRP)

Params: mom_weight=['0.0', '0.4', '0.6', '0.8']

| Mom_weight | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | XRP | +25.68% | 8.82% | 1.18 | 0.61 | 1.26 | 58 | 15.5% | 2.58 |
| 0.4 | ADA | +11.24% | 11.53% | 0.55 | 0.55 | 0.44 | 228 | 21.5% | 1.29 |
| 0 | ADA | +12.27% | 8.88% | 0.54 | 0.41 | 0.62 | 128 | 25.0% | 1.42 |
| 0.6 | ADA | +6.54% | 10.83% | 0.40 | 0.38 | 0.27 | 236 | 22.0% | 1.19 |
| 0 | BTC | +6.74% | 16.70% | 0.37 | 0.25 | 0.18 | 141 | 17.0% | 1.17 |
| 0 | SOL | +6.88% | 9.64% | 0.35 | 0.27 | 0.32 | 127 | 20.5% | 1.24 |
| 0.8 | ADA | +4.43% | 8.48% | 0.31 | 0.30 | 0.24 | 232 | 21.6% | 1.14 |
| 0.8 | XRP | +3.24% | 14.74% | 0.24 | 0.20 | 0.10 | 190 | 18.4% | 1.09 |
| 0.8 | BTC | +2.83% | 15.47% | 0.21 | 0.19 | 0.08 | 259 | 16.6% | 1.07 |
| 0.6 | XRP | +2.66% | 15.79% | 0.20 | 0.16 | 0.08 | 190 | 18.4% | 1.07 |
| 0.6 | BTC | +0.95% | 18.15% | 0.10 | 0.09 | 0.02 | 261 | 16.9% | 1.02 |
| 0.4 | XRP | +0.71% | 17.00% | 0.08 | 0.07 | 0.02 | 178 | 18.0% | 1.02 |
| 0.4 | BTC | -1.63% | 21.22% | -0.06 | -0.05 | -0.04 | 249 | 16.5% | 0.96 |
| 0.8 | SOL | -1.64% | 8.80% | -0.07 | -0.08 | -0.09 | 267 | 17.2% | 0.96 |
| 0.6 | SOL | -4.38% | 10.04% | -0.23 | -0.25 | -0.20 | 275 | 16.4% | 0.90 |
| 0.4 | SOL | -7.61% | 12.25% | -0.40 | -0.43 | -0.29 | 273 | 15.8% | 0.84 |

## 2026-03-09 00:56 UTC — Signal Experiment: VW / MR / CS Weight Sweep

Portfolio: BTC(G), SOL(G), ADA(G), XRP(F)
IS: 2021-2023, OOS: 2024-2026, Capital: $10,000, Leverage: 3.0x

| Signal | Weight | IS Sharpe | OOS Sharpe | OOS Return | OOS MaxDD |
| --- | --- | --- | --- | --- | --- |
| VW | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| VW | 0.1 | 1.36 | 0.74 | +21.39% | 13.19% |
| VW | 0.2 | 1.38 | 0.74 | +23.50% | 15.18% |
| VW | 0.3 | 1.38 | 0.77 | +26.18% | 16.42% |
| VW | 0.4 | 1.37 | 0.77 | +26.94% | 17.06% |
| VW | 0.5 | 1.38 | 0.77 | +27.63% | 17.23% |
| MR | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| MR | 0.1 | 1.39 | 0.81 | +20.35% | 10.45% |
| MR | 0.2 | 1.39 | 0.81 | +19.98% | 10.04% |
| MR | 0.3 | 1.38 | 0.81 | +19.60% | 9.63% |
| MR | 0.4 | 1.38 | 0.81 | +19.20% | 9.21% |
| MR | 0.5 | 1.37 | 0.81 | +18.77% | 8.78% |
| CS | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| CS | 0.1 | 1.25 | 0.79 | +20.35% | 11.65% |
| CS | 0.2 | 1.29 | 0.78 | +19.97% | 12.42% |
| CS | 0.3 | 1.33 | 0.76 | +19.56% | 13.14% |
| CS | 0.4 | 1.36 | 0.77 | +19.97% | 13.54% |
| CS | 0.5 | 1.38 | 0.77 | +20.37% | 13.80% |

## 2026-03-09 12:16 UTC — Signal Experiment: VW / MR / CS Weight Sweep

Portfolio: BTC(G), SOL(G), ADA(G), XRP(F)
IS: 2021-2023, OOS: 2024-2026, Capital: $10,000, Leverage: 3.0x

| Signal | Weight | IS Sharpe | OOS Sharpe | OOS Return | OOS MaxDD |
| --- | --- | --- | --- | --- | --- |
| VW | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| VW | 0.1 | 1.36 | 0.74 | +21.39% | 13.19% |
| VW | 0.2 | 1.38 | 0.74 | +23.50% | 15.18% |
| VW | 0.3 | 1.38 | 0.77 | +26.18% | 16.42% |
| VW | 0.4 | 1.37 | 0.77 | +26.94% | 17.06% |
| VW | 0.5 | 1.38 | 0.77 | +27.63% | 17.23% |
| MR | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| MR | 0.1 | 1.39 | 0.81 | +20.35% | 10.45% |
| MR | 0.2 | 1.39 | 0.81 | +19.98% | 10.04% |
| MR | 0.3 | 1.38 | 0.81 | +19.60% | 9.63% |
| MR | 0.4 | 1.38 | 0.81 | +19.20% | 9.21% |
| MR | 0.5 | 1.37 | 0.81 | +18.77% | 8.78% |
| CS | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| CS | 0.1 | 1.25 | 0.79 | +20.35% | 11.65% |
| CS | 0.2 | 1.29 | 0.78 | +19.97% | 12.42% |
| CS | 0.3 | 1.33 | 0.76 | +19.56% | 13.14% |
| CS | 0.4 | 1.36 | 0.77 | +19.97% | 13.54% |
| CS | 0.5 | 1.38 | 0.77 | +20.37% | 13.80% |

## 2026-03-09 12:40 UTC — Signal Experiment: VW / MR / CS Weight Sweep

Portfolio: BTC(G), SOL(G), ADA(G), XRP(F)
IS: 2021-2023, OOS: 2024-2026, Capital: $10,000, Leverage: 3.0x

| Signal | Weight | IS Sharpe | OOS Sharpe | OOS Return | OOS MaxDD |
| --- | --- | --- | --- | --- | --- |
| VW | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| VW | 0.1 | 1.36 | 0.74 | +21.39% | 13.19% |
| VW | 0.2 | 1.38 | 0.74 | +23.50% | 15.18% |
| VW | 0.3 | 1.38 | 0.77 | +26.18% | 16.42% |
| VW | 0.4 | 1.37 | 0.77 | +26.94% | 17.06% |
| VW | 0.5 | 1.38 | 0.77 | +27.63% | 17.23% |
| MR | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| MR | 0.1 | 1.39 | 0.81 | +20.35% | 10.45% |
| MR | 0.2 | 1.39 | 0.81 | +19.98% | 10.04% |
| MR | 0.3 | 1.38 | 0.81 | +19.60% | 9.63% |
| MR | 0.4 | 1.38 | 0.81 | +19.20% | 9.21% |
| MR | 0.5 | 1.37 | 0.81 | +18.77% | 8.78% |
| CS | 0.0 | 1.40 | 0.81 | +20.71% | 10.85% |
| CS | 0.1 | 1.25 | 0.79 | +20.35% | 11.65% |
| CS | 0.2 | 1.29 | 0.78 | +19.97% | 12.42% |
| CS | 0.3 | 1.33 | 0.76 | +19.56% | 13.14% |
| CS | 0.4 | 1.36 | 0.77 | +19.97% | 13.54% |
| CS | 0.5 | 1.38 | 0.77 | +20.37% | 13.80% |

## 2026-03-24 — FNG OOS A/B Experiment: Walk-Forward Validation

- **Hypothesis**: FNG 特征在 feature importance 中排名极高（top 4），但高 importance 可能只是 IS 过拟合。需要 OOS 验证是否真正提升预测能力。
- **Method**:
  - Group A: 134 特征（不含 FNG）
  - Group B: 138 特征（含 fng_raw, fng_ma_7, fng_ma_30, fng_zscore_30）
  - 完全相同的：训练数据(2021-2024)、OOS(2024-2026Q1)、模型超参(LGB n=500, lr=0.03, depth=5)、walk-forward 3-fold CV、Kelly sizing
  - BTC/ETH/SOL, 1H, target=fwd_return_4h
- **Results**:

| Metric | No FNG (A) | With FNG (B) | Delta |
|--------|-----------|-------------|-------|
| OOS Avg Return | -21.86% | -16.76% | **+5.10%** |
| OOS Avg Sharpe | -2.778 | -1.789 | **+0.989** |
| OOS Avg Sortino | -3.186 | -2.120 | **+1.065** |
| OOS Worst MaxDD | 32.74% | 29.60% | **-3.14%** |
| OOS Avg WinRate | 48.3% | 49.0% | +0.68% |
| CV Dir Accuracy | 0.5343 | 0.5347 | +0.0005 |

  Per-Symbol OOS Sharpe: BTC -5.27 -> -3.57 (+1.70), ETH -1.50 -> -0.95 (+0.55), SOL -1.57 -> -0.86 (+0.72)

  Per-Quarter OOS Return (avg across 3 symbols):
  - 2024Q1: +0.15% -> +3.26% (**FNG+**), 2024Q2: -5.95% -> -3.28% (**FNG+**)
  - 2024Q3: -5.02% -> -4.57% (~), 2024Q4: -1.99% -> -1.17% (**FNG+**)
  - 2025Q1: -4.59% -> -4.54% (~), 2025Q2: -1.93% -> -1.78% (~)
  - 2025Q3: -0.55% -> +0.26% (**FNG+**), 2025Q4: -2.14% -> -3.40% (**FNG-**)
  - 2026Q1: -2.57% -> -3.12% (**FNG-**)

- **Conclusion**:
  - FNG 在 OOS 中确实有正贡献（Sharpe +0.99, Return +5.1%, MaxDD -3.1%），**不是纯粹的 IS 过拟合**
  - 所有 3 个币种均一致性改善，非单币种噪声
  - **但注意**：两组 OOS 表现都是负的（ML 模型整体亏损），说明 ML pipeline 本身需要优化
  - FNG 在 2024 年效果最好（市场情绪波动大），2025Q4-2026Q1 反而略差（可能是 FNG 信号与 price action 滞后）
  - **Decision**: 保留 sentiment 特征组在 production pipeline 中，但 ML pipeline 的整体负收益是更大的待解决问题

---

## 2026-03-24 — Fear & Greed Index Feature Experiment

- **Hypothesis**: Crypto Fear & Greed Index (alternative.me) 包含市场情绪信息，作为特征可能提升 ML 预测能力
- **Method**:
  1. 从 alternative.me API 拉取完整 FNG 历史数据（2018-02-01 ~ 2026-03-25, 2971 天）
  2. 创建 `SentimentFeatures` 模块，按日期与 1H OHLCV 做 join，生成 4 个特征：
     - `fng_raw`: 原始值归一化到 0-1
     - `fng_ma_7`: 7日移动平均
     - `fng_ma_30`: 30日移动平均
     - `fng_zscore_30`: 30日 z-score
  3. 所有特征 shift(1) 防穿越（FNG 为日度数据，仅使用前一天的值）
  4. 训练 LightGBM (n_estimators=300, target=fwd_return_4h) 对比加入 FNG 前后的 feature importance
- **Data**: BTC/ETH/SOL, 1H, 2021-01-01 ~ present (OKX)
- **Results**:
  - FNG 4 个特征全部进入 top 4（共 138 个特征中）：
    - #1 fng_ma_30 (importance=352)
    - #2 fng_zscore_30 (318)
    - #3 fng_ma_7 (313)
    - #4 fng_raw (272)
  - Top-20 稳定性：15/20 个原有特征保留，5 个被 FNG 挤出（vol_of_vol_168, atr_pctrank, dc_width_72, parkinson_168, obv_slope_14）
  - 加入 FNG 后第 5 名以后的排名基本稳定，说明 FNG 提供了独立信息而非替代已有特征
- **Conclusion**: FNG 特征信息量非常高，已加入默认特征组。但需注意：
  - **⚠️ 高 importance ≠ 高预测力**。FNG 是市场聚合指标，可能与 price action 高度相关。需要 OOS 验证是否真正提升 Sharpe
  - **⚠️ 数据频率不匹配**（日 vs 小时），同一天内所有小时用同一个 FNG 值，可能导致信息冗余
  - **Next**: 跑 walk-forward OOS backtest 验证 FNG 是否真正带来 alpha

## 2026-03-25 — DonchianMTF 4-Coin Portfolio OOS 重新验证（实盘前最终确认）

- **目的**: 用最新数据（到2026-03-24）重跑 OOS 验证，确认策略表现未衰退，作为实盘部署的前提
- **Method**: `run_backtest.py --portfolio --symbol-combos BTC:G,SOL:G,ADA:G,XRP:F --start 2024-01-01 --end 2026-03-24 --interval 4h --capital 10000 --leverage 3.0`
- **Results**:

| Symbol | Combo | Return | MaxDD | Sharpe | Trades | WinRate | PF |
|--------|-------|--------|-------|--------|--------|---------|-----|
| BTC | G (24/72/168) | +8.25% | 26.32% | 0.32 | 146 | 16.4% | 1.12 |
| SOL | G (24/72/168) | +5.02% | 16.33% | 0.21 | 130 | 20.0% | 1.09 |
| ADA | G (24/72/168) | +13.94% | 15.45% | 0.40 | 132 | 24.2% | 1.23 |
| XRP | F (48/168/504) | +43.24% | 15.37% | 1.10 | 60 | 15.0% | 2.24 |
| **Portfolio** | — | **+17.61%** | **10.85%** | **0.69** | 468 | — | — |

  与历史记录对比：
  - Portfolio Sharpe: 0.86（早期记录）→ **0.69**（本次），下降 0.17
  - XRP 表现强劲（+43.24%），贡献了组合 62% 的利润（$1081/$1761）
  - BTC MaxDD 26.32% 偏高，但组合 MaxDD 仅 10.85%（分散化有效）
  - 早期记录的 Sharpe 0.86 可能因 OOS 时间范围较短（数据只到更早时间点）

- **Conclusion**:
  - Portfolio Sharpe 0.69 > 0.6 阈值，**策略仍然有效，可以进入实盘**
  - ⚠️ BTC 单币种 Sharpe 仅 0.32，MaxDD 26.32%——如果资金有限，考虑降低 BTC 权重或移除
  - ⚠️ XRP 贡献过度集中——如果 XRP 的大趋势不重现，组合 alpha 可能大幅缩水
  - ⚠️ Sharpe 从 0.86 降至 0.69 说明策略在最近时期有边际衰退，需持续监控

---

## 2026-03-25 20:04 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +5.64% | Max DD: 31.66% | Sharpe: 0.23 | Sortino: 0.14 | Calmar: 0.08
- Trades: 246 | Win rate: 16.7% | Profit factor: 1.06
- Fees: $161.63 | Slippage: $692.68 | Time in market: 14.9%
- Initial: $2,500 | Final: $2,641.05

## 2026-03-25 20:06 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -29.17% | Max DD: 32.68% | Sharpe: -1.20 | Sortino: -0.58 | Calmar: -0.44
- Trades: 260 | Win rate: 16.9% | Profit factor: 0.55
- Fees: $57.19 | Slippage: $245.08 | Time in market: 13.6%
- Initial: $2,500 | Final: $1,770.68

## 2026-03-25 20:07 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +43.76% | Max DD: 24.80% | Sharpe: 0.73 | Sortino: 0.41 | Calmar: 0.71
- Trades: 228 | Win rate: 18.9% | Profit factor: 1.34
- Fees: $145.05 | Slippage: $619.64 | Time in market: 11.6%
- Initial: $2,500 | Final: $3,594.03

## 2026-03-25 20:09 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +80.68% | Max DD: 17.43% | Sharpe: 1.38 | Sortino: 0.45 | Calmar: 1.75
- Trades: 82 | Win rate: 24.4% | Profit factor: 2.57
- Fees: $61.73 | Slippage: $264.57 | Time in market: 4.0%
- Initial: $2,500 | Final: $4,517.01

## 2026-03-26 — DonchianMTF 1H vs 4H OOS 对比实验

- **Hypothesis**: 4H timeframe 一直被假设为"best signal-to-noise"，但从未被严格验证。1H 数据量更大，可能捕捉更多突破。
- **Method**:
  - 公平对比：1H lookback x4 保持相同时间窗口（4H G=[24,72,168] vs 1H G=[96,288,672]）
  - 4 coins: BTC, SOL, ADA, XRP, OOS 2024-2026, 3x leverage, $2500/coin

| Symbol | 4H Return | 4H Sharpe | 4H MaxDD | 1H Return | 1H Sharpe | 1H MaxDD | Winner |
|--------|-----------|-----------|----------|-----------|-----------|----------|--------|
| BTC | +8.25% | 0.32 | 26.32% | +5.64% | 0.23 | 31.66% | **4H** |
| SOL | +5.02% | 0.21 | 16.33% | -29.17% | -1.20 | 32.68% | **4H** |
| ADA | +13.94% | 0.40 | 15.45% | +43.76% | 0.73 | 24.80% | **1H** |
| XRP | +43.24% | 1.10 | 15.37% | +80.68% | 1.38 | 17.43% | **1H** |

  Execution cost: 1H avg fees+slippage $530 vs 4H $167 (3x higher)
  Trade count: 1H avg 204 vs 4H avg 117 (1.7x more)

- **Conclusion**:
  - 4H 更稳健--所有 4 个币种均正收益，SOL 在 1H 上崩溃（-29%）
  - 1H 收益天花板更高--ADA/XRP 在 1H 上显著跑赢（但费用也更高）
  - SOL 在 1H 上被高波动反复止损，不适合高频 Donchian
  - **Decision**: 维持 4H 实盘配置。未来可考虑混合方案（BTC/SOL 4H, ADA/XRP 1H）

---

## 2026-03-26 07:46 UTC — Backtest: DonchianMTF on BTC

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +5.64% | Max DD: 31.66% | Sharpe: 0.23 | Sortino: 0.14 | Calmar: 0.08
- Trades: 246 | Win rate: 16.7% | Profit factor: 1.06
- Fees: $161.63 | Slippage: $692.68 | Time in market: 14.9%
- Initial: $2,500 | Final: $2,641.05

## 2026-03-26 07:47 UTC — Backtest: DonchianMTF on SOL

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: -29.17% | Max DD: 32.68% | Sharpe: -1.20 | Sortino: -0.58 | Calmar: -0.44
- Trades: 260 | Win rate: 16.9% | Profit factor: 0.55
- Fees: $57.19 | Slippage: $245.08 | Time in market: 13.6%
- Initial: $2,500 | Final: $1,770.68

## 2026-03-26 07:49 UTC — Backtest: DonchianMTF on ADA

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +43.76% | Max DD: 24.80% | Sharpe: 0.73 | Sortino: 0.41 | Calmar: 0.71
- Trades: 228 | Win rate: 18.9% | Profit factor: 1.34
- Fees: $145.05 | Slippage: $619.64 | Time in market: 11.6%
- Initial: $2,500 | Final: $3,594.03

## 2026-03-26 07:51 UTC — Backtest: DonchianMTF on XRP

- Period: 2024-01-01 to 2026-03-23
- Config: donchian_period=20, atr_period=14, atr_sl_mult=2.0, risk_per_trade=0.02, leverage=3.0
- Return: +80.68% | Max DD: 17.43% | Sharpe: 1.38 | Sortino: 0.45 | Calmar: 1.75
- Trades: 82 | Win rate: 24.4% | Profit factor: 2.57
- Fees: $61.73 | Slippage: $264.57 | Time in market: 4.0%
- Initial: $2,500 | Final: $4,517.01

## 2026-03-27 — Hurst 加权组合实验

- **Hypothesis**: Rolling Hurst 指数可以动态调整币种权重，给予趋势性更强的币种更高权重，从而提升 Donchian 组合的风险调整收益
- **Method**: 8H, 12d/20d/112d, med-heavy 参数。3 种组合方案在 3 个 Walk-Forward 窗口 + Holdout 上对比：
  - A: 等权全部 24 币种
  - B: 等权仅 Hurst>0.58 的币种
  - C: Rolling 180 天 Hurst 加权 (weight = max(0, hurst - 0.50), 月度重平衡)

| Window | A: 等权全部 | B: Hurst 筛选 | C: Hurst 加权 | Winner |
|--------|-----------|-------------|-------------|--------|
| W1 (2022.07-2023.07) | -0.473 | **-0.386** | -0.435 | B |
| W2 (2023.07-2024.07) | -0.149 | **-0.148** | -0.207 | B |
| W3 (2024.07-2025.07) | 0.172 | **0.273** | 0.216 | B |
| **HOLDOUT** (2025.07-2026.03) | **0.042** | -0.795 | -0.176 | **A** |

| 方案 | Val Avg Sharpe | Val Avg Return | Holdout Sharpe |
|------|---------------|---------------|----------------|
| A: 等权 | -0.150 | +5.49% | **+0.042** |
| B: Hurst 筛选 | **-0.087** | +7.68% | -0.795 |
| C: Hurst 加权 | -0.142 | +7.31% | -0.176 |

- **Key findings**:
  1. **B (Hurst 筛选) 在 Validation 上最好** — 三个窗口都是最优，avg Sharpe -0.087
  2. **但 B 在 Holdout 上崩溃** (-0.795) — Holdout 期间只有 2 个币种过了 Hurst>0.58 (BCH, MANA)，样本太小无法分散风险
  3. **A (等权) 在 Holdout 上最好** (+0.042) — 分散化的力量：即使单个币种亏损，24 个币种等权组合仍然微赚
  4. **C (Hurst 加权) 表现中间** — 没有明显优于 A 或 B
  5. **Rolling Hurst 极不稳定**：同一币种的 Hurst 在不同窗口变化巨大（如 ADA: W1=0.65, W3=0.55, Holdout=0.53），说明 Hurst 不是稳定的币种属性

- **Conclusion**:
  - **Rolling Hurst 加权方案不可靠** — Hurst 本身随时间变化太大，不适合作为动态权重
  - **等权全部币种仍然是最稳健的方案** — Holdout 证明了分散化胜过精选
  - 之前发现的 Hurst vs Sharpe 的相关性 (rho=0.53) 是用全历史数据计算的静态 Hurst，不代表 rolling Hurst 有预测能力
  - **Decision**: 放弃 Hurst 加权方案，维持等权全币种组合

---

## 2026-03-27 — DonchianMTF 全面参数 Sweep + 币种特征分析

### Part 1: 频率 x Lookback 联合 Sweep

- **Method**: 5 freq (1H/2H/4H/8H/1D) x ~100 lookback combos x 2 weights = 1070 params, 24 coins, 3 walk-forward windows
- **Walk-Forward**: W1(IS 2021-2022.06, Val 2022.07-2023.06), W2(IS 2021-2023.06, Val 2023.07-2024.06), W3(IS 2021-2024.06, Val 2024.07-2025.06)
- **Fee model**: taker 5bps + slippage 3bps

**Results**:
- W1 IS: 15/1070 (1.4%) survived; W2 IS: 3/1070 (0.3%); W3 IS: 3/1070 (0.3%)
- **0 个参数在所有 3 个 Validation 窗口上 Sharpe 同时为正**
- "最不差"的参数: **8H, 12d/20d/112d, med-heavy** (Val Sharpe: W1=-0.01, W2=-0.24, W3=+0.18, avg=-0.03)
- Per-coin: 13/24 正 Sharpe, 11/24 负 Sharpe (正组最高 XRP=1.33, 负组最差 ETC=-1.37)

**Conclusion**: Donchian MTF 等权全币种组合在任何频率/lookback 下都不盈利。策略有效性取决于币种选择。

### Part 2: 正/负 Sharpe 币种特征分析

- **Hypothesis**: 正/负 Sharpe 两组币种存在可观测的市场微结构差异,可作为客观筛选标准
- **Method**: 对 24 个币种计算 5 个指标, 比较两组均值 (Mann-Whitney U 检验)

| 指标 | 正组均值 | 负组均值 | Diff | p-value | 显著性 |
|------|---------|---------|------|---------|--------|
| Daily Volatility | 0.0581 | 0.0562 | +0.002 | 0.643 | - |
| Avg Daily Vol (USD) | 44.2B | 250.9M | +44B | 0.643 | - |
| **Autocorr (lag-1)** | -0.019 | -0.034 | +0.015 | 0.487 | - |
| **Hurst Exponent** | **0.597** | **0.577** | **+0.020** | **0.021** | ***** |
| Avg Trend Days | 1.915 | 1.912 | +0.003 | 1.000 | - |

**Spearman correlation with Validation Sharpe:**

| 指标 | rho | p-value | 显著性 |
|------|-----|---------|--------|
| Daily Volatility | -0.08 | 0.701 | - |
| Avg Daily Vol | -0.21 | 0.320 | - |
| Autocorr (lag-1) | +0.08 | 0.710 | - |
| **Hurst Exponent** | **+0.526** | **0.008** | **\*\*\*** |
| Avg Trend Days | -0.03 | 0.901 | - |

**Key finding: Hurst 指数是唯一显著区分两组的指标 (p=0.021), 且与 Validation Sharpe 高度正相关 (rho=0.53, p=0.008)。**

Hurst > 0.5 表示时间序列有趋势持续性 (persistence), 这正是 Donchian 趋势跟踪策略盈利的前提条件。
- 正组平均 Hurst = 0.597 (更强趋势性)
- 负组平均 Hurst = 0.577 (趋势性弱, 更接近随机游走)

**Per-coin Hurst vs Sharpe**:
- XRP: Hurst=0.604, Sharpe=1.33 (强趋势, 高收益)
- ADA: 0.608, 0.92; DOGE: 0.611, 0.77; SOL: 0.609, 0.41
- BCH: 0.544, -0.12; UNI: 0.563, -0.91; LTC: 0.558, -0.35 (弱趋势, 亏损)
- 例外: NEAR Hurst=0.608 但 Sharpe=-0.77; AVAX 0.602 但 -0.11 (Hurst 不是唯一因素)

**Decision**: Hurst 指数可作为**辅助**筛选标准, 但不足以单独决定:
- 建议阈值: Hurst > 0.58 优先纳入 (排除 BCH/ATOM/LTC/TRX/AAVE/UNI)
- 仍需结合 Validation 回测确认
- 定期重算 Hurst (市场结构会变化)

---

## 2026-04-01 — 跨资产 Donchian Breakout 实验

- **Hypothesis**: 传统资产（股指、大宗商品、外汇、债券、个股）的 Donchian 趋势跟踪可以提供与 crypto 低相关的收益来源，通过跨资产分散化显著改善组合 Sharpe
- **Method**:
  - Yahoo Finance 日线数据, 2015-2025, 30 个品种（4 股指 + 8 大宗 + 9 外汇 + 2 债券 + 7 个股）
  - 230 个参数组合（lookback: 短12-48 × 中48-168 × 长168-672, 权重: equal + med-heavy）
  - 5 个 Walk-Forward 窗口 + Holdout (2023-2025)
  - 费用: 0.08% + 0.03% 滑点

**Results**:

| 品种 | 类型 | 最优参数 | Avg Val Sharpe | Pos Windows |
|------|------|---------|---------------|-------------|
| HG=F (铜) | 大宗 | 36/48/168 equal | **+0.268** | 2/5 |
| BZ=F (布伦特) | 大宗 | 12/48/168 equal | -0.643 | 0/5 |
| SI=F (白银) | 大宗 | 36/120/168 med | -0.871 | 1/5 |
| AMZN | 个股 | 12/48/168 med | -1.198 | 0/5 |
| **其余 26/30 品种** | 全部 | — | **NO PARAM** | 0/5 |

**26 个品种连一个 IS 阶段正 Sharpe 的参数都没有。** 包括所有股指（SPY/QQQ/IWM/DIA）、黄金、原油、天然气、所有外汇对、所有债券、6/7 个股。

Holdout: 唯一通过的 HG=F(铜) 在 Holdout 上 Sharpe=-0.97, Return=-19.92%

- **Conclusion**:
  - **Donchian 趋势突破策略对传统资产基本无效。** 30 个品种中只有 4 个能找到 IS Sharpe 正的参数，且 Validation 上全部为负或接近零。
  - **原因分析**:
    - 传统资产波动率远低于 crypto（SPY 年化 ~15% vs BTC ~60%），趋势信号弱
    - 外汇波动率更低（~7-10%），均值回归主导，Donchian 完全不适用
    - 股票是长期上涨趋势，Donchian 的做空信号反复被打止损
    - 大宗商品中只有高波动品种（铜）有微弱的正信号，但不稳定
  - **跨资产分散化假设被否定** — 不是因为相关性问题（传统资产确实和 crypto 低相关），而是因为 Donchian 策略本身在传统资产上不赚钱，加入亏损资产不可能改善组合
  - **Decision**: 不在传统资产上使用 Donchian 趋势策略。如果要做跨资产分散化，需要为传统资产设计不同的策略（如均值回归用于外汇、动量策略用于股指）

---

## 2026-04-02 — 实盘升级：B0 (Donchian + Regime Filter) 部署

- **变更**: 实盘策略从原始 DonchianMTF 升级为 B0（加入 ADX + 波动率收缩 regime filter）
- **Regime Filter 参数**:
  - ADX 窗口: 20 根 8H bar
  - ADX >= 25 → 正常交易 (regime_scale=1.0)
  - ADX 20-25 → 仓位减半 (regime_scale=0.5)
  - ADX < 20 → 不开新仓 (regime_scale=0.0)
  - 波动率收缩: vol_10d < vol_30d × 0.7 → 不开新仓 (OR 关系)
- **只影响开仓**: 已有仓位的止损和平仓逻辑不受影响
- **代码一致性**: regime filter 直接写在 `DonchianMTF.generate_signal()` 中，回测和实盘共用同一份代码
- **部署验证**: dry-run 确认 ADX 和 regime_scale 正确输出：BTC(ADX=18.3,choppy), SOL(ADX=28.3,trending), ADA(ADX=16.4,choppy), XRP(ADX=18.9,choppy)
- **回测依据**: B0 Holdout Sharpe=+0.344，优于原始 A0 的 -0.001

---

## 2026-04-02 — 机构先验知识方法：无参数优化实验

- **Hypothesis**: 用先验知识（多 lookback 信号混合 + 目标波动率仓位管理）替代参数优化，应该比 per-coin 优化更 robust
- **Method**: 所有参数来自理论/先验，不做回测优化。24 crypto (8H) + 30 传统 (1D)

### 汇总表

| 版本 | 资产 | 描述 | W1 | W2 | W3 | **Avg Val** | **Holdout** | MaxDD |
|------|------|------|-----|-----|-----|-----------|---------|-------|
| B0 | Crypto | Donchian+Regime (=A1) | -0.086 | +0.011 | -0.115 | -0.063 | **+0.344** | 13.7% |
| B1 | Crypto | +多LB信号混合 | -0.109 | 0.000 | -0.092 | -0.067 | **+0.354** | 13.3% |
| B2 | Crypto | +目标波动率仓位 | +0.043 | +0.109 | -0.914 | -0.254 | **+0.477** | 0.3% |
| B3 | Crypto | B1+B2 全部 | +0.043 | +0.109 | -0.914 | -0.254 | **+0.477** | 0.3% |
| C1 | Crypto | 多LB TSMOM | -0.159 | -1.483 | -0.904 | -0.849 | 0.000 | — |
| C2 | Crypto | C1+目标波动率 | +0.052 | -0.985 | -0.719 | -0.551 | 0.000 | — |
| C1 | 传统 | 多LB TSMOM | — | — | — | — | -0.546 | 67.8% |
| C2 | 传统 | C1+目标波动率 | — | — | — | — | -0.214 | 4.8% |

### 核心发现

**1. 多 Lookback 信号混合 (B1) 没有改善**
- B0 avg=-0.063 vs B1 avg=-0.067，Holdout B0=0.344 vs B1=0.354
- 差异极小。多 lookback 混合既没帮忙也没添乱，因为原始策略已经用了三组 lookback 的加权

**2. 目标波动率仓位管理 (B2) 效果矛盾**
- Holdout Sharpe 最高 (+0.477)，MaxDD 极低 (0.3%)
- **但仓位太小了**：Return 接近零 (+0.07%)。仓位被缩到几乎不交易
- W3 Sharpe=-0.914 暴跌，可能因为高波动期仓位太小错过了所有大趋势
- B2=B3 完全相同，说明信号混合模块在目标波动率仓位下没有区别

**3. 统一参数 TSMOM (C1/C2) 在 crypto 上全军覆没**
- C1 crypto avg=-0.849，远差于 per-coin 优化版的 +0.100
- 说明统一参数确实减少了过拟合，但也把所有 alpha 一起消灭了
- C2 加了目标波动率后略好（avg=-0.551）但仍然是负的

**4. 统一参数 TSMOM 在传统资产上也是负的**
- C1 传统 Holdout=-0.546，MaxDD=67.8%（灾难性）
- C2 传统 Holdout=-0.214，MaxDD=4.8%（目标波动率控制了风险但仍是负的）

### 结论

- **Donchian + Regime Filter (B0) 仍然是最佳选择**: 简单、robust、Holdout +0.344
- **目标波动率仓位管理**: 理念正确但 30% 目标对 crypto 太保守，仓位缩到几乎为零。如果用可能需要更高目标（60-80%）
- **统一参数 TSMOM 不可行**: 消除了过拟合但也消除了 alpha。不同资产确实需要不同 lookback
- **跨资产混合组合**: 当两个组件（crypto TSMOM + 传统 TSMOM）都是负 Sharpe 时，混合也是负的。分散化不能把负期望变正

---

## 2026-04-02 — Donchian 优化 + TSMOM Baseline 对比实验

### 实验一：Donchian Breakout + 优化模块 A/B Test

Base: 8H, 12d/20d/112d, med-heavy, 24 crypto coins, 3 walk-forward windows

| Version | 描述 | W1 Val | W2 Val | W3 Val | **Avg Val** | **Holdout** |
|---------|------|--------|--------|--------|-----------|---------|
| A0 | Base Donchian | -0.507 | -0.159 | +0.153 | -0.171 | -0.001 |
| **A1** | **+Regime Filter (ADX)** | -0.349 | +0.078 | -0.011 | **-0.094** | **+0.417** |
| A2 | +Dynamic Lookback | -0.458 | -0.066 | -0.029 | -0.184 | +0.375 |
| A3 | +Vol-Adaptive Sizing | -0.089 | -0.106 | -0.126 | -0.107 | +0.196 |

增量贡献:
- A0->A1 (Regime Filter): **+0.077** -- 有效。ADX 过滤掉 choppy 市场减少假突破
- A1->A2 (Dynamic Lookback): **-0.090** -- **无效**。动态调整 lookback 反而增加噪音
- A2->A3 (Vol-Adaptive Sizing): **+0.077** -- 有效但 MaxDD 从 22% 降到 0.87%（仓位太小了）

**结论**: Regime Filter 是唯一稳健的优化。但所有版本的 Avg Val Sharpe 仍然是负的。

### 实验二：TSMOM (时间序列动量) Baseline

24 crypto coins, 日线, lookbacks: 5-252天, binary + continuous 信号

**Top 10 Crypto TSMOM (按 Avg Val Sharpe):**

| Coin | Lookback | Signal | Avg Val Sharpe | Pos/3 | Holdout Sharpe |
|------|----------|--------|---------------|-------|----------------|
| AVAX | 10d | binary | **+0.712** | 3/3 | -0.387 |
| DOGE | 126d | binary | +0.557 | 3/3 | **+0.709** |
| NEAR | 10d | cont | +0.358 | 2/3 | -0.996 |
| SAND | 42d | binary | +0.357 | 3/3 | -0.356 |
| ADA | 84d | binary | +0.315 | 2/3 | **+1.433** |
| XRP | 5d | binary | +0.242 | 2/3 | +0.321 |
| ALGO | 21d | binary | +0.213 | 2/3 | -1.099 |
| MANA | 15d | binary | +0.211 | 3/3 | -1.196 |
| ETH | 10d | binary | +0.207 | 2/3 | -0.971 |
| DOT | 15d | binary | +0.190 | 2/3 | -1.725 |

**17/24 coins Avg Val Sharpe 为正**（vs Donchian 的 13/24）

**Holdout**: 20 coins 平均 Sharpe = **-0.737**（很差）。只有 ADA(+1.43), DOGE(+0.71), XRP(+0.32), TRX(+0.22) 在 Holdout 上正的。大部分在 Holdout 崩溃，说明 TSMOM 参数选择也存在过拟合。

### 汇总对比表

| 策略 | 资产 | Avg Val Sharpe | Holdout Sharpe |
|------|------|---------------|----------------|
| Donchian A0 (Base) | Crypto | -0.171 | -0.001 |
| Donchian A1 (+Regime) | Crypto | **-0.094** | **+0.417** |
| Donchian A2 (+DynLB) | Crypto | -0.184 | +0.375 |
| Donchian A3 (+VolSize) | Crypto | -0.107 | +0.196 |
| TSMOM (per-coin best) | Crypto | +0.100* | **-0.737** |
| Donchian A0 | 传统资产 | N/A (全负) | N/A |
| TSMOM | 传统资产 | (yfinance未加载) | N/A |

*TSMOM 的 +0.100 是所有 24 coins 的平均值，但每个 coin 用的是各自最优参数

### 核心发现

1. **TSMOM 在 Validation 上优于 Donchian**（+0.100 vs -0.171），但在 **Holdout 上远差于 Donchian**（-0.737 vs -0.001）。说明 TSMOM 的 per-coin 参数优化严重过拟合。

2. **Donchian + Regime Filter (A1) 在 Holdout 上最好**（+0.417）。这是因为 A1 用的是固定参数（不做 per-coin 优化），regime filter 减少了假突破，对新数据的泛化性最好。

3. **传统资产 TSMOM 数据未能加载**（yfinance 在此环境下返回空数据），需要单独重跑。

4. **优化模块中 Dynamic Lookback 无效** -- 根据波动率动态调整 lookback 增加了不必要的复杂性。

5. **关键教训**: 策略的 robustness 比 Sharpe 最大化更重要。简单策略（固定参数 Donchian + regime filter）在 Holdout 上击败了看似更好的 TSMOM。

### 补充：TSMOM 传统资产结果（重跑完成）

**传统资产 TSMOM Top 10 (按 Avg Val Sharpe):**

| Ticker | 类型 | Lookback | Signal | Avg Val Sharpe | Pos/5 | Holdout Sharpe |
|--------|------|----------|--------|---------------|-------|----------------|
| MSFT | 个股 | 168d | binary | **+0.999** | 4/5 | +0.417 |
| AUDUSD=X | 外汇 | 126d | binary | +0.789 | 3/5 | -0.414 |
| NVDA | 个股 | 84d | cont | +0.726 | 4/5 | **+1.167** |
| TSLA | 个股 | 126d | cont | +0.628 | 2/5 | -0.595 |
| QQQ | 股指 | 168d | cont | +0.552 | 4/5 | **+0.796** |
| SPY | 股指 | 168d | cont | +0.539 | 2/5 | **+0.873** |
| AAPL | 个股 | 21d | binary | +0.447 | 4/5 | -0.038 |
| IEF | 债券 | 168d | binary | +0.417 | 2/5 | -0.787 |
| CL=F | 大宗 | 15d | binary | +0.414 | 4/5 | -1.373 |
| AMZN | 个股 | 63d | binary | +0.252 | 3/5 | -0.170 |

**26/30 传统品种找到了参数**（vs Donchian 的 4/30）。TSMOM 在传统资产上远优于 Donchian。

**Holdout 传统资产 TSMOM**: 24 assets 平均 Sharpe = **-0.205**
- 8 个品种 Holdout 正: NVDA(+1.17), GC=F(+0.98), SPY(+0.87), META(+0.86), QQQ(+0.80), DIA(+0.65), USDJPY(+0.42), MSFT(+0.42)
- 外汇和大宗在 Holdout 崩溃

**关键发现：跨资产相关性矩阵（Holdout 期间）**:

| | 值 |
|---|---|
| Crypto-Crypto 平均相关性 | **+0.599** (高) |
| 传统-传统 平均相关性 | **+0.168** (低) |
| **Crypto-传统 平均相关性** | **+0.120** (很低) |

**这证明了跨资产分散化的核心论点**：crypto 内部高度相关（0.60），传统资产内部低相关（0.17），crypto 与传统资产之间几乎不相关（0.12）。

### 更新后的汇总对比表

| 策略 | 资产 | Avg Val Sharpe | Holdout Sharpe |
|------|------|---------------|----------------|
| Donchian A0 | Crypto | -0.171 | -0.001 |
| **Donchian A1 (+Regime)** | **Crypto** | **-0.094** | **+0.417** |
| TSMOM (per-coin) | Crypto | +0.100 | -0.737 |
| Donchian A0 | 传统 | 全负/无参数 | N/A |
| **TSMOM** | **传统** | **+0.177*** | **-0.205** |

*传统资产 TSMOM 的 +0.177 是 26 个品种的平均值

### 最终建议

1. **Crypto 实盘**: 维持 Donchian + Regime Filter，TSMOM 过拟合严重
2. **传统资产**: TSMOM 比 Donchian 有效得多（26/30 品种有参数 vs 4/30），但 Holdout 也是负的
3. **跨资产分散化有真实价值**: crypto-传统相关性仅 0.12，理论上混合组合能显著降低波动率
4. **但前提是找到正期望的策略**: 目前无论 Donchian 还是 TSMOM，Holdout 平均都是负的。分散化只能降风险，不能把负期望变正
5. **股指和科技龙头 TSMOM 最 robust**: SPY/QQQ/MSFT/NVDA 在 Validation 和 Holdout 上都正，这些品种的长期动量效应最可靠
6. **外汇和大宗 TSMOM 不稳定**: Validation 正但 Holdout 崩溃，说明这些品种的动量效应是间歇性的

---

## Mean Reversion Experiment (2026-04-04)

### Dynamic Slippage Model Impact on B0
- Fixed slippage (15bps): avg Holdout Sharpe = 0.239
- Dynamic slippage (auto): avg Holdout Sharpe = 0.304
- Delta: +0.065

### Mean Reversion Best Parameters (per coin)
| Coin | Lookback | Entry Z | Exit Z | Stop Z | Avg Val Sharpe |
|------|----------|---------|--------|--------|----------------|
| BTC | 96 | 3.0 | 0.00 | 4.0 | 1.619 |
| ETH | 336 | 2.5 | 0.50 | 3.0 | 0.534 |
| LTC | 168 | 2.0 | 0.00 | 4.0 | 0.723 |
| TRX | 24 | 3.0 | 0.00 | 4.0 | 0.385 |
| BCH | 252 | 2.5 | 0.00 | 3.0 | 0.591 |
| DOT | 252 | 2.0 | 0.00 | 4.0 | 1.065 |
| ADA | 336 | 2.0 | 0.50 | 3.0 | 1.710 |
| LINK | 168 | 1.5 | 0.00 | 3.5 | 0.658 |
| XLM | 336 | 2.0 | 0.25 | 4.0 | 1.125 |
| XRP | 336 | 1.5 | 0.50 | 3.5 | 1.071 |
| ETC | 336 | 2.0 | 0.50 | 3.0 | 1.249 |
| ALGO | 12 | 2.5 | 0.00 | 3.0 | 0.610 |
| ATOM | 336 | 2.0 | 0.00 | 4.0 | 1.141 |
| AAVE | 96 | 3.0 | 0.00 | 3.5 | 1.013 |
| SOL | 96 | 3.0 | 0.00 | 4.0 | 0.794 |
| ICP | 168 | 3.0 | 0.00 | 3.5 | 1.221 |
| UNI | 336 | 2.0 | 0.25 | 3.5 | 0.772 |
| FIL | 336 | 1.5 | 0.00 | 4.0 | 0.279 |
| AVAX | 72 | 3.0 | 0.00 | 4.0 | 0.689 |
| NEAR | 96 | 3.0 | 0.50 | 4.0 | 0.724 |
| CRV | 252 | 3.0 | 0.25 | 4.0 | 0.460 |
| DOGE | 336 | 1.5 | 0.00 | 3.5 | 0.407 |

### Holdout Results
| Coin | Donchian SR | MeanRev SR | Don Ret% | MR Ret% | Correlation |
|------|-------------|------------|----------|---------|-------------|
| BTC | 1.561 | 2.397 | 13.06 | 7.49 | nan |
| ETH | 0.934 | 0.394 | 7.00 | 1.15 | -0.04 |
| LTC | 1.168 | -0.731 | 6.04 | -2.06 | 0.00 |
| TRX | -0.721 | -0.066 | -2.44 | -3.54 | -0.04 |
| BCH | -1.577 | 1.175 | -5.49 | 11.42 | -0.10 |
| DOT | 0.541 | 0.000 | 3.72 | 0.00 | nan |
| ADA | 0.540 | 0.000 | 3.52 | 0.00 | nan |
| LINK | -0.222 | -1.481 | -1.66 | -3.30 | 0.12 |
| XLM | 1.121 | -1.926 | 8.32 | -3.15 | -0.06 |
| XRP | 0.454 | -1.155 | 3.48 | -2.12 | -0.14 |
| ETC | 1.165 | -2.011 | 6.29 | -5.41 | -0.13 |
| ALGO | -2.349 | 0.983 | -7.92 | 26.33 | 0.00 |
| ATOM | -1.086 | 0.000 | -2.67 | 0.00 | nan |
| AAVE | 1.440 | 0.963 | 13.72 | 17.27 | -0.01 |
| SOL | 0.083 | 0.000 | -0.16 | 0.00 | nan |
| ICP | 0.399 | 0.793 | 2.71 | 2.25 | -0.00 |
| UNI | 1.425 | 0.000 | 33.07 | 0.00 | nan |
| FIL | -1.721 | -1.548 | -5.13 | -1.43 | 0.03 |
| AVAX | 1.185 | -1.103 | 6.41 | -9.32 | 0.01 |
| NEAR | 1.432 | 0.000 | 10.53 | 0.00 | nan |
| CRV | 0.349 | 0.000 | 1.91 | 0.00 | nan |
| DOGE | 0.567 | -2.437 | 3.05 | -2.02 | -0.08 |

### Portfolio Comparison (Holdout)
| Portfolio | Sharpe | MaxDD% | Return% |
|-----------|--------|--------|---------|
| A) Donchian B0 only | 1.006 | 4.11 | 4.77 |
| B) MeanRev only | 1.219 | 1.15 | 1.40 |
| C) 50/50 Equal Weight | 1.232 | 1.93 | 3.08 |

Average Donchian-MeanRev daily return correlation: -0.031

## Regime Dynamic Switching Experiment (2026-04-04)

### Portfolio Comparison (Holdout 2025.07-2026.03)
| Portfolio | Sharpe | MaxDD% | Return% | Trades |
|-----------|--------|--------|---------|--------|
| A) Donchian B0 only | 1.006 | 4.11 | 4.77 | 418 |
| B) MeanRev only | 1.219 | 1.15 | 1.40 | 60 |
| C) 50/50 Equal Weight | 1.232 | 1.93 | 3.08 | 478 |
| D) Regime Switch | 0.177 | 21.07 | -0.04 | 2050 |

### Key Finding
- Regime Switch Sharpe: 0.177 vs Donchian: 1.006 vs 50/50: 1.232
- Best approach: C) 50/50 Equal Weight (Sharpe 1.232)

## Regime Switching with Hysteresis (2026-04-04)

### Hysteresis Parameters
- Trending -> Ranging: ADX must drop below 18 (was 20)
- Ranging -> Trending: ADX must rise above 27 (was 25)
- No gray zone (binary: trending or ranging)
- Minimum 10 bars (80h) hold before re-switching
- On switch: existing positions held until natural exit

### Portfolio Comparison (Holdout 2025.07-2026.03)
| Portfolio | Sharpe | MaxDD% | Return% | Trades |
|-----------|--------|--------|---------|--------|
| A) Donchian B0 only | 1.006 | 4.11 | 4.77 | 418 |
| B) MeanRev only | 1.219 | 1.15 | 1.40 | 60 |
| C) 50/50 Equal Weight | 1.232 | 1.93 | 3.08 | 478 |
| D) Regime Switch | 0.177 | 21.07 | -0.04 | 2050 |
| D-fix) Hysteresis | -0.340 | 20.58 | -7.04 | 2982 |

### Key Finding
- Best approach: C) 50/50 Equal Weight (Sharpe 1.232)
- Hysteresis reduced trades: 2050 -> 2982
- Hysteresis Sharpe: -0.340 vs original: 0.177

## Regime Switching with Hysteresis (2026-04-04)

### Hysteresis Parameters
- Trending -> Ranging: ADX must drop below 18 (was 20)
- Ranging -> Trending: ADX must rise above 27 (was 25)
- No gray zone (binary: trending or ranging)
- Minimum 10 bars (80h) hold before re-switching
- On switch: existing positions held until natural exit

### Portfolio Comparison (Holdout 2025.07-2026.03)
| Portfolio | Sharpe | MaxDD% | Return% | Trades |
|-----------|--------|--------|---------|--------|
| A) Donchian B0 only | 1.006 | 4.11 | 4.77 | 418 |
| B) MeanRev only | 1.219 | 1.15 | 1.40 | 60 |
| C) 50/50 Equal Weight | 1.232 | 1.93 | 3.08 | 478 |
| D) Regime Switch | 0.177 | 21.07 | -0.04 | 2050 |
| D-fix) Hysteresis | 0.415 | 10.96 | 2.60 | 101 |

### Key Finding
- Best approach: C) 50/50 Equal Weight (Sharpe 1.232)
- Hysteresis reduced trades: 2050 -> 101
- Hysteresis Sharpe: 0.415 vs original: 0.177

## HMM Regime Detection Experiment (2026-04-04)

### Portfolio Comparison (Holdout 2025.07-2026.03)
| Portfolio | Sharpe | MaxDD% | Return% | Trades |
|-----------|--------|--------|---------|--------|
| A) Donchian B0 | 1.006 | 4.11 | 4.77 | 418 |
| B) MeanRev | 1.381 | 1.49 | 1.95 | 61 |
| C) 50/50 Equal | 1.327 | 1.91 | 3.36 | 479 |
| D-fix) ADX hyst | 0.479 | 10.85 | 3.22 | 100 |
| E) HMM | -0.810 | 11.45 | -5.90 | 112 |
| F) HMM+hyst | -0.960 | 12.98 | -7.26 | 113 |
| G) ADX+HMM vote | -0.944 | 8.94 | -4.71 | 135 |

Best: B) MeanRev (Sharpe 1.381)

## Mean Reversion Frequency Sweep (2026-04-04)

### Unified params (all coins same), stop_z = entry_z + 1.0

| Freq | Lookback | Entry Z | Exit Z | Avg Val Sharpe | Holdout Sharpe | Trades |
|------|----------|---------|--------|----------------|----------------|--------|
| 1h | 336 | 3.0 | 0.50 | -0.047 | -0.022 | 153 |
| 2h | 72 | 3.0 | 0.25 | -0.103 | -0.338 | 633 |
| 4h | 672 | 2.0 | 0.25 | 0.035 | -0.781 | 52 |
| 8h | 504 | 2.0 | 0.00 | 0.596 | 0.090 | 3 |

Best frequency: 8h (Holdout Sharpe 0.090)

## Portfolio Optimization (2026-04-04)

### Direction 1: Leverage (50/50 Equal Weight)
| Leverage | Sharpe | Return% | MaxDD% | Max Day Loss% | Trades |
|----------|--------|---------|--------|---------------|--------|
| 3x | 0.231 | 0.69 | 5.39 | -2.07 | 116 |
| 5x | 0.213 | 0.75 | 8.44 | -2.83 | 116 |
| 7x | 0.190 | 0.61 | 11.13 | -3.29 | 116 |
| 10x | 0.154 | 0.17 | 14.66 | -3.69 | 116 |

Best leverage (MaxDD<=10%): **3x**

### Direction 2: Dynamic Allocation (3x leverage)
| Method | Sharpe | Return% | MaxDD% | Trades |
|--------|--------|---------|--------|--------|
| 50/50 Fixed | 0.231 | 0.69 | 5.39 | 116 |
| MR Priority | 0.148 | 0.33 | 10.32 | 90 |
| Signal Weighted | 0.148 | 0.33 | 10.32 | 90 |
| 70/30 Don/MR | 0.207 | 0.69 | 7.46 | 114 |

Best allocation: **50/50 Fixed**

### Direction 3: MR Entry Threshold
| Threshold | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| Original Z | 0.231 | 0.69 | 5.39 | 116 |
| Z - 0.5 | 0.042 | -0.06 | 4.93 | 183 |
| Z - 1.0 | -0.394 | -1.66 | 6.01 | 268 |

Best threshold: **Original Z**

### Combined Optimal
| Method | Sharpe | Return% | MaxDD% | Trades |
|--------|--------|---------|--------|--------|
| 50/50 Fixed | 0.231 | 0.69 | 5.39 | 116 |
| 50/50 3x | 0.231 | 0.69 | 5.39 | 116 |
| 50/50 Fixed | 0.231 | 0.69 | 5.39 | 116 |
| Original Z | 0.231 | 0.69 | 5.39 | 116 |
| 3x + 50/50 Fixed + Original Z | 0.231 | 0.69 | 5.39 | 116 |
| 5x + 50/50 Fixed + Original Z | 0.213 | 0.75 | 8.44 | 116 |
| 3x + 70/30 + Original Z | 0.207 | 0.69 | 7.46 | 114 |

**Best overall: 50/50 3x** (Sharpe 0.231, Return 0.69%, MaxDD 5.39%)

## Combo Experiments (2026-04-04)

### Experiment 1: Dual-Lookback MR
- Short MR: lookback=72, entry_z=2.0, exit_z=0.5, stop_z=3.0
- Long MR: lookback=336, entry_z=2.5, exit_z=0.0, stop_z=3.5
- Each gets 25% of capital (total MR = 50%)

### Experiment 2: Exit Z Sweep

### Experiment 3: Expanded Coins
- Extra coins tested: ['APT', 'ARB', 'AXS', 'BNB', 'HBAR', 'MANA', 'OP', 'PEPE', 'SAND', 'SUI']
- Extra coins with MR params: ['APT', 'ARB', 'AXS', 'BNB', 'HBAR', 'MANA', 'OP', 'PEPE', 'SAND', 'SUI']

### Results
| Method | Sharpe | Return% | MaxDD% | Trades |
|--------|--------|---------|--------|--------|
| Baseline 50/50 | 1.327 | 3.36 | 1.91 | 479 |
| Dual-LB MR | 0.993 | 2.44 | 2.12 | 629 |
| Exit Z=0.00 | 1.295 | 3.27 | 1.91 | 479 |
| Exit Z=0.25 | 1.292 | 3.26 | 1.99 | 481 |
| Exit Z=0.50 | 1.443 | 3.62 | 1.96 | 484 |
| Exit Z=0.75 | 1.396 | 3.52 | 2.01 | 488 |
| Exit Z=1.00 | 1.324 | 3.32 | 2.08 | 493 |
| 22 coins | 1.327 | 3.36 | 1.91 | 479 |
| Extra coins only | nan | -inf | inf | 304 |
| All coins combined | 1.027 | 2.47 | 2.12 | 777 |

Best: **Exit Z=0.50** (Sharpe 1.443)

### Extra Coin Donchian Sharpes
- BNB: 1.745
- ARB: 1.417
- AXS: 1.122
- SUI: 0.609
- MANA: 0.511
- OP: 0.186
- HBAR: -0.262
- SAND: -1.585
- APT: -2.903
- PEPE: nan

## Expanded Coin Universe (2026-04-04)

### Universe
- Tier 1 (OKX 2021+): 25 coins
- Tier 2 (OKX 2022+): 25 coins
- Tier 3 (HL only): 37 coins
- Total usable: 87
- Coins with holdout data: 87

### Donchian B0 Holdout (40/87 positive Sharpe)
Top 10 new coins by Donchian Sharpe:
- MERL: Sharpe 3.394 (vol 255K)
- AVNT: Sharpe 2.866 (vol 165K)
- IP: Sharpe 2.751 (vol 787K)
- GALA: Sharpe 2.006 (vol 164K)
- AR: Sharpe 1.877 (vol 207K)
- APE: Sharpe 1.858 (vol 219K)
- ENA: Sharpe 1.818 (vol 2.3M)
- BNB: Sharpe 1.745 (vol 2.4M)
- BIO: Sharpe 1.726 (vol 235K)
- ZK: Sharpe 1.673 (vol 985K)

### Portfolio Comparison (Holdout, 50/50, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
| A) Original 22 | 1.397 | 3.75 | 2.14 | 414 | 19 |
| B) All coins | 1.348 | 0.17 | 0.71 | 1979 | 87 |
| C) New only | -3.105 | -0.44 | 1.23 | 1581 | 68 |
| D) Orig + pos-Don new | 4.176 | 1.89 | 0.55 | 1051 | 44 |
| E) Tier 1 (25) | 1.040 | 2.57 | 2.00 | 568 | 25 |
| F) Top 30 Donchian | 4.045 | 2.57 | 0.65 | 682 | 30 |

Best: **D) Orig + pos-Don new** (Sharpe 4.176)

## Expanded Coins v2 - No Data Snooping (2026-04-04)

### Methodology Fix
- Coin selection: avg **validation** Donchian Sharpe > 0 (NOT holdout)
- Holdout touched ONCE after all selection/tuning complete

### Coin Screening (Validation)
- Total usable: 92
- Passed screening (avg val SR > 0): 26
- Original 22 that passed: 9/22
- New coins selected: 17

New selected coins: MELANIA, PNUT, MOODENG, IO, BIGTIME, HYPE, HBAR, SAND, ACE, POPCAT, ZK, ZEN, GMT, GALA, APT, STX, AR

### Holdout (50/50 Donchian+MR, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
| A) Original 22 | 1.443 | 3.62 | 1.96 | 484 | 22 |
| B) Val-selected all | -0.553 | -1.45 | 3.95 | 649 | 26 |
| C) New selected only | -1.089 | -3.18 | 6.04 | 432 | 17 |
| D) Orig + new selected | 0.384 | 0.87 | 2.60 | 911 | 39 |
| E) Top 30 by val SR | -0.553 | -1.45 | 3.95 | 649 | 26 |

Best: **A) Original 22** (Sharpe 1.443)

## Expanded Coins v3 - Correct Methodology (2026-04-04)

### Methodology
- Single capital pool (run_combo) — no double-counting
- Only coins with OKX data from 2021 (full 3-window WF): 28
- Coin screening: avg validation Donchian Sharpe > 0 across all 3 windows
- Holdout touched once

### Validation Screening
- Passed: 11/28 (avg val Sharpe > 0, all 3 windows)
- New coins (not in original 22): AXS, YGG, CELO, GALA, SAND, PEOPLE
- New coins that passed: SAND, GALA

### Holdout (50/50 Donchian+MR, 3x leverage)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
| F) Pure Donchian 22 | 0.148 | 0.33 | 10.32 | 90 | 22 |
| A) Orig 22 (per-coin ez) | 0.231 | 0.69 | 5.39 | 116 | 22 |
| B) Orig 22 (ez=0.50) | 0.287 | 0.91 | 5.14 | 119 | 22 |
| C) All 28 (ez=0.50) | 0.321 | 1.00 | 4.00 | 164 | 28 |
| D) Val-passed | -0.142 | -1.00 | 8.66 | 76 | 11 |
| E) Orig + new passed | 0.257 | 0.80 | 5.76 | 133 | 24 |

Best: **C) All 28 (ez=0.50)** (Sharpe 0.321)

## Expanded Coins v3 - Correct Methodology (2026-04-04)

### Methodology
- Single capital pool (run_combo) — no double-counting
- Only coins with OKX data from 2021 (full 3-window WF): 28
- Coin screening: avg validation Donchian Sharpe > 0 across all 3 windows
- Holdout touched once

### Validation Screening
- Passed: 11/28 (avg val Sharpe > 0, all 3 windows)
- New coins (not in original 22): AXS, YGG, CELO, GALA, SAND, PEOPLE
- New coins that passed: SAND, GALA

### Holdout (50/50 Donchian+MR, 3x leverage)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
| F) Pure Donchian 22 | 1.006 | 4.77 | 4.11 | 418 | 22 |
| A) Orig 22 (per-coin ez) | 1.000 | 2.51 | 2.50 | 601 | 22 |
| B) Orig 22 (ez=0.50) | 1.070 | 2.69 | 2.24 | 573 | 22 |
| C) All 28 (ez=0.50) | 1.284 | 2.91 | 2.02 | 728 | 28 |
| D) Val-passed | 0.363 | 0.78 | 2.44 | 336 | 11 |
| E) Orig + new passed | 0.915 | 2.23 | 2.14 | 628 | 24 |

Best: **C) All 28 (ez=0.50)** (Sharpe 1.284)

## Cross-Sectional Momentum Experiment (2026-04-04)

### Best Parameters
- Lookback: 36 bars
- Top/Bottom K: 5
- Rebalance: every 21 bars (168h)
- Weighting: equal-weight
- Avg validation Sharpe: 1.118

### Holdout (28 coins, 50/50 Donchian+MR, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Donchian 28 | 1.092 | 4.76 | 3.73 | 530 |
| B) XS Momentum | 0.913 | 18.34 | 18.69 | 421 |
| C) Don+XSMom 50/50 | -0.052 | -0.87 | 8.91 | 934 |
| D) Don+MR+XSMom 33% | 0.041 | -0.08 | 5.76 | 1100 |
| E) Don50+MR25+XSMom25 | 0.329 | 0.98 | 4.23 | 1081 |

### Market Neutrality
- Beta to BTC: -0.08803493755240038
- Net exposure: $63.32

## Cross-Sectional Momentum Experiment (2026-04-05)

### Best Parameters
- Lookback: 36 bars
- Top/Bottom K: 5
- Rebalance: every 21 bars (168h)
- Weighting: equal-weight
- Avg validation Sharpe: 1.118

### Holdout (28 coins, 50/50 Donchian+MR, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Donchian 28 | 1.092 | 4.76 | 3.73 | 530 |
| B) XS Momentum | 0.913 | 18.34 | 18.69 | 421 |
| C) Don+XSMom 50/50 | -0.052 | -0.87 | 8.91 | 934 |
| D) Don+MR+XSMom 33% | 0.041 | -0.08 | 5.76 | 1100 |
| E) Don50+MR25+XSMom25 | 0.329 | 0.98 | 4.23 | 1081 |

### Market Neutrality
- Beta to BTC: -0.08803493755240038
- Net exposure: $63.32

## Portfolio Combinations Fix (2026-04-05)

### Bug Fix
Previous combo results were wrong due to time-alignment issue: XSMom had 725 holdout bars 
(46-bar warmup) while Donchian had 375 bars (396-bar warmup). Taking common length from start 
cut off XSMom's profitable second half. Fixed by aligning from the END (same end date).

XSMom standalone: full 725 bars = +18.34%, aligned 375 bars (same period as Donchian) = +28.87%

### Corrected Holdout Results (2025.07-2026.03, 28 coins, time-aligned)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Pure Donchian 28 | 1.092 | 4.76 | 3.73 | 530 |
| B) Pure MR 28 | 0.627 | 0.44 | 0.87 | 282 |
| C) Pure XSMom 28 | 2.382 | 28.87 | 10.00 | 421 |
| D) Don+MR 50/50 | 1.164 | 2.60 | 2.07 | 812 |
| E) Don+XSMom 50/50 | 2.425 | 16.81 | 5.42 | 951 |
| F) MR+XSMom 50/50 | 2.339 | 14.66 | 5.25 | 703 |
| G) Don+MR+XSMom 33/33/33 | 2.441 | 11.36 | 3.60 | 1233 |
| H) Don50+MR25+XSMom25 | 2.366 | 9.71 | 2.73 | 1233 |
| I) Don25+MR25+XSMom50 | 2.413 | 15.73 | 5.33 | 1233 |

### Key Findings
- XSMom is the strongest single strategy (Sharpe 2.382, +28.87%) but MaxDD 10%
- G) 33/33/33 has highest Sharpe (2.441) with only 3.60% MaxDD
- H) Don50+MR25+XSMom25 has lowest MaxDD (2.73%) with good Sharpe (2.366)
- Adding XSMom to any combo dramatically improves Sharpe vs Don+MR only (1.164 -> 2.4+)
- XSMom beta to BTC = -0.088 (market neutral confirmed)

## Portfolio Combinations - Correct Time Alignment (2026-04-05)

### Time Alignment
- All strategies use LAST 375 bars of holdout (aligned from start to Donchian warmup end)
- Donchian warmup = 396 bars (longest), XSMom warmup = 46 bars
- Common trading window: 375 bars (approx 2025-11-10 to 2026-03-25, 125 days)

### XSMom Full Trajectory (important context)
- Full holdout (725 bars): $10,000 -> min $8,950 -> $11,834 (+18.34%)
- **In Donchian-aligned window (375 bars): $9,183 -> $11,834 (+28.87%)**
- XSMom lost money in first half (Jul-Nov 2025) then recovered strongly (Nov 2025 - Mar 2026)
- The 28.87% in the aligned window is inflated because it starts from a drawdown trough

### Holdout Results (same 375-bar window, from-start alignment)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Pure Donchian 28 | 1.092 | 4.76 | 3.73 | 530 |
| B) Pure MR 28 | 0.627 | 0.44 | 0.87 | 282 |
| C) Pure XSMom 28 | 2.382 | 28.87 | 10.00 | 421 |
| D) Don+MR 50/50 | 1.164 | 2.60 | 2.07 | 812 |
| E) Don+XSMom 50/50 | 2.425 | 16.81 | 5.42 | 951 |
| F) MR+XSMom 50/50 | 2.339 | 14.66 | 5.25 | 703 |
| G) Don+MR+XSMom 33/33/33 | 2.441 | 11.36 | 3.60 | 1233 |
| H) Don50+MR25+XSMom25 | 2.366 | 9.71 | 2.73 | 1233 |
| I) Don25+MR25+XSMom50 | 2.413 | 15.73 | 5.33 | 1233 |

### Sanity Checks
- D) Don+MR 50/50: (4.76+0.44)/2 = 2.60% -> matches 2.60% (correct)
- E) Don+XSMom 50/50: (4.76+28.87)/2 = 16.81% -> matches 16.81% (correct)
- G) 33/33/33: (4.76+0.44+28.87)/3 = 11.36% -> matches 11.36% (correct)

### Caveat
XSMom 28.87% return in the aligned window is NOT comparable to its full-holdout 18.34%.
The aligned window starts at a drawdown trough (XSMom was at $9,183 vs $10,000 start).
A fairer comparison would use the FULL holdout return of 18.34%.

## Portfolio Combinations - Final (2026-04-05)

### Methodology
- Warmup data prepended from 2025-01-15 (before holdout)
- All strategies start trading 2025-07-01, equity = $10,000
- Common window: 771 bars (257 days)

### Results
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Pure Donchian 28 | -0.174 | -1.27 | 6.25 | 1238 |
| B) Pure MR 28 (ez=0.50) | -0.330 | -0.64 | 2.12 | 696 |
| C) Pure XSMom 28 | 1.093 | 25.79 | 16.51 | 805 |
| D) Don+MR 50/50 | -0.299 | -0.96 | 3.14 | 1934 |
| E) Don+XSMom 50/50 | 0.943 | 12.26 | 9.26 | 2043 |
| F) MR+XSMom 50/50 | 0.996 | 12.58 | 8.76 | 1501 |
| G) Don+MR+XSMom 33/33/33 | 0.897 | 7.96 | 6.22 | 2739 |
| H) Don50+MR25+XSMom25 | 0.791 | 5.65 | 5.49 | 2739 |
| I) Don25+MR25+XSMom50 | 0.973 | 12.42 | 9.01 | 2739 |

### Sanity Checks
- D) (-1.27+-0.64)/2 = -0.96% vs actual -0.96%
- E) (-1.27+25.79)/2 = 12.26% vs actual 12.26%
- G) (-1.27+-0.64+25.79)/3 = 7.96% vs actual 7.96%

Best Sharpe: **C) Pure XSMom 28** (1.093, 25.79%, MaxDD 16.51%)

## Multi-Signal Trend Walk-Forward (2026-04-05)

### Part 2: Frequency x Filter
| Config | W1 Params | W1 IS SR | W1 OOS SR | W2 Params | W2 IS SR | W2 OOS SR | Match |
|--------|-----------|----------|-----------|-----------|----------|-----------|-------|
| 8H pure | A/0.3/0.15 | 2.646 | -1.083 | A/0.3/0.2 | 0.154 | 0.689 | NO |
| 8H + 1D filter | A/0.3/0.1 | 2.704 | -0.783 | A/0.2/0.2 | 0.165 | 0.773 | NO |
| 1H pure | B/0.3/0.2 | 2.401 | -0.404 | A/0.5/0.2 | 0.084 | 0.265 | NO |
| 1H + 1D filter | B/0.3/0.2 | 2.414 | -0.400 | A/0.5/0.2 | -0.048 | 0.237 | NO |

### Part 3: Position Management Diagnostic (W1 OOS = 2023)

| Sizing | Strategy | Sharpe | Return% | MaxDD% | Trades |
|--------|----------|--------|---------|--------|--------|
| A) Equal weight | Trend only | -0.563 | -44.85 | 67.95 | 10577 |
| A) Equal weight | Trend60+XS40 | -1.286 | -42.37 | 55.90 | 11820 |
| A) Equal weight | XSMom only | -0.812 | -34.24 | 51.95 | 1243 |
| B) Inv volatility | Trend only | -0.238 | -6.13 | 22.48 | 9470 |
| B) Inv volatility | Trend60+XS40 | -1.220 | -19.13 | 28.21 | 10713 |
| B) Inv volatility | XSMom only | -0.812 | -34.24 | 51.95 | 1243 |
| C) InvVol + DD scaling | Trend only | -1.284 | -10.58 | 15.88 | 6325 |
| C) InvVol + DD scaling | Trend60+XS40 | -2.109 | -21.80 | 24.90 | 7568 |
| C) InvVol + DD scaling | XSMom only | -0.812 | -34.24 | 51.95 | 1243 |
| D) InvVol + DD + Regime | Trend only | -1.574 | -11.10 | 15.02 | 5498 |
| D) InvVol + DD + Regime | Trend60+XS40 | -2.227 | -22.11 | 24.80 | 6741 |
| D) InvVol + DD + Regime | XSMom only | -0.812 | -34.24 | 51.95 | 1243 |

## Final Holdout (2026-04-05)

### Config
- Multi-signal trend: 8H + 1D filter, Set A, thresh=0.2, tvol=0.20 (W2 params)
- Sizing: Inverse Volatility
- 28 coins, unified params

### Results (Holdout 2025.07-2026.03, 822 bars)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Donchian B0 | -0.071 | -0.22 | 2.35 | 8272 |
| B) Multi-signal trend | -0.332 | -10.00 | 17.42 | 9674 |
| C) XSMom | -0.243 | -9.58 | 30.98 | 1526 |
| D) Trend60+XSMom40 | -0.434 | -9.83 | 20.74 | 11200 |
| E) Trend+MR+XSMom 33ea | -0.515 | -6.90 | 15.06 | 15243 |
| F) TSMOM only | -0.229 | -8.23 | 21.08 | 9279 |
| G) XSMom+MR 50/50 | -0.385 | -5.36 | 16.59 | 5569 |

### Sanity Checks
- D) 0.6*B+0.4*C = -9.83% vs actual -9.83%
- E) (B+MR+C)/3 = -6.90% vs actual -6.90%
- F) TSMOM-only = -8.23% vs full 9-signal = -10.00%

### PM Data Saved
- pm_training_2024.parquet
- pm_validation_2025h1.parquet

## Final Holdout v2 - Clean Start (2026-04-05)

### Fix Applied
- All strategies start with ZERO positions at holdout first bar
- Warmup only computes indicators, no trades
- Position state confirmed at bar 0 for each strategy

### Results (Holdout 2025-07-01 to 2026-03-25, 822 bars)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Donchian B0 | -0.237 | -1.77 | 6.53 | 1093 |
| B) Multi-signal trend | -0.352 | -10.37 | 17.44 | 9645 |
| C) XSMom | 1.010 | 24.75 | 16.49 | 520 |
| D) Trend60+XSMom40 | 0.323 | 3.68 | 11.80 | 10165 |
| E) Trend+MR+XSMom 33ea | 0.442 | 4.48 | 8.10 | 10808 |
| F) TSMOM only | -0.238 | -8.40 | 21.11 | 9265 |
| G) XSMom+MR 50/50 | 0.894 | 11.90 | 8.91 | 1163 |

### Sanity Checks
- D) 0.6*B+0.4*C = 3.68% vs actual 3.68%
- E) (B+MR+C)/3 = 4.48% vs actual 4.48%
- G) (C+MR)/2 = 11.90% vs actual 11.90%

## 5 Mean Reversion Strategies (2026-04-05)

| Strategy | W1 Params | W1 OOS SR | W2 Params | W2 OOS SR | Match | MktNeutral |
|----------|-----------|-----------|-----------|-----------|-------|------------|
| 1_Pairs | [90, 1.5, 0.25] | -0.671 | [90, 1.5, 0.25] | -0.725 | YES | YES |
| 2_Bollinger | [90, 1.5] | -1.397 | [90, 2.5] | 0.200 | NO | NO |
| 3_OU | [360, 1.5, 0.05] | 0.000 | [180, 1.5, 0.05] | 0.418 | NO | NO |
| 4_Coint | [90, 1.5, 0.25, 90] | 1.065 | [90, 1.5, 0.25, 90] | 1.157 | YES | YES |
| 5_Funding | N/A | N/A | [180, 2.5, 0.5] | -1.238 | NO | NO |

## Cointegration + OU Fixed (2026-04-06)

### Fixes Applied
- Cointegration: LOG prices, beta clamped [0.3, 3.0], max 10% per pair, max 15 pairs
- OU: handle insufficient warmup gracefully

### Results
| Strategy | W1 OOS SR | W1 Ret% | W1 DD% | W2 OOS SR | W2 Ret% | W2 DD% | Match |
|----------|-----------|---------|--------|-----------|---------|--------|-------|
| Coint | 0.221 | -36.89 | 77.12 | -0.122 | -57.46 | 87.81 | YES |
| OU | 0.102 | 0.00 | 0.01 | 0.000 | 0.00 | 0.00 | YES |

### Cointegration: Beta-filtered pairs found
- W1 IS: 0 pairs (no valid pairs with beta in [0.3, 3.0])
- W1 OOS: 67 pairs found (trained on OOS data since IS had none)
- W2 IS: 0 pairs -> W2 OOS: 62 pairs
- Top stable pairs: DOT/FIL (p=0.0001), ICP/AVAX, SAND/PEOPLE, FIL/PEOPLE
- BUT: OOS returns -37% to -57% with 77-88% drawdown -> cointegration is NOT profitable

### OU: Nearly zero activity
- W1 OOS: 2 trades, W2 OOS: 0 trades
- theta values all < 0.03 (very slow reversion, ~33+ days half-life)
- theta_min=0.01 passes most coins but signals barely trigger with entry_thresh=1.0
- The OU model finds crypto does NOT have meaningful mean reversion at 8H scale

### Correlation with XSMom (W2 OOS)
- Cointegration vs XSMom: 0.017 (nearly zero - good diversification but useless strategy)

### Conclusion
- **Cointegration: REJECTED** (massive losses despite position capping)
- **OU: REJECTED** (zero activity, theta too slow for practical trading)
- Both confirm that classical mean reversion models do not work well on crypto
- The existing Z-score MR (Sharpe ~0.6) remains the best MR approach

## Advanced Cointegration + Avellaneda-Lee PCA (2026-04-06)

### Part 3: Full Comparison
| Strategy | Timeframe | W1 Params | W1 OOS SR | W2 Params | W2 OOS SR | Match | Pairs |
|----------|-----------|-----------|-----------|-----------|-----------|-------|-------|
| Coint | 1d | [90, 1.5, 0.25, 90 | 0.000 | [90, 1.5, 0.25, 90 | 0.000 | YES | 0 |
| Coint | 1h | [90, 1.5, 0.25, 90 | 0.000 | [90, 1.5, 0.25, 90 | 0.000 | YES | 0 |
| Coint | 4h | [90, 1.5, 0.25, 90 | 0.000 | [90, 1.5, 0.25, 90 | 0.000 | YES | 0 |
| Coint | 8h | [90, 1.5, 0.25, 90 | 0.000 | [90, 1.5, 0.25, 90 | 0.000 | YES | 0 |
| PCA | 1d | [5, 1.0, 0.25, 180 | -0.873 | [5, 1.0, 0.25, 180 | -0.678 | YES | None |
| PCA | 1h | [3, 1.0, 0.25, 360 | -1.124 | [3, 1.0, 0.25, 360 | -0.429 | YES | None |
| PCA | 4h | [3, 2.0, 0.25, 360 | -0.022 | [3, 1.0, 0.25, 360 | 0.065 | NO | None |
| PCA | 8h | [5, 1.5, 0.25, 180 | 1.485 | [5, 1.5, 0.25, 180 | 1.143 | YES | None |

### Pair Stability (triple-filter)
- 1h: W1=0 pairs, W2=0 pairs, overlap=0
- 4h: W1=0 pairs, W2=0 pairs, overlap=0
- 8h: W1=0 pairs, W2=0 pairs, overlap=0
- 1d: W1=0 pairs, W2=0 pairs, overlap=0

### PCA Variance Explained
- PCA_1d: ['0.528', '0.091', '0.046', '0.041', '0.040'] (cum=0.746)
- PCA_1h: ['0.667', '0.043', '0.042'] (cum=0.752)
- PCA_4h: ['0.622', '0.056', '0.040'] (cum=0.718)
- PCA_8h: ['0.584', '0.060', '0.055', '0.046', '0.036'] (cum=0.782)

### Correlation with XSMom
- PCA_1h: -0.016
- PCA_4h: 0.026
- PCA_8h: 0.024
- PCA_1d: 0.014

## PCA + XSMom Holdout (2026-04-07)

Config: PCA 8H K=5, entry=1.5, exit=0.25, OU=180, recalib=180

| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) PCA 8H | -0.133 | -2.04 | 14.22 | 12041 |
| B) XSMom | -0.799 | -22.20 | 27.82 | 560 |
| C) PCA+XSMom 50/50 | -0.861 | -12.12 | 18.52 | 12601 |
| D) PCA+XSMom+MR 33ea | -0.939 | -8.40 | 12.87 | 13244 |
| E) PCA60+XSMom40 | -0.826 | -10.11 | 16.69 | 12601 |
| F) PCA40+XSMom60 | -0.867 | -14.14 | 20.35 | 12601 |

Sanity: C) (-2.04+-22.20)/2=-12.12% OK

Correlations: PCA-XSMom=0.005, PCA-MR=0.048, XSMom-MR=-0.010

## PCA + XSMom Holdout (2026-04-07)

Config: PCA 8H K=5, entry=1.5, exit=0.25, OU=180, recalib=180

| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) PCA 8H | -0.133 | -2.04 | 14.22 | 12041 |
| B) XSMom | -0.799 | -22.20 | 27.82 | 560 |
| C) PCA+XSMom 50/50 | -0.861 | -12.12 | 18.52 | 12601 |
| D) PCA+XSMom+MR 33ea | -0.939 | -8.40 | 12.87 | 13244 |
| E) PCA60+XSMom40 | -0.826 | -10.11 | 16.69 | 12601 |
| F) PCA40+XSMom60 | -0.867 | -14.14 | 20.35 | 12601 |

Sanity: C) (-2.04+-22.20)/2=-12.12% OK

Correlations: PCA-XSMom=0.005, PCA-MR=0.048, XSMom-MR=-0.010

## Phase-Averaged Holdout (2026-04-07)

21 phases (data start 2025-06-01 to 2025-06-21), all zero-position clean start.

| Strategy | Avg SR | SR std | Best SR | Worst SR | Avg Ret% | Ret std | Verdict |
|----------|--------|--------|---------|----------|---------|---------|--------|
| A) PCA 8H | -0.386 | 0.286 | 0.107 | -0.850 | -4.52 | 2.78 | ROBUST |
| B) XSMom | 0.216 | 0.687 | 1.075 | -0.825 | 3.21 | 18.00 | UNRELIABLE |
| C) Donchian B0 | 0.811 | 0.049 | 0.856 | 0.721 | 3.87 | 0.19 | ROBUST |
| D) Trend 8H+1D | -0.334 | 0.078 | -0.211 | -0.577 | -10.19 | 1.57 | ROBUST |
| E) Z-score MR | -0.131 | 0.137 | 0.009 | -0.280 | -0.29 | 0.28 | ROBUST |
| F) PCA+XSMom 50/50 | -0.005 | 0.658 | 0.862 | -1.006 | -0.48 | 9.09 | UNRELIABLE |
| G) PCA+XSMom+MR 33 | -0.049 | 0.666 | 0.812 | -1.056 | -0.39 | 6.06 | UNRELIABLE |
| H) XSMom+MR 50/50 | 0.113 | 0.701 | 0.964 | -0.930 | 1.50 | 9.01 | UNRELIABLE |

### Interpretation
- SR std < 0.3 = ROBUST (result trustworthy)
- SR std 0.3-0.6 = MODERATE (some phase dependency)
- SR std > 0.6 = UNRELIABLE (result is luck)

## Definitive Holdout v3 (2026-04-07)

### CLAUDE.md Rules Enforced
All 7 rules checked and passed.

### Data Coverage (Rule 6)
- Data load: 2024-06-21
- Warmup end: 2025-07-01
- Trading: 2025-07-01 to 2026-03-31
- Total bars: 821

### v2 Consistency (Rule 5)
- Donchian: v2=-0.237 / v3=-0.237 (diff=0.000)
- MR: v2=-0.96% / v3=-0.75% (diff=0.21%)

### Results
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
| A) Donchian B0 | -0.237 | -1.77 | 6.53 | 1093 |
| B) Trend 8H+1D | -0.352 | -10.37 | 17.44 | 9645 |
| C) XSMom | -1.176 | -26.38 | 32.07 | 539 |
| D) PCA 8H | -0.096 | -1.67 | 14.22 | 12041 |
| E) Z-score MR | -0.374 | -0.75 | 2.12 | 643 |
| F) PCA+XSMom 50/50 | -1.231 | -14.02 | 21.05 | 12580 |
| G) PCA+XSMom+MR 33 | -1.329 | -9.60 | 14.40 | 13223 |
| H) XSMom+MR 50/50 | -1.374 | -13.57 | 16.59 | 1182 |
| I) Don+PCA+XSMom 33 | -1.289 | -9.94 | 15.14 | 13673 |
| J) Trend+XSMom 60/40 | -1.006 | -16.78 | 21.35 | 10184 |
| K) Trend+MR+XSMom 33 | -1.251 | -12.50 | 15.33 | 10827 |

### Sanity Checks (Rule 4)
All passed.

## Phase-Averaged Holdout v2 (2026-04-07)

Rule 7 enforced: phase shift via rebalance counter offset, all phases cover full holdout.
Data: 2024-06-21 to 2026-04-01. Holdout: 802 bars.

| Strategy | Avg SR | SR std | Best SR | Worst SR | Avg Ret% | Ret std | Verdict |
|----------|--------|--------|---------|----------|---------|---------|--------|
| A) Donchian B0 | -0.237 | 0.000 | -0.237 | -0.237 | -1.77 | 0.00 | INVARIANT |
| B) Trend 8H+1D | -0.352 | 0.000 | -0.352 | -0.352 | -10.37 | 0.00 | INVARIANT |
| C) XSMom | -0.041 | 0.654 | 1.041 | -1.155 | -3.77 | 15.93 | UNRELIABLE |
| D) PCA 8H | -0.328 | 0.324 | 0.168 | -1.061 | -4.03 | 3.28 | MARGINAL |
| E) Z-score MR | -0.476 | 0.000 | -0.476 | -0.476 | -0.96 | 0.00 | INVARIANT |
| F) PCA+XSMom 50/50 | -0.282 | 0.647 | 0.851 | -1.213 | -4.32 | 8.30 | UNRELIABLE |
| G) PCA+XSMom+MR 33 | -0.343 | 0.656 | 0.805 | -1.291 | -3.09 | 5.53 | UNRELIABLE |
| H) XSMom+MR 50/50 | -0.192 | 0.703 | 1.022 | -1.292 | -2.48 | 8.24 | UNRELIABLE |
| I) Don+PCA+XSMom 33 | -0.362 | 0.630 | 0.746 | -1.272 | -3.48 | 5.53 | UNRELIABLE |

### Previous phase avg comparison
- Previous Donchian avg SR was 0.811 (WRONG: warmup ate holdout bars)
- Corrected Donchian SR: -0.237 (phase invariant, matches v2 corrected -0.237)
- Previous XSMom avg SR was 0.216 with std 0.687 (WRONG: different holdout coverage per phase)
