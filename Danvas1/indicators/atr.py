"""
Danvas1 - ATR Calculator
Version: 1.0.0

Average True Range calculations for volatility and position sizing.
"""

import logging
from typing import Optional
import pandas as pd


class ATRCalculator:
    """
    ATR indicator calculations.

    Responsibilities:
    - Calculate True Range
    - Calculate ATR with configurable periods
    - Provide dynamic stop loss distances
    """

    def __init__(self, config: dict):
        """
        Initialize ATR Calculator.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.ATR")
        self.config = config

        self.default_period = config['strategy'].get('atr_period', 14)

        self.logger.info("ATR Calculator initialized")

    def calculate(self, candles: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calculate ATR.

        Args:
            candles: Candlestick data
            period: ATR period (optional, uses default)

        Returns:
            ATR series
        """
        if period is None:
            period = self.default_period

        if candles is None or len(candles) < period + 1:
            return pd.Series()

        try:
            high = candles['high']
            low = candles['low']
            close = candles['close']

            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR
            atr = tr.rolling(period).mean()

            return atr

        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return pd.Series()

    def get_current_atr(self, candles: pd.DataFrame, period: int = None) -> float:
        """
        Get current ATR value.

        Args:
            candles: Candlestick data
            period: ATR period

        Returns:
            Current ATR value
        """
        atr = self.calculate(candles, period)

        if len(atr) > 0:
            return float(atr.iloc[-1])

        return 0.0

    def get_atr_percentage(self, candles: pd.DataFrame, period: int = None) -> float:
        """
        Get ATR as percentage of current price.

        Args:
            candles: Candlestick data
            period: ATR period

        Returns:
            ATR percentage
        """
        atr = self.get_current_atr(candles, period)

        if len(candles) > 0:
            current_price = float(candles['close'].iloc[-1])

            if current_price > 0:
                return (atr / current_price) * 100

        return 0.0

    def calculate_stop_distance(self, candles: pd.DataFrame,
                                 multiplier: float = 2.5,
                                 period: int = None) -> float:
        """
        Calculate stop loss distance based on ATR.

        Args:
            candles: Candlestick data
            multiplier: ATR multiplier
            period: ATR period

        Returns:
            Stop distance in price units
        """
        atr = self.get_current_atr(candles, period)

        return atr * multiplier

    def calculate_tp_distance(self, candles: pd.DataFrame,
                              multiplier: float = 4.0,
                              period: int = None) -> float:
        """
        Calculate take profit distance based on ATR.

        Args:
            candles: Candlestick data
            multiplier: ATR multiplier
            period: ATR period

        Returns:
            TP distance in price units
        """
        atr = self.get_current_atr(candles, period)

        return atr * multiplier

    def get_stop_loss(self, candles: pd.DataFrame, direction: str,
                     multiplier: float = 2.5,
                     period: int = None) -> Optional[float]:
        """
        Calculate stop loss price.

        Args:
            candles: Candlestick data
            direction: 'long' or 'short'
            multiplier: ATR multiplier
            period: ATR period

        Returns:
            Stop loss price
        """
        if candles is None or len(candles) == 0:
            return None

        atr = self.get_current_atr(candles, period)
        current_price = float(candles['close'].iloc[-1])

        if atr == 0:
            return None

        distance = atr * multiplier

        if direction == 'long':
            return current_price - distance
        elif direction == 'short':
            return current_price + distance

        return None

    def get_take_profit(self, candles: pd.DataFrame, direction: str,
                       multiplier: float = 4.0,
                       period: int = None) -> Optional[float]:
        """
        Calculate take profit price.

        Args:
            candles: Candlestick data
            direction: 'long' or 'short'
            multiplier: ATR multiplier
            period: ATR period

        Returns:
            Take profit price
        """
        if candles is None or len(candles) == 0:
            return None

        atr = self.get_current_atr(candles, period)
        current_price = float(candles['close'].iloc[-1])

        if atr == 0:
            return None

        distance = atr * multiplier

        if direction == 'long':
            return current_price + distance
        elif direction == 'short':
            return current_price - distance

        return None