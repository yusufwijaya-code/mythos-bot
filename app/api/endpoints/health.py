from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from loguru import logger

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/status")
def get_health_status(user: dict = Depends(get_current_user)):
    """Full health status for dashboard monitoring."""
    from app.main import trading_engine

    health = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": "healthy",
        "components": {},
    }

    # 1. Trading Engine Status
    engine_status = "running" if trading_engine.active else "stopped"
    if trading_engine.risk_manager.is_emergency:
        engine_status = "error"
        health["overall"] = "unhealthy"
    health["components"]["trading_engine"] = {
        "status": engine_status,
        "mode": "paper" if trading_engine.is_paper else "live",
        "strategy": trading_engine.active_strategy,
    }

    # 2. Binance API Connectivity
    binance_status = "unknown"
    try:
        price = trading_engine.binance.get_ticker_price("BTCUSDT")
        binance_status = "connected" if price else "error"
    except Exception:
        binance_status = "disconnected"
        health["overall"] = "degraded"
    health["components"]["binance_api"] = {"status": binance_status}

    # 3. Fonnte Connectivity
    fonnte_status = "configured" if trading_engine.notifier and trading_engine.notifier.token else "not_configured"
    health["components"]["fonnte"] = {"status": fonnte_status}

    # 4. Error Monitoring
    rm = trading_engine.risk_manager
    health["components"]["risk_manager"] = {
        "emergency_stop": rm.is_emergency,
        "error_count": rm.error_count,
        "max_errors": rm.max_errors,
        "daily_trades": rm.daily_trades,
        "daily_pnl": round(rm.daily_pnl, 2),
    }

    # 5. Performance Metrics
    balance = trading_engine.get_balance()
    initial = trading_engine.get_initial_balance()
    drawdown_pct = round((1 - balance / initial) * 100, 2) if initial > 0 else 0
    health["components"]["performance"] = {
        "balance": round(balance, 2),
        "initial_balance": round(initial, 2),
        "drawdown_pct": drawdown_pct,
    }

    # 6. System Resources
    try:
        import psutil
        health["components"]["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 1),
            "disk_percent": psutil.disk_usage("/").percent if hasattr(psutil, "disk_usage") else 0,
        }
    except ImportError:
        health["components"]["system"] = {"status": "psutil not installed"}

    # Determine overall health
    if rm.is_emergency:
        health["overall"] = "unhealthy"
    elif binance_status == "disconnected":
        health["overall"] = "degraded"
    elif rm.error_count > 5:
        health["overall"] = "degraded"

    return health


@router.get("/ping")
def health_ping():
    """Simple health check - no auth required."""
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
