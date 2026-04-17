import sys
import os
from loguru import logger

from app.core.database import SessionLocal
from app.models.log_entry import LogEntry

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def db_sink(message):
    """Write log entries to database for dashboard viewing."""
    record = message.record
    level = record["level"].name
    if level not in ("INFO", "WARNING", "ERROR"):
        return
    try:
        db = SessionLocal()
        entry = LogEntry(
            level=level,
            module=record["name"],
            message=record["message"],
            details={"file": record["file"].name, "line": record["line"]},
        )
        db.add(entry)
        db.commit()
        db.close()
    except Exception:
        pass


def setup_logger():
    """Configure loguru logger with file + console + DB sinks."""
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console
    logger.add(sys.stdout, format=log_format, level="INFO", colorize=True)

    # File - all logs
    logger.add(
        os.path.join(LOG_DIR, "bot_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="INFO",
        rotation="1 day",
        retention="30 days",
        compression="zip",
    )

    # File - errors only
    logger.add(
        os.path.join(LOG_DIR, "errors_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="ERROR",
        rotation="1 day",
        retention="30 days",
    )

    # Database sink
    logger.add(db_sink, level="INFO")

    return logger


setup_logger()
