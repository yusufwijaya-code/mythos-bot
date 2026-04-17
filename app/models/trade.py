from datetime import datetime
from sqlalchemy import String, Numeric, Enum, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(Enum("BUY", "SELL"), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    pnl: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    mode: Mapped[str] = mapped_column(
        Enum("paper", "live"), nullable=False, default="paper"
    )
    order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
