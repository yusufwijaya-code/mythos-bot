"""
Run scheduler only (without API server).
Usage: python scripts/run_scheduler.py
"""
import os
import sys
import time
import signal as sig

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from app.core.database import init_db
from app.core.trading_engine import TradingEngine
from app.notifications.fonnte import FonnteNotifier
from app.workers.scheduler import BotScheduler
from app.utils.logger import setup_logger
from loguru import logger


running = True


def stop_handler(signum, frame):
    global running
    running = False


def main():
    setup_logger()
    init_db()

    sig.signal(sig.SIGINT, stop_handler)
    sig.signal(sig.SIGTERM, stop_handler)

    notifier = FonnteNotifier()
    engine = TradingEngine(notifier=notifier)
    engine.start()

    scheduler = BotScheduler(engine)
    scheduler.start()

    logger.info("Scheduler running. Press Ctrl+C to stop.")

    while running:
        time.sleep(1)

    scheduler.stop()
    engine.stop()
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
