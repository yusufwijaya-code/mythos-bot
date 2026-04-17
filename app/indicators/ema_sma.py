import pandas as pd
from app.indicators.base import BaseIndicator


class EMAIndicator(BaseIndicator):
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df[f"ema_{self.fast_period}"] = df["close"].ewm(
            span=self.fast_period, adjust=False
        ).mean()
        df[f"ema_{self.slow_period}"] = df["close"].ewm(
            span=self.slow_period, adjust=False
        ).mean()
        df["ema_crossover"] = (
            df[f"ema_{self.fast_period}"] > df[f"ema_{self.slow_period}"]
        ).astype(int)
        df["ema_crossover_signal"] = df["ema_crossover"].diff()
        return df


class SMAIndicator(BaseIndicator):
    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df[f"sma_{self.fast_period}"] = df["close"].rolling(
            window=self.fast_period
        ).mean()
        df[f"sma_{self.slow_period}"] = df["close"].rolling(
            window=self.slow_period
        ).mean()
        df["sma_crossover"] = (
            df[f"sma_{self.fast_period}"] > df[f"sma_{self.slow_period}"]
        ).astype(int)
        df["sma_crossover_signal"] = df["sma_crossover"].diff()
        return df
