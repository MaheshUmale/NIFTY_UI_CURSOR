"""CLI runner for backtesting with real historical data.

Usage:
    python run_backtest.py --date 20260505
    python run_backtest.py --date 20260505 --capital 500000
    python run_backtest.py --all --output results.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backtest.data_loader import DuckDBLoader
from src.backtest.engine import BacktestEngine, BacktestResult
from src.utils.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def run_single_backtest(
    data_dir: str,
    date_str: str,
    capital: float = 200_000.0,
) -> BacktestResult | None:
    """Run backtest on a single weekly expiry file."""
    loader = DuckDBLoader(data_dir)

    # Load spot data
    data = loader.load_week(date_str)
    if not data:
        logger.warning("No data for date: %s", date_str)
        return None

    spot_df = data["spot_data"]
    options_df = data["options_data"]
    metadata = data["metadata"]

    logger.info(
        "Loaded %s: %d spot rows, %d options rows, strikes=%s",
        date_str, metadata["spot_rows"], metadata["options_rows"],
        len(metadata["strikes"]),
    )

    # Convert spot data to ticks
    ticks = []
    for _, row in spot_df.iterrows():
        tick = {
            "symbol": "NIFTY",
            "last_price": float(row.get("Close", 0.0)),
            "volume": int(row.get("Volume", 0)),
            "oi": 0,
            "timestamp": str(row.get("Timestamp", "")),
            "open": float(row.get("Open", 0.0)),
            "high": float(row.get("High", 0.0)),
            "low": float(row.get("Low", 0.0)),
            "close": float(row.get("Close", 0.0)),
        }
        ticks.append(tick)

    if not ticks:
        logger.warning("No ticks generated for date: %s", date_str)
        return None

    # Run backtest
    engine = BacktestEngine(capital=capital)
    result = engine.run(ticks)

    return result


def print_results(result: BacktestResult, date_str: str) -> None:
    """Print formatted backtest results."""
    print(f"\n{'='*60}")
    print(f"  BACKTEST RESULTS — {date_str}")
    print(f"{'='*60}")
    print(f"  Capital:       ₹{result.config.get('capital', 0):,.0f}")
    print(f"  Bars Processed: {result.total_bars_processed}")
    print(f"{'─'*60}")
    print(f"  Total Trades:  {result.total_trades}")
    print(f"  Winning:        {result.winning_trades}")
    print(f"  Losing:         {result.losing_trades}")
    print(f"  Win Rate:       {result.win_rate*100:.1f}%")
    print(f"{'─'*60}")
    print(f"  Total P&L:      ₹{result.total_pnl:,.2f}")
    print(f"  Avg P&L/Trade:  ₹{result.avg_pnl_per_trade:,.2f}")
    print(f"  Max Win:        ₹{result.max_win:,.2f}")
    print(f"  Max Loss:       ₹{result.max_loss:,.2f}")
    print(f"  Profit Factor:  {result.profit_factor:.2f}")
    print(f"{'─'*60}")
    print(f"  Max Drawdown:   ₹{result.max_drawdown:,.2f} ({result.max_drawdown_pct*100:.2f}%)")
    print(f"  Sharpe Ratio:   {result.sharpe_ratio:.2f}")
    print(f"  Sortino Ratio:  {result.sortino_ratio:.2f}")
    print(f"  Avg Hold (bars): {result.avg_holding_period_bars:.1f}")
    print(f"{'='*60}")

    if result.trades:
        print(f"\n  TRADE LOG ({len(result.trades)} trades):")
        print(f"  {'Tag':<10} {'Side':<6} {'Entry':>10} {'Exit':>10} {'Qty':>5} {'P&L':>12} {'P&L%':>8}")
        print(f"  {'─'*63}")
        for t in result.trades:
            print(
                f"  {t.tag:<10} {t.side:<6} {t.entry_price:>10.2f} "
                f"{t.exit_price:>10.2f} {t.qty:>5} "
                f"₹{t.pnl:>10,.2f} {t.pnl_pct*100:>7.2f}%"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NIFTY backtest")
    parser.add_argument("--date", type=str, help="Date string (YYYYMMDD) for weekly expiry")
    parser.add_argument("--all", action="store_true", help="Run backtest on all available files")
    parser.add_argument("--data-dir", type=str, default="D:\\OPTIONS_DATA", help="Data directory")
    parser.add_argument("--capital", type=float, default=200_000.0, help="Starting capital")
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument("--recent", type=int, default=5, help="Number of recent weeks to backtest")
    args = parser.parse_args()

    loader = DuckDBLoader(args.data_dir)

    if args.all:
        files = loader.list_files()
        # Use most recent N weeks
        files = files[-args.recent:] if len(files) > args.recent else files

        all_results = []
        total_pnl = 0.0
        total_trades = 0

        for f in files:
            date_str = Path(f).stem
            result = run_single_backtest(args.data_dir, date_str, args.capital)
            if result and result.total_trades > 0:
                print_results(result, date_str)
                total_pnl += result.total_pnl
                total_trades += result.total_trades
                all_results.append({
                    "date": date_str,
                    "trades": result.total_trades,
                    "pnl": result.total_pnl,
                    "win_rate": result.win_rate,
                    "sharpe": result.sharpe_ratio,
                    "max_drawdown": result.max_drawdown,
                })

        print(f"\n{'='*60}")
        print(f"  AGGREGATE RESULTS — {len(all_results)} weeks")
        print(f"{'='*60}")
        print(f"  Total Trades:  {total_trades}")
        print(f"  Total P&L:      ₹{total_pnl:,.2f}")
        print(f"  Avg P&L/Week:   ₹{total_pnl/len(all_results):,.2f}" if all_results else "")
        print(f"{'='*60}")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(all_results, f, indent=2)
            print(f"\nResults saved to {args.output}")

    elif args.date:
        result = run_single_backtest(args.data_dir, args.date, args.capital)
        if result:
            print_results(result, args.date)
            if args.output:
                with open(args.output, "w") as f:
                    json.dump({
                        "date": args.date,
                        "total_trades": result.total_trades,
                        "total_pnl": result.total_pnl,
                        "win_rate": result.win_rate,
                        "sharpe_ratio": result.sharpe_ratio,
                        "max_drawdown": result.max_drawdown,
                        "config": result.config,
                    }, f, indent=2)
                print(f"\nResults saved to {args.output}")
        else:
            print(f"No data found for date: {args.date}")
            sys.exit(1)
    else:
        # Default: run on most recent week
        files = loader.list_files()
        if files:
            date_str = Path(files[-1]).stem
            print(f"Running backtest on most recent week: {date_str}")
            result = run_single_backtest(args.data_dir, date_str, args.capital)
            if result:
                print_results(result, date_str)
        else:
            print("No DuckDB files found in data directory")
            sys.exit(1)


if __name__ == "__main__":
    main()