from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):
    """Base class for all technical indicators."""

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicator and add columns to dataframe.

        Args:
            df: OHLCV dataframe with columns: open, high, low, close, volume

        Returns:
            DataFrame with added indicator columns
        """
        pass
