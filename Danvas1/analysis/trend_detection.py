"""
Danvas1 - Trend Detection
Version: 1.0.0

Detects and analyzes market trends across multiple timeframes.
"""

import logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class TrendDetector:
    """
    Trend detection and analysis.

    Responsibilities:
    - Detect trend direction and strength
    - Identify trend exhaustion
    - Track trend changes
    - Multi-timeframe trend analysis
    """

    def __init__(self, config: Dict):
        """
        Initialize Trend Detector.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.TrendDetector")
        self.config = config

        # Trend parameters
        self.ema_fast = 9
        self.ema_slow = 21
        self.ema_trend = 50

        self.logger.info("Trend Detector initialized")

    def detect_trend(self, candles: pd.DataFrame) -> Dict:
        """
        Detect current trend.

        Args:
            candles: Candlestick data

        Returns:
            Trend analysis result
        """
        result = {
            'direction': 'neutral',
            'strength': 0,
            'exhaustion': False,
            'details': {}
        }

        try:
            if candles is None or len(candles) < 50:
                return result

            # Calculate EMAs
            ema_fast = self._calculate_ema(candles['close'], self.ema_fast)
            ema_slow = self._calculate_ema(candles['close'], self.ema_slow)
            ema_trend = self._calculate_ema(candles['close'], self.ema_trend)

            latest = candles.iloc[-1]
            close = latest['close']

            # Determine direction
            if close > ema_fast > ema_slow > ema_trend:
                result['direction'] = 'bullish'
            elif close < ema_fast < ema_slow < ema_trend:
                result['direction'] = 'bearish'
            else:
                result['direction'] = 'neutral'

            # Calculate strength
            result['strength'] = self._calculate_strength(
                candles, ema_fast, ema_slow
            )

            # Check for exhaustion
            result['exhaustion'] = self._check_exhaustion(candles)

            result['details'] = {
                'ema_fast': float(ema_fast.iloc[-1]),
                'ema_slow': float(ema_slow.iloc[-1]),
                'ema_trend': float(ema_trend.iloc[-1]),
                'price_vs_ema': float((close - ema_fast.iloc[-1]) / ema_fast.iloc[-1] * 100)
            }

        except Exception as e:
            self.logger.error(f"Error detecting trend: {e}")

        return result

    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_strength(self, candles: pd.DataFrame,
                           ema_fast: pd.Series,
                           ema_slow: pd.Series) -> float:
        """Calculate trend strength (0-1)."""
        try:
            # Calculate distance between EMAs
            ema_distance = (ema_fast - ema_slow) / ema_slow
            avg_distance = ema_distance.abs().iloc[-20:].mean()

            # Normalize to 0-1
            strength = min(avg_distance * 10, 1.0)

            # Adjust based on price momentum
            returns = candles['close'].pct_change().iloc[-14:]
            momentum = returns.mean()

            if abs(momentum) > 0.001:
                strength = min(strength + abs(momentum) * 50, 1.0)

            return float(strength)

        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return 0.5

    def _check_exhaustion(self, candles: pd.DataFrame) -> bool:
        """Check for trend exhaustion signals."""
        try:
            if len(candles) < 20:
                return False

            # Check for divergence
            recent_prices = candles['close'].iloc[-10:]
            recent_highs = candles['high'].iloc[-10:]

            # Price making higher highs but RSI making lower highs
            if len(recent_prices) >= 5:
                price_trend = recent_prices.iloc[-1] > recent_prices.iloc[0]
                high_trend = recent_highs.iloc[-1] > recent_highs.iloc[0]

                if price_trend and not high_trend:
                    return True  # Exhaustion detected

            # Check for large candles against trend
            for i in range(-5, 0):
                candle = candles.iloc[i]
                body = abs(candle['close'] - candle['open'])
                total_range = candle['high'] - candle['low']

                if total_range > 0:
                    body_ratio = body / total_range

                    # Large counter-trend candle
                    if body_ratio > 0.8:
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking exhaustion: {e}")
            return False

    def get_trend_lines(self, candles: pd.DataFrame) -> Dict:
        """
        Calculate trend lines (support/resistance).

        Args:
            candles: Candlestick data

        Returns:
            Trend line data
        """
        result = {
            'support': [],
            'resistance': []
        }

        try:
            if candles is None or len(candles) < 20:
                return result

            # Find swing highs and lows
            highs = []
            lows = []

            for i in range(2, len(candles) - 2):
                # Swing high
                if (candles['high'].iloc[i] > candles['high'].iloc[i-1] and
                    candles['high'].iloc[i] > candles['high'].iloc[i+1] and
                    candles['high'].iloc[i] > candles['high'].iloc[i-2] and
                    candles['high'].iloc[i] > candles['high'].iloc[i+2]):
                    highs.append(candles['high'].iloc[i])

                # Swing low
                if (candles['low'].iloc[i] < candles['low'].iloc[i-1] and
                    candles['low'].iloc[i] < candles['low'].iloc[i+1] and
                    candles['low'].iloc[i] < candles['low'].iloc[i-2] and
                    candles['low'].iloc[i] < candles['low'].iloc[i+2]):
                    lows.append(candles['low'].iloc[i])

            # Recent highs/lows
            result['resistance'] = sorted(highs[-5:]) if highs else []
            result['support'] = sorted(lows[-5:]) if lows else []

        except Exception as e:
            self.logger.error(f"Error calculating trend lines: {e}")

        return result

    def detect_trend_change(self, candles: pd.DataFrame) -> Dict:
        """
        Detect trend change signals.

        Args:
            candles: Candlestick data

        Returns:
            Trend change analysis
        """
        result = {
            'change_detected': False,
            'direction': None,
            'confidence': 0,
            'signals': []
        }

        try:
            if len(candles) < 50:
                return result

            # EMA crossover check
            ema_fast = self._calculate_ema(candles['close'], self.ema_fast)
            ema_slow = self._calculate_ema(candles['close'], self.ema_slow)

            # Current crossover
            current_diff = ema_fast.iloc[-1] - ema_slow.iloc[-1]
            prev_diff = ema_fast.iloc[-2] - ema_slow.iloc[-2]

            # Bullish crossover
            if prev_diff < 0 and current_diff >= 0:
                result['change_detected'] = True
                result['direction'] = 'bullish'
                result['confidence'] = 0.7
                result['signals'].append('EMA bullish crossover')

            # Bearish crossover
            elif prev_diff > 0 and current_diff <= 0:
                result['change_detected'] = True
                result['direction'] = 'bearish'
                result['confidence'] = 0.7
                result['signals'].append('EMA bearish crossover')

            # Check for structure break
            trend_lines = self.get_trend_lines(candles)

            current_price = candles['close'].iloc[-1]

            # Price breaking below resistance
            if trend_lines['resistance'] and current_price > max(trend_lines['resistance']):
                result['change_detected'] = True
                result['direction'] = 'bullish'
                result['confidence'] = 0.8
                result['signals'].append('Breakout above resistance')

            # Price breaking below support
            if trend_lines['support'] and current_price < min(trend_lines['support']):
                result['change_detected'] = True
                result['direction'] = 'bearish'
                result['confidence'] = 0.8
                result['signals'].append('Breakdown below support')

        except Exception as e:
            self.logger.error(f"Error detecting trend change: {e}")

        return result

    def calculate_trend_quality(self, candles: pd.DataFrame) -> float:
        """
        Calculate trend quality score (0-1).

        Higher scores indicate more reliable trends.

        Args:
            candles: Candlestick data

        Returns:
            Quality score
        """
        try:
            if candles is None or len(candles) < 30:
                return 0

            # Factor 1: EMA alignment
            ema_fast = self._calculate_ema(candles['close'], self.ema_fast)
            ema_slow = self._calculate_ema(candles['close'], self.ema_slow)

            alignment = 1 if (ema_fast.iloc[-1] > ema_slow.iloc[-1]) else 0

            # Factor 2: Consistent higher highs/lows
            highs = candles['high'].iloc[-10:].values
            lows = candles['low'].iloc[-10:].values

            higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
            higher_lows = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])

            consistency = (higher_highs + higher_lows) / 20

            # Factor 3: Low drawdown within trend
            returns = candles['close'].pct_change().iloc[-20:]
            max_drawdown = abs(returns.min())

            drawdown_score = 1 - min(max_drawdown * 10, 1)

            # Combine scores
            quality = (alignment + consistency + drawdown_score) / 3

            return float(quality)

        except Exception as e:
            self.logger.error(f"Error calculating trend quality: {e}")
            return 0.5

    def is_trend_healthy(self, candles: pd.DataFrame, direction: str) -> bool:
        """
        Check if current trend is healthy (sustainable).

        Args:
            candles: Candlestick data
            direction: 'bullish' or 'bearish'

        Returns:
            Boolean indicating if trend is healthy
        """
        try:
            # Check for lower highs (bearish reversal)
            if direction == 'bullish':
                recent_highs = candles['high'].iloc[-10:].values

                for i in range(2, len(recent_highs) - 2):
                    if (recent_highs[i] > recent_highs[i-1] and
                        recent_highs[i] > recent_highs[i+1] and
                        recent_highs[i] > recent_highs[i-2] and
                        recent_highs[i] > recent_highs[i+2]):
                        return False  # Lower high detected

            # Check for higher highs (bullish continuation)
            elif direction == 'bearish':
                recent_lows = candles['low'].iloc[-10:].values

                for i in range(2, len(recent_lows) - 2):
                    if (recent_lows[i] < recent_lows[i-1] and
                        recent_lows[i] < recent_lows[i+1] and
                        recent_lows[i] < recent_lows[i-2] and
                        recent_lows[i] < recent_lows[i+2]):
                        return False  # Higher low detected (for bearish)

            return True

        except Exception as e:
            self.logger.error(f"Error checking trend health: {e}")
            return True