import time
from typing import Optional

import httpx
from loguru import logger

from config.settings import settings
from app.notifications.base import BaseNotifier
from app.utils.helpers import format_pair, format_price, now_str

_SEP = "─────────────────"
_QUOTA_REFRESH = 900  # refresh quota cache every 15 minutes


class FonnteNotifier(BaseNotifier):
    """WhatsApp notification via Fonnte API."""

    API_URL = "https://api.fonnte.com/send"
    DEVICE_URL = "https://api.fonnte.com/device"
    MAX_RETRIES = 3
    DASHBOARD_LINK = "bit.ly/mythosbymydios"

    def __init__(self):
        self.token = settings.FONNTE_TOKEN
        self.target = settings.FONNTE_TARGET
        self._quota_val: str = "?"
        self._quota_fetched: float = 0.0

    # ─── Quota cache ──────────────────────────────────────────────────────────

    def _get_quota_line(self) -> str:
        """Return formatted quota footer, refreshing cache every 15 min."""
        now = time.time()
        if now - self._quota_fetched > _QUOTA_REFRESH:
            try:
                info = self.get_device_info()
                self._quota_val = str(info.get("quota", "?")) if info else "?"
            except Exception:
                pass
            self._quota_fetched = now

        try:
            n = int(self._quota_val)
            icon = "🔴" if n <= 50 else ("🟡" if n <= 200 else "🟢")
        except (ValueError, TypeError):
            icon = "⚪"
        return f"📡 Fonnte     : {icon} {self._quota_val} msgs left"

    # ─── Core sender ──────────────────────────────────────────────────────────

    def send_message(self, message: str) -> bool:
        """Send a WhatsApp message via Fonnte. Appends quota + dashboard link."""
        if not self.token or not self.target:
            logger.warning("Fonnte token or target not configured, skipping notification")
            return False

        quota_line = self._get_quota_line()
        full_message = (
            f"{message}\n"
            f"{_SEP}\n"
            f"{quota_line}\n"
            f"📊 Dashboard  : {self.DASHBOARD_LINK}"
        )

        headers = {"Authorization": self.token}
        payload = {"target": self.target, "message": full_message}

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
                time.sleep(2 * attempt)

        logger.error(f"Failed to send WhatsApp after {self.MAX_RETRIES} attempts")
        return False

    # ─── Device / account info ────────────────────────────────────────────────

    def get_device_info(self) -> dict:
        """Fetch Fonnte device/account info including quota and expiry."""
        if not self.token:
            return {}
        try:
            response = httpx.post(
                self.DEVICE_URL,
                headers={"Authorization": self.token},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    # Refresh internal cache too
                    self._quota_val = str(data.get("quota", "?"))
                    self._quota_fetched = time.time()
                    return data
                logger.warning(f"Fonnte device info error: {data}")
        except Exception as e:
            logger.error(f"Fonnte get_device_info error: {e}")
        return {}

    def send_fonnte_status(self) -> bool:
        """Send Fonnte account status (quota, expiry, device) via WhatsApp."""
        info = self.get_device_info()
        if not info:
            return self.send_message(
                f"📡 *FONNTE STATUS*\n{_SEP}\n❌ Failed to retrieve Fonnte account info.\n⏱ {now_str()}"
            )

        quota = info.get("quota", "N/A")
        expired = info.get("expired", "N/A")
        device = info.get("device", "N/A")
        name = info.get("name", "N/A")
        package = info.get("package", info.get("plan", "N/A"))

        try:
            n = int(quota)
            quota_icon = "🔴" if n <= 50 else ("🟡" if n <= 200 else "🟢")
        except (ValueError, TypeError):
            quota_icon = "⚪"

        message = (
            f"📡 *FONNTE STATUS*\n"
            f"{_SEP}\n"
            f"📱 Device      : {device}\n"
            f"👤 Name        : {name}\n"
            f"📦 Package     : {package}\n"
            f"{_SEP}\n"
            f"{quota_icon} Quota Left   : *{quota} msgs*\n"
            f"📅 Expires     : {expired}\n"
            f"⏱ Checked at  : {now_str()}"
        )
        return self.send_message(message)

    # ─── Trade notifications ───────────────────────────────────────────────────

    def _account_stats_section(
        self,
        balance: Optional[float],
        today_trades: Optional[int],
        win_rate: Optional[float],
        today_pnl: Optional[float],
    ) -> str:
        """Build the account stats section string."""
        lines = []
        if balance is not None:
            lines.append(f"💰 Balance     : *${format_price(balance)} USDT*")
        if today_trades is not None:
            lines.append(f"📈 Today Trades: {today_trades}")
        if win_rate is not None:
            lines.append(f"🏆 Win Rate    : {win_rate:.1f}%")
        if today_pnl is not None:
            sign = "+" if today_pnl >= 0 else ""
            lines.append(f"💵 Today PnL   : *{sign}{today_pnl:.2f} USDT*")
        if not lines:
            return ""
        return f"{_SEP}\n📊 *ACCOUNT*\n" + "\n".join(lines) + "\n"

    def send_trade_buy(
        self,
        pair: str,
        entry: float,
        sl: float,
        tp: float,
        quantity: float = 0.0,
        strategy: str = "",
        balance: Optional[float] = None,
        today_trades: Optional[int] = None,
        win_rate: Optional[float] = None,
        today_pnl: Optional[float] = None,
    ) -> bool:
        sl_pct = abs((entry - sl) / entry * 100) if entry else 0
        tp_pct = abs((tp - entry) / entry * 100) if entry else 0
        rr = round(tp_pct / sl_pct, 2) if sl_pct else 0
        strat_line = f"🤖 Strategy    : {strategy.upper()}\n" if strategy else ""
        qty_line = f"💎 Quantity    : {quantity}\n" if quantity > 0 else ""
        stats = self._account_stats_section(balance, today_trades, win_rate, today_pnl)

        message = (
            f"🟢 *TRADE BUY — {format_pair(pair)}*\n"
            f"{_SEP}\n"
            f"{strat_line}"
            f"📍 Entry       : *${format_price(entry)}*\n"
            f"🛑 Stop Loss   : ${format_price(sl)} _(-{sl_pct:.1f}%)_\n"
            f"🎯 Take Profit : ${format_price(tp)} _(+{tp_pct:.1f}%)_\n"
            f"⚖️ R/R Ratio   : 1:{rr}\n"
            f"{qty_line}"
            f"⏱ Time        : {now_str()}\n"
            f"{stats}"
        )
        return self.send_message(message)

    def send_trade_sell(
        self,
        pair: str,
        exit_price: float,
        pnl_pct: float,
        pnl: float = 0.0,
        entry: float = 0.0,
        quantity: float = 0.0,
        reason: str = "",
        balance: Optional[float] = None,
        today_trades: Optional[int] = None,
        win_rate: Optional[float] = None,
        today_pnl: Optional[float] = None,
    ) -> bool:
        is_win = pnl_pct >= 0
        result_label = "WIN 🏆" if is_win else "LOSS 📉"
        title_icon = "🎉" if is_win else "🔴"
        pnl_sign = "+" if pnl >= 0 else ""
        pct_sign = "+" if pnl_pct >= 0 else ""
        reason_line = f"📋 Reason      : {reason}\n" if reason else ""
        entry_line = f"📍 Entry       : ${format_price(entry)}\n" if entry > 0 else ""
        qty_line = f"💎 Quantity    : {quantity}\n" if quantity > 0 else ""
        pnl_usdt_line = (
            f"💵 PnL (USDT)  : *{pnl_sign}{pnl:.4f} USDT*\n" if pnl != 0.0 else ""
        )
        stats = self._account_stats_section(balance, today_trades, win_rate, today_pnl)

        message = (
            f"{title_icon} *TRADE SELL — {format_pair(pair)}*\n"
            f"{_SEP}\n"
            f"{reason_line}"
            f"{entry_line}"
            f"📤 Exit        : *${format_price(exit_price)}*\n"
            f"{qty_line}"
            f"{pnl_usdt_line}"
            f"📊 PnL (%)     : *{pct_sign}{pnl_pct:.2f}%*\n"
            f"🏁 Result      : *{result_label}*\n"
            f"⏱ Time        : {now_str()}\n"
            f"{stats}"
        )
        return self.send_message(message)

    # ─── System notifications ─────────────────────────────────────────────────

    def send_error(self, message: str) -> bool:
        msg = (
            f"⚠️ *ERROR ALERT*\n"
            f"{_SEP}\n"
            f"🔴 {message}\n"
            f"⏱ Time        : {now_str()}"
        )
        return self.send_message(msg)

    def send_daily_report(self, report: dict) -> bool:
        total = report.get("total_trades", 0)
        wins = report.get("winning_trades", 0)
        losses = report.get("losing_trades", 0)
        win_rate = report.get("win_rate", 0)
        net = report.get("net_profit", 0)
        gross_p = report.get("gross_profit", 0)
        gross_l = report.get("gross_loss", 0)
        drawdown = report.get("max_drawdown", 0)
        net_sign = "+" if net >= 0 else ""

        message = (
            f"📊 *DAILY REPORT — {report.get('date', now_str())}*\n"
            f"{_SEP}\n"
            f"📈 Total Trades : *{total}*\n"
            f"✅ Win          : *{wins}*   |   ❌ Loss: *{losses}*\n"
            f"🏆 Win Rate     : *{win_rate:.1f}%*\n"
            f"{_SEP}\n"
            f"💰 Net Profit   : *{net_sign}{net:.2f} USDT*\n"
            f"📤 Gross Profit : +{gross_p:.2f} USDT\n"
            f"📥 Gross Loss   : -{gross_l:.2f} USDT\n"
            f"📉 Max Drawdown : {drawdown:.2f}%\n"
            f"⏱ Generated    : {now_str()}"
        )
        return self.send_message(message)

    def send_health_alert(self, issues: list, balance: float = 0) -> bool:
        issues_text = "\n".join(f"  • {i}" for i in issues)
        message = (
            f"🏥 *HEALTH ALERT*\n"
            f"{_SEP}\n"
            f"⚠️ Issues detected:\n"
            f"{issues_text}\n"
            f"{_SEP}\n"
            f"💰 Balance     : {format_price(balance)} USDT\n"
            f"⏱ Time        : {now_str()}"
        )
        return self.send_message(message)

    def send_system_stopped(self, reason: str = "") -> bool:
        message = (
            f"🚨 *SYSTEM STOPPED*\n"
            f"{_SEP}\n"
            f"❌ Reason      : {reason or 'Unknown'}\n"
            f"🔧 Action      : Check dashboard immediately\n"
            f"⏱ Time        : {now_str()}"
        )
        return self.send_message(message)

    def send_weekly_report(self, report: dict) -> bool:
        total = report.get("total_trades", 0)
        wins = report.get("winning_trades", 0)
        losses = report.get("losing_trades", 0)
        win_rate = report.get("win_rate", 0)
        net = report.get("net_profit", 0)
        pf = report.get("profit_factor", 0)
        drawdown = report.get("max_drawdown", 0)
        net_sign = "+" if net >= 0 else ""

        message = (
            f"📅 *WEEKLY REPORT*\n"
            f"{_SEP}\n"
            f"📆 Period       : {report.get('period', 'N/A')}\n"
            f"{_SEP}\n"
            f"📈 Total Trades : *{total}*\n"
            f"✅ Win          : *{wins}*   |   ❌ Loss: *{losses}*\n"
            f"🏆 Win Rate     : *{win_rate:.1f}%*\n"
            f"{_SEP}\n"
            f"💰 Net Profit   : *{net_sign}{net:.2f} USDT*\n"
            f"📊 Profit Factor: {pf:.2f}\n"
            f"📉 Max Drawdown : {drawdown:.2f}%\n"
            f"⏱ Generated    : {now_str()}"
        )
        return self.send_message(message)
