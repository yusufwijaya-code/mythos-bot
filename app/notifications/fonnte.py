import httpx
from loguru import logger

from config.settings import settings
from app.notifications.base import BaseNotifier
from app.utils.helpers import format_pair, format_price, now_str


class FonnteNotifier(BaseNotifier):
    """WhatsApp notification via Fonnte API."""

    API_URL = "https://api.fonnte.com/send"
    MAX_RETRIES = 3
    DASHBOARD_LINK = "bit.ly/mythosbymydios"

    def __init__(self):
        self.token = settings.FONNTE_TOKEN
        self.target = settings.FONNTE_TARGET
        # Sender is configured in Fonnte dashboard (6282114939571)

    def send_message(self, message: str) -> bool:
        """Send a WhatsApp message via Fonnte."""
        if not self.token or not self.target:
            logger.warning("Fonnte token or target not configured, skipping notification")
            return False

        full_message = f"{message}\n\n📊 Dashboard: {self.DASHBOARD_LINK}"

        headers = {"Authorization": self.token}
        payload = {
            "target": self.target,
            "message": full_message,
        }

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = httpx.post(
                    self.API_URL, headers=headers, data=payload, timeout=15
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status"):
                        logger.info(f"WhatsApp sent to {self.target}")
                        return True
                    else:
                        logger.warning(f"Fonnte response: {result}")
                else:
                    logger.warning(
                        f"Fonnte HTTP {response.status_code} (attempt {attempt})"
                    )
            except Exception as e:
                logger.error(f"Fonnte send error (attempt {attempt}): {e}")

            if attempt < self.MAX_RETRIES:
                import time
                time.sleep(2 * attempt)

        logger.error(f"Failed to send WhatsApp after {self.MAX_RETRIES} attempts")
        return False

    def send_trade_buy(
        self, pair: str, entry: float, sl: float, tp: float
    ) -> bool:
        message = (
            f"[TRADE BUY]\n"
            f"Pair: {format_pair(pair)}\n"
            f"Entry: {format_price(entry)}\n"
            f"SL: {format_price(sl)}\n"
            f"TP: {format_price(tp)}\n"
            f"Time: {now_str()}"
        )
        return self.send_message(message)

    def send_trade_sell(self, pair: str, exit_price: float, pnl_pct: float) -> bool:
        sign = "+" if pnl_pct >= 0 else ""
        message = (
            f"[TRADE SELL]\n"
            f"Pair: {format_pair(pair)}\n"
            f"Exit: {format_price(exit_price)}\n"
            f"PnL: {sign}{pnl_pct:.2f}%\n"
            f"Time: {now_str()}"
        )
        return self.send_message(message)

    def send_error(self, message: str) -> bool:
        msg = (
            f"[ERROR]\n"
            f"Message: {message}\n"
            f"Time: {now_str()}"
        )
        return self.send_message(msg)

    def send_daily_report(self, report: dict) -> bool:
        message = (
            f"[DAILY REPORT]\n"
            f"Date: {report.get('date', now_str())}\n"
            f"Total Trades: {report.get('total_trades', 0)}\n"
            f"Win Rate: {report.get('win_rate', 0):.1f}%\n"
            f"Net Profit: {report.get('net_profit', 0):+.2f} USDT\n"
            f"Gross Profit: {report.get('gross_profit', 0):.2f} USDT\n"
            f"Gross Loss: {report.get('gross_loss', 0):.2f} USDT\n"
            f"Drawdown: {report.get('max_drawdown', 0):.2f}%\n"
            f"Time: {now_str()}"
        )
        return self.send_message(message)

    def send_health_alert(self, issues: list, balance: float = 0) -> bool:
        message = (
            f"[HEALTH ALERT]\n"
            + "\n".join(f"- {i}" for i in issues)
            + f"\nBalance: {format_price(balance)} USDT\n"
            f"Time: {now_str()}"
        )
        return self.send_message(message)

    def send_system_stopped(self, reason: str = "") -> bool:
        message = (
            f"[SYSTEM STOPPED]\n"
            f"Reason: {reason or 'Unknown'}\n"
            f"Time: {now_str()}\n"
            f"Action: Check dashboard immediately"
        )
        return self.send_message(message)

    def send_weekly_report(self, report: dict) -> bool:
        message = (
            f"[WEEKLY REPORT]\n"
            f"Period: {report.get('period', 'N/A')}\n"
            f"Total Trades: {report.get('total_trades', 0)}\n"
            f"Win Rate: {report.get('win_rate', 0):.1f}%\n"
            f"Net Profit: {report.get('net_profit', 0):+.2f} USDT\n"
            f"Profit Factor: {report.get('profit_factor', 0):.2f}\n"
            f"Max Drawdown: {report.get('max_drawdown', 0):.2f}%\n"
            f"Time: {now_str()}"
        )
        return self.send_message(message)
