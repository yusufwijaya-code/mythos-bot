import pandas as pd
from app.indicators.base import BaseIndicator


class VolumeIndicator(BaseIndicator):
    def __init__(self, period: int = 20, threshold: float = 1.5):
        self.period = period
        self.threshold = threshold

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df["volume_sma"] = df["volume"].rolling(window=self.period).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"].replace(0, 1e-10)
        df["volume_spike"] = (df["volume_ratio"] >= self.threshold).astype(int)

        # OBV (On Balance Volume)
        obv = [0.0]
        for i in range(1, len(df)):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                obv.append(obv[-1] + df["volume"].iloc[i])
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                obv.append(obv[-1] - df["volume"].iloc[i])
            else:
                obv.append(obv[-1])
        df["obv"] = obv
        return df
