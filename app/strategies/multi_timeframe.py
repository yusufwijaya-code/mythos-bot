import pandas as pd
from loguru import logger
from typing import Dict

from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.ema_sma import EMAIndicator
from app.indicators.rsi import RSIIndicator
from app.indicators.macd import MACDIndicator
from app.indicators.support_resistance import SupportResistanceIndicator


class MultiTimeframeStrategy(BaseStrategy):
    """Multi-timeframe confirmation strategy.

    Uses higher timeframe for trend direction and lower timeframe for entry.
    """

    name = "multi_timeframe"

    def __init__(self):
        self.ema = EMAIndicator(fast_period=9, slow_period=21)
        self.rsi = RSIIndicator()
        self.macd = MACDIndicator()
        self.sr = SupportResistanceIndicator()

    def analyze_timeframe(self, df: pd.DataFrame) -> dict:
        """Analyze a single timeframe and return signals dict."""
        df = self.ema.calculate(df.copy())
        df = self.rsi.calculate(df)
        df = self.macd.calculate(df)
        df = self.sr.calculate(df)

        last = df.iloc[-1]
        ema_fast_col = f"ema_{self.ema.fast_period}"
        ema_slow_col = f"ema_{self.ema.slow_period}"

        fast_above_slow = last.get(ema_fast_col, 0) > last.get(ema_slow_col, 0)
        return {
            "trend": "bullish" if fast_above_slow else "bearish",
            "rsi": float(last.get("rsi", 50)),
            "macd_histogram": float(last.get("macd_histogram", 0)),
            "near_support": bool(last.get("near_support", 0)),
            "near_resistance": bool(last.get("near_resistance", 0)),
            "ema_bullish": int(fast_above_slow),   # 1 = fast > slow (position state)
            "ema_crossover_signal": float(last.get("ema_crossover_signal", 0)),
            "close": float(last["close"]),
        }

    def analyze(self, df: pd.DataFrame, pair: str) -> SignalResult:
        """Analyze using primary timeframe data.

        For multi-TF, the caller should provide higher TF data via analyze_multi().
        This method works as a single-TF fallback.
        """
        return self.analyze_multi({"primary": df}, pair)

    def analyze_multi(
        self, timeframes: Dict[str, pd.DataFrame], pair: str
    ) -> SignalResult:
        """Analyze multiple timeframes for confirmation.

        Args:
            timeframes: Dict with keys like 'primary' (entry TF) and 'higher' (trend TF)
            pair: Trading pair
        """
        primary_df = timeframes.get("primary")
        higher_df = timeframes.get("higher", primary_df)

        if primary_df is None or not self.validate_data(primary_df):
            return SignalResult(
                action="HOLD", pair=pair, strategy=self.name,
                reason="Insufficient data"
            )

        primary = self.analyze_timeframe(primary_df)
        higher = self.analyze_timeframe(higher_df) if higher_df is not primary_df else primary

        indicators = {
            "primary_trend": primary["trend"],
            "higher_trend": higher["trend"],
            "primary_rsi": round(primary["rsi"], 2),
            "higher_rsi": round(higher["rsi"], 2),
            "primary_macd_hist": round(primary["macd_histogram"], 4),
            "close": primary["close"],
        }

        # BUY: Higher TF bullish + primary TF in bullish EMA state + confirmations
        buy_conditions = [
            higher["trend"] == "bullish",
            primary["ema_bullish"] == 1,   # fast EMA above slow (not just crossover event)
            primary["rsi"] < 65,
            primary["macd_histogram"] > 0,
            primary["near_support"],
        ]

        # SELL: Higher TF bearish + primary TF in bearish EMA state + confirmations
        sell_conditions = [
            higher["trend"] == "bearish",
            primary["ema_bullish"] == 0,   # fast EMA below slow
            primary["rsi"] > 35,
            primary["macd_histogram"] < 0,
            primary["near_resistance"],
        ]

        buy_score = sum(buy_conditions)
        sell_score = sum(sell_conditions)

        if buy_score >= 3 and higher["trend"] == "bullish":
            confidence = min(buy_score / 5 * 100, 95)
            logger.info(
                f"[{pair}] MTF BUY: higher={higher['trend']}, "
                f"RSI={primary['rsi']:.1f}, score={buy_score}/5"
            )
            return SignalResult(
                action="BUY",
                pair=pair,
                strategy=self.name,
                confidence=confidence,
                indicators=indicators,
                reason=f"MTF bullish confirmation (score={buy_score}/5)",
            )

        if sell_score >= 3 and higher["trend"] == "bearish":
            confidence = min(sell_score / 5 * 100, 95)
            logger.info(
                f"[{pair}] MTF SELL: higher={higher['trend']}, "
                f"RSI={primary['rsi']:.1f}, score={sell_score}/5"
            )
            return SignalResult(
                action="SELL",
                pair=pair,
                strategy=self.name,
                confidence=confidence,
                indicators=indicators,
                reason=f"MTF bearish confirmation (score={sell_score}/5)",
            )

        return SignalResult(
            action="HOLD",
            pair=pair,
            strategy=self.name,
            confidence=0,
            indicators=indicators,
            reason="No multi-TF confirmation",
        )
