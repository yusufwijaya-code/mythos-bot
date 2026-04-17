import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from config.settings import settings, ENV_PATH
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["control"])


class ModeRequest(BaseModel):
    mode: str  # "paper" or "live"


class StrategyRequest(BaseModel):
    strategy: str


def _persist_env_value(key: str, value: str) -> None:
    """Write a key=value pair to the .env file so it persists after restart."""
    try:
        with open(ENV_PATH, "r") as f:
            content = f.read()
        pattern = rf"^{re.escape(key)}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content = content.rstrip("\n") + f"\n{replacement}\n"
        with open(ENV_PATH, "w") as f:
            f.write(content)
    except Exception as e:
        logger.warning(f"Could not persist {key} to .env: {e}")


@router.post("/bot/start")
def start_bot(user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    if trading_engine.active:
        return {"status": "already_running", "message": "Bot is already running"}
    trading_engine.start()
    return {"status": "started", "message": "Bot started successfully"}


@router.post("/bot/stop")
def stop_bot(user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    if not trading_engine.active:
        return {"status": "already_stopped", "message": "Bot is already stopped"}
    trading_engine.stop()
    return {"status": "stopped", "message": "Bot stopped successfully"}


@router.post("/bot/mode")
def set_mode(req: ModeRequest, user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    if req.mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail="Mode must be 'paper' or 'live'")

    if req.mode == "live" and trading_engine.active:
        raise HTTPException(
            status_code=400,
            detail="Stop the bot before switching to live mode"
        )

    settings.TRADING_MODE = req.mode
    _persist_env_value("TRADING_MODE", req.mode)
    logger.warning(f"Trading mode changed to: {req.mode}")
    return {
        "status": "ok",
        "mode": req.mode,
        "message": f"Mode set to {req.mode}",
    }


@router.post("/strategy/set")
def set_strategy(req: StrategyRequest, user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    available = list(trading_engine.strategies.keys())
    if req.strategy not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy must be one of: {available}"
        )
    trading_engine.set_strategy(req.strategy)
    return {
        "status": "ok",
        "strategy": req.strategy,
        "message": f"Strategy set to {req.strategy}",
    }


@router.get("/strategies")
def get_strategies(user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    return {
        "active": trading_engine.active_strategy,
        "available": list(trading_engine.strategies.keys()),
    }


@router.post("/emergency/clear")
def clear_emergency(user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    trading_engine.risk_manager.clear_emergency()
    return {"status": "ok", "message": "Emergency stop cleared"}
