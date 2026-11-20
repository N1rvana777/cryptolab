#!/usr/bin/env python3
"""Bulk download historical OHLCV data from OKX."""

import argparse
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.manager import DataManager
from cryptolab.data.types import OKX_SYMBOL_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 2021-01-01 00:00:00 UTC in milliseconds
START_MS = 1609459200000

DEFAULT_SYMBOLS = list(OKX_SYMBOL_MAP.keys())


def main():
    parser = argparse.ArgumentParser(description="Seed OHLCV cache from OKX")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbols (default: all 18)")
    parser.add_argument("--interval", type=str, default="1h",
                        help="Candle interval (default: 1h)")
    parser.add_argument("--source", type=str, default="okx",
                        help="Data source (default: okx)")
    parser.add_argument("--start-ms", type=int, default=START_MS,
                        help="Start timestamp in ms (default: 2021-01-01)")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]
    dm = DataManager()

    for sym in symbols:
        print(f"\n{'='*50}")
        print(f"Seeding {sym} {args.interval} from {args.source}...")
        print(f"{'='*50}")
        report = dm.seed(sym, args.interval, args.start_ms, source=args.source)
        print(report.summary())
        print()


if __name__ == "__main__":
    main()
