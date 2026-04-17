import pandas as pd
from app.indicators.base import BaseIndicator


class RSIIndicator(BaseIndicator):
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1 / self.period, min_periods=self.period).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, min_periods=self.period).mean()

        rs = avg_gain / avg_loss.replace(0, 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi_overbought"] = (df["rsi"] >= self.overbought).astype(int)
        df["rsi_oversold"] = (df["rsi"] <= self.oversold).astype(int)
        return df
