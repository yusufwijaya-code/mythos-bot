import pytest
from app.core.risk_manager import RiskManager


class TestRiskManager:
    def setup_method(self):
        self.rm = RiskManager()

    def test_can_trade_initially(self):
        can, reason = self.rm.can_trade(balance=10000, initial_balance=10000)
        assert can is True
        assert reason == "OK"

    def test_max_daily_trades(self):
        self.rm.max_trades_per_day = 3
        self.rm.daily_trades = 3
        can, reason = self.rm.can_trade(balance=10000, initial_balance=10000)
        assert can is False
        assert "Max daily trades" in reason

    def test_max_daily_loss(self):
        self.rm.max_daily_loss_pct = 5.0
        self.rm.daily_pnl = -600  # -6% of 10000
        can, reason = self.rm.can_trade(balance=9400, initial_balance=10000)
        assert can is False
        assert "Max daily loss" in reason

    def test_balance_threshold_emergency(self):
        self.rm.can_trade(balance=7500, initial_balance=10000)  # -25%
        assert self.rm.is_emergency is True

    def test_error_rate_emergency(self):
        self.rm.max_errors = 3
        for _ in range(3):
            self.rm.record_error()
        assert self.rm.is_emergency is True
        can, reason = self.rm.can_trade(balance=10000, initial_balance=10000)
        assert can is False

    def test_clear_emergency(self):
        self.rm._emergency_stop = True
        self.rm.clear_emergency()
        assert self.rm.is_emergency is False

    def test_calculate_position_size(self):
        size = self.rm.calculate_position_size(
            balance=10000, price=50000, step_size=0.00001
        )
        # 10% of 10000 = 1000 USDT, 1000/50000 = 0.02
        assert 0.01 < size < 0.03

    def test_calculate_stop_loss_long(self):
        sl = self.rm.calculate_stop_loss(entry_price=100, side="LONG")
        assert sl == 98.0  # 2% below

    def test_calculate_stop_loss_short(self):
        sl = self.rm.calculate_stop_loss(entry_price=100, side="SHORT")
        assert sl == 102.0  # 2% above

    def test_calculate_take_profit_long(self):
        tp = self.rm.calculate_take_profit(entry_price=100, side="LONG")
        assert tp == 104.0  # 4% above

    def test_should_stop_loss_triggered(self):
        assert self.rm.should_stop_loss(
            entry_price=100, current_price=97, stop_loss=98
        ) is True

    def test_should_stop_loss_not_triggered(self):
        assert self.rm.should_stop_loss(
            entry_price=100, current_price=99, stop_loss=98
        ) is False

    def test_should_take_profit_triggered(self):
        assert self.rm.should_take_profit(
            current_price=105, take_profit=104
        ) is True

    def test_trailing_stop_moves_up(self):
        ts1 = self.rm.calculate_trailing_stop(100, 105, None)
        ts2 = self.rm.calculate_trailing_stop(100, 110, ts1)
        assert ts2 > ts1  # Trailing stop should move up

    def test_trailing_stop_never_moves_down(self):
        ts1 = self.rm.calculate_trailing_stop(100, 110, None)
        ts2 = self.rm.calculate_trailing_stop(100, 105, ts1)
        assert ts2 == ts1  # Should not move down

    def test_record_trade(self):
        self.rm.record_trade(pnl=50)
        assert self.rm.daily_trades == 1
        assert self.rm.daily_pnl == 50

    def test_record_trade_loss(self):
        self.rm.record_trade(pnl=-30)
        self.rm.record_trade(pnl=-20)
        assert self.rm.daily_trades == 2
        assert self.rm.daily_pnl == -50
