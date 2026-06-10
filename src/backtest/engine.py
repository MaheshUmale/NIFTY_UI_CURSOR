"""Backtesting engine — replays historical data through the strategy pipeline.

Simulates tick-by-tick execution with:
- Signal generation (reuses SignalGenerator)
- Risk gate checks (reuses RiskManager logic)
- Order execution simulation
- P&L tracking with realistic fills
- Performance metrics (Sharpe, max drawdown, win rate)

Source citation:
    > src/strategy/AGENTS.md — Backtesting mandatory for every signal generator
    > config/AGENTS.md — Immutable risk rules (2% per trade, 4% daily, 3 trades/day)
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.strategy.signal_generator import Signal, SignalGenerator
from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """A completed trade from backtesting."""
    tag: str
    symbol: str
    side: str  # "LONG" or "SHORT"
    instrument_key: str
    entry_price: float
    exit_price: float
    qty: int
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    signal_confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    """Complete backtest results."""
    # Trade summary
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L
    total_pnl: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    profit_factor: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0

    # Timing
    avg_holding_period_bars: float = 0.0
    total_bars_processed: int = 0

    # Trades list
    trades: list[Trade] = field(default_factory=list)

    # Configuration used
    config: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Backtesting Engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Replays historical ticks through the strategy pipeline.

    Parameters
    ----------
    capital : float
        Starting capital in INR (default 200000).
    max_trades_per_day : int
        Maximum trades per day (default 3, from risk_constants).
    max_risk_per_trade_pct : float
        Max risk per trade as fraction (default 0.02 = 2%).
    max_daily_loss_pct : float
        Max daily loss as fraction (default 0.04 = 4%).
    slippage_pct : float
        Slippage per trade as fraction (default 0.005 = 0.5%).
    """

    def __init__(
        self,
        capital: float = 200_000.0,
        max_trades_per_day: int = 3,
        max_risk_per_trade_pct: float = 0.02,
        max_daily_loss_pct: float = 0.04,
        slippage_pct: float = 0.005,
    ) -> None:
        self._capital = capital
        self._max_trades_per_day = max_trades_per_day
        self._max_risk_per_trade_pct = max_risk_per_trade_pct
        self._max_daily_loss_pct = max_daily_loss_pct
        self._slippage_pct = slippage_pct

        # Strategy
        self._signal_gen = SignalGenerator()

        # State
        self._current_capital = capital
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._current_date = ""
        self._trades: list[Trade] = []
        self._open_position: dict[str, Any] | None = None
        self._equity_curve: list[float] = [capital]
        self._bars_processed = 0
        self._trade_counter = 0

    def run(
        self,
        ticks: list[dict[str, Any]],
        spot_price: float | None = None,
    ) -> BacktestResult:
        """Run backtest on a list of ticks.

        Parameters
        ----------
        ticks : list[dict]
            List of tick dicts with keys: symbol, last_price, volume, oi, timestamp, etc.
        spot_price : float, optional
            Starting spot price for the session.

        Returns
        -------
        BacktestResult with all metrics and trades.
        """
        logger.info(
            "Starting backtest: %d ticks, capital=%.0f",
            len(ticks), self._capital,
        )

        self._reset()

        for tick in ticks:
            self._process_tick(tick)

        # Close any open position at end of data
        if self._open_position is not None:
            self._close_position(
                self._open_position["exit_price"],
                self._open_position.get("timestamp", now_ist()),
            )

        result = self._compute_results()
        logger.info(
            "Backtest complete: %d trades, PnL=%.2f, win_rate=%.1f%%",
            result.total_trades, result.total_pnl, result.win_rate * 100,
        )
        return result

    def run_from_spot_data(
        self,
        spot_rows: list[dict[str, Any]],
        options_rows: list[dict[str, Any]] | None = None,
    ) -> BacktestResult:
        """Run backtest using spot data (from DuckDB spot_data table).

        Parameters
        ----------
        spot_rows : list[dict]
            Spot data rows with keys: Timestamp, Open, High, Low, Close, Volume
        options_rows : list[dict], optional
            Options data for OI-based signals.

        Returns
        -------
        BacktestResult
        """
        ticks = []
        for row in spot_rows:
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

        return self.run(ticks)

    def _reset(self) -> None:
        """Reset all state for a new backtest."""
        self._current_capital = self._capital
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._current_date = ""
        self._trades = []
        self._open_position = None
        self._equity_curve = [self._capital]
        self._bars_processed = 0
        self._trade_counter = 0
        self._signal_gen = SignalGenerator()

    def _process_tick(self, tick: dict[str, Any]) -> None:
        """Process a single tick through the pipeline."""
        self._bars_processed += 1

        # Check for date change (daily reset)
        tick_date = str(tick.get("timestamp", ""))[:10]
        if tick_date != self._current_date:
            self._current_date = tick_date
            self._daily_pnl = 0.0
            self._daily_trades = 0
            self._signal_gen.reset()

        # If we have an open position, check for exit
        if self._open_position is not None:
            self._check_exit(tick)
            return

        # Run strategy to generate signals
        try:
            signal = self._signal_gen.on_tick(tick)
        except Exception:
            logger.debug("Strategy error on bar %d", self._bars_processed)
            return

        if signal is None:
            return

        # Risk gate checks
        if not self._risk_check(signal):
            return

        # Open position
        self._open_position(signal, tick)

    def _risk_check(self, signal: Signal) -> bool:
        """Check if the signal passes risk gates."""
        # Check daily trade limit
        if self._daily_trades >= self._max_trades_per_day:
            logger.debug("Daily trade limit reached: %d", self._daily_trades)
            return False

        # Check daily loss limit
        daily_loss_pct = abs(self._daily_pnl) / self._capital if self._daily_pnl < 0 else 0
        if daily_loss_pct >= self._max_daily_loss_pct:
            logger.debug("Daily loss limit reached: %.2f%%", daily_loss_pct * 100)
            return False

        # Check if we can afford the trade
        risk_amount = self._current_capital * self._max_risk_per_trade_pct
        if risk_amount <= 0:
            return False

        return True

    def _open_position(self, signal: Signal, tick: dict[str, Any]) -> None:
        """Open a new position based on the signal."""
        price = signal.entry_price

        # Apply slippage
        if signal.side == "LONG":
            fill_price = price * (1 + self._slippage_pct)
        else:
            fill_price = price * (1 - self._slippage_pct)

        # Calculate position size based on risk
        risk_amount = self._current_capital * self._max_risk_per_trade_pct
        stop_distance = abs(fill_price - signal.stop_loss)
        if stop_distance <= 0:
            return

        qty = max(1, int(risk_amount / stop_distance))
        # Cap at reasonable size (lot size = 25 for NIFTY)
        qty = min(qty, 75)  # Max 3 lots

        self._trade_counter += 1
        self._open_position = {
            "tag": f"BT-{self._trade_counter:04d}",
            "symbol": signal.symbol,
            "side": signal.side,
            "instrument_key": signal.instrument_key,
            "entry_price": fill_price,
            "stop_loss": signal.stop_loss,
            "target": signal.target,
            "qty": qty,
            "entry_time": signal.timestamp,
            "confidence": signal.confidence,
            "bars_held": 0,
            "exit_price": fill_price,  # Will be updated
            "timestamp": tick.get("timestamp", ""),
        }

        logger.debug(
            "Position opened: %s %s @ %.2f qty=%d",
            signal.side, signal.symbol, fill_price, qty,
        )

    def _check_exit(self, tick: dict[str, Any]) -> None:
        """Check if open position should be closed."""
        pos = self._open_position
        if pos is None:
            return

        pos["bars_held"] += 1
        current_price = float(tick.get("last_price", 0.0))
        if current_price <= 0:
            return

        # Check stop loss
        if pos["side"] == "LONG" and current_price <= pos["stop_loss"]:
            self._close_position(pos["stop_loss"], tick.get("timestamp", ""))
            return
        elif pos["side"] == "SHORT" and current_price >= pos["stop_loss"]:
            self._close_position(pos["stop_loss"], tick.get("timestamp", ""))
            return

        # Check target
        if pos["side"] == "LONG" and current_price >= pos["target"]:
            self._close_position(pos["target"], tick.get("timestamp", ""))
            return
        elif pos["side"] == "SHORT" and current_price <= pos["target"]:
            self._close_position(pos["target"], tick.get("timestamp", ""))
            return

        # Update exit price for trailing
        pos["exit_price"] = current_price

    def _close_position(self, exit_price: float, timestamp: Any) -> None:
        """Close the open position and record the trade."""
        pos = self._open_position
        if pos is None:
            return

        # Apply slippage on exit
        if pos["side"] == "LONG":
            fill_price = exit_price * (1 - self._slippage_pct)
        else:
            fill_price = exit_price * (1 + self._slippage_pct)

        # Calculate P&L
        if pos["side"] == "LONG":
            pnl = (fill_price - pos["entry_price"]) * pos["qty"] * 25  # NIFTY lot size = 25
        else:
            pnl = (pos["entry_price"] - fill_price) * pos["qty"] * 25

        pnl_pct = pnl / self._capital if self._capital > 0 else 0

        # Create trade record
        trade = Trade(
            tag=pos["tag"],
            symbol=pos["symbol"],
            side=pos["side"],
            instrument_key=pos["instrument_key"],
            entry_price=pos["entry_price"],
            exit_price=fill_price,
            qty=pos["qty"],
            entry_time=pos["entry_time"],
            exit_time=timestamp if isinstance(timestamp, datetime) else now_ist(),
            pnl=pnl,
            pnl_pct=pnl_pct,
            signal_confidence=pos["confidence"],
            metadata={"bars_held": pos["bars_held"]},
        )

        self._trades.append(trade)
        self._daily_pnl += pnl
        self._daily_trades += 1
        self._current_capital += pnl
        self._equity_curve.append(self._current_capital)
        self._open_position = None

        logger.debug(
            "Position closed: %s %s @ %.2f PnL=%.2f (%.2f%%)",
            trade.side, trade.symbol, fill_price, pnl, pnl_pct * 100,
        )

    def _compute_results(self) -> BacktestResult:
        """Compute final backtest results."""
        result = BacktestResult()

        result.trades = self._trades
        result.total_trades = len(self._trades)
        result.total_bars_processed = self._bars_processed

        if result.total_trades == 0:
            result.config = self._get_config()
            return result

        # Win/loss stats
        pnls = [t.pnl for t in self._trades]
        result.winning_trades = sum(1 for p in pnls if p > 0)
        result.losing_trades = sum(1 for p in pnls if p <= 0)
        result.win_rate = result.winning_trades / result.total_trades

        # P&L stats
        result.total_pnl = sum(pnls)
        result.avg_pnl_per_trade = result.total_pnl / result.total_trades
        result.max_win = max(pnls) if pnls else 0
        result.max_loss = min(pnls) if pnls else 0

        # Profit factor
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Max drawdown
        peak = self._capital
        max_dd = 0
        max_dd_pct = 0
        for eq in self._equity_curve:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = dd / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        result.max_drawdown = max_dd
        result.max_drawdown_pct = max_dd_pct

        # Sharpe ratio (annualized, assuming 252 trading days)
        if len(pnls) > 1:
            mean_return = statistics.mean(pnls)
            std_return = statistics.stdev(pnls)
            if std_return > 0:
                result.sharpe_ratio = (mean_return / std_return) * (252 ** 0.5)
                # Sortino ratio (downside deviation only)
                downside = [p for p in pnls if p < 0]
                if downside:
                    downside_std = statistics.stdev(downside)
                    if downside_std > 0:
                        result.sortino_ratio = (mean_return / downside_std) * (252 ** 0.5)

        # Average holding period
        holding_periods = [t.metadata.get("bars_held", 0) for t in self._trades]
        result.avg_holding_period_bars = (
            statistics.mean(holding_periods) if holding_periods else 0
        )

        result.config = self._get_config()
        return result

    def _get_config(self) -> dict[str, Any]:
        """Return the configuration used for this backtest."""
        return {
            "capital": self._capital,
            "max_trades_per_day": self._max_trades_per_day,
            "max_risk_per_trade_pct": self._max_risk_per_trade_pct,
            "max_daily_loss_pct": self._max_daily_loss_pct,
            "slippage_pct": self._slippage_pct,
        }