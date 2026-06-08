"""
Danvas1 - RSI Calculator
Version: 1.0.0

Relative Strength Index calculations.
"""

import logging
from typing import Optional
import pandas as pd


class RSICalculator:
    """
    RSI indicator calculations.

    Responsibilities:
    - Calculate RSI with configurable periods
    - Detect overbought/oversold conditions
    - Identify RSI divergences
    """

    def __init__(self, config: dict):
        """
        Initialize RSI Calculator.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.RSI")
        self.config = config

        self.default_period = config['strategy'].get('rsi_period', 14)
        self.oversold = config['strategy'].get('rsi_oversold', 30)
        self.overbought = config['strategy'].get('rsi_overbought', 70)

        self.logger.info("RSI Calculator initialized")

    def calculate(self, candles: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calculate RSI.

        Args:
            candles: Candlestick data
            period: RSI period

        Returns:
            RSI series
        """
        if period is None:
            period = self.default_period

        if candles is None or 'close' not in candles or len(candles) < period + 1:
            return pd.Series()

        try:
            delta = candles['close'].diff()

            # Separate gains and losses
            gains = delta.copy()
            losses = delta.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0

            # Calculate average gains and losses
            avg_gain = gains.rolling(period).mean()
            avg_loss = abs(losses.rolling(period).mean())

            # Calculate RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return rsi

        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series()

    def get_current_rsi(self, candles: pd.DataFrame, period: int = None) -> float:
        """
        Get current RSI value.

        Args:
            candles: Candlestick data
            period: RSI period

        Returns:
            Current RSI value (0-100)
        """
        rsi = self.calculate(candles, period)

        if len(rsi) > 0:
            return float(rsi.iloc[-1])

        return 50.0

    def get_state(self, candles: pd.DataFrame, period: int = None) -> str:
        """
        Get RSI state.

        Args:
            candles: Candlestick data
            period: RSI period

        Returns:
            'oversold', 'overbought', or 'neutral'
        """
        rsi = self.get_current_rsi(candles, period)

        if rsi < self.oversold:
            return 'oversold'
        elif rsi > self.overbought:
            return 'overbought'
        else:
            return 'neutral'

    def is_oversold(self, candles: pd.DataFrame, period: int = None) -> bool:
        """Check if RSI is in oversold territory."""
        return self.get_state(candles, period) == 'oversold'

    def is_overbought(self, candles: pd.DataFrame, period: int = None) -> bool:
        """Check if RSI is in overbought territory."""
        return self.get_state(candles, period) == 'overbought'

    def find_divergence(self, candles: pd.DataFrame, lookback: int = 20) -> Optional[dict]:
        """
        Find RSI divergence.

        Args:
            candles: Candlestick data
            lookback: Period to look back

        Returns:
            Divergence info or None
        """
        try:
            if candles is None or len(candles) < lookback + 10:
                return None

            rsi = self.calculate(candles)

            # Get price and RSI data
            recent_data = candles.iloc[-lookback:]
            recent_rsi = rsi.iloc[-lookback:]

            # Find swing highs and lows
            price_high_idx = recent_data['high'].values.argmax()
            price_low_idx = recent_data['low'].values.argmin()

            rsi_high_idx = recent_rsi.values.argmax()
            rsi_low_idx = recent_rsi.values.argmin()

            # Check for divergence
            current_price = float(candles['close'].iloc[-1])
            current_rsi = float(rsi.iloc[-1])

            # Bearish divergence: Price higher high, RSI lower high
            if price_high_idx > len(recent_data) // 2:  # Recent high
                if current_price > float(recent_data['high'].iloc[0]):
                    if rsi_high_idx < len(recent_rsi) // 2:  # Earlier RSI high
                        return {
                            'type': 'bearish',
                            'strength': 0.7
                        }

            # Bullish divergence: Price lower low, RSI higher low
            if price_low_idx > len(recent_data) // 2:  # Recent low
                if current_price < float(recent_data['low'].iloc[0]):
                    if rsi_low_idx < len(recent_rsi) // 2:  # Earlier RSI low
                        return {
                            'type': 'bullish',
                            'strength': 0.7
                        }

            return None

        except Exception as e:
            self.logger.error(f"Error finding divergence: {e}")
            return None

    def get_momentum(self, candles: pd.DataFrame, period: int = None) -> float:
        """
        Get RSI momentum (rate of change).

        Args:
            candles: Candlestick data
            period: RSI period

        Returns:
            RSI momentum value
        """
        rsi = self.calculate(candles, period)

        if len(rsi) >= 2:
            current = float(rsi.iloc[-1])
            previous = float(rsi.iloc[-2])

            return current - previous

        return 0.0

    def is_recovering(self, candles: pd.DataFrame, period: int = None) -> bool:
        """Check if RSI is recovering from oversold."""
        rsi = self.calculate(candles, period)

        if len(rsi) < 3:
            return False

        current = float(rsi.iloc[-1])
        prev = float(rsi.iloc[-2])

        return current > prev and current < 50

    def is_weakening(self, candles: pd.DataFrame, period: int = None) -> bool:
        """Check if RSI is weakening from overbought."""
        rsi = self.calculate(candles, period)

        if len(rsi) < 3:
            return False

        current = float(rsi.iloc[-1])
        prev = float(rsi.iloc[-2])

        return current < prev and current > 50