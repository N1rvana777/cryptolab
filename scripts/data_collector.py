#!/usr/bin/env python3
"""Crypto data collection daemon — collects multi-source data on schedule.

Collects:
  - Hyperliquid: funding rates, open interest, orderbook depth (hourly)
  - Reddit: hot posts from crypto subreddits (hourly)
  - CryptoPanic: crypto news sentiment (hourly, needs API key)
  - Glassnode: on-chain metrics (daily, needs API key)
  - Whale Alert: large transfers (hourly, needs API key)
  - Coinglass: liquidation data (hourly, needs API key)

Usage:
    # Run once (test all collectors)
    python scripts/data_collector.py --once

    # Run continuously on schedule
    python scripts/data_collector.py

    # Run specific collector only
    python scripts/data_collector.py --once --only hl_funding

Storage: data/collection/ (SQLite databases per data type)
Config:  data/collection/collector_config.json (API keys)
Logs:    data/collection/collector_log.txt
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COLLECTION_DIR = Path(__file__).resolve().parent.parent / "data" / "collection"
COLLECTION_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = COLLECTION_DIR / "crypto_data.db"
CONFIG_PATH = COLLECTION_DIR / "collector_config.json"
LOG_PATH = COLLECTION_DIR / "collector_log.txt"

TRACKED_SYMBOLS = [
    "BTC", "ETH", "LTC", "TRX", "BCH", "DOT", "ADA", "LINK", "XLM", "XRP",
    "ETC", "ALGO", "ATOM", "AAVE", "SOL", "ICP", "UNI", "FIL", "AVAX", "NEAR",
    "SAND", "CRV", "MANA", "DOGE",
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger("collector")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    # Create template
    template = {
        "cryptopanic_api_key": "",
        "glassnode_api_key": "",
        "whale_alert_api_key": "",
        "coinglass_api_key": "",
    }
    CONFIG_PATH.write_text(json.dumps(template, indent=2))
    return template


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────
# Schema creation
# ─────────────────────────────────────────────────────────────

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS hl_funding (
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        funding_rate REAL,
        mark_price REAL,
        open_interest REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS hl_orderbook (
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        bid_prices TEXT,
        bid_sizes TEXT,
        ask_prices TEXT,
        ask_sizes TEXT,
        spread_bps REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reddit_posts (
        timestamp TEXT NOT NULL,
        subreddit TEXT NOT NULL,
        title TEXT,
        score INTEGER,
        num_comments INTEGER,
        upvote_ratio REAL,
        url TEXT,
        post_id TEXT,
        PRIMARY KEY (post_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cryptopanic_news (
        timestamp TEXT NOT NULL,
        title TEXT,
        url TEXT,
        source TEXT,
        currencies TEXT,
        votes_positive INTEGER,
        votes_negative INTEGER,
        post_id TEXT,
        PRIMARY KEY (post_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS glassnode_metrics (
        timestamp TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        symbol TEXT NOT NULL,
        value REAL,
        PRIMARY KEY (timestamp, metric_name, symbol)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS whale_transfers (
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        amount_usd REAL,
        from_type TEXT,
        to_type TEXT,
        tx_hash TEXT,
        PRIMARY KEY (tx_hash)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS coinglass_liquidations (
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        long_liquidations_usd REAL,
        short_liquidations_usd REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS fng_index (
        timestamp TEXT NOT NULL,
        value INTEGER,
        classification TEXT,
        PRIMARY KEY (timestamp)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS coingecko_prices (
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        price_usd REAL,
        market_cap REAL,
        volume_24h REAL,
        change_24h_pct REAL,
        PRIMARY KEY (timestamp, symbol)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS coingecko_global (
        timestamp TEXT NOT NULL,
        total_market_cap REAL,
        total_volume REAL,
        btc_dominance REAL,
        eth_dominance REAL,
        active_cryptocurrencies INTEGER,
        PRIMARY KEY (timestamp)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS collector_runs (
        timestamp TEXT NOT NULL,
        collector TEXT NOT NULL,
        status TEXT,
        rows_added INTEGER DEFAULT 0,
        error TEXT DEFAULT '',
        duration_ms INTEGER DEFAULT 0
    )""")

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# Collectors
# ─────────────────────────────────────────────────────────────

