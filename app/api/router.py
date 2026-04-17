from fastapi import APIRouter
from app.api.endpoints import dashboard, control, backtest, auth, health

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(control.router)
api_router.include_router(backtest.router)
