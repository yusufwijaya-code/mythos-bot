import pandas as pd
from loguru import logger

from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.ema_sma import EMAIndicator
from app.indicators.rsi import RSIIndicator
from app.indicators.macd import MACDIndicator
from app.indicators.volume import VolumeIndicator


class EMACrossoverStrategy(BaseStrategy):
    """EMA Crossover with trend filter, RSI momentum, MACD, and Volume confirmation.

    Improvements over original:
    - EMA 21/55 instead of 9/21 (less noise, fewer false signals)
    - 200 EMA trend filter: only BUY when price > EMA200 (uptrend context)
    - RSI 45-65 for BUY (momentum zone, avoids chasing overbought)
    - MACD histogram must be positive AND growing (momentum confirmation)
    - Volume ratio >= 1.1 (above average volume)
    - Stricter entry: requires 4+ out of 5 conditions
    """

    name = "ema_crossover"

    def __init__(
        self,
        ema_fast: int = 21,
        ema_slow: int = 55,
        rsi_period: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
    ):
        self.ema = EMAIndicator(fast_period=ema_fast, slow_period=ema_slow)
        self.rsi = RSIIndicator(
            period=rsi_period, overbought=rsi_overbought, oversold=rsi_oversold
        )
        self.macd = MACDIndicator()
        self.volume = VolumeIndicator()

    def analyze(self, df: pd.DataFrame, pair: str) -> SignalResult:
        if not self.validate_data(df):
            return SignalResult(
                action="HOLD", pair=pair, strategy=self.name, reason="Insufficient data"
            )

        df = self.ema.calculate(df.copy())
        df = self.rsi.calculate(df)
        df = self.macd.calculate(df)
        df = self.volume.calculate(df)

        # Add 200 EMA trend filter inline
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        indicators = {
            "ema_fast": round(float(last.get(f"ema_{self.ema.fast_period}", 0)), 2),
            "ema_slow": round(float(last.get(f"ema_{self.ema.slow_period}", 0)), 2),
            "ema_200": round(float(last.get("ema_200", 0)), 2),
            "rsi": round(float(last.get("rsi", 50)), 2),
            "macd_histogram": round(float(last.get("macd_histogram", 0)), 4),
            "volume_ratio": round(float(last.get("volume_ratio", 1)), 2),
            "close": round(float(last["close"]), 2),
        }

        close_price = float(last["close"])
        ema_200 = float(last.get("ema_200", 0))
        rsi_val = float(last.get("rsi", 50))
        macd_hist = float(last.get("macd_histogram", 0))
        prev_macd_hist = float(prev.get("macd_histogram", 0))
        vol_ratio = float(last.get("volume_ratio", 1))

        # BUY conditions
        # Use EMA position state (fast > slow), not just the rare crossover event
        ema_bullish = last.get("ema_crossover", 0) == 1  # fast EMA currently above slow
        price_above_200ema = close_price > ema_200 if ema_200 > 0 else True
        rsi_momentum = 45.0 <= rsi_val <= 65.0  # Rising momentum zone
        macd_positive = macd_hist > 0
        macd_growing = macd_hist > prev_macd_hist  # Histogram expanding upward
        volume_ok = vol_ratio >= 1.1

        # SELL conditions
        ema_bearish = last.get("ema_crossover", 0) == 0  # fast EMA currently below slow
        rsi_overbought = rsi_val > self.rsi.overbought   # RSI > 70
        macd_turning_neg = macd_hist < 0 and prev_macd_hist >= 0  # Momentum reversal
        # Soft exit: covers RSI 65-70 gap where neither BUY nor SELL would otherwise trigger.
        # If RSI is above buy zone AND MACD momentum is fading, exit early.
        rsi_elevated = rsi_val > 65
        macd_declining = macd_hist < prev_macd_hist and macd_hist > 0
        momentum_fading = rsi_elevated and macd_declining

        buy_score = sum([rsi_momentum, macd_positive, macd_growing, volume_ok, price_above_200ema])
        sell_score = sum([ema_bearish, rsi_overbought, macd_turning_neg, momentum_fading])

        # BUY: fast EMA above slow + price in uptrend + 4+ indicator confirmations
        if ema_bullish and price_above_200ema and buy_score >= 4:
            confidence = min((buy_score + 1) / 6 * 100, 95)
            reasons = ["EMA21 > EMA55 (bullish)"]
            if rsi_momentum:
                reasons.append(f"RSI={indicators['rsi']} (momentum)")
            if macd_growing:
                reasons.append("MACD expanding")
            if volume_ok:
                reasons.append(f"Vol={indicators['volume_ratio']}x")
            reasons.append("Above EMA200")

            logger.info(f"[{pair}] BUY signal: {', '.join(reasons)}")
            return SignalResult(
                action="BUY",
                pair=pair,
                strategy=self.name,
                confidence=confidence,
                indicators=indicators,
                reason=", ".join(reasons),
            )

        # SELL: bearish EMA | RSI overbought | MACD reversal | momentum fading
        if sell_score >= 1:
            confidence = min(sell_score / 4 * 100, 95)
            reasons = []
            if ema_bearish:
                reasons.append("EMA21 < EMA55 (bearish)")
            if rsi_overbought:
                reasons.append(f"RSI overbought={indicators['rsi']}")
            if macd_turning_neg:
                reasons.append("MACD momentum reversal")
            if momentum_fading:
                reasons.append(f"RSI={indicators['rsi']} elevated + MACD fading")

            logger.info(f"[{pair}] SELL signal: {', '.join(reasons)}")
            return SignalResult(
                action="SELL",
                pair=pair,
                strategy=self.name,
                confidence=confidence,
                indicators=indicators,
                reason=", ".join(reasons),
            )

        return SignalResult(
            action="HOLD",
            pair=pair,
            strategy=self.name,
            confidence=0,
            indicators=indicators,
            reason="No clear signal",
        )
