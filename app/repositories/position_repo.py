from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.position import Position


class PositionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Position:
        position = Position(**kwargs)
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def get_open_positions(self, mode: str = None) -> list[Position]:
        q = self.db.query(Position).filter(Position.status == "open")
        if mode:
            q = q.filter(Position.mode == mode)
        return q.all()

    def get_open_position(self, pair: str, mode: str = None) -> Optional[Position]:
        q = self.db.query(Position).filter(
            Position.pair == pair,
            Position.status == "open",
        )
        if mode:
            q = q.filter(Position.mode == mode)
        return q.first()

    def close_position(
        self, position_id: int, current_price: float = None
    ) -> Optional[Position]:
        pos = self.db.query(Position).filter(Position.id == position_id).first()
        if pos:
            pos.status = "closed"
            pos.closed_at = datetime.utcnow()
            if current_price:
                pos.current_price = current_price
                pos.unrealized_pnl = (
                    (current_price - float(pos.entry_price)) * float(pos.quantity)
                )
            self.db.commit()
            self.db.refresh(pos)
        return pos

    def update_price(self, position_id: int, current_price: float, trailing_stop: float = None):
        pos = self.db.query(Position).filter(Position.id == position_id).first()
        if pos:
            pos.current_price = current_price
            pos.unrealized_pnl = (
                (current_price - float(pos.entry_price)) * float(pos.quantity)
            )
            if trailing_stop is not None:
                pos.trailing_stop = trailing_stop
            self.db.commit()

    def get_all_closed(self, limit: int = 100) -> list[Position]:
        return (
            self.db.query(Position)
            .filter(Position.status == "closed")
            .order_by(Position.closed_at.desc())
            .limit(limit)
            .all()
        )
