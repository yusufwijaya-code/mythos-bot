import pandas as pd
import numpy as np
import pytest

from app.strategies.ema_crossover import EMACrossoverStrategy
from app.strategies.multi_timeframe import MultiTimeframeStrategy
from app.strategies.base import SignalResult


def make_ohlcv(n=100, base_price=100.0, seed=42):
    np.random.seed(seed)
    closes = base_price + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open": closes - np.random.rand(n) * 0.3,
        "high": closes + np.abs(np.random.randn(n)) * 0.5,
        "low": closes - np.abs(np.random.randn(n)) * 0.5,
        "close": closes,
        "volume": np.random.randint(100, 10000, n).astype(float),
    })


def make_bullish_crossover(n=100):
    """Generate data with a clear bullish EMA crossover at the end."""
    prices = list(range(80, 80 + n))  # Steady uptrend
    # Add some noise at the beginning, then strong uptrend
    for i in range(n // 2):
        prices[i] = 100 - i * 0.2  # Slight downtrend first half
    for i in range(n // 2, n):
        prices[i] = prices[n // 2 - 1] + (i - n // 2) * 0.5  # Strong uptrend

    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open": [p - 0.1 for p in prices],
        "high": [p + 0.3 for p in prices],
        "low": [p - 0.3 for p in prices],
        "close": prices,
        "volume": [5000.0] * n,
    })


class TestEMACrossoverStrategy:
    def test_returns_signal_result(self):
        df = make_ohlcv()
        strategy = EMACrossoverStrategy()
        result = strategy.analyze(df, "BTCUSDT")
        assert isinstance(result, SignalResult)
        assert result.action in ("BUY", "SELL", "HOLD")
        assert result.pair == "BTCUSDT"
        assert result.strategy == "ema_crossover"

    def test_hold_on_insufficient_data(self):
        df = make_ohlcv(n=10)
        strategy = EMACrossoverStrategy()
        result = strategy.analyze(df, "BTCUSDT")
        assert result.action == "HOLD"
        assert "Insufficient data" in result.reason

    def test_signal_has_indicators(self):
        df = make_ohlcv()
        strategy = EMACrossoverStrategy()
        result = strategy.analyze(df, "BTCUSDT")
        if result.indicators:
            assert "rsi" in result.indicators
            assert "close" in result.indicators

    def test_confidence_in_valid_range(self):
        df = make_ohlcv()
        strategy = EMACrossoverStrategy()
        result = strategy.analyze(df, "BTCUSDT")
        assert 0 <= result.confidence <= 100


class TestMultiTimeframeStrategy:
    def test_returns_signal_result(self):
        df = make_ohlcv()
        strategy = MultiTimeframeStrategy()
        result = strategy.analyze(df, "ETHUSDT")
        assert isinstance(result, SignalResult)
        assert result.action in ("BUY", "SELL", "HOLD")
        assert result.strategy == "multi_timeframe"

    def test_multi_with_two_timeframes(self):
        primary = make_ohlcv(n=100, seed=42)
        higher = make_ohlcv(n=100, seed=99)
        strategy = MultiTimeframeStrategy()
        result = strategy.analyze_multi(
            {"primary": primary, "higher": higher}, "BTCUSDT"
        )
        assert isinstance(result, SignalResult)

    def test_hold_on_insufficient_data(self):
        df = make_ohlcv(n=10)
        strategy = MultiTimeframeStrategy()
        result = strategy.analyze(df, "BTCUSDT")
        assert result.action == "HOLD"


class TestBaseStrategy:
    def test_validate_data_enough(self):
        df = make_ohlcv(n=100)
        strategy = EMACrossoverStrategy()
        assert strategy.validate_data(df, min_rows=50) is True

    def test_validate_data_not_enough(self):
        df = make_ohlcv(n=20)
        strategy = EMACrossoverStrategy()
        assert strategy.validate_data(df, min_rows=50) is False
