from datetime import datetime
from sqlalchemy import String, Numeric, Enum, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(
        Enum("LONG", "SHORT"), nullable=False, default="LONG"
    )
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    stop_loss: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    trailing_stop: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("open", "closed"), nullable=False, default="open"
    )
    mode: Mapped[str] = mapped_column(
        Enum("paper", "live"), nullable=False, default="paper"
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
