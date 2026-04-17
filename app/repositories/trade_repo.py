from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.trade import Trade


class TradeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Trade:
        trade = Trade(**kwargs)
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def get_by_id(self, trade_id: int) -> Optional[Trade]:
        return self.db.query(Trade).filter(Trade.id == trade_id).first()

    def get_recent(self, limit: int = 50, mode: str = None) -> list[Trade]:
        q = self.db.query(Trade)
        if mode:
            q = q.filter(Trade.mode == mode)
        return q.order_by(Trade.created_at.desc()).limit(limit).all()

    def get_by_pair(self, pair: str, limit: int = 50) -> list[Trade]:
        return (
            self.db.query(Trade)
            .filter(Trade.pair == pair)
            .order_by(Trade.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_today_trades(self, mode: str = None) -> list[Trade]:
        today = date.today()
        q = self.db.query(Trade).filter(
            func.date(Trade.created_at) == today
        )
        if mode:
            q = q.filter(Trade.mode == mode)
        return q.all()

    def get_trades_between(
        self, start: datetime, end: datetime, mode: str = None
    ) -> list[Trade]:
        q = self.db.query(Trade).filter(
            Trade.created_at >= start,
            Trade.created_at <= end,
        )
        if mode:
            q = q.filter(Trade.mode == mode)
        return q.order_by(Trade.created_at.asc()).all()

    def get_daily_stats(self, target_date: date = None, mode: str = None) -> dict:
        target_date = target_date or date.today()
        q = self.db.query(Trade).filter(
            func.date(Trade.created_at) == target_date
        )
        if mode:
            q = q.filter(Trade.mode == mode)
        trades = q.all()

        sell_trades = [t for t in trades if t.side == "SELL" and t.pnl is not None]
        total = len(sell_trades)
        winners = [t for t in sell_trades if float(t.pnl) > 0]
        losers = [t for t in sell_trades if float(t.pnl) <= 0]

        gross_profit = sum(float(t.pnl) for t in winners)
        gross_loss = abs(sum(float(t.pnl) for t in losers))

        return {
            "date": target_date.isoformat(),
            "total_trades": total,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": round(len(winners) / total * 100, 2) if total else 0,
            "net_profit": round(gross_profit - gross_loss, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(
                gross_profit / gross_loss, 4
            ) if gross_loss > 0 else 0,
        }
