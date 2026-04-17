from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.signal import Signal


class SignalRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Signal:
        signal = Signal(**kwargs)
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def get_recent(self, limit: int = 50) -> list[Signal]:
        return (
            self.db.query(Signal)
            .order_by(Signal.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_pair(self, pair: str, limit: int = 20) -> list[Signal]:
        return (
            self.db.query(Signal)
            .filter(Signal.pair == pair)
            .order_by(Signal.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_last_signal(self, pair: str) -> Optional[Signal]:
        return (
            self.db.query(Signal)
            .filter(Signal.pair == pair, Signal.action != "HOLD")
            .order_by(Signal.created_at.desc())
            .first()
        )

    def mark_executed(self, signal_id: int):
        signal = self.db.query(Signal).filter(Signal.id == signal_id).first()
        if signal:
            signal.executed = True
            self.db.commit()
