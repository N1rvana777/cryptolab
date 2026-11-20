"""Tests for observability and defensive guardrail modules."""

import json
import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from cryptolab.config import Config
from cryptolab.backtest.engine import BacktestEngine, Trade
from cryptolab.backtest.telemetry import TelemetryRecorder, TelemetrySnapshot
from cryptolab.backtest.metrics import worst_trades, mae_analysis, missed_moves
from cryptolab.backtest.bias_audit import audit_fill_timing, run_full_audit
from cryptolab.backtest.regime_monitor import (
    compute_rolling_sharpe, scan_regime_warnings, regime_summary,
    RegimeMonitorConfig,
)
from cryptolab.execution.kill_switch import KillSwitch, SystemMode, HealthState
from cryptolab.execution.hl_client import APIError
from cryptolab.strategy.donchian_mtf import DonchianMTF


def _make_ohlcv(n=300, start_price=100.0, seed=42):
    """Generate synthetic OHLCV data for testing."""
    rng = np.random.default_rng(seed)
    prices = [start_price]
    for _ in range(n - 1):
        ret = rng.normal(0.001, 0.02)
        prices.append(prices[-1] * (1 + ret))

    rows = []
    for i, p in enumerate(prices):
        h = p * (1 + rng.uniform(0, 0.015))
        l = p * (1 - rng.uniform(0, 0.015))
        o = p * (1 + rng.normal(0, 0.005))
        v = rng.uniform(100, 1000)
        rows.append({
            "timestamp": pd.Timestamp("2022-01-01") + pd.Timedelta(hours=4 * i),
            "open": o, "high": h, "low": l, "close": p, "volume": v,
        })
    return pd.DataFrame(rows)


def _run_backtest(n=300):
    """Run a backtest and return result + ohlcv_df."""
    df = _make_ohlcv(n)
    cfg = Config(
        initial_capital=10000,
        mtf_lookbacks=[24, 72, 168],
        mtf_weights=[0.33, 0.34, 0.33],
    )
    strategy = DonchianMTF(cfg)
    engine = BacktestEngine(strategy, cfg)
    result = engine.run("TEST", df)
    return result, df


# --- Telemetry Tests ---

class TestTelemetry:
    def test_telemetry_records_every_bar(self):
        result, df = _run_backtest()
        assert result.telemetry is not None
        # Should have a snapshot for every bar
        assert len(result.telemetry.snapshots) == len(df)

    def test_telemetry_snapshot_has_key_fields(self):
        result, _ = _run_backtest()
        snap = result.telemetry.snapshots[50]  # pick a bar well past warmup
        d = snap.to_dict()
        assert "close" in d
        assert "equity" in d
        assert "signal" in d
        assert "position_usd" in d

    def test_telemetry_jsonl_roundtrip(self):
        result, _ = _run_backtest()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = result.telemetry.save_jsonl(tmpdir, "TEST", "2022-01-01", "2022-03-01")
            assert os.path.exists(path)

            # Read back and verify
            with open(path, "r") as f:
                lines = f.readlines()
            assert len(lines) == len(result.telemetry.snapshots)

            first = json.loads(lines[0])
            assert first["symbol"] == "TEST"
            assert "close" in first

    def test_action_snapshots_filter(self):
        result, _ = _run_backtest()
        actions = result.telemetry.action_snapshots()
        for a in actions:
            assert a.signal in ("LONG", "SHORT", "CLOSE") or \
                   (a.signal == "HOLD" and a.metadata.get("pyramid_add"))

    def test_actions_jsonl_subset(self):
        result, _ = _run_backtest()
        with tempfile.TemporaryDirectory() as tmpdir:
            full_path = result.telemetry.save_jsonl(tmpdir, "T", "a", "b")
            act_path = result.telemetry.save_actions_jsonl(tmpdir, "T", "a", "b")

            with open(full_path) as f:
                full_count = sum(1 for _ in f)
            with open(act_path) as f:
                act_count = sum(1 for _ in f)

            assert act_count <= full_count


# --- Worst-Offender Tests ---

