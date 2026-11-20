"""回测绩效指标计算。所有函数都是纯函数（无副作用），输入权益曲线/交易列表，输出指标。"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List

import numpy as np
import pandas as pd
from scipy import stats

if TYPE_CHECKING:
    from cryptolab.backtest.engine import Trade


def max_drawdown(equity_series: pd.Series) -> tuple[float, float]:
    """Return (max_dd_usd, max_dd_pct) from an equity series."""
    peak = equity_series.iloc[0]
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    for eq in equity_series:
        if eq > peak:
            peak = eq
        dd_usd = peak - eq
        dd_pct = (dd_usd / peak * 100.0) if peak > 0 else 0.0
        if dd_usd > max_dd_usd:
            max_dd_usd = dd_usd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
    return max_dd_usd, max_dd_pct


def drawdown_series(equity_series: pd.Series) -> pd.Series:
    """Return drawdown percentage at each point."""
    peak = equity_series.cummax()
    return ((peak - equity_series) / peak * 100.0).fillna(0.0)


def win_rate_and_pnl(trades: List[Trade]) -> dict:
    """Compute win rate, avg win/loss, profit factor from closed trades."""
    # Only count trades that realized PnL (closes/reduces)
    realized = [t for t in trades if t.realized_pnl != 0.0]
    if not realized:
        return {
            "win_rate": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "profit_factor": 0.0,
        }

    wins = [t for t in realized if t.realized_pnl > 0]
    losses = [t for t in realized if t.realized_pnl < 0]

    win_rate = len(wins) / len(realized) * 100.0 if realized else 0.0

    avg_win = sum(t.realized_pnl for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.realized_pnl for t in losses) / len(losses) if losses else 0.0

    gross_wins = sum(t.realized_pnl for t in wins)
    gross_losses = abs(sum(t.realized_pnl for t in losses))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf") if gross_wins > 0 else 0.0

    return {
        "win_rate": win_rate,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "profit_factor": profit_factor,
    }


def time_in_market(trades: List[Trade], total_bars: int) -> tuple[float, float]:
    """Return (time_in_market_pct, avg_trade_duration_bars).

    Approximates from trade log: count bars where position != 0.
    """
    if not trades or total_bars == 0:
        return 0.0, 0.0

    # Build position timeline from trades
    bars_in_market = 0
    trade_durations = []
    open_bar = None

    for t in trades:
        if t.old_position == 0.0 and t.new_position != 0.0:
            open_bar = t.bar_idx
        elif t.old_position != 0.0 and t.new_position == 0.0:
            if open_bar is not None:
                duration = t.bar_idx - open_bar
                trade_durations.append(duration)
                bars_in_market += duration
            open_bar = None

    # If still in a position at the end
    if open_bar is not None:
        duration = total_bars - open_bar
        trade_durations.append(duration)
        bars_in_market += duration

    tim_pct = bars_in_market / total_bars * 100.0
    avg_dur = sum(trade_durations) / len(trade_durations) if trade_durations else 0.0
    return tim_pct, avg_dur


def sharpe_ratio(equity_series: pd.Series, periods_per_year: float) -> float:
    """Annualized Sharpe ratio (assuming 0 risk-free rate for crypto)."""
    returns = equity_series.pct_change().dropna()
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float((returns.mean() / returns.std()) * (periods_per_year ** 0.5))


def sortino_ratio(equity_series: pd.Series, periods_per_year: float) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    returns = equity_series.pct_change().dropna()
    downside = returns[returns < 0]
    if len(downside) < 2 or downside.std() == 0:
        return 0.0
    return float((returns.mean() / downside.std()) * (periods_per_year ** 0.5))


def calmar_ratio(equity_series: pd.Series, periods_per_year: float) -> float:
    """Calmar ratio = annualized return / max drawdown."""
    if len(equity_series) < 2:
        return 0.0
    total_return = equity_series.iloc[-1] / equity_series.iloc[0] - 1
    n_periods = len(equity_series)
    ann_return = (1 + total_return) ** (periods_per_year / n_periods) - 1
    _, dd_pct = max_drawdown(equity_series)
    if dd_pct == 0:
        return 0.0
    return (ann_return * 100) / dd_pct


def monthly_returns(equity_curve: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly return table from equity curve.

    Returns DataFrame with columns: year, month, return_pct.
    """
    ec = equity_curve[["timestamp", "equity"]].copy()
    ec["year"] = ec["timestamp"].dt.year
    ec["month"] = ec["timestamp"].dt.month

    rows = []
    for (year, month), group in ec.groupby(["year", "month"]):
        start_eq = group["equity"].iloc[0]
        end_eq = group["equity"].iloc[-1]
        ret = (end_eq / start_eq - 1) * 100.0 if start_eq > 0 else 0.0
        rows.append({"year": int(year), "month": int(month), "return_pct": ret})

    return pd.DataFrame(rows)