def collect_hl_funding():
    """Hyperliquid funding rates + open interest for all tracked symbols."""
    import requests

    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "metaAndAssetCtxs"}, timeout=15)
    resp.raise_for_status()
    meta, ctxs = resp.json()

    universe = meta.get("universe", [])
    name_to_ctx = {}
    for i, u in enumerate(universe):
        name = u.get("name")
        if name and i < len(ctxs):
            name_to_ctx[name] = ctxs[i]

    ts = utc_now()
    conn = get_db()
    rows = 0

    for sym in TRACKED_SYMBOLS:
        ctx = name_to_ctx.get(sym)
        if not ctx:
            continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO hl_funding VALUES (?, ?, ?, ?, ?)",
                (ts, sym,
                 float(ctx.get("funding", 0)),
                 float(ctx.get("markPx", 0)),
                 float(ctx.get("openInterest", 0))),
            )
            rows += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return rows


def collect_hl_orderbook():
    """Hyperliquid L2 orderbook snapshots (top 10 levels)."""
    import requests

    ts = utc_now()
    conn = get_db()
    rows = 0

    for sym in TRACKED_SYMBOLS:
        try:
            resp = requests.post("https://api.hyperliquid.xyz/info",
                                 json={"type": "l2Book", "coin": sym}, timeout=10)
            resp.raise_for_status()
            book = resp.json()
            levels = book.get("levels", [[], []])

            bids = levels[0][:10] if len(levels) > 0 else []
            asks = levels[1][:10] if len(levels) > 1 else []

            bid_pxs = json.dumps([float(b.get("px", 0)) for b in bids])
            bid_szs = json.dumps([float(b.get("sz", 0)) for b in bids])
            ask_pxs = json.dumps([float(a.get("px", 0)) for a in asks])
            ask_szs = json.dumps([float(a.get("sz", 0)) for a in asks])

            spread = 0
            if bids and asks:
                best_bid = float(bids[0].get("px", 0))
                best_ask = float(asks[0].get("px", 0))
                mid = (best_bid + best_ask) / 2
                spread = (best_ask - best_bid) / mid * 10000 if mid > 0 else 0

            conn.execute(
                "INSERT OR IGNORE INTO hl_orderbook VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ts, sym, bid_pxs, bid_szs, ask_pxs, ask_szs, round(spread, 2)),
            )
            rows += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return rows


