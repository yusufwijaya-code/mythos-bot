import pytest
from app.services.paper_trading import PaperTradingService


class TestPaperTrading:
    def setup_method(self):
        self.paper = PaperTradingService(initial_balance=10000.0)

    def test_initial_balance(self):
        assert self.paper.balance == 10000.0
        assert self.paper.get_balance("USDT") == 10000.0

    def test_buy_order(self):
        order = self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        assert order is not None
        assert order["side"] == "BUY"
        assert order["status"] == "FILLED"
        assert self.paper.balance < 10000.0
        assert self.paper.has_position("BTCUSDT")

    def test_buy_insufficient_balance(self):
        order = self.paper.place_order("BTCUSDT", "BUY", 1.0, 50000.0)
        assert order is None  # 50000 > 10000

    def test_sell_order_with_profit(self):
        self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        order = self.paper.place_order("BTCUSDT", "SELL", 0.1, 55000.0)
        assert order is not None
        assert order["side"] == "SELL"
        assert not self.paper.has_position("BTCUSDT")
        assert self.paper.balance > self.paper.initial_balance - 100  # Rough check (minus fees)

    def test_sell_no_position(self):
        order = self.paper.place_order("BTCUSDT", "SELL", 0.1, 50000.0)
        assert order is None

    def test_fee_deduction(self):
        initial = self.paper.balance
        self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        # Cost = 0.1 * 50000 = 5000 + fee (5000 * 0.001 = 5)
        expected_balance = initial - 5000 - 5
        assert abs(self.paper.balance - expected_balance) < 0.01

    def test_get_all_balances(self):
        self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        balances = self.paper.get_all_balances()
        assert "USDT" in balances
        assert "BTC" in balances
        assert balances["BTC"]["free"] == 0.1

    def test_trade_history(self):
        self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        self.paper.place_order("BTCUSDT", "SELL", 0.1, 52000.0)
        assert len(self.paper.trade_history) == 2
        assert self.paper.trade_history[0]["side"] == "BUY"
        assert self.paper.trade_history[1]["side"] == "SELL"
        assert self.paper.trade_history[1]["pnl"] is not None

    def test_get_unrealized_pnl(self):
        self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        pnl = self.paper.get_unrealized_pnl("BTCUSDT", 55000.0)
        assert pnl == 500.0  # (55000 - 50000) * 0.1

    def test_get_total_equity(self):
        self.paper.place_order("BTCUSDT", "BUY", 0.1, 50000.0)
        equity = self.paper.get_total_equity({"BTCUSDT": 55000.0})
        # balance_remaining + 0.1 * 55000
        assert equity > 10000  # Should have unrealized profit
