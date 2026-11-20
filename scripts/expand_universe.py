#!/usr/bin/env python3
"""Expand coin universe: scan HL, seed OKX data, catalog available coins.

Steps:
1. Get all HL perps with >100K daily volume
2. Exclude stablecoins, wrapped tokens, <6 months listed
3. For each candidate: check OKX 1H data, seed if missing
4. For coins not on OKX: fetch HL 4H candles as backup
5. Output full catalog of available coins with data ranges
"""

import sys, os, time, json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.execution.hl_client import (
    init_hl_sdk, fetch_meta_and_asset_ctxs, build_perp_maps, get_closed_candles,
)
from cryptolab.data.cache import ParquetCache
from cryptolab.data.manager import DataManager
from cryptolab.data.types import OKX_SYMBOL_MAP

STABLES = {'USDT','USDC','DAI','TUSD','BUSD','FRAX','LUSD','SUSD','USDP',
           'PYUSD','FDUSD','USDD','CRVUSD','GHO','USDE','USTC','STBL','STABLE'}
WRAPPED = {'WBTC','WETH','WSTETH','STETH','CBETH','RETH','SFRXETH','MSOL',
           'BSOL','JITOSOL','RESOLV'}
# Coins with k prefix on HL (mapped to different OKX names)
K_PREFIX_MAP = {'kPEPE': 'PEPE', 'kBONK': 'BONK', 'kSHIB': 'SHIB', 'kFLOKI': 'FLOKI', 'kLUNC': 'LUNC'}

SIX_MONTHS_MS = 6 * 30 * 24 * 3600 * 1000