def collect_reddit():
    """Reddit hot posts from crypto subreddits."""
    import urllib.request

    subreddits = ["cryptocurrency", "bitcoin", "ethtrader"]
    ts = utc_now()
    conn = get_db()
    rows = 0

    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            req = urllib.request.Request(url, headers={"User-Agent": "cryptolab-collector/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                post_id = post.get("id", "")
                if not post_id:
                    continue
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO reddit_posts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (ts, sub,
                         post.get("title", "")[:500],
                         int(post.get("score", 0)),
                         int(post.get("num_comments", 0)),
                         float(post.get("upvote_ratio", 0)),
                         post.get("url", "")[:500],
                         post_id),
                    )
                    rows += 1
                except sqlite3.IntegrityError:
                    pass
            time.sleep(1)  # rate limit
        except Exception as e:
            logger.warning(f"Reddit r/{sub} failed: {e}")

    conn.commit()
    conn.close()
    return rows


def collect_cryptopanic(api_key: str):
    """CryptoPanic news with sentiment votes."""
    if not api_key:
        raise ValueError("CryptoPanic API key not configured")

    import urllib.request

    url = f"https://cryptopanic.com/api/free/v1/posts/?auth_token={api_key}&public=true&kind=news"
    req = urllib.request.Request(url, headers={"User-Agent": "cryptolab/1.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())

    ts = utc_now()
    conn = get_db()
    rows = 0

    for post in data.get("results", []):
        post_id = str(post.get("id", ""))
        if not post_id:
            continue

        currencies = ",".join(c.get("code", "") for c in post.get("currencies", []))
        votes = post.get("votes", {})

        try:
            conn.execute(
                "INSERT OR IGNORE INTO cryptopanic_news VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (post.get("published_at", ts),
                 post.get("title", "")[:500],
                 post.get("url", "")[:500],
                 post.get("source", {}).get("title", ""),
                 currencies,
                 int(votes.get("positive", 0)),
                 int(votes.get("negative", 0)),
                 post_id),
            )
            rows += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return rows


def collect_glassnode(api_key: str):
    """Glassnode on-chain metrics (BTC only, free tier)."""
    if not api_key:
        raise ValueError("Glassnode API key not configured")

    import urllib.request

    metrics = [
        ("addresses/active_count", "active_addresses"),
        ("transactions/count", "transaction_count"),
        ("transactions/transfers_volume_sum", "transfer_volume"),
    ]

    ts = utc_now()
    conn = get_db()
    rows = 0

    for endpoint, metric_name in metrics:
        try:
            url = f"https://api.glassnode.com/v1/metrics/{endpoint}?a=BTC&api_key={api_key}&i=24h"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            if data and isinstance(data, list):
                latest = data[-1]
                conn.execute(
                    "INSERT OR IGNORE INTO glassnode_metrics VALUES (?, ?, ?, ?)",
                    (datetime.fromtimestamp(latest["t"], tz=timezone.utc).strftime("%Y-%m-%d"),
                     metric_name, "BTC", float(latest.get("v", 0))),
                )
                rows += 1
        except Exception as e:
            logger.warning(f"Glassnode {metric_name} failed: {e}")

    conn.commit()
    conn.close()
    return rows


def collect_whale_alert(api_key: str):
    """Whale Alert large crypto transfers."""
    if not api_key:
        raise ValueError("Whale Alert API key not configured")

    import urllib.request

    now = int(time.time())
    start = now - 3600  # last hour
    url = f"https://api.whale-alert.io/v1/transactions?api_key={api_key}&min_value=500000&start={start}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())

    conn = get_db()
    rows = 0

    for tx in data.get("transactions", []):
        symbol = tx.get("symbol", "").upper()
        if symbol not in ("BTC", "ETH"):
            continue
        tx_hash = tx.get("hash", "")
        if not tx_hash:
            continue

        try:
            conn.execute(
                "INSERT OR IGNORE INTO whale_transfers VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.fromtimestamp(tx.get("timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                 symbol,
                 float(tx.get("amount_usd", 0)),
                 tx.get("from", {}).get("owner_type", "unknown"),
                 tx.get("to", {}).get("owner_type", "unknown"),
                 tx_hash),
            )
            rows += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return rows


def collect_coinglass(api_key: str):
    """Coinglass liquidation data."""
    if not api_key:
        raise ValueError("Coinglass API key not configured")

    import urllib.request

    ts = utc_now()
    conn = get_db()
    rows = 0

    for sym in ["BTC", "ETH", "SOL", "XRP", "DOGE"]:
        try:
            url = f"https://open-api-v3.coinglass.com/api/futures/liquidation/v2/history?symbol={sym}&timeType=h1"
            req = urllib.request.Request(url, headers={
                "accept": "application/json",
                "CG-API-KEY": api_key,
            })
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for item in data.get("data", [])[:1]:
                conn.execute(
                    "INSERT OR IGNORE INTO coinglass_liquidations VALUES (?, ?, ?, ?)",
                    (ts, sym,
                     float(item.get("longLiquidationUsd", 0)),
                     float(item.get("shortLiquidationUsd", 0))),
                )
                rows += 1
        except Exception as e:
            logger.warning(f"Coinglass {sym} failed: {e}")

    conn.commit()
    conn.close()
    return rows


def collect_fng():
    """Fear & Greed Index from alternative.me (no API key needed)."""
    import urllib.request

    url = "https://api.alternative.me/fng/?limit=1&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "cryptolab/1.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())

    conn = get_db()
    rows = 0
    for entry in data.get("data", []):
        ts = datetime.fromtimestamp(int(entry["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO fng_index VALUES (?, ?, ?)",
                (ts, int(entry["value"]), entry["value_classification"]),
            )
            rows += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return rows


def collect_coingecko_prices():
    """CoinGecko prices, market cap, volume for tracked coins (no API key)."""
    import urllib.request

    # Map our symbols to CoinGecko IDs
    cg_ids = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
        "DOGE": "dogecoin", "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
        "DOT": "polkadot", "NEAR": "near", "ATOM": "cosmos", "FIL": "filecoin",
        "LTC": "litecoin", "BCH": "bitcoin-cash", "ETC": "ethereum-classic",
        "UNI": "uniswap", "AAVE": "aave", "CRV": "curve-dao-token",
        "ALGO": "algorand", "XLM": "stellar", "ICP": "internet-computer",
        "SAND": "the-sandbox", "MANA": "decentraland", "TRX": "tron",
    }

    ids_str = ",".join(cg_ids.values())
    url = (f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}"
           f"&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true")
    req = urllib.request.Request(url, headers={"User-Agent": "cryptolab/1.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())

    ts = utc_now()
    conn = get_db()
    rows = 0

    for sym, cg_id in cg_ids.items():
        info = data.get(cg_id)
        if not info:
            continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO coingecko_prices VALUES (?, ?, ?, ?, ?, ?)",
                (ts, sym,
                 float(info.get("usd", 0)),
                 float(info.get("usd_market_cap", 0)),
                 float(info.get("usd_24h_vol", 0)),
                 float(info.get("usd_24h_change", 0))),
            )
            rows += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return rows


def collect_coingecko_global():
    """CoinGecko global market data: total mcap, BTC dominance, etc."""
    import urllib.request

    url = "https://api.coingecko.com/api/v3/global"
    req = urllib.request.Request(url, headers={"User-Agent": "cryptolab/1.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read()).get("data", {})

    ts = utc_now()
    conn = get_db()

    try:
        conn.execute(
            "INSERT OR IGNORE INTO coingecko_global VALUES (?, ?, ?, ?, ?, ?)",
            (ts,
             float(data.get("total_market_cap", {}).get("usd", 0)),
             float(data.get("total_volume", {}).get("usd", 0)),
             float(data.get("market_cap_percentage", {}).get("btc", 0)),
             float(data.get("market_cap_percentage", {}).get("eth", 0)),
             int(data.get("active_cryptocurrencies", 0))),
        )
        conn.commit()
        conn.close()
        return 1
    except sqlite3.IntegrityError:
        conn.close()
        return 0


# ─────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────

HOURLY_COLLECTORS = [
    ("hl_orderbook", collect_hl_orderbook, False),
    ("reddit", collect_reddit, False),
]

DAILY_COLLECTORS = []


def run_collector(name, func, needs_key):
    """Run a single collector with error handling and logging."""
    t0 = time.time()
    try:
        if needs_key:
            cfg = load_config()
            key_name = f"{name}_api_key"
            # Check for matching key
            has_key = any(v for k, v in cfg.items() if name.split("_")[0] in k.lower() and v)
            if not has_key:
                logger.info(f"  [{name}] SKIPPED (no API key)")
                return "skipped", 0

        rows = func()
        elapsed = int((time.time() - t0) * 1000)
        logger.info(f"  [{name}] OK - {rows} rows ({elapsed}ms)")

        conn = get_db()
        conn.execute("INSERT INTO collector_runs VALUES (?, ?, ?, ?, ?, ?)",
                     (utc_now(), name, "ok", rows, "", elapsed))
        conn.commit()
        conn.close()
        return "ok", rows

    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        err = str(e)[:200]
        logger.error(f"  [{name}] FAILED - {err}")

        try:
            conn = get_db()
            conn.execute("INSERT INTO collector_runs VALUES (?, ?, ?, ?, ?, ?)",
                         (utc_now(), name, "error", 0, err, elapsed))
            conn.commit()
            conn.close()
        except Exception:
            pass
        return "error", 0


def run_all(only=None):
    """Run all collectors once."""
    ts = utc_now()
    hour = datetime.now(timezone.utc).hour

    logger.info(f"=== Collection run at {ts} ===")

    # Hourly collectors
    for name, func, needs_key in HOURLY_COLLECTORS:
        if only and name != only:
            continue
        run_collector(name, func, needs_key)

    # Daily collectors (run at UTC 00:xx)
    if hour == 0 or only:
        for name, func, needs_key in DAILY_COLLECTORS:
            if only and name != only:
                continue
            run_collector(name, func, needs_key)

    logger.info(f"=== Collection complete ===\n")


def run_daemon():
    """Run continuously, collecting every hour at :05."""
    logger.info("Data collector daemon started")
    logger.info(f"DB: {DB_PATH}")
    logger.info(f"Config: {CONFIG_PATH}")

    # Run immediately on start
    run_all()

    while True:
        try:
            now = datetime.now(timezone.utc)
            # Wait until next hour + 5 minutes
            minutes_to_wait = 60 - now.minute + 5
            if minutes_to_wait > 60:
                minutes_to_wait -= 60
            if now.minute >= 5 and now.minute < 10:
                # Just missed the window, wait for next hour
                minutes_to_wait = 60 - now.minute + 5

            logger.info(f"Next collection in {minutes_to_wait} minutes...")
            time.sleep(minutes_to_wait * 60)
            run_all()

        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
            break
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            time.sleep(300)  # wait 5 min and retry


def show_status():
    """Show collection status summary."""
    if not DB_PATH.exists():
        print("No database found. Run --once first.")
        return

    conn = get_db()

    tables = {
        "hl_funding": "timestamp",
        "hl_orderbook": "timestamp",
        "reddit_posts": "timestamp",
        "fng_index": "timestamp",
        "coingecko_prices": "timestamp",
        "coingecko_global": "timestamp",
        "cryptopanic_news": "timestamp",
        "glassnode_metrics": "timestamp",
        "whale_transfers": "timestamp",
        "coinglass_liquidations": "timestamp",
    }

    print(f"\n{'='*60}")
    print(f"  Data Collection Status")
    print(f"  DB: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.0f} KB)")
    print(f"{'='*60}")

    for table, ts_col in tables.items():
        try:
            row = conn.execute(f"SELECT COUNT(*), MAX({ts_col}) FROM {table}").fetchone()
            count, last_ts = row
            print(f"  {table:<30s} {count:>8d} rows  last: {last_ts or 'never'}")
        except Exception:
            print(f"  {table:<30s} (no data)")

    # Recent runs
    print(f"\n  Recent collector runs:")
    runs = conn.execute(
        "SELECT timestamp, collector, status, rows_added, duration_ms FROM collector_runs ORDER BY rowid DESC LIMIT 10"
    ).fetchall()
    for ts, name, status, rows, dur in runs:
        icon = "OK" if status == "ok" else ("--" if status == "skipped" else "XX")
        print(f"    [{icon}] {ts} {name:<15s} +{rows} rows ({dur}ms)")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Crypto data collector")
    parser.add_argument("--once", action="store_true", help="Run all collectors once then exit")
    parser.add_argument("--only", type=str, help="Run only this collector (e.g. hl_funding, reddit)")
    parser.add_argument("--status", action="store_true", help="Show collection status")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (default)")
    args = parser.parse_args()

    init_db()

    if args.status:
        show_status()
    elif args.once:
        run_all(only=args.only)
        show_status()
    else:
        run_daemon()


if __name__ == "__main__":
    main()
