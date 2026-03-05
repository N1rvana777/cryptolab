#!/usr/bin/env python3
"""Bulk download BTC/ETH/SOL 4H data from 2021-01-01 to now."""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.manager import DataManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 2021-01-01 00:00:00 UTC in milliseconds
START_MS = 1609459200000

SYMBOLS = ["BTC", "ETH", "SOL"]
INTERVAL = "4h"
SOURCE = "okx"


def main():
    dm = DataManager()
    for sym in SYMBOLS:
        print(f"\n{'='*50}")
        print(f"Seeding {sym} {INTERVAL} from {SOURCE}...")
        print(f"{'='*50}")
        report = dm.seed(sym, INTERVAL, START_MS, source=SOURCE)
        print(report.summary())
        print()


if __name__ == "__main__":
    main()
