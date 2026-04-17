from datetime import datetime
from typing import Optional
from loguru import logger

from config.settings import settings


class PaperTradingService:
    """Simulates trading without real money."""

    def __init__(self, initial_balance: float = None):
        self.balance = initial_balance or settings.PAPER_INITIAL_BALANCE
        self.initial_balance = self.balance
        self.positions: dict = {}  # pair -> position dict
        self.trade_history: list = []
        self._order_counter = 0
        logger.info(f"Paper trading initialized with balance: {self.balance} USDT")

    def get_balance(self, asset: str = "USDT") -> float:
        if asset == "USDT":
            return self.balance
        for pair, pos in self.positions.items():
            if pair.replace("USDT", "") == asset:
                return pos["quantity"]
        return 0.0

    def get_all_balances(self) -> dict:
        balances = {"USDT": {"free": self.balance, "locked": 0}}
        for pair, pos in self.positions.items():
            asset = pair.replace("USDT", "")
            balances[asset] = {"free": pos["quantity"], "locked": 0}
        return balances

    def place_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        current_price: float,
    ) -> Optional[dict]:
        """Simulate order execution."""
        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter:06d}"
        total = quantity * current_price
        fee = total * 0.001  # 0.1% simulated fee

        if side == "BUY":
            cost = total + fee
            if cost > self.balance:
                logger.warning(
                    f"[PAPER] Insufficient balance for BUY {quantity} {pair}. "
                    f"Need {cost:.2f}, have {self.balance:.2f}"
                )
                return None

            self.balance -= cost
            self.positions[pair] = {
                "quantity": quantity,
                "entry_price": current_price,
                "side": "LONG",
                "opened_at": datetime.utcnow(),
            }

        elif side == "SELL":
            if pair not in self.positions:
                logger.warning(f"[PAPER] No position to sell for {pair}")
                return None

            pos = self.positions[pair]
            revenue = total - fee
            pnl = revenue - (pos["entry_price"] * pos["quantity"])
            pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"] * 100

            self.balance += revenue
            del self.positions[pair]

            trade = {
                "order_id": order_id,
                "pair": pair,
                "side": "SELL",
                "price": current_price,
                "quantity": quantity,
                "total": total,
                "fee": fee,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "timestamp": datetime.utcnow(),
            }
            self.trade_history.append(trade)
            logger.info(
                f"[PAPER] SELL {quantity} {pair} @ {current_price:.2f} | "
                f"PnL: {pnl:+.2f} ({pnl_pct:+.2f}%)"
            )

        order = {
            "orderId": order_id,
            "symbol": pair,
            "side": side,
            "price": str(current_price),
            "origQty": str(quantity),
            "executedQty": str(quantity),
            "status": "FILLED",
            "type": "MARKET",
        }

        if side == "BUY":
            trade = {
                "order_id": order_id,
                "pair": pair,
                "side": "BUY",
                "price": current_price,
                "quantity": quantity,
                "total": total,
                "fee": fee,
                "pnl": None,
                "pnl_pct": None,
                "timestamp": datetime.utcnow(),
            }
            self.trade_history.append(trade)
            logger.info(
                f"[PAPER] BUY {quantity} {pair} @ {current_price:.2f} | "
                f"Cost: {cost:.2f} USDT"
            )

        return order

    def get_position(self, pair: str) -> Optional[dict]:
        return self.positions.get(pair)

    def has_position(self, pair: str) -> bool:
        return pair in self.positions

    def get_total_equity(self, prices: dict) -> float:
        """Calculate total equity (balance + unrealized positions)."""
        equity = self.balance
        for pair, pos in self.positions.items():
            price = prices.get(pair, pos["entry_price"])
            equity += pos["quantity"] * price
        return equity

    def get_unrealized_pnl(self, pair: str, current_price: float) -> float:
        """Get unrealized PnL for a position."""
        pos = self.positions.get(pair)
        if not pos:
            return 0.0
        return (current_price - pos["entry_price"]) * pos["quantity"]
