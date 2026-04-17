import pandas as pd
import numpy as np
from app.indicators.base import BaseIndicator


class SupportResistanceIndicator(BaseIndicator):
    def __init__(self, lookback: int = 20, tolerance_pct: float = 0.5):
        self.lookback = lookback
        self.tolerance_pct = tolerance_pct

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df["support"] = df["low"].rolling(window=self.lookback).min()
        df["resistance"] = df["high"].rolling(window=self.lookback).max()

        # Distance from support/resistance as percentage
        df["dist_support_pct"] = (
            (df["close"] - df["support"]) / df["support"] * 100
        )
        df["dist_resistance_pct"] = (
            (df["resistance"] - df["close"]) / df["close"] * 100
        )

        # Near support/resistance flags
        df["near_support"] = (df["dist_support_pct"] <= self.tolerance_pct).astype(int)
        df["near_resistance"] = (
            df["dist_resistance_pct"] <= self.tolerance_pct
        ).astype(int)

        # Pivot points
        df["pivot"] = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
        df["pivot_s1"] = 2 * df["pivot"] - df["high"].shift(1)
        df["pivot_r1"] = 2 * df["pivot"] - df["low"].shift(1)

        return df
