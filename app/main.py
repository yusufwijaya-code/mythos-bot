import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from config.settings import settings
from app.core.database import init_db
from app.core.trading_engine import TradingEngine
from app.notifications.fonnte import FonnteNotifier
from app.workers.scheduler import BotScheduler
from app.api.router import api_router
from app.utils.logger import setup_logger

# Initialize components
setup_logger()
notifier = FonnteNotifier()
trading_engine = TradingEngine(notifier=notifier)
bot_scheduler = BotScheduler(trading_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=== Bot Trading Mythos Starting ===")
    init_db()
    bot_scheduler.start()
    logger.info(f"Mode: {settings.TRADING_MODE} | Pairs: {settings.TRADING_PAIRS}")
    yield
    # Shutdown
    bot_scheduler.stop()
    trading_engine.stop()
    logger.info("=== Bot Trading Mythos Stopped ===")


app = FastAPI(
    title="Bot Trading Mythos",
    description="AI Crypto Trading Bot with Risk Management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)

# Serve dashboard
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
if os.path.exists(dashboard_dir):
    app.mount("/static", StaticFiles(directory=dashboard_dir), name="static")


@app.get("/")
def serve_dashboard():
    index_path = os.path.join(dashboard_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Bot Trading Mythos API", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": settings.TRADING_MODE,
        "bot_active": trading_engine.active,
    }