def main():
    cache = ParquetCache()
    dm = DataManager()
    exchange, info, addr = init_hl_sdk()

    print("Step 1: Scanning HL universe...")
    meta, ctxs = fetch_meta_and_asset_ctxs()
    universe_map, ctx_map = build_perp_maps(meta, ctxs)

    now_ms = int(time.time() * 1000)
    candidates = []
    for coin, ctx in ctx_map.items():
        vol = float(ctx.get('dayNtlVlm', 0))
        if vol < 100_000: continue
        if coin.upper() in STABLES: continue
        if coin.upper() in WRAPPED: continue
        candidates.append((coin, vol))

    candidates.sort(key=lambda x: -x[1])
    print(f"  {len(candidates)} candidates (>100K vol, non-stable/wrapped)")

    # Step 2: Check HL listing age via candle history
    print("\nStep 2: Checking listing age and data availability...")
    catalog = []

    for ci, (coin, vol) in enumerate(candidates):
        # Rate limiting
        if ci > 0 and ci % 10 == 0:
            time.sleep(1)

        # Check HL candle history (get earliest available)
        try:
            candles = get_closed_candles(info, coin, '4h', 5000)
            hl_bars_4h = len(candles) if candles else 0
            if candles:
                hl_start_ms = int(candles[0]['t'])
                hl_start = datetime.fromtimestamp(hl_start_ms / 1000).strftime('%Y-%m-%d')
                age_ms = now_ms - hl_start_ms
            else:
                hl_start = 'N/A'
                age_ms = 0
        except Exception:
            hl_bars_4h = 0; hl_start = 'error'; age_ms = 0
            time.sleep(0.5)

        if age_ms < SIX_MONTHS_MS:
            # Listed less than 6 months, skip
            catalog.append({
                'coin': coin, 'hl_vol_24h': vol, 'hl_start': hl_start,
                'hl_bars_4h': hl_bars_4h, 'status': 'TOO_NEW', 'okx_bars_1h': 0,
                'okx_start': 'N/A',
            })
            continue

        # Check OKX data
        okx_name = K_PREFIX_MAP.get(coin, coin)
        okx_df = cache.read('okx', okx_name, '1h')
        okx_bars = len(okx_df) if okx_df is not None and not okx_df.empty else 0
        okx_start = str(okx_df['timestamp'].min())[:10] if okx_bars > 0 else 'N/A'

        catalog.append({
            'coin': coin, 'hl_vol_24h': vol, 'hl_start': hl_start,
            'hl_bars_4h': hl_bars_4h, 'okx_bars_1h': okx_bars,
            'okx_start': okx_start,
            'okx_name': okx_name,
            'status': 'HAS_OKX' if okx_bars > 1000 else 'NEED_SEED',
        })

        if (ci + 1) % 20 == 0:
            print(f"    {ci+1}/{len(candidates)} checked...", flush=True)

    # Summary
    has_okx = [c for c in catalog if c['status'] == 'HAS_OKX']
    need_seed = [c for c in catalog if c['status'] == 'NEED_SEED']
    too_new = [c for c in catalog if c['status'] == 'TOO_NEW']

    print(f"\n  Results:")
    print(f"    Already have OKX data: {len(has_okx)}")
    print(f"    Need to seed from OKX: {len(need_seed)}")
    print(f"    Too new (<6 months): {len(too_new)}")

    # Step 3: Try to seed missing coins from OKX
    print(f"\nStep 3: Seeding missing OKX data for {len(need_seed)} coins...")

    # Check which ones are in OKX_SYMBOL_MAP
    for entry in need_seed:
        okx_name = entry.get('okx_name', entry['coin'])
        # Try to find OKX instrument ID
        okx_id = OKX_SYMBOL_MAP.get(okx_name)
        if okx_id:
            entry['has_okx_pair'] = True
            print(f"  {entry['coin']} -> OKX {okx_id}: seeding...", end=" ", flush=True)
            try:
                dm.seed(okx_name, '1h', start_ms=1609459200000)  # 2021-01-01
                df = cache.read('okx', okx_name, '1h')
                bars = len(df) if df is not None and not df.empty else 0
                entry['okx_bars_1h'] = bars
                if bars > 1000:
                    entry['status'] = 'HAS_OKX'
                    entry['okx_start'] = str(df['timestamp'].min())[:10]
                    print(f"{bars} bars from {entry['okx_start']}", flush=True)
                else:
                    print(f"only {bars} bars", flush=True)
            except Exception as e:
                print(f"failed: {e}", flush=True)
                entry['has_okx_pair'] = False
        else:
            entry['has_okx_pair'] = False
            print(f"  {entry['coin']}: not in OKX_SYMBOL_MAP, will use HL data only")

    # Step 4: For coins without OKX, save HL candles to cache
    hl_only = [c for c in catalog if c['status'] == 'NEED_SEED' and not c.get('has_okx_pair')]
    print(f"\nStep 4: Fetching HL candles for {len(hl_only)} OKX-unavailable coins...")

    for entry in hl_only:
        coin = entry['coin']
        if entry['hl_bars_4h'] < 100:
            print(f"  {coin}: too few HL bars ({entry['hl_bars_4h']}), skip")
            continue

        try:
            candles = get_closed_candles(info, coin, '4h', 5000)
            if not candles:
                continue

            df = pd.DataFrame([{
                'timestamp': pd.Timestamp(int(c['t']), unit='ms'),
                'open': float(c['o']),
                'high': float(c['h']),
                'low': float(c['l']),
                'close': float(c['c']),
                'volume': float(c['v']),
            } for c in candles])

            # Save to cache as hl_{coin}_4h
            cache.write('hl', coin, '4h', df)
            entry['status'] = 'HAS_HL'
            entry['hl_saved'] = True
            print(f"  {coin}: saved {len(df)} HL 4H bars", flush=True)
            time.sleep(0.3)
        except Exception as e:
            print(f"  {coin}: HL fetch failed: {e}")

    # Final catalog
    usable = [c for c in catalog if c['status'] in ('HAS_OKX', 'HAS_HL')]
    print(f"\n{'='*70}")
    print(f"FINAL CATALOG: {len(usable)} usable coins")
    print(f"{'='*70}")
    print(f"{'Coin':<10} {'HL Vol':>10} {'Source':>8} {'Start':>12} {'Bars':>8}")
    print('-' * 52)
    for c in sorted(usable, key=lambda x: -x['hl_vol_24h']):
        vol = f"{c['hl_vol_24h']/1e6:.1f}M" if c['hl_vol_24h'] >= 1e6 else f"{c['hl_vol_24h']/1e3:.0f}K"
        src = 'OKX' if c['status'] == 'HAS_OKX' else 'HL'
        start = c['okx_start'] if c['status'] == 'HAS_OKX' else c['hl_start']
        bars = c['okx_bars_1h'] if c['status'] == 'HAS_OKX' else c['hl_bars_4h']
        print(f"{c['coin']:<10} {vol:>10} {src:>8} {start:>12} {bars:>8}")

    # Save catalog
    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/coin_catalog.json", "w") as f:
        json.dump(catalog, f, indent=2, default=str)
    print(f"\nCatalog saved to sweep_results/coin_catalog.json")


if __name__ == "__main__":
    main()
