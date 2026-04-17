from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class SignalResult:
    action: str  # "BUY", "SELL", "HOLD"
    pair: str
    strategy: str
    confidence: float = 0.0
    indicators: Optional[dict] = None
    reason: str = ""


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    name: str = "base"

    @abstractmethod
    def analyze(self, df: pd.DataFrame, pair: str) -> SignalResult:
        """Analyze market data and return a signal.

        Args:
            df: OHLCV dataframe with calculated indicators
            pair: Trading pair symbol

        Returns:
            SignalResult with action, confidence, and indicator data
        """
        pass

    def validate_data(self, df: pd.DataFrame, min_rows: int = 50) -> bool:
        """Check if dataframe has enough data for analysis."""
        return len(df) >= min_rows and not df.empty
