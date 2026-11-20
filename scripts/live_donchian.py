#!/usr/bin/env python3
"""DonchianMTF 实盘交易入口。

用法:
  # Dry-run 模式（默认，不会真正下单）
  python scripts/live_donchian.py

  # 真实交易
  python scripts/live_donchian.py --live

  # 自定义币种和配置
  python scripts/live_donchian.py --symbols BTC:G,SOL:G,ADA:G,XRP:F --leverage 3.0

  # 立即执行一次（不等待4H收盘）
  python scripts/live_donchian.py --run-once

通过 tmux 保持运行:
  wsl
  tmux new -s trading
  cd /mnt/c/Users/n1rva/projects/cryptolab
  python scripts/live_donchian.py --live
  # Ctrl+B D 断开
  # tmux attach -t trading 重新连接
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.config import Config
from cryptolab.execution.orchestrator import (
    LiveOrchestrator, SymbolConfig, MTF_COMBO_MAP,
)

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"


def parse_symbol_combos(spec: str) -> list[SymbolConfig]:
    """Parse 'BTC:G,SOL:G,ADA:G,XRP:F' into SymbolConfig list."""
    configs = []
    for part in spec.split(","):
        part = part.strip()
        if ":" in part:
            sym, combo = part.split(":", 1)
        else:
            sym, combo = part, "G"
        combo = combo.upper()
        if combo not in MTF_COMBO_MAP:
            print(f"Unknown combo '{combo}' for {sym}, using G")
            combo = "G"
        configs.append(SymbolConfig(
            symbol=sym.upper(),
            combo=combo,
            lookbacks=MTF_COMBO_MAP[combo],
        ))
    return configs


def main():
    parser = argparse.ArgumentParser(
        description="DonchianMTF live trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # B0 combo (36/60/336 = 12d/20d/112d at 8H) for all 28 coins
    default_symbols = ",".join(f"{s}:B0" for s in [
        "BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
        "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
        "CRV","DOGE","AXS","YGG","CELO","GALA","SAND","PEOPLE",
    ])
    parser.add_argument(
        "--symbols", type=str, default=default_symbols,
        help="Comma-separated SYMBOL:COMBO pairs",
    )
    parser.add_argument("--leverage", type=float, default=3.0)
    parser.add_argument("--live", action="store_true", help="Enable real trading (default: dry-run)")
    parser.add_argument("--run-once", action="store_true", help="Run one cycle immediately then exit")
    parser.add_argument("--run-dir", type=str, default=None, help="Override run directory")
    parser.add_argument("--poll-sec", type=int, default=30, help="Poll interval in seconds")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    parser.add_argument("--enable-pm", action="store_true",
                        help="Enable Portfolio Manager (regime-based Donchian+MeanRev switching)")
    args = parser.parse_args()

    # Setup logging
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(level=log_level, format=LOG_FORMAT)
    # Quiet noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("hyperliquid").setLevel(logging.WARNING)

    # Parse symbols
    symbol_configs = parse_symbol_combos(args.symbols)

    # Load MR params if PM enabled
    if args.enable_pm:
        mr_params_path = os.path.join("sweep_results", "meanrev_experiment.json")
        if os.path.exists(mr_params_path):
            import json
            with open(mr_params_path) as f:
                mr_data = json.load(f)
            mr_params = mr_data.get("meanrev_best_params", {})
            for sc in symbol_configs:
                p = mr_params.get(sc.symbol)
                if p and len(p) == 4:
                    sc.mr_lookback = p[0]
                    sc.mr_entry_z = p[1]
                    sc.mr_exit_z = p[2]
                    sc.mr_stop_z = p[3]
            n_mr = sum(1 for sc in symbol_configs if sc.mr_lookback is not None)
            print(f"  PM enabled: {n_mr}/{len(symbol_configs)} coins with MR params")
        else:
            print(f"  WARNING: {mr_params_path} not found, PM disabled")
            args.enable_pm = False

    # Config
    cfg = Config()
    cfg.symbols = [sc.symbol for sc in symbol_configs]
    cfg.interval = "4h"
    cfg.leverage = args.leverage
    cfg.dry_run = not args.live
    cfg.candle_lookback = 600  # enough for longest lookback (504) + warmup

    # Run directory
    if args.run_dir:
        run_dir = args.run_dir
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        mode = "live" if args.live else "dry"
        run_dir = os.path.join("runs", f"{ts}_{mode}_donchian")

    # Banner
    print("=" * 60)
    print(f"  DonchianMTF Live Trading")
    print(f"  Mode:     {'LIVE' if args.live else 'DRY-RUN'}")
    print(f"  Symbols:  {', '.join(f'{sc.symbol}({sc.combo})' for sc in symbol_configs)}")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Run dir:  {run_dir}")
    print("=" * 60)

    if args.live:
        print("\n  *** LIVE TRADING MODE ***")
        print("  Real orders will be placed on Hyperliquid.")
        print("  Press Ctrl+C to stop.\n")

    # Also log to file
    file_handler = logging.FileHandler(os.path.join(run_dir, "trading.log") if os.path.isdir(run_dir) else "trading.log")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(file_handler)

    # Initialize
    orch = LiveOrchestrator(
        cfg=cfg,
        symbol_configs=symbol_configs,
        run_dir=run_dir,
        poll_interval_sec=args.poll_sec,
        enable_pm=args.enable_pm,
    )

    # File handler needs run_dir to exist (created by init)
    orch.init()

    # Move file handler to correct location
    logging.getLogger().removeHandler(file_handler)
    log_path = os.path.join(run_dir, "trading.log")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(file_handler)

    if args.run_once:
        print("\n  Running one cycle immediately...")
        orch.run_once()
        status = orch.status()
        print(f"\n  Equity: ${status['equity']:.2f}")
        print(f"  Positions: {status['positions']}")
        print(f"  Mode: {status['mode']}")
    else:
        orch.run_forever()


if __name__ == "__main__":
    main()
