from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config.settings import settings
from app.core.database import SessionLocal
from app.repositories.trade_repo import TradeRepository
from app.repositories.performance_repo import PerformanceRepository


# Timeframe to cron mapping (for reference only)
TIMEFRAME_CRON = {
    "1m": {"minute": "*/1"},
    "5m": {"minute": "*/5"},
    "15m": {"minute": "*/15"},
    "1h": {"minute": "0"},
    "4h": {"minute": "0", "hour": "*/4"},
}


class BotScheduler:
    """APScheduler wrapper for running strategy on candle close."""

    def __init__(self, trading_engine):
        self.engine = trading_engine
        # FIX 1: Changed timezone from UTC to Asia/Jakarta
        self.scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

    def start(self):
        """Start the scheduler with configured timeframe."""
        tf = settings.TIMEFRAME

        # FIX 3: Trading cycle always runs every 1 minute regardless of timeframe
        self.scheduler.add_job(
            self._run_trading_cycle,
            CronTrigger(minute="*/1", timezone="Asia/Jakarta"),
            id="trading_cycle",
            name=f"Trading Cycle ({tf})",
            replace_existing=True,
        )

        # SL/TP check every minute
        self.scheduler.add_job(
            self._check_sl_tp,
            CronTrigger(minute="*/1", timezone="Asia/Jakarta"),
            id="sl_tp_check",
            name="SL/TP Check",
            replace_existing=True,
        )

        # Daily report at 23:55 WIB (Asia/Jakarta)
        self.scheduler.add_job(
            self._generate_daily_report,
            CronTrigger(hour=23, minute=55, timezone="Asia/Jakarta"),
            id="daily_report",
            name="Daily Report",
            replace_existing=True,
        )

        # Weekly report on Sunday at 23:50 WIB (Asia/Jakarta)
        self.scheduler.add_job(
            self._generate_weekly_report,
            CronTrigger(day_of_week="sun", hour=23, minute=50, timezone="Asia/Jakarta"),
            id="weekly_report",
            name="Weekly Report",
            replace_existing=True,
        )

        # Health check every 5 minutes
        self.scheduler.add_job(
            self._health_check,
            CronTrigger(minute="*/5", timezone="Asia/Jakarta"),
            id="health_check",
            name="Health Check",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler started | Timeframe: {tf} | Cycle: every 1 min | Timezone: Asia/Jakarta"
        )

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def _run_trading_cycle(self):
        try:
            logger.info("--- Trading cycle started ---")
            self.engine.run_cycle()
        except Exception as e:
            logger.error(f"Trading cycle error: {e}")

    def _check_sl_tp(self):
        try:
            if self.engine.active:
                self.engine.check_stop_loss_take_profit()
        except Exception as e:
            logger.error(f"SL/TP check error: {e}")

    def _generate_daily_report(self):
        try:
            db = SessionLocal()
            trade_repo = TradeRepository(db)
            perf_repo = PerformanceRepository(db)

            stats = trade_repo.get_daily_stats(
                target_date=date.today(), mode=settings.TRADING_MODE
            )

            perf_repo.create_or_update(
                report_type="daily",
                report_date=date.today(),
                total_trades=stats["total_trades"],
                winning_trades=stats["winning_trades"],
                losing_trades=stats["losing_trades"],
                win_rate=stats["win_rate"],
                net_profit=stats["net_profit"],
                gross_profit=stats["gross_profit"],
                gross_loss=stats["gross_loss"],
                profit_factor=stats["profit_factor"],
                mode=settings.TRADING_MODE,
            )

            if self.engine.notifier:
                self.engine.notifier.send_daily_report(stats)

            logger.info(f"Daily report generated: {stats}")
            db.close()

        except Exception as e:
            logger.error(f"Daily report error: {e}")

    def _generate_weekly_report(self):
        try:
            db = SessionLocal()
            trade_repo = TradeRepository(db)
            perf_repo = PerformanceRepository(db)

            today = date.today()
            week_start = today - timedelta(days=7)

            from datetime import datetime
            trades = trade_repo.get_trades_between(
                datetime.combine(week_start, datetime.min.time()),
                datetime.combine(today, datetime.max.time()),
                mode=settings.TRADING_MODE,
            )

            sell_trades = [t for t in trades if t.side == "SELL" and t.pnl is not None]
            total = len(sell_trades)
            winners = [t for t in sell_trades if float(t.pnl) > 0]
            losers = [t for t in sell_trades if float(t.pnl) <= 0]
            net_profit = sum(float(t.pnl) for t in sell_trades)
            gross_profit = sum(float(t.pnl) for t in winners)
            gross_loss = abs(sum(float(t.pnl) for t in losers))
            win_rate = len(winners) / total * 100 if total > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

            stats = {
                "total_trades": total,
                "winning_trades": len(winners),
                "losing_trades": len(losers),
                "win_rate": win_rate,
                "net_profit": net_profit,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "profit_factor": profit_factor,
                "period": f"{week_start} to {today}",
            }

            perf_repo.create_or_update(
                report_type="weekly",
                report_date=today,
                total_trades=stats["total_trades"],
                winning_trades=stats["winning_trades"],
                losing_trades=stats["losing_trades"],
                win_rate=stats["win_rate"],
                net_profit=stats["net_profit"],
                gross_profit=stats["gross_profit"],
                gross_loss=stats["gross_loss"],
                profit_factor=stats["profit_factor"],
                mode=settings.TRADING_MODE,
            )

            if self.engine.notifier:
                self.engine.notifier.send_weekly_report(stats)

            logger.info(f"Weekly report generated: {stats}")
            db.close()

        except Exception as e:
            logger.error(f"Weekly report error: {e}")

    def _health_check(self):
        try:
            if not self.engine.active:
                return
            balance = self.engine.get_balance()
            logger.debug(f"Health check | Balance: {balance:.2f} USDT")
        except Exception as e:
            logger.error(f"Health check error: {e}")
