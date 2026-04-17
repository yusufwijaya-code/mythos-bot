from datetime import datetime, date
from loguru import logger

from config.settings import settings


class RiskManager:
    """Enforces risk management rules for all trading operations."""

    def __init__(self):
        self.stop_loss_pct = settings.STOP_LOSS_PCT
        self.take_profit_pct = settings.TAKE_PROFIT_PCT
        self.max_position_pct = settings.MAX_POSITION_PCT
        self.max_daily_loss_pct = settings.MAX_DAILY_LOSS_PCT
        self.trailing_stop_pct = settings.TRAILING_STOP_PCT
        self.max_trades_per_day = settings.MAX_TRADES_PER_DAY

        # Tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset_date = date.today()
        self.error_count = 0
        self.max_errors = 10
        self._emergency_stop = False

    def reset_daily(self):
        """Reset daily counters if new day."""
        today = date.today()
        if today != self.last_reset_date:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.error_count = 0
            self.last_reset_date = today
            logger.info("Daily risk counters reset")

    def can_trade(self, balance: float, initial_balance: float) -> tuple[bool, str]:
        """Check if trading is allowed under current risk rules."""
        self.reset_daily()

        if self._emergency_stop:
            return False, "Emergency stop activated"

        # Max daily trades
        if self.daily_trades >= self.max_trades_per_day:
            return False, f"Max daily trades reached ({self.max_trades_per_day})"

        # Max daily loss
        if initial_balance > 0:
            daily_loss_pct = abs(self.daily_pnl) / initial_balance * 100
            if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
                return False, f"Max daily loss reached ({daily_loss_pct:.2f}%)"

        # Balance threshold (stop if lost > 20% of initial)
        if initial_balance > 0:
            balance_drop_pct = (1 - balance / initial_balance) * 100
            if balance_drop_pct >= 20:
                self._emergency_stop = True
                return False, f"Balance dropped {balance_drop_pct:.1f}% - EMERGENCY STOP"

        # Error rate
        if self.error_count >= self.max_errors:
            self._emergency_stop = True
            return False, f"Too many errors ({self.error_count}) - EMERGENCY STOP"

        return True, "OK"

    def calculate_position_size(
        self, balance: float, price: float, step_size: float = 0.001
    ) -> float:
        """Calculate position size based on max position % of capital."""
        max_allocation = balance * (self.max_position_pct / 100)
        quantity = max_allocation / price

        # Round to step size
        if step_size > 0:
            quantity = int(quantity / step_size) * step_size

        return round(quantity, 8)

    def calculate_stop_loss(self, entry_price: float, side: str = "LONG") -> float:
        """Calculate stop loss price."""
        if side == "LONG":
            return round(entry_price * (1 - self.stop_loss_pct / 100), 8)
        return round(entry_price * (1 + self.stop_loss_pct / 100), 8)

    def calculate_take_profit(self, entry_price: float, side: str = "LONG") -> float:
        """Calculate take profit price."""
        if side == "LONG":
            return round(entry_price * (1 + self.take_profit_pct / 100), 8)
        return round(entry_price * (1 - self.take_profit_pct / 100), 8)

    def calculate_trailing_stop(
        self, entry_price: float, current_price: float, current_trailing: float | None,
        side: str = "LONG",
    ) -> float:
        """Calculate trailing stop loss. Moves up as price increases."""
        new_trailing = current_price * (1 - self.trailing_stop_pct / 100)

        if side == "LONG":
            if current_trailing is None:
                return round(new_trailing, 8)
            return round(max(current_trailing, new_trailing), 8)
        else:
            new_trailing = current_price * (1 + self.trailing_stop_pct / 100)
            if current_trailing is None:
                return round(new_trailing, 8)
            return round(min(current_trailing, new_trailing), 8)

    def should_stop_loss(
        self, entry_price: float, current_price: float, stop_loss: float,
        trailing_stop: float | None = None, side: str = "LONG",
    ) -> bool:
        """Check if stop loss or trailing stop has been hit."""
        if side == "LONG":
            if trailing_stop and current_price <= trailing_stop:
                return True
            return current_price <= stop_loss
        else:
            if trailing_stop and current_price >= trailing_stop:
                return True
            return current_price >= stop_loss

    def should_take_profit(
        self, current_price: float, take_profit: float, side: str = "LONG"
    ) -> bool:
        """Check if take profit has been hit."""
        if side == "LONG":
            return current_price >= take_profit
        return current_price <= take_profit

    def record_trade(self, pnl: float):
        """Record a completed trade for daily tracking."""
        self.daily_trades += 1
        self.daily_pnl += pnl

    def record_error(self):
        """Record an error for failsafe tracking."""
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self._emergency_stop = True
            logger.error(f"Error threshold reached ({self.error_count}). Emergency stop!")

    def clear_emergency(self):
        """Manually clear emergency stop."""
        self._emergency_stop = False
        self.error_count = 0
        logger.warning("Emergency stop cleared manually")

    @property
    def is_emergency(self) -> bool:
        return self._emergency_stop
