"""
Run trading worker only (without API server).
Usage: python scripts/run_worker.py
"""
import os
import sys
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from app.core.database import init_db
from app.core.trading_engine import TradingEngine
from app.notifications.fonnte import FonnteNotifier
from app.utils.logger import setup_logger
from loguru import logger


running = True


def stop_handler(signum, frame):
    global running
    running = False
    logger.info("Shutdown signal received")


def main():
    setup_logger()
    init_db()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    notifier = FonnteNotifier()
    engine = TradingEngine(notifier=notifier)
    engine.start()

    # Timeframe to seconds
    tf_seconds = {
        "1m": 60, "5m": 300, "15m": 900,
        "1h": 3600, "4h": 14400,
    }
    interval = tf_seconds.get(settings.TIMEFRAME, 3600)

    logger.info(f"Worker started | Interval: {interval}s | Mode: {settings.TRADING_MODE}")

    while running:
        try:
            engine.run_cycle()
            engine.check_stop_loss_take_profit()
        except Exception as e:
            logger.error(f"Worker cycle error: {e}")

        # Sleep in small increments for graceful shutdown
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    engine.stop()
    logger.info("Worker stopped")


if __name__ == "__main__":
    main()
