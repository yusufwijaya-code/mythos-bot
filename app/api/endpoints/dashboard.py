from datetime import date, datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.repositories.trade_repo import TradeRepository
from app.repositories.signal_repo import SignalRepository
from app.repositories.position_repo import PositionRepository
from app.repositories.performance_repo import PerformanceRepository
from app.models.log_entry import LogEntry

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/balance")
def get_balance(user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    balances = trading_engine.get_all_balances()
    total_usdt = balances.get("USDT", {}).get("free", 0)
    return {
        "balances": balances,
        "total_usdt": total_usdt,
        "mode": "paper" if trading_engine.is_paper else "live",
    }


@router.get("/positions")
def get_positions(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    repo = PositionRepository(db)
    positions = repo.get_open_positions(
        mode="paper" if trading_engine.is_paper else "live"
    )
    result = []
    for p in positions:
        price = trading_engine.binance.get_ticker_price(p.pair)
        entry = float(p.entry_price)
        qty = float(p.quantity)
        pnl = (price - entry) * qty if price else 0
        pnl_pct = ((price - entry) / entry * 100) if price and entry else 0
        result.append({
            "id": p.id,
            "pair": p.pair,
            "side": p.side,
            "entry_price": entry,
            "quantity": qty,
            "current_price": price,
            "unrealized_pnl": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2),
            "stop_loss": float(p.stop_loss) if p.stop_loss else None,
            "take_profit": float(p.take_profit) if p.take_profit else None,
            "trailing_stop": float(p.trailing_stop) if p.trailing_stop else None,
            "opened_at": p.opened_at.isoformat() if p.opened_at else None,
        })
    return {"positions": result}


@router.get("/trades")
def get_trades(limit: int = 50, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    from app.main import trading_engine
    repo = TradeRepository(db)
    mode = "paper" if trading_engine.is_paper else "live"
    trades = repo.get_recent(limit=limit, mode=mode)
    return {
        "trades": [
            {
                "id": t.id,
                "pair": t.pair,
                "side": t.side,
                "price": float(t.price),
                "quantity": float(t.quantity),
                "total": float(t.total),
                "pnl": float(t.pnl) if t.pnl else None,
                "pnl_pct": float(t.pnl_pct) if t.pnl_pct else None,
                "mode": t.mode,
                "strategy": t.strategy,
                "created_at": (t.created_at.isoformat() + 'Z') if t.created_at else None,
            }
            for t in trades
        ]
    }


@router.get("/signals")
def get_signals(limit: int = 50, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    repo = SignalRepository(db)
    signals = repo.get_recent(limit=limit)
    return {
        "signals": [
            {
                "id": s.id,
                "pair": s.pair,
                "strategy": s.strategy,
                "action": s.action,
                "confidence": float(s.confidence) if s.confidence else None,
                "indicators": s.indicators,
                "executed": s.executed,
                "created_at": (s.created_at.isoformat() + 'Z') if s.created_at else None,
            }
            for s in signals
        ]
    }


@router.get("/performance")
def get_performance(
    report_type: str = "daily", limit: int = 30,
    db: Session = Depends(get_db), user: dict = Depends(get_current_user),
):
    from app.main import trading_engine
    repo = PerformanceRepository(db)
    mode = "paper" if trading_engine.is_paper else "live"
    metrics = repo.get_recent(report_type=report_type, limit=limit, mode=mode)
    return {
        "performance": [
            {
                "id": m.id,
                "report_type": m.report_type,
                "report_date": m.report_date.isoformat(),
                "total_trades": m.total_trades,
                "winning_trades": m.winning_trades,
                "losing_trades": m.losing_trades,
                "win_rate": float(m.win_rate),
                "net_profit": float(m.net_profit),
                "profit_factor": float(m.profit_factor),
                "max_drawdown": float(m.max_drawdown),
            }
            for m in metrics
        ]
    }


@router.get("/logs")
def get_logs(
    level: str = None, limit: int = 100,
    db: Session = Depends(get_db), user: dict = Depends(get_current_user),
):
    q = db.query(LogEntry)
    if level:
        q = q.filter(LogEntry.level == level.upper())
    logs = q.order_by(LogEntry.created_at.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "id": l.id,
                "level": l.level,
                "module": l.module,
                "message": l.message,
                "created_at": (l.created_at.isoformat() + 'Z') if l.created_at else None,
            }
            for l in logs
        ]
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get overall dashboard stats."""
    from app.main import trading_engine
    repo = TradeRepository(db)
    mode = "paper" if trading_engine.is_paper else "live"
    today_stats = repo.get_daily_stats(target_date=date.today(), mode=mode)

    # In live mode, show total portfolio value (all assets converted to USDT)
    if trading_engine.is_paper:
        balance = trading_engine.get_balance()
    else:
        balance = trading_engine.binance.get_total_portfolio_usdt()

    return {
        "balance": balance,
        "mode": mode,
        "bot_active": trading_engine.active,
        "engine_start_time": (trading_engine.start_time.isoformat() + 'Z') if trading_engine.start_time else None,
        "strategy": trading_engine.active_strategy,
        "today": today_stats,
        "risk": {
            "daily_trades": trading_engine.risk_manager.daily_trades,
            "daily_pnl": trading_engine.risk_manager.daily_pnl,
            "emergency_stop": trading_engine.risk_manager.is_emergency,
            "error_count": trading_engine.risk_manager.error_count,
        },
    }
