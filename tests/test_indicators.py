import pandas as pd
import numpy as np
import pytest

from app.indicators.ema_sma import EMAIndicator, SMAIndicator
from app.indicators.rsi import RSIIndicator
from app.indicators.macd import MACDIndicator
from app.indicators.volume import VolumeIndicator
from app.indicators.support_resistance import SupportResistanceIndicator


def make_ohlcv(n=100, base_price=100.0, seed=42):
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(seed)
    closes = base_price + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open": closes - np.random.rand(n) * 0.3,
        "high": closes + np.abs(np.random.randn(n)) * 0.5,
        "low": closes - np.abs(np.random.randn(n)) * 0.5,
        "close": closes,
        "volume": np.random.randint(100, 10000, n).astype(float),
    })
    return df


class TestEMAIndicator:
    def test_calculate_adds_columns(self):
        df = make_ohlcv()
        ema = EMAIndicator(fast_period=9, slow_period=21)
        result = ema.calculate(df)
        assert "ema_9" in result.columns
        assert "ema_21" in result.columns
        assert "ema_crossover" in result.columns
        assert "ema_crossover_signal" in result.columns

    def test_ema_values_are_valid(self):
        df = make_ohlcv()
        ema = EMAIndicator(fast_period=9, slow_period=21)
        result = ema.calculate(df)
        assert not result["ema_9"].isna().all()
        assert not result["ema_21"].isna().all()

    def test_crossover_is_binary(self):
        df = make_ohlcv()
        ema = EMAIndicator()
        result = ema.calculate(df)
        assert set(result["ema_crossover"].dropna().unique()).issubset({0, 1})


class TestSMAIndicator:
    def test_calculate_adds_columns(self):
        df = make_ohlcv()
        sma = SMAIndicator(fast_period=10, slow_period=20)
        result = sma.calculate(df)
        assert "sma_10" in result.columns
        assert "sma_20" in result.columns

    def test_sma_has_nan_for_warmup(self):
        df = make_ohlcv(n=30)
        sma = SMAIndicator(fast_period=10, slow_period=20)
        result = sma.calculate(df)
        assert result["sma_20"].isna().sum() == 19


class TestRSIIndicator:
    def test_calculate_adds_rsi(self):
        df = make_ohlcv()
        rsi = RSIIndicator()
        result = rsi.calculate(df)
        assert "rsi" in result.columns
        assert "rsi_overbought" in result.columns
        assert "rsi_oversold" in result.columns

    def test_rsi_in_valid_range(self):
        df = make_ohlcv()
        rsi = RSIIndicator()
        result = rsi.calculate(df)
        valid = result["rsi"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


class TestMACDIndicator:
    def test_calculate_adds_columns(self):
        df = make_ohlcv()
        macd = MACDIndicator()
        result = macd.calculate(df)
        assert "macd_line" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns
        assert "macd_crossover_signal" in result.columns


class TestVolumeIndicator:
    def test_calculate_adds_columns(self):
        df = make_ohlcv()
        vol = VolumeIndicator()
        result = vol.calculate(df)
        assert "volume_sma" in result.columns
        assert "volume_ratio" in result.columns
        assert "volume_spike" in result.columns
        assert "obv" in result.columns

    def test_obv_length_matches(self):
        df = make_ohlcv()
        vol = VolumeIndicator()
        result = vol.calculate(df)
        assert len(result["obv"]) == len(df)


class TestSupportResistanceIndicator:
    def test_calculate_adds_columns(self):
        df = make_ohlcv()
        sr = SupportResistanceIndicator()
        result = sr.calculate(df)
        assert "support" in result.columns
        assert "resistance" in result.columns
        assert "pivot" in result.columns
        assert "near_support" in result.columns
        assert "near_resistance" in result.columns
