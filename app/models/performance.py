from datetime import date, datetime
from sqlalchemy import String, Numeric, Enum, DateTime, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(
        Enum("daily", "weekly"), nullable=False
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    net_profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    gross_profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    gross_loss: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    max_drawdown: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    mode: Mapped[str] = mapped_column(
        Enum("paper", "live"), nullable=False, default="paper"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
