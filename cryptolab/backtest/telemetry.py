"""Decision telemetry: capture full state snapshots at every signal event.

Writes JSONL files to telemetry_logs/ for post-mortem analysis and
interactive visualization.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from cryptolab.strategy.base import StrategySignal


class TelemetrySnapshot:
    """A single decision snapshot capturing the full state at signal time."""

    __slots__ = (
        "bar_idx", "timestamp", "symbol", "open", "high", "low", "close",
        "volume", "equity", "position_usd", "signal", "target_position",
        "confidence", "suggested_stop_px", "metadata",
    )

    def __init__(
        self,
        bar_idx: int,
        timestamp: str,
        symbol: str,
        ohlcv: dict,
        equity: float,
        position_usd: float,
        signal: "StrategySignal",
    ):
        self.bar_idx = bar_idx
        self.timestamp = str(timestamp)
        self.symbol = symbol
        self.open = ohlcv.get("open")
        self.high = ohlcv.get("high")
        self.low = ohlcv.get("low")
        self.close = ohlcv.get("close")
        self.volume = ohlcv.get("volume")
        self.equity = equity
        self.position_usd = position_usd
        self.signal = signal.signal
        self.target_position = signal.target_position
        self.confidence = signal.confidence
        self.suggested_stop_px = signal.suggested_stop_px
        self.metadata = signal.metadata

    def to_dict(self) -> dict:
        return {
            "bar_idx": self.bar_idx,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "equity": self.equity,
            "position_usd": self.position_usd,
            "signal": self.signal,
            "target_position": self.target_position,
            "confidence": self.confidence,
            "suggested_stop_px": self.suggested_stop_px,
            **self.metadata,
        }

    def to_json(self) -> str:
        d = self.to_dict()
        # Convert any non-serializable values
        for k, v in d.items():
            if isinstance(v, float) and (v != v):  # NaN check
                d[k] = None
        return json.dumps(d, default=str)


class TelemetryRecorder:
    """Collects snapshots during a backtest run and writes JSONL output."""

    def __init__(self):
        self.snapshots: List[TelemetrySnapshot] = []

    def record(
        self,
        bar_idx: int,
        timestamp,
        symbol: str,
        bar_data: dict,
        equity: float,
        position_usd: float,
        signal: "StrategySignal",
    ):
        snap = TelemetrySnapshot(
            bar_idx=bar_idx,
            timestamp=timestamp,
            symbol=symbol,
            ohlcv=bar_data,
            equity=equity,
            position_usd=position_usd,
            signal=signal,
        )
        self.snapshots.append(snap)

    def action_snapshots(self) -> List[TelemetrySnapshot]:
        """Return only snapshots where an actual trade signal was generated
        (LONG, SHORT, CLOSE, or HOLD with pyramid_add)."""
        result = []
        for s in self.snapshots:
            if s.signal in ("LONG", "SHORT", "CLOSE"):
                result.append(s)
            elif s.signal == "HOLD" and s.metadata.get("pyramid_add"):
                result.append(s)
        return result

    def save_jsonl(self, output_dir: str, symbol: str, start_date: str, end_date: str):
        """Write all snapshots to a JSONL file in output_dir."""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"telemetry_{symbol}_{start_date}_{end_date}.jsonl"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for snap in self.snapshots:
                f.write(snap.to_json() + "\n")

        return filepath

    def save_actions_jsonl(self, output_dir: str, symbol: str, start_date: str, end_date: str):
        """Write only action snapshots (entries/exits/pyramids) to JSONL."""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"actions_{symbol}_{start_date}_{end_date}.jsonl"
        filepath = os.path.join(output_dir, filename)

        actions = self.action_snapshots()
        with open(filepath, "w", encoding="utf-8") as f:
            for snap in actions:
                f.write(snap.to_json() + "\n")

        return filepath
