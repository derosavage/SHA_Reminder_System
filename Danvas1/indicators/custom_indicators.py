"""
Danvas1 - Custom Indicators
Version: 1.0.0

Custom technical indicators for the trading system.
"""

import logging
from typing import Optional, Dict
import pandas as pd
import numpy as np


class CustomIndicators:
    """
    Custom technical indicators.

    Responsibilities:
    - Calculate Bollinger Bands
    - Calculate Stochastic
    - Calculate Ichimoku (simplified)
    - Custom momentum indicators
    """

    def __init__(self, config: dict):
        """
        Initialize Custom Indicators.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.CustomIndicators")
        self.config = config

        self.logger.info("Custom Indicators initialized")

    def calculate_bollinger_bands(self, candles: pd.DataFrame,
                                  period: int = 20,
                                  std_dev: float = 2.0) -> Dict:
        """
        Calculate Bollinger Bands.

        Args:
            candles: Candlestick data
            period: BB period
            std_dev: Standard deviation multiplier

        Returns:
            Dict with upper, middle, lower bands
        """
        try:
            if candles is None or 'close' not in candles:
                return {}

            sma = candles['close'].rolling(period).mean()
            std = candles['close'].rolling(period).std()

            return {
                'upper': sma + (std * std_dev),
                'middle': sma,
                'lower': sma - (std * std_dev)
            }

        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            return {}

    def calculate_stochastic(self, candles: pd.DataFrame,
                           k_period: int = 14,
                           d_period: int = 3) -> Dict:
        """
        Calculate Stochastic Oscillator.

        Args:
            candles: Candlestick data
            k_period: %K period
            d_period: %D period

        Returns:
            Dict with %K and %D values
        """
        try:
            if candles is None or len(candles) < k_period:
                return {}

            low_min = candles['low'].rolling(k_period).min()
            high_max = candles['high'].rolling(k_period).max()

            # %K
            k = 100 * (candles['close'] - low_min) / (high_max - low_min)

            # %D
            d = k.rolling(d_period).mean()

            return {
                'k': k,
                'd': d
            }

        except Exception as e:
            self.logger.error(f"Error calculating Stochastic: {e}")
            return {}

    def calculate_obv(self, candles: pd.DataFrame) -> pd.Series:
        """
        Calculate On-Balance Volume.

        Args:
            candles: Candlestick data

        Returns:
            OBV series
        """
        try:
            if candles is None or 'volume' not in candles:
                return pd.Series()

            obv = pd.Series(index=candles.index, dtype=float)
            obv.iloc[0] = 0

            for i in range(1, len(candles)):
                if candles['close'].iloc[i] > candles['close'].iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] + candles['volume'].iloc[i]
                elif candles['close'].iloc[i] < candles['close'].iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] - candles['volume'].iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]

            return obv

        except Exception as e:
            self.logger.error(f"Error calculating OBV: {e}")
            return pd.Series()

    def calculate_vortex(self, candles: pd.DataFrame, period: int = 14) -> Dict:
        """
        Calculate Vortex Indicator.

        Args:
            candles: Candlestick data
            period: VI period

        Returns:
            Dict with +VI and -VI
        """
        try:
            if candles is None or len(candles) < period + 1:
                return {}

            vm_plus = abs(candles['high'] - candles['low'].shift(1))
            vm_minus = abs(candles['low'] - candles['high'].shift(1))

            tr = pd.concat([
                candles['high'] - candles['low'],
                abs(candles['high'] - candles['close'].shift(1)),
                abs(candles['low'] - candles['close'].shift(1))
            ], axis=1).max(axis=1)

            sum_vm_plus = vm_plus.rolling(period).sum()
            sum_vm_minus = vm_minus.rolling(period).sum()
            sum_tr = tr.rolling(period).sum()

            vi_plus = sum_vm_plus / sum_tr
            vi_minus = sum_vm_minus / sum_tr

            return {
                'vi_plus': vi_plus,
                'vi_minus': vi_minus
            }

        except Exception as e:
            self.logger.error(f"Error calculating Vortex: {e}")
            return {}

    def calculate_keltner_channels(self, candles: pd.DataFrame,
                                  ema_period: int = 20,
                                  atr_period: int = 10,
                                  multiplier: float = 2.0) -> Dict:
        """
        Calculate Keltner Channels.

        Args:
            candles: Candlestick data
            ema_period: EMA period for middle line
            atr_period: ATR period
            multiplier: ATR multiplier for bands

        Returns:
            Dict with upper, middle, lower channels
        """
        try:
            if candles is None:
                return {}

            # Middle line (EMA)
            middle = candles['close'].ewm(span=ema_period, adjust=False).mean()

            # True Range
            tr1 = candles['high'] - candles['low']
            tr2 = abs(candles['high'] - candles['close'].shift(1))
            tr3 = abs(candles['low'] - candles['close'].shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            atr = tr.rolling(atr_period).mean()

            # Bands
            upper = middle + (atr * multiplier)
            lower = middle - (atr * multiplier)

            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'atr': atr
            }

        except Exception as e:
            self.logger.error(f"Error calculating Keltner Channels: {e}")
            return {}

    def calculate_supertrend(self, candles: pd.DataFrame,
                           period: int = 10,
                           multiplier: float = 3.0) -> Dict:
        """
        Calculate Supertrend Indicator.

        Args:
            candles: Candlestick data
            period: ATR period
            multiplier: ATR multiplier

        Returns:
            Dict with supertrend values
        """
        try:
            if candles is None:
                return {}

            # True Range
            tr1 = candles['high'] - candles['low']
            tr2 = abs(candles['high'] - candles['close'].shift(1))
            tr3 = abs(candles['low'] - candles['close'].shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            atr = tr.rolling(period).mean()

            # HL2
            hl2 = (candles['high'] + candles['low']) / 2

            # Upper and Lower bands
            upper_band = hl2 + (multiplier * atr)
            lower_band = hl2 - (multiplier * atr)

            # Supertrend
            supertrend = pd.Series(index=candles.index, dtype=float)
            direction = pd.Series(index=candles.index, dtype=int)

            for i in range(len(candles)):
                if i == 0:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = 1
                    continue

                # Check direction
                if candles['close'].iloc[i] > upper_band.iloc[i-1]:
                    direction.iloc[i] = 1  # Bullish
                elif candles['close'].iloc[i] < lower_band.iloc[i-1]:
                    direction.iloc[i] = -1  # Bearish
                else:
                    direction.iloc[i] = direction.iloc[i-1]

                # Calculate supertrend
                if direction.iloc[i] == 1:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    if supertrend.iloc[i] < supertrend.iloc[i-1]:
                        supertrend.iloc[i] = supertrend.iloc[i-1]
                else:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    if supertrend.iloc[i] > supertrend.iloc[i-1]:
                        supertrend.iloc[i] = supertrend.iloc[i-1]

            return {
                'supertrend': supertrend,
                'direction': direction,
                'upper_band': upper_band,
                'lower_band': lower_band
            }

        except Exception as e:
            self.logger.error(f"Error calculating Supertrend: {e}")
            return {}

    def calculate_momentum_bands(self, candles: pd.DataFrame,
                               period: int = 20) -> Dict:
        """
        Calculate momentum-based bands.

        Args:
            candles: Candlestick data
            period: Lookback period

        Returns:
            Dict with upper, middle, lower momentum bands
        """
        try:
            if candles is None or len(candles) < period:
                return {}

            # Calculate momentum
            momentum = candles['close'].pct_change(period)

            # Rolling statistics
            middle = momentum.rolling(period).mean()
            std = momentum.rolling(period).std()

            upper = middle + (2 * std)
            lower = middle - (2 * std)

            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'momentum': momentum
            }

        except Exception as e:
            self.logger.error(f"Error calculating momentum bands: {e}")
            return {}

    def detect_support_zone(self, candles: pd.DataFrame,
                           lookback: int = 50) -> Optional[float]:
        """
        Detect support zone based on price action.

        Args:
            candles: Candlestick data
            lookback: Period to look back

        Returns:
            Support zone price or None
        """
        try:
            if candles is None or len(candles) < lookback:
                return None

            recent = candles.iloc[-lookback:]

            # Find swing lows
            lows = []

            for i in range(5, len(recent) - 5):
                if (recent['low'].iloc[i] <= recent['low'].iloc[i-1] and
                    recent['low'].iloc[i] <= recent['low'].iloc[i+1] and
                    recent['low'].iloc[i] <= recent['low'].iloc[i-2] and
                    recent['low'].iloc[i] <= recent['low'].iloc[i+2]):
                    lows.append(float(recent['low'].iloc[i]))

            if lows:
                # Cluster similar levels
                avg_low = sum(lows) / len(lows)

                # Find lowest level
                return min(lows)

            return None

        except Exception as e:
            self.logger.error(f"Error detecting support zone: {e}")
            return None

    def detect_resistance_zone(self, candles: pd.DataFrame,
                              lookback: int = 50) -> Optional[float]:
        """
        Detect resistance zone based on price action.

        Args:
            candles: Candlestick data
            lookback: Period to look back

        Returns:
            Resistance zone price or None
        """
        try:
            if candles is None or len(candles) < lookback:
                return None

            recent = candles.iloc[-lookback:]

            # Find swing highs
            highs = []

            for i in range(5, len(recent) - 5):
                if (recent['high'].iloc[i] >= recent['high'].iloc[i-1] and
                    recent['high'].iloc[i] >= recent['high'].iloc[i+1] and
                    recent['high'].iloc[i] >= recent['high'].iloc[i-2] and
                    recent['high'].iloc[i] >= recent['high'].iloc[i+2]):
                    highs.append(float(recent['high'].iloc[i]))

            if highs:
                return max(highs)

            return None

        except Exception as e:
            self.logger.error(f"Error detecting resistance zone: {e}")
            return None