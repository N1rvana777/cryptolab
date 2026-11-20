#!/usr/bin/env python3
"""Fetch Fear & Greed Index history from alternative.me and save as CSV."""

import json
import urllib.request
import csv
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

URL = "https://api.alternative.me/fng/?limit=5000&format=json"

def main():
    print(f"Fetching FNG data from {URL} ...")
    req = urllib.request.Request(URL, headers={"User-Agent": "cryptolab/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode())

    data = raw.get("data", [])
    print(f"Received {len(data)} entries")

    if not data:
        print("ERROR: No data received")
        return

    # Parse and sort by date ascending
    rows = []
    for entry in data:
        ts = int(entry["timestamp"])
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "fng_value": int(entry["value"]),
            "fng_class": entry["value_classification"],
        })

    rows.sort(key=lambda r: r["date"])

    out_path = DATA_DIR / "fng_history.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "fng_value", "fng_class"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {out_path}")
    print(f"Date range: {rows[0]['date']} to {rows[-1]['date']}")


if __name__ == "__main__":
    main()
