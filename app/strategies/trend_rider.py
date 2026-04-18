import pandas as pd
from loguru import logger

from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.ema_sma import EMAIndicator
from app.indicators.rsi import RSIIndicator
from app.indicators.macd import MACDIndicator
from app.indicators.volume import VolumeIndicator


class TrendRiderStrategy(BaseStrategy):
    """Trend Rider: 1H macro trend filter + 5M EMA crossover precision entry.

    Two-layer system
    ─────────────────────────────────────────────────────────────
    LAYER 1 — 1H Trend (the 'highway')
      EMA 200 : defines the primary bull/bear market context
      EMA 50  : confirms mid-term momentum direction
      EMA 50 slope : ensures the trend is still alive, not stalling
      Rule: only trade BUY when the highway is pointing UP

    LAYER 2 — 5M Entry (the 'on-ramp')
      EMA 21/55 crossover : short-term momentum state
      RSI 40-70           : momentum zone (avoid chasing / overbought)
      MACD histogram      : positive and expanding = acceleration
      Volume ratio >= 1.0 : smart money participating

    BUY fires when:
      • 1H: price above EMA200 (non-negotiable)
      • 1H: trend score >= 2/4  (e.g. golden zone + slope up)
      • 5M: EMA21 currently above EMA55 (bullish position)
      • 5M: buy score >= 3/5 indicators confirm

    SELL fires when ANY of:
      • 1H price drops below EMA200 (trend broken → exit fast, +3 score)
      • 1H death zone (EMA50 < EMA200 + slope down, +2 score)
      • 5M EMA bearish crossover (+1)
      • 5M RSI > 73 overbought (+1)
      • 5M MACD turns negative or reverses (+1)
      → Fires when sell_score >= 2
    """

    name = "trend_rider"
    requires_multi_tf = True  # Signal to engine to fetch both TFs
    trend_tf = "1h"           # Higher TF: trend direction
    entry_tf = "5m"           # Lower TF: entry timing

    def __init__(self):
        # 5M indicators
        self.ema_entry = EMAIndicator(fast_period=21, slow_period=55)
        self.rsi = RSIIndicator(period=14, overbought=73, oversold=30)
        self.macd = MACDIndicator()
        self.volume = VolumeIndicator()

    # ─── 1H Trend Layer ───────────────────────────────────────────────────────

    def _analyze_1h_trend(self, df: pd.DataFrame) -> dict:
        """Analyze 1H chart for macro trend direction using EMA 50/200."""
        df = df.copy()
        df["ema_21"]  = df["close"].ewm(span=21,  adjust=False).mean()
        df["ema_50"]  = df["close"].ewm(span=50,  adjust=False).mean()
        df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

        last = df.iloc[-1]
        close   = float(last["close"])
        ema_21  = float(last["ema_21"])
        ema_50  = float(last["ema_50"])
        ema_200 = float(last["ema_200"])

        # EMA50 slope over last 5 candles (% change) — detects momentum fade
        slope_window = 5
        if len(df) > slope_window + 1:
            ema50_now  = float(df["ema_50"].iloc[-1])
            ema50_past = float(df["ema_50"].iloc[-(slope_window + 1)])
            slope_pct  = (ema50_now - ema50_past) / ema50_past * 100 if ema50_past else 0.0
        else:
            slope_pct = 0.0

        above_ema200  = close  > ema_200   # Primary: in bull market zone
        above_ema50   = close  > ema_50    # Secondary: strong bull momentum
        golden_zone   = ema_50 > ema_200   # Golden cross confirmed (EMA50 > EMA200)
        slope_up      = slope_pct > 0.03   # EMA50 still rising (>0.03% over 5 bars)

        # Bearish flags
        below_ema200  = close  < ema_200
        death_zone    = ema_50 < ema_200
        slope_down    = slope_pct < -0.03

        score = sum([above_ema200, above_ema50, golden_zone, slope_up])

        return {
            "close":         round(close,   6),
            "ema_21":        round(ema_21,  6),
            "ema_50":        round(ema_50,  6),
            "ema_200":       round(ema_200, 6),
            "slope_pct":     round(slope_pct, 4),
            "above_ema200":  above_ema200,
            "above_ema50":   above_ema50,
            "golden_zone":   golden_zone,
            "slope_up":      slope_up,
            "below_ema200":  below_ema200,
            "death_zone":    death_zone,
            "slope_down":    slope_down,
            "score":         score,
        }

    # ─── 5M Entry Layer ───────────────────────────────────────────────────────

    def _analyze_5m_entry(self, df: pd.DataFrame) -> dict:
        """Analyze 5M chart for entry timing using EMA crossover + indicators."""
        df = df.copy()
        df = self.ema_entry.calculate(df)
        df = self.rsi.calculate(df)
        df = self.macd.calculate(df)
        df = self.volume.calculate(df)

        last  = df.iloc[-1]
        prev  = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) > 3 else prev

        rsi_val         = float(last.get("rsi", 50))
        macd_hist       = float(last.get("macd_histogram", 0))
        prev_hist       = float(prev.get("macd_histogram", 0))
        prev2_hist      = float(prev2.get("macd_histogram", 0))
        vol_ratio       = float(last.get("volume_ratio", 1))
        ema_21          = float(last.get("ema_21", 0))
        ema_55          = float(last.get("ema_55", 0))
        prev_ema_21     = float(prev.get("ema_21", 0))
        prev_ema_55     = float(prev.get("ema_55", 0))

        # Position state (not just the rare crossover tick)
        ema_bullish     = ema_21 > ema_55
        ema_bearish     = ema_21 < ema_55

        # Fresh crossover this candle (bonus signal — stronger entry)
        ema_just_crossed_up   = ema_bullish and prev_ema_21 <= prev_ema_55
        ema_just_crossed_down = ema_bearish and prev_ema_21 >= prev_ema_55

        # BUY conditions (each +1 to score)
        rsi_momentum      = 40 <= rsi_val <= 70
        macd_positive     = macd_hist > 0
        macd_growing      = macd_hist > prev_hist
        macd_accelerating = macd_hist > prev_hist > prev2_hist  # Three candles of growth
        volume_ok         = vol_ratio >= 1.0

        # SELL conditions
        rsi_overbought   = rsi_val > 73
        macd_negative    = macd_hist < 0
        macd_reversing   = macd_hist < prev_hist and prev_hist > 0  # Peak passed

        buy_score = sum([ema_bullish, rsi_momentum, macd_positive, macd_growing, volume_ok])
        # Bonus: fresh crossover + triple acceleration = stronger conviction
        buy_bonus = (0.5 if ema_just_crossed_up else 0) + (0.5 if macd_accelerating else 0)

        sell_score = sum([ema_bearish, rsi_overbought, macd_negative, macd_reversing])

        return {
            "ema_21":              round(ema_21, 6),
            "ema_55":              round(ema_55, 6),
            "rsi":                 round(rsi_val, 2),
            "macd_histogram":      round(macd_hist, 6),
            "volume_ratio":        round(vol_ratio, 2),
            "ema_bullish":         ema_bullish,
            "ema_bearish":         ema_bearish,
            "ema_just_crossed_up": ema_just_crossed_up,
            "rsi_momentum":        rsi_momentum,
            "rsi_overbought":      rsi_overbought,
            "macd_positive":       macd_positive,
            "macd_growing":        macd_growing,
            "macd_accelerating":   macd_accelerating,
            "macd_reversing":      macd_reversing,
            "volume_ok":           volume_ok,
            "buy_score":           round(buy_score + buy_bonus, 1),
            "sell_score":          sell_score,
        }

    # ─── Public interface ─────────────────────────────────────────────────────

    def analyze(self, df: pd.DataFrame, pair: str) -> SignalResult:
        """Single-TF fallback — Trend Rider requires multi-TF mode."""
        return SignalResult(
            action="HOLD", pair=pair, strategy=self.name,
            reason="Trend Rider requires 1H+5M data — use analyze_multi()"
        )

    def analyze_multi(
        self, df_entry: pd.DataFrame, df_trend: pd.DataFrame, pair: str
    ) -> SignalResult:
        """Core logic: combine 1H trend + 5M entry signal."""
        if not self.validate_data(df_entry, min_rows=60):
            return SignalResult(
                action="HOLD", pair=pair, strategy=self.name,
                reason="Insufficient 5M data (need 60+ candles)"
            )
        if not self.validate_data(df_trend, min_rows=210):
            return SignalResult(
                action="HOLD", pair=pair, strategy=self.name,
                reason="Insufficient 1H data (need 210+ candles for EMA200)"
            )

        tf1h = self._analyze_1h_trend(df_trend)
        tf5m = self._analyze_5m_entry(df_entry)

        indicators = {
            # 1H
            "1h_ema_50":      tf1h["ema_50"],
            "1h_ema_200":     tf1h["ema_200"],
            "1h_slope_pct":   tf1h["slope_pct"],
            "1h_score":       tf1h["score"],
            "1h_above_ema200": tf1h["above_ema200"],
            "1h_golden_zone": tf1h["golden_zone"],
            # 5M
            "5m_ema_21":      tf5m["ema_21"],
            "5m_ema_55":      tf5m["ema_55"],
            "5m_rsi":         tf5m["rsi"],
            "5m_macd_hist":   tf5m["macd_histogram"],
            "5m_vol_ratio":   tf5m["volume_ratio"],
            "5m_buy_score":   tf5m["buy_score"],
            "5m_fresh_cross": tf5m["ema_just_crossed_up"],
        }

        # ═══════════════════════════════════════════════════════════════════
        # BUY — 1H highway is UP + 5M shows bullish entry
        # ═══════════════════════════════════════════════════════════════════
        trend_ok    = tf1h["above_ema200"] and tf1h["score"] >= 2
        entry_ready = tf5m["ema_bullish"] and tf5m["buy_score"] >= 3.0

        if trend_ok and entry_ready:
            # Confidence: 1H provides 40%, 5M provides 60% (entry timing weighs more)
            h1_conf  = tf1h["score"] / 4.0 * 40
            m5_conf  = min(tf5m["buy_score"] / 5.5, 1.0) * 60
            confidence = min(h1_conf + m5_conf, 95.0)

            reasons = []
            if tf1h["above_ema200"]:
                reasons.append(f"1H above EMA200 ({tf1h['ema_200']:.4f})")
            if tf1h["golden_zone"]:
                reasons.append("1H golden zone")
            if tf1h["slope_up"]:
                reasons.append(f"1H slope +{tf1h['slope_pct']:.2f}%")
            if tf5m["ema_just_crossed_up"]:
                reasons.append("5M fresh EMA crossover ▲")
            elif tf5m["ema_bullish"]:
                reasons.append("5M EMA21>EMA55")
            if tf5m["rsi_momentum"]:
                reasons.append(f"5M RSI={tf5m['rsi']:.1f}")
            if tf5m["macd_accelerating"]:
                reasons.append("5M MACD accelerating")
            elif tf5m["macd_growing"]:
                reasons.append("5M MACD growing")
            if tf5m["volume_ok"]:
                reasons.append(f"5M Vol={tf5m['volume_ratio']:.1f}x")

            logger.info(
                f"[{pair}] TREND RIDER BUY | "
                f"1H={tf1h['score']}/4 | 5M={tf5m['buy_score']}/5 | "
                f"conf={confidence:.0f}% | {' + '.join(reasons[:3])}"
            )
            return SignalResult(
                action="BUY",
                pair=pair,
                strategy=self.name,
                confidence=confidence,
                indicators=indicators,
                reason=" + ".join(reasons),
            )

        # ═══════════════════════════════════════════════════════════════════
        # SELL — 1H trend breaks down OR 5M exhausted
        # ═══════════════════════════════════════════════════════════════════
        sell_reasons = []
        sell_score   = 0

        # 1H macro breaks — high urgency
        if tf1h["below_ema200"]:
            sell_reasons.append(f"1H price below EMA200 ({tf1h['ema_200']:.4f}) — trend broken")
            sell_score += 3  # Instant trigger: trend is over

        if tf1h["death_zone"] and tf1h["slope_down"]:
            sell_reasons.append(f"1H death zone (EMA50<EMA200, slope {tf1h['slope_pct']:.2f}%)")
            sell_score += 2

        # 5M exhaustion signals
        if tf5m["ema_bearish"]:
            sell_reasons.append("5M EMA21<EMA55 (bearish crossover)")
            sell_score += 1
        if tf5m["rsi_overbought"]:
            sell_reasons.append(f"5M RSI={tf5m['rsi']:.1f} overbought")
            sell_score += 1
        if tf5m["macd_negative"]:
            sell_reasons.append("5M MACD negative")
            sell_score += 1
        elif tf5m["macd_reversing"]:
            sell_reasons.append("5M MACD reversing")
            sell_score += 1

        if sell_score >= 2:
            confidence = min(sell_score / 6.0 * 100, 95.0)
            logger.info(
                f"[{pair}] TREND RIDER SELL | "
                f"sell_score={sell_score} | {' + '.join(sell_reasons[:2])}"
            )
            return SignalResult(
                action="SELL",
                pair=pair,
                strategy=self.name,
                confidence=confidence,
                indicators=indicators,
                reason=" + ".join(sell_reasons),
            )

        # ═══════════════════════════════════════════════════════════════════
        # HOLD
        # ═══════════════════════════════════════════════════════════════════
        logger.debug(
            f"[{pair}] HOLD | 1H={tf1h['score']}/4 above200={tf1h['above_ema200']} | "
            f"5M buy={tf5m['buy_score']:.1f}/5 ema_bull={tf5m['ema_bullish']}"
        )
        return SignalResult(
            action="HOLD",
            pair=pair,
            strategy=self.name,
            confidence=0,
            indicators=indicators,
            reason=f"1H={tf1h['score']}/4 (above200={tf1h['above_ema200']}) | "
                   f"5M buy={tf5m['buy_score']:.1f}/5",
        )
