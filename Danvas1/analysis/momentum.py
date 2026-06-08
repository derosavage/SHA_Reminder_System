"""
Danvas1 - Momentum Analyzer
Version: 1.0.0

Analyzes price momentum and strength indicators.
"""

import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd


class MomentumAnalyzer:
    """
    Momentum analysis for trade signals.

    Responsibilities:
    - Calculate momentum indicators
    - Detect momentum shifts
    - Identify momentum divergences
    - Assess momentum strength
    """

    def __init__(self, config: Dict):
        """
        Initialize Momentum Analyzer.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.Momentum")
        self.config = config

        self.logger.info("Momentum Analyzer initialized")

    def calculate_momentum(self, candles: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate momentum value.

        Args:
            candles: Candlestick data
            period: Lookback period

        Returns:
            Momentum value
        """
        try:
            if candles is None or len(candles) < period + 1:
                return 0

            current_close = candles['close'].iloc[-1]
            past_close = candles['close'].iloc[-period]

            if past_close > 0:
                momentum = ((current_close - past_close) / past_close) * 100

            return float(momentum)

        except Exception as e:
            self.logger.error(f"Error calculating momentum: {e}")
            return 0

    def calculate_rsi(self, candles: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate RSI.

        Args:
            candles: Candlestick data
            period: RSI period

        Returns:
            RSI value (0-100)
        """
        try:
            if candles is None or len(candles) < period + 1:
                return 50

            # Calculate price changes
            delta = candles['close'].diff()

            # Separate gains and losses
            gains = delta.copy()
            losses = delta.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0

            # Calculate average gains and losses
            avg_gain = gains.rolling(period).mean().iloc[-1]
            avg_loss = abs(losses.rolling(period).mean().iloc[-1])

            # Calculate RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            return float(rsi) if not np.isnan(rsi) else 50

        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return 50

    def calculate_macd(self, candles: pd.DataFrame,
                      fast: int = 12, slow: int = 26,
                      signal: int = 9) -> Dict:
        """
        Calculate MACD.

        Args:
            candles: Candlestick data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            MACD values
        """
        try:
            if candles is None or len(candles) < slow + signal:
                return {'macd': 0, 'signal': 0, 'histogram': 0}

            close = candles['close']

            # Calculate EMAs
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()

            # MACD line
            macd = ema_fast - ema_slow

            # Signal line
            signal_line = macd.ewm(span=signal, adjust=False).mean()

            # Histogram
            histogram = macd - signal_line

            return {
                'macd': float(macd.iloc[-1]),
                'signal': float(signal_line.iloc[-1]),
                'histogram': float(histogram.iloc[-1])
            }

        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            return {'macd': 0, 'signal': 0, 'histogram': 0}

    def detect_divergence(self, candles: pd.DataFrame,
                          indicator: str = 'rsi') -> Dict:
        """
        Detect price/indicator divergence.

        Args:
            candles: Candlestick data
            indicator: 'rsi' or 'macd'

        Returns:
            Divergence analysis
        """
        result = {
            'divergence': False,
            'type': None,  # 'bullish', 'bearish'
            'strength': 0,
            'reason': ''
        }

        try:
            if len(candles) < 30:
                return result

            # Get indicator values
            if indicator == 'rsi':
                indicator_values = [self._calculate_rsi(candles.iloc[:i])
                                  for i in range(20, len(candles))]
            else:
                macd_values = [self.calculate_macd(candles.iloc[:i])['histogram']
                              for i in range(30, len(candles))]
                indicator_values = macd_values

            # Get recent highs/lows
            prices = candles['close'].iloc[-20:].values

            # Find swing points
            price_high_idx = np.argmax(prices)
            price_low_idx = np.argmin(prices)

            price_high = prices[price_high_idx]
            price_low = prices[price_low_idx]

            # Get corresponding indicator values
            indicator_high_idx = np.argmax(indicator_values[-10:])
            indicator_low_idx = np.argmin(indicator_values[-10:])

            indicator_high = indicator_values[indicator_high_idx]
            indicator_low = indicator_values[indicator_low_idx]

            # Check for bullish divergence
            # Price making lower low, indicator making higher low
            if price_low_idx > len(prices) // 2 and indicator_low_idx < len(indicator_values) // 2:
                if price_low < prices[0]:  # New lower low
                    result['divergence'] = True
                    result['type'] = 'bullish'
                    result['strength'] = 0.7
                    result['reason'] = 'Price making lower low, indicator higher low'

            # Check for bearish divergence
            # Price making higher high, indicator making lower high
            if price_high_idx > len(prices) // 2 and indicator_high_idx < len(indicator_values) // 2:
                if price_high > prices[0]:  # New higher high
                    result['divergence'] = True
                    result['type'] = 'bearish'
                    result['strength'] = 0.7
                    result['reason'] = 'Price making higher high, indicator lower high'

        except Exception as e:
            self.logger.error(f"Error detecting divergence: {e}")

        return result

    def analyze_momentum_shift(self, candles: pd.DataFrame) -> Dict:
        """
        Detect momentum shifts.

        Args:
            candles: Candlestick data

        Returns:
            Momentum shift analysis
        """
        result = {
            'shift_detected': False,
            'direction': None,
            'strength': 0,
            'reason': ''
        }

        try:
            if len(candles) < 20:
                return result

            # Calculate momentum for different periods
            short_momentum = self.calculate_momentum(candles, 5)
            medium_momentum = self.calculate_momentum(candles, 14)
            long_momentum = self.calculate_momentum(candles, 30)

            # Momentum acceleration
            if short_momentum > medium_momentum > 0 and medium_momentum > long_momentum:
                result['shift_detected'] = True
                result['direction'] = 'bullish'
                result['strength'] = min(abs(short_momentum) / 10, 1.0)
                result['reason'] = 'Accelerating bullish momentum'

            elif short_momentum < medium_momentum < 0 and medium_momentum < long_momentum:
                result['shift_detected'] = True
                result['direction'] = 'bearish'
                result['strength'] = min(abs(short_momentum) / 10, 1.0)
                result['reason'] = 'Accelerating bearish momentum'

            # Check MACD histogram shift
            macd = self.calculate_macd(candles)

            if len(candles) >= 5:
                # Get recent histogram values
                recent_hist = []
                for i in range(-5, 0):
                    hist = self.calculate_macd(candles.iloc[:i])['histogram']
                    recent_hist.append(hist)

                if recent_hist:
                    # Histogram turning positive
                    if recent_hist[-1] > 0 and all(h <= 0 for h in recent_hist[:-1]):
                        result['shift_detected'] = True
                        result['direction'] = 'bullish'
                        result['strength'] = 0.8
                        result['reason'] = 'MACD histogram turning positive'

                    # Histogram turning negative
                    elif recent_hist[-1] < 0 and all(h >= 0 for h in recent_hist[:-1]):
                        result['shift_detected'] = True
                        result['direction'] = 'bearish'
                        result['strength'] = 0.8
                        result['reason'] = 'MACD histogram turning negative'

        except Exception as e:
            self.logger.error(f"Error analyzing momentum shift: {e}")

        return result

    def calculate_momentum_strength(self, candles: pd.DataFrame) -> float:
        """
        Calculate normalized momentum strength (0-1).

        Args:
            candles: Candlestick data

        Returns:
            Momentum strength score
        """
        try:
            if candles is None or len(candles) < 20:
                return 0.5

            # Factor 1: RSI strength
            rsi = self.calculate_rsi(candles)
            rsi_strength = abs(rsi - 50) / 50

            # Factor 2: MACD histogram
            macd = self.calculate_macd(candles)
            hist = abs(macd['histogram'])

            # Normalize histogram
            recent_closes = candles['close'].iloc[-20:]
            price_range = recent_closes.max() - recent_closes.min()

            if price_range > 0:
                hist_strength = min(hist / (price_range * 0.01), 1.0)
            else:
                hist_strength = 0.5

            # Factor 3: Momentum consistency
            returns = candles['close'].pct_change().iloc[-10:]
            positive_count = (returns > 0).sum()
            momentum_consistency = positive_count / 10

            # Combine
            strength = (rsi_strength + hist_strength + momentum_consistency) / 3

            return float(strength)

        except Exception as e:
            self.logger.error(f"Error calculating momentum strength: {e}")
            return 0.5

    def is_momentum_fading(self, candles: pd.DataFrame) -> bool:
        """
        Check if momentum is fading.

        Args:
            candles: Candlestick data

        Returns:
            Boolean indicating if momentum is fading
        """
        try:
            if len(candles) < 20:
                return False

            # Compare recent momentum to earlier
            recent = candles.iloc[-10:]
            earlier = candles.iloc[-20:-10]

            recent_momentum = self.calculate_momentum(recent, 10)
            earlier_momentum = self.calculate_momentum(earlier, 10)

            # Momentum fading if current is significantly lower
            if abs(earlier_momentum) > 0.5:
                fade_ratio = abs(recent_momentum) / abs(earlier_momentum)

                return fade_ratio < 0.5

            return False

        except Exception as e:
            self.logger.error(f"Error checking momentum fading: {e}")
            return False

    def _calculate_rsi(self, candles: pd.DataFrame, period: int = 14) -> float:
        """Internal RSI calculation."""
        delta = candles['close'].diff()
        gains = delta.copy()
        losses = delta.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0

        avg_gain = gains.rolling(period).mean().iloc[-1]
        avg_loss = abs(losses.rolling(period).mean().iloc[-1])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))