from fastapi import APIRouter, Depends
from pydantic import BaseModel
from loguru import logger

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    pair: str = "BTCUSDT"
    timeframe: str = "1h"
    strategy: str = "ema_crossover"
    days: int = 30
    initial_balance: float = 10000.0


@router.post("/run")
def run_backtest(req: BacktestRequest, user: dict = Depends(get_current_user)):
    try:
        from backtesting.engine import BacktestEngine

        engine = BacktestEngine(
            pair=req.pair,
            timeframe=req.timeframe,
            strategy_name=req.strategy,
            days=req.days,
            initial_balance=req.initial_balance,
        )
        results = engine.run()
        return {"status": "ok", "results": results}

    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/results")
def get_backtest_results(user: dict = Depends(get_current_user)):
    """Get last backtest results (stored in memory)."""
    try:
        from backtesting.engine import last_backtest_results
        if last_backtest_results:
            return {"status": "ok", "results": last_backtest_results}
        return {"status": "no_results", "message": "No backtest has been run yet"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
