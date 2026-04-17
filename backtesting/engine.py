import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from loguru import logger
import numpy as np

from app.services.binance_client import BinanceService
from app.strategies.ema_crossover import EMACrossoverStrategy
from app.strategies.multi_timeframe import MultiTimeframeStrategy

# Store last results for API access
last_backtest_results = None


class BacktestEngine:
    """Historical backtesting engine using Binance data."""

    def __init__(
        self,
        pair: str = "BTCUSDT",
        timeframe: str = "1h",
        strategy_name: str = "ema_crossover",
        days: int = 30,
        initial_balance: float = 10000.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
        max_position_pct: float = 10.0,
        fee_pct: float = 0.1,
    ):
        self.pair = pair
        self.timeframe = timeframe
        self.strategy_name = strategy_name
        self.days = days
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_position_pct = max_position_pct
        self.fee_pct = fee_pct

        self.binance = BinanceService()
        self.strategies = {
            "ema_crossover": EMACrossoverStrategy(),
            "multi_timeframe": MultiTimeframeStrategy(),
        }

        self.trades = []
        self.equity_curve = []
        self.position = None

    def run(self) -> dict:
        global last_backtest_results

        logger.info(
            f"Backtest started: {self.pair} | {self.timeframe} | "
            f"{self.strategy_name} | {self.days} days"
        )

        # Fetch historical data
        limit = min(self.days * self._candles_per_day(), 1000)
        df = self.binance.get_klines(self.pair, self.timeframe, limit=limit)

        if df.empty or len(df) < 50:
            return {"error": "Insufficient historical data"}

        strategy = self.strategies.get(self.strategy_name)
        if not strategy:
            return {"error": f"Unknown strategy: {self.strategy_name}"}

        # Iterate through candles (skip first 50 for indicator warmup)
        for i in range(50, len(df)):
            window = df.iloc[:i + 1].copy()
            current_price = float(df.iloc[i]["close"])
            timestamp = df.iloc[i]["timestamp"]

            # Check SL/TP for open position
            if self.position:
                self._check_exit(current_price, timestamp)

            # Only process if no open position
            if not self.position:
                signal = strategy.analyze(window, self.pair)

                if signal.action == "BUY":
                    self._open_position(current_price, timestamp)

            elif self.position:
                signal = strategy.analyze(window, self.pair)
                if signal.action == "SELL":
                    self._close_position(current_price, timestamp, "strategy_sell")

            # Track equity
            equity = self.balance
            if self.position:
                equity += self.position["quantity"] * current_price
            self.equity_curve.append({
                "timestamp": str(timestamp),
                "equity": round(equity, 2),
            })

        # Close any remaining position at last price
        if self.position:
            last_price = float(df.iloc[-1]["close"])
            self._close_position(last_price, df.iloc[-1]["timestamp"], "end_of_backtest")

        results = self._calculate_results()
        last_backtest_results = results

        logger.info(
            f"Backtest complete: {results['total_trades']} trades | "
            f"Win rate: {results['win_rate']:.1f}% | "
            f"Net profit: {results['net_profit']:.2f} USDT"
        )

        return results

    def _candles_per_day(self) -> int:
        mapping = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24, "4h": 6, "1d": 1}
        return mapping.get(self.timeframe, 24)

    def _open_position(self, price: float, timestamp):
        allocation = self.balance * (self.max_position_pct / 100)
        quantity = allocation / price
        fee = allocation * (self.fee_pct / 100)
        cost = allocation + fee

        if cost > self.balance:
            return

        self.balance -= cost
        self.position = {
            "entry_price": price,
            "quantity": quantity,
            "stop_loss": price * (1 - self.stop_loss_pct / 100),
            "take_profit": price * (1 + self.take_profit_pct / 100),
            "entry_time": timestamp,
            "fee": fee,
        }

    def _close_position(self, price: float, timestamp, reason: str):
        if not self.position:
            return

        quantity = self.position["quantity"]
        revenue = quantity * price
        fee = revenue * (self.fee_pct / 100)
        net_revenue = revenue - fee

        entry_price = self.position["entry_price"]
        pnl = net_revenue - (entry_price * quantity) - self.position["fee"]
        pnl_pct = (price - entry_price) / entry_price * 100

        self.balance += net_revenue

        self.trades.append({
            "entry_price": entry_price,
            "exit_price": price,
            "quantity": quantity,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "entry_time": str(self.position["entry_time"]),
            "exit_time": str(timestamp),
            "reason": reason,
        })

        self.position = None

    def _check_exit(self, current_price: float, timestamp):
        if not self.position:
            return

        if current_price <= self.position["stop_loss"]:
            self._close_position(current_price, timestamp, "stop_loss")
        elif current_price >= self.position["take_profit"]:
            self._close_position(current_price, timestamp, "take_profit")

    def _calculate_results(self) -> dict:
        if not self.trades:
            return {
                "pair": self.pair,
                "timeframe": self.timeframe,
                "strategy": self.strategy_name,
                "days": self.days,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "net_profit": 0,
                "net_profit_pct": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "max_drawdown_pct": 0,
                "sharpe_ratio": 0,
                "final_balance": round(self.balance, 2),
                "trades": [],
                "equity_curve": self.equity_curve,
            }

        winners = [t for t in self.trades if t["pnl"] > 0]
        losers = [t for t in self.trades if t["pnl"] <= 0]
        gross_profit = sum(t["pnl"] for t in winners)
        gross_loss = abs(sum(t["pnl"] for t in losers))

        # Max drawdown
        equities = [e["equity"] for e in self.equity_curve]
        max_dd = 0
        max_dd_pct = 0
        peak = equities[0] if equities else self.initial_balance
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = dd / peak * 100 if peak > 0 else 0
            if dd_pct > max_dd_pct:
                max_dd = dd
                max_dd_pct = dd_pct

        # Sharpe ratio (annualized, assuming daily returns)
        pnls = [t["pnl"] for t in self.trades]
        sharpe = 0
        if len(pnls) > 1:
            mean_pnl = np.mean(pnls)
            std_pnl = np.std(pnls)
            if std_pnl > 0:
                sharpe = round((mean_pnl / std_pnl) * np.sqrt(252), 2)

        net_profit = self.balance - self.initial_balance

        return {
            "pair": self.pair,
            "timeframe": self.timeframe,
            "strategy": self.strategy_name,
            "days": self.days,
            "total_trades": len(self.trades),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": round(len(winners) / len(self.trades) * 100, 2),
            "net_profit": round(net_profit, 2),
            "net_profit_pct": round(net_profit / self.initial_balance * 100, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else 0,
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "sharpe_ratio": sharpe,
            "final_balance": round(self.balance, 2),
            "trades": self.trades,
            "equity_curve": self.equity_curve,
        }
