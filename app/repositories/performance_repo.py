from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.models.performance import PerformanceMetric


class PerformanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_update(self, **kwargs) -> PerformanceMetric:
        existing = (
            self.db.query(PerformanceMetric)
            .filter(
                PerformanceMetric.report_type == kwargs.get("report_type"),
                PerformanceMetric.report_date == kwargs.get("report_date"),
                PerformanceMetric.mode == kwargs.get("mode", "paper"),
            )
            .first()
        )

        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        metric = PerformanceMetric(**kwargs)
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def get_daily(self, target_date: date, mode: str = "paper") -> Optional[PerformanceMetric]:
        return (
            self.db.query(PerformanceMetric)
            .filter(
                PerformanceMetric.report_type == "daily",
                PerformanceMetric.report_date == target_date,
                PerformanceMetric.mode == mode,
            )
            .first()
        )

    def get_recent(self, report_type: str = "daily", limit: int = 30, mode: str = "paper") -> list[PerformanceMetric]:
        return (
            self.db.query(PerformanceMetric)
            .filter(
                PerformanceMetric.report_type == report_type,
                PerformanceMetric.mode == mode,
            )
            .order_by(PerformanceMetric.report_date.desc())
            .limit(limit)
            .all()
        )
