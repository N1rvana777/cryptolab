"""Slim utility helpers: time, file I/O, rounding, interval conversion."""

import os
import csv
import math
import time
from datetime import datetime, timezone


def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def utc_now_sec() -> int:
    return int(time.time())


def utc_now_ms() -> int:
    return int(time.time() * 1000)


def csv_append(path: str, header: list, row: list):
    exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(header)
        w.writerow(row)


def interval_to_ms(interval: str) -> int:
    interval = interval.strip().lower()
    if interval.endswith("m"):
        return int(interval[:-1]) * 60_000
    if interval.endswith("h"):
        return int(interval[:-1]) * 3_600_000
    if interval.endswith("d"):
        return int(interval[:-1]) * 86_400_000
    raise ValueError(f"Unsupported interval: {interval}")


def interval_to_sec(interval: str) -> int:
    return interval_to_ms(interval) // 1000


def round_size(size: float, sz_decimals: int) -> float:
    if sz_decimals < 0:
        return size
    factor = 10 ** sz_decimals
    return math.floor(size * factor) / factor
