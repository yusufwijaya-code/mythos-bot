import pandas as pd
from app.indicators.base import BaseIndicator


class MACDIndicator(BaseIndicator):
    def __init__(
        self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        ema_fast = df["close"].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow_period, adjust=False).mean()

        df["macd_line"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd_line"].ewm(
            span=self.signal_period, adjust=False
        ).mean()
        df["macd_histogram"] = df["macd_line"] - df["macd_signal"]

        # Crossover signals
        df["macd_crossover"] = (df["macd_line"] > df["macd_signal"]).astype(int)
        df["macd_crossover_signal"] = df["macd_crossover"].diff()
        return df
