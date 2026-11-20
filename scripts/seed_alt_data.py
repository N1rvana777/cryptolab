#!/usr/bin/env python3
"""Seed alternative data (funding rates) from Hyperliquid."""

import argparse
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.manager import DataManager
from cryptolab.data.types import HL_SYMBOL_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 2021-01-01 00:00:00 UTC in milliseconds
# Note: HL launched perps in ~mid 2023, so earlier data won't exist
START_MS = 1609459200000

DEFAULT_SYMBOLS = list(HL_SYMBOL_MAP.keys())


def main():
    parser = argparse.ArgumentParser(description="Seed alt data from Hyperliquid")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbols (default: all HL symbols)")
    parser.add_argument("--start-ms", type=int, default=START_MS)
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]
    dm = DataManager()

    for sym in symbols:
        print(f"\n{'='*50}")
        print(f"Seeding funding rates for {sym}...")
        print(f"{'='*50}")
        try:
            df = dm.seed_funding(sym, args.start_ms)
            if df.empty:
                print(f"  No funding data available for {sym}")
            else:
                print(f"  Cached {len(df)} funding records")
                print(f"  Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        except Exception as e:
            print(f"  Error: {e}")

    # Also fetch current meta snapshot (OI, mark price)
    print(f"\n{'='*50}")
    print("Fetching current market snapshot (OI, funding, mark prices)...")
    print(f"{'='*50}")
    try:
        meta = dm.get_meta_snapshot()
        # Filter to our symbols
        meta_filtered = meta[meta["symbol"].isin(symbols)]
        for _, row in meta_filtered.iterrows():
            print(f"  {row['symbol']:>5s}: mark={row['mark_px']:>12,.2f}  "
                  f"OI={row['open_interest']:>10,.2f}  "
                  f"funding={row['funding']:>10.6f}  "
                  f"24h_vol=${row['day_volume']:>14,.0f}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    main()
