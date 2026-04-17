from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    @abstractmethod
    def send_message(self, message: str) -> bool:
        pass

    @abstractmethod
    def send_trade_buy(
        self,
        pair: str,
        entry: float,
        sl: float,
        tp: float,
        quantity: float = 0.0,
        strategy: str = "",
    ) -> bool:
        pass

    @abstractmethod
    def send_trade_sell(
        self,
        pair: str,
        exit_price: float,
        pnl_pct: float,
        pnl: float = 0.0,
        entry: float = 0.0,
        quantity: float = 0.0,
        reason: str = "",
    ) -> bool:
        pass

    @abstractmethod
    def send_error(self, message: str) -> bool:
        pass

    @abstractmethod
    def send_daily_report(self, report: dict) -> bool:
        pass

    @abstractmethod
    def send_weekly_report(self, report: dict) -> bool:
        pass

    @abstractmethod
    def send_health_alert(self, issues: list, balance: float = 0) -> bool:
        pass

    @abstractmethod
    def send_system_stopped(self, reason: str = "") -> bool:
        pass