# Map interval string -> number of bars per year
PERIODS_PER_YEAR = {
    "1h": 8766,
    "2h": 4383,
    "4h": 2190,
    "8h": 1096,
    "1d": 365,
    "1w": 52,
}


def compute_metrics(
    equity_curve: pd.DataFrame,
    trades: List[Trade],
    initial_equity: float,
    interval: str = "4h",
) -> dict:
    """Compute all backtest metrics from equity curve and trade log."""
    eq = equity_curve["equity"]
    final = eq.iloc[-1]
    total_return = (final - initial_equity) / initial_equity * 100.0

    dd_usd, dd_pct = max_drawdown(eq)
    wp = win_rate_and_pnl(trades)
    total_bars = len(equity_curve)
    tim_pct, avg_dur = time_in_market(trades, total_bars)
    total_fees = sum(t.fee for t in trades)
    total_slippage = sum(t.metadata.get("slippage_usd", 0.0) for t in trades)

    ppy = PERIODS_PER_YEAR.get(interval, 2190)
    sr = sharpe_ratio(eq, ppy)
    so = sortino_ratio(eq, ppy)
    cr = calmar_ratio(eq, ppy)

    return {
        "final_equity": final,
        "total_return_pct": total_return,
        "max_drawdown_usd": dd_usd,
        "max_drawdown_pct": dd_pct,
        "sharpe": sr,
        "sortino": so,
        "calmar": cr,
        "total_trades": len(trades),
        "win_rate": wp["win_rate"],
        "avg_win_pct": wp["avg_win_pct"],
        "avg_loss_pct": wp["avg_loss_pct"],
        "profit_factor": wp["profit_factor"],
        "total_fees": total_fees,
        "total_slippage_est": total_slippage,
        "time_in_market_pct": tim_pct,
        "avg_trade_duration_bars": avg_dur,
    }


# ---------------------------------------------------------------------------
# Portfolio metrics
# ---------------------------------------------------------------------------