class TestWorstOffender:
    def test_worst_trades(self):
        result, _ = _run_backtest()
        wt = worst_trades(result.trades, n=5)
        # All returned trades should have negative PnL
        for t in wt:
            assert t["realized_pnl"] < 0
        # Should be sorted by PnL ascending (worst first)
        if len(wt) >= 2:
            assert wt[0]["realized_pnl"] <= wt[1]["realized_pnl"]

    def test_mae_analysis(self):
        result, df = _run_backtest()
        mae = mae_analysis(result.trades, df, n=5)
        for m in mae:
            assert m["mae_pct"] >= 0
            assert m["holding_bars"] > 0

    def test_missed_moves_needs_telemetry(self):
        result, df = _run_backtest()
        # Without telemetry df, returns empty
        assert missed_moves(df, None) == []


# --- Bias Audit Tests ---

class TestBiasAudit:
    def test_fill_timing_audit_passes(self):
        result, df = _run_backtest()
        violations = audit_fill_timing(result, df)
        assert len(violations) == 0, f"Fill timing violations: {violations}"

    def test_full_audit_clean(self):
        result, df = _run_backtest()
        report = run_full_audit(result, df)
        assert report["status"] == "CLEAN", f"Audit violations: {report}"


# --- Regime Monitor Tests ---

class TestRegimeMonitor:
    def test_rolling_sharpe_length(self):
        result, _ = _run_backtest()
        eq = result.equity_curve["equity"]
        sharpe = compute_rolling_sharpe(eq, window=42)
        assert len(sharpe) == len(eq)

    def test_scan_returns_warnings(self):
        # Use a longer series to ensure ADX can be computed
        result, df = _run_backtest(n=500)
        config = RegimeMonitorConfig(adx_rolling_window=42, sharpe_rolling_window=42)
        warnings = scan_regime_warnings(df, result.equity_curve, "TEST", config)
        # Just verify it runs and returns the right type
        assert isinstance(warnings, list)
        for w in warnings:
            assert w.warning_type in ("LOW_ADX", "NEGATIVE_SHARPE", "BOTH")

    def test_regime_summary(self):
        result, df = _run_backtest(n=500)
        config = RegimeMonitorConfig(adx_rolling_window=42, sharpe_rolling_window=42)
        warnings = scan_regime_warnings(df, result.equity_curve, "TEST", config)
        summary = regime_summary(warnings)
        assert "total_warnings" in summary


# --- Kill Switch Tests ---

class TestKillSwitch:
    def test_initial_state_normal(self):
        ks = KillSwitch()
        assert ks.mode == SystemMode.NORMAL
        assert ks.is_trading_allowed()

    def test_api_failures_trigger_reduce_only(self):
        ks = KillSwitch(max_api_failures=3)
        ks.record_api_failure("timeout")
        ks.record_api_failure("timeout")
        assert ks.mode == SystemMode.NORMAL
        ks.record_api_failure("timeout")  # 3rd failure
        assert ks.mode == SystemMode.REDUCE_ONLY
        assert not ks.is_trading_allowed()

    def test_success_resets_counter(self):
        ks = KillSwitch(max_api_failures=3)
        ks.record_api_failure("err")
        ks.record_api_failure("err")
        ks.record_success()
        assert ks.health.consecutive_api_failures == 0
        ks.record_api_failure("err")
        assert ks.mode == SystemMode.NORMAL  # only 1 failure since reset

    def test_validate_candles_clean(self):
        df = _make_ohlcv(50)
        ks = KillSwitch()
        assert ks.validate_candles(df) is True

    def test_validate_candles_nan_triggers(self):
        df = _make_ohlcv(50)
        df.loc[10, "close"] = np.nan
        ks = KillSwitch(max_data_errors=1)
        assert ks.validate_candles(df) is False

    def test_validate_candles_empty_triggers(self):
        ks = KillSwitch(max_data_errors=1)
        assert ks.validate_candles(pd.DataFrame()) is False

    def test_sentinel_file_halts(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix="_KILL") as f:
            sentinel = f.name
        try:
            ks = KillSwitch(sentinel_path=sentinel)
            assert not ks.is_trading_allowed()
            assert ks.mode == SystemMode.HALTED
        finally:
            os.unlink(sentinel)

    def test_manual_reset(self):
        ks = KillSwitch(max_api_failures=1)
        ks.record_api_failure("err")
        assert ks.mode == SystemMode.REDUCE_ONLY
        ks.reset()
        assert ks.mode == SystemMode.NORMAL

    def test_api_error_class(self):
        err = APIError("timeout", status_code=504)
        assert err.status_code == 504
        assert "timeout" in str(err)
