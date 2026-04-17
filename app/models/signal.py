from datetime import datetime
from sqlalchemy import String, Numeric, Enum, DateTime, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(Enum("BUY", "SELL", "HOLD"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    indicators: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