def portfolio_equity_curve(
    symbol_curves: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Combine per-symbol equity curves into a portfolio equity curve.

    Each symbol curve has columns: timestamp, equity, drawdown_pct.
    We compute per-symbol PnL (equity - initial), sum PnL, add back total initial.
    """
    merged = None
    initials = {}
    for symbol, ec in symbol_curves.items():
        col = ec[["timestamp", "equity"]].copy()
        col = col.rename(columns={"equity": f"eq_{symbol}"})
        initials[symbol] = ec["equity"].iloc[0]
        if merged is None:
            merged = col
        else:
            merged = pd.merge(merged, col, on="timestamp", how="outer")

    merged = merged.sort_values("timestamp").reset_index(drop=True)

    # Forward-fill gaps (symbol might not have data for every bar)
    eq_cols = [c for c in merged.columns if c.startswith("eq_")]
    for c in eq_cols:
        merged[c] = merged[c].ffill()
        # Back-fill any leading NaN with that symbol's initial capital
        sym = c.replace("eq_", "")
        merged[c] = merged[c].fillna(initials[sym])

    merged["equity"] = merged[eq_cols].sum(axis=1)
    merged["drawdown_pct"] = drawdown_series(merged["equity"])
    return merged[["timestamp", "equity", "drawdown_pct"] + eq_cols]


# ---------------------------------------------------------------------------
# Overfitting detection
# ---------------------------------------------------------------------------

def bootstrap_sharpe_ci(
    equity_series: pd.Series,
    periods_per_year: float,
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict:
    """Bootstrap confidence interval on annualized Sharpe ratio.

    Resamples returns (with replacement) n_boot times, computes Sharpe each time.
    Returns dict with lower, upper, median, std of bootstrap distribution.
    """
    rng = np.random.default_rng(seed)
    returns = equity_series.pct_change().dropna().values
    n = len(returns)
    if n < 10:
        return {"lower": 0.0, "upper": 0.0, "median": 0.0, "std": 0.0}

    sharpes = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(returns, size=n, replace=True)
        s = sample.std()
        sharpes[i] = (sample.mean() / s * math.sqrt(periods_per_year)) if s > 0 else 0.0

    alpha = (1 - ci) / 2
    return {
        "lower": float(np.percentile(sharpes, alpha * 100)),
        "upper": float(np.percentile(sharpes, (1 - alpha) * 100)),
        "median": float(np.median(sharpes)),
        "std": float(np.std(sharpes)),
    }


def deflated_sharpe(
    observed_sharpe: float,
    all_trial_sharpes: List[float],
    T: int,
    periods_per_year: float,
) -> dict:
    """Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

    Tests whether the best Sharpe from N trials is significantly above 0,
    accounting for multiple testing.

    Args:
        observed_sharpe: The Sharpe of the selected (best) configuration.
        all_trial_sharpes: Sharpes from ALL tested configurations.
        T: Number of return observations.
        periods_per_year: For annualization context (sharpes should already be annualized).

    Returns:
        dict with deflated_sharpe, p_value, expected_max_sharpe, n_trials.
    """
    n_trials = len(all_trial_sharpes)
    if n_trials < 2 or T < 10:
        return {"deflated_sharpe": observed_sharpe, "p_value": 0.0,
                "expected_max_sharpe": 0.0, "n_trials": n_trials}

    sharpe_std = float(np.std(all_trial_sharpes))
    if sharpe_std <= 0:
        sharpe_std = 0.01  # avoid division by zero

    # Expected maximum Sharpe under null (all Sharpes are noise)
    # E[max] ≈ std * [(1 - γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/(N*e))]
    # Simplified: E[max] ≈ sharpe_std * Z(1 - 1/N) for large N
    euler_mascheroni = 0.5772156649
    z_n = stats.norm.ppf(1 - 1.0 / n_trials) if n_trials > 1 else 0
    expected_max = sharpe_std * (
        (1 - euler_mascheroni) * z_n
        + euler_mascheroni * stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
    )

    # Standard error of Sharpe ratio
    se_sharpe = math.sqrt((1 + 0.5 * observed_sharpe**2) / T)

    # Deflated Sharpe = (observed - expected_max) / SE
    dsr = (observed_sharpe - expected_max) / se_sharpe if se_sharpe > 0 else 0.0

    # p-value: probability of observing this DSR under the null
    p_value = 1 - stats.norm.cdf(dsr)

    return {
        "deflated_sharpe": float(dsr),
        "p_value": float(p_value),
        "expected_max_sharpe": float(expected_max),
        "n_trials": n_trials,
    }


# ---------------------------------------------------------------------------
# Worst-Offender Analysis
# ---------------------------------------------------------------------------

def worst_trades(trades: List[Trade], n: int = 10) -> List[dict]:
    """Return the N trades with the largest absolute losses."""
    realized = [t for t in trades if t.realized_pnl < 0]
    realized.sort(key=lambda t: t.realized_pnl)
    results = []
    for t in realized[:n]:
        results.append({
            "bar_idx": t.bar_idx,
            "timestamp": str(t.timestamp),
            "symbol": t.symbol,
            "side": t.side,
            "signal": t.signal,
            "size_usd": t.size_usd,
            "realized_pnl": t.realized_pnl,
            "fill_px": t.fill_px,
            "metadata": t.metadata,
        })
    return results


def mae_analysis(
    trades: List[Trade],
    ohlcv_df: pd.DataFrame,
    n: int = 10,
) -> List[dict]:
    """Compute Maximum Adverse Excursion (MAE) for each round-trip trade.

    MAE = the deepest drawdown during a trade's holding period.
    Returns the N trades with the deepest MAE that did NOT hit the stop loss
    (i.e. survived and closed for other reasons).
    """
    # Build round trips: open -> close
    round_trips = []
    open_trade = None
    for t in trades:
        if t.old_position == 0.0 and t.new_position != 0.0:
            open_trade = t
        elif t.old_position != 0.0 and t.new_position == 0.0:
            if open_trade is not None:
                round_trips.append((open_trade, t))
            open_trade = None

    results = []
    for entry, exit_t in round_trips:
        # Skip stop-triggered exits (we want trades that survived)
        if exit_t.signal == "STOP_GAP":
            continue
        exit_reason = exit_t.metadata.get("exit_reason", "")
        if exit_reason == "trail_stop":
            continue

        # Get bars during holding period
        mask = (ohlcv_df.index >= entry.bar_idx) & (ohlcv_df.index <= exit_t.bar_idx)
        if not mask.any():
            # Try with bar_idx column if index doesn't match
            if "bar_idx" not in ohlcv_df.columns:
                holding = ohlcv_df.iloc[entry.bar_idx:exit_t.bar_idx + 1]
            else:
                continue
        else:
            holding = ohlcv_df.loc[mask]

        if holding.empty:
            continue

        is_long = entry.new_position > 0
        entry_px = entry.fill_px

        if is_long:
            worst_px = holding["low"].min()
            mae_pct = (entry_px - worst_px) / entry_px * 100.0
        else:
            worst_px = holding["high"].max()
            mae_pct = (worst_px - entry_px) / entry_px * 100.0

        results.append({
            "entry_bar": entry.bar_idx,
            "exit_bar": exit_t.bar_idx,
            "entry_timestamp": str(entry.timestamp),
            "exit_timestamp": str(exit_t.timestamp),
            "symbol": entry.symbol,
            "side": "LONG" if is_long else "SHORT",
            "entry_px": entry_px,
            "worst_px": worst_px,
            "mae_pct": mae_pct,
            "exit_pnl": exit_t.realized_pnl,
            "exit_reason": exit_reason,
            "holding_bars": exit_t.bar_idx - entry.bar_idx,
        })

    results.sort(key=lambda x: x["mae_pct"], reverse=True)
    return results[:n]


def missed_moves(
    ohlcv_df: pd.DataFrame,
    telemetry_df: "pd.DataFrame",
    top_n: int = 10,
    window: int = 6,
) -> List[dict]:
    """Identify large price moves where combined_score was below entry threshold.

    Scans for windows of `window` bars where price moved significantly
    but the strategy's combined score was in the deadzone.

    Args:
        ohlcv_df: OHLCV DataFrame with columns: timestamp, open, high, low, close.
        telemetry_df: Telemetry DataFrame with columns: timestamp, close,
                      final_combined (or combined), signal.
        top_n: Number of biggest missed moves to return.
        window: Rolling window in bars to measure price change.
    """
    if telemetry_df is None or telemetry_df.empty:
        return []

    df = telemetry_df.copy()
    if "final_combined" not in df.columns and "combined" not in df.columns:
        return []

    score_col = "final_combined" if "final_combined" in df.columns else "combined"

    # Rolling absolute return over `window` bars
    df["fwd_return_pct"] = df["close"].pct_change(window).shift(-window).abs() * 100.0

    # Filter: signal was HOLD (no entry) and score was weak
    hold_mask = df["signal"] == "HOLD"
    weak_mask = df[score_col].abs() < 0.3  # below typical entry threshold
    candidates = df[hold_mask & weak_mask].copy()

    if candidates.empty:
        return []

    candidates = candidates.dropna(subset=["fwd_return_pct"])
    candidates = candidates.sort_values("fwd_return_pct", ascending=False)

    results = []
    for _, row in candidates.head(top_n).iterrows():
        results.append({
            "timestamp": str(row.get("timestamp", "")),
            "close": row.get("close"),
            "fwd_return_pct": row["fwd_return_pct"],
            score_col: row[score_col],
            "signal": row["signal"],
            "bar_idx": row.get("bar_idx"),
        })
    return results


def worst_offender_report(
    trades: List[Trade],
    ohlcv_df: pd.DataFrame,
    telemetry_df: "pd.DataFrame" = None,
    n: int = 10,
) -> dict:
    """Generate a comprehensive worst-offender report.

    Returns dict with keys: worst_trades, mae_survivors, missed_moves.
    """
    report = {
        "worst_trades": worst_trades(trades, n),
        "mae_survivors": mae_analysis(trades, ohlcv_df, n),
    }
    if telemetry_df is not None:
        report["missed_moves"] = missed_moves(ohlcv_df, telemetry_df, n)
    else:
        report["missed_moves"] = []
    return report


def regime_split_sharpe(
    ohlcv_df: pd.DataFrame,
    equity_curve: pd.DataFrame,
    sma_period: int = 200,
    periods_per_year: float = 2190,
) -> dict:
    """Split equity curve returns into bull/bear regimes and compute Sharpe for each.

    Bull = close > SMA(sma_period), Bear = close < SMA(sma_period).
    """
    df = ohlcv_df.copy()
    df["sma"] = df["close"].rolling(sma_period).mean()
    df = df.dropna(subset=["sma"])

    ec = equity_curve[["timestamp", "equity"]].copy()
    ec["return"] = ec["equity"].pct_change()

    # Align regime labels to equity curve by timestamp
    regime_df = df[["timestamp", "close", "sma"]].copy()
    regime_df["regime"] = np.where(regime_df["close"] > regime_df["sma"], "bull", "bear")

    merged = pd.merge(ec, regime_df[["timestamp", "regime"]], on="timestamp", how="inner")
    merged = merged.dropna(subset=["return"])

    result = {}
    for regime in ["bull", "bear"]:
        subset = merged[merged["regime"] == regime]
        n = len(subset)
        if n < 10:
            result[regime] = {"sharpe": 0.0, "bars": n, "pct_of_total": 0.0}
            continue
        rets = subset["return"]
        s = float((rets.mean() / rets.std()) * math.sqrt(periods_per_year)) if rets.std() > 0 else 0.0
        result[regime] = {
            "sharpe": s,
            "bars": n,
            "pct_of_total": n / len(merged) * 100,
        }

    return result
