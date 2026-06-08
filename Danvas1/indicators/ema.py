"""
Danvas1 - EMA Calculator
Version: 1.0.0

Exponential Moving Average calculations.
"""

import logging
from typing import Optional
import pandas as pd


class EMACalculator:
    """
    EMA indicator calculations.

    Responsibilities:
    - Calculate EMA for various periods
    - Provide EMA crossover signals
    - Calculate EMA ribbon
    """

    def __init__(self, config: dict):
        """
        Initialize EMA Calculator.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.EMA")
        self.config = config

        self.logger.info("EMA Calculator initialized")

    def calculate(self, candles: pd.DataFrame, period: int = 21) -> pd.Series:
        """
        Calculate EMA.

        Args:
            candles: Candlestick data
            period: EMA period

        Returns:
            EMA series
        """
        if candles is None or 'close' not in candles:
            return pd.Series()

        try:
            return candles['close'].ewm(span=period, adjust=False).mean()

        except Exception as e:
            self.logger.error(f"Error calculating EMA: {e}")
            return pd.Series()

    def calculate_ribbon(self, candles: pd.DataFrame,
                        periods: list = None) -> dict:
        """
        Calculate multiple EMAs for ribbon.

        Args:
            candles: Candlestick data
            periods: List of periods

        Returns:
            Dictionary of EMA series
        """
        if periods is None:
            periods = [9, 21, 50, 100, 200]

        ribbon = {}

        for period in periods:
            ribbon[f'ema_{period}'] = self.calculate(candles, period)

        return ribbon

    def get_crossover(self, fast_ema: pd.Series, slow_ema: pd.Series) -> Optional[str]:
        """
        Detect EMA crossover.

        Args:
            fast_ema: Fast EMA series
            slow_ema: Slow EMA series

        Returns:
            'bullish', 'bearish', or None
        """
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return None

        prev_fast = float(fast_ema.iloc[-2])
        curr_fast = float(fast_ema.iloc[-1])
        prev_slow = float(slow_ema.iloc[-2])
        curr_slow = float(slow_ema.iloc[-1])

        # Bullish: Fast crosses above Slow
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return 'bullish'

        # Bearish: Fast crosses below Slow
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return 'bearish'

        return None

    def is_above(self, candles: pd.DataFrame, period: int = 21) -> bool:
        """Check if price is above EMA."""
        ema = self.calculate(candles, period)

        if len(ema) == 0:
            return False

        return float(candles['close'].iloc[-1]) > float(ema.iloc[-1])

    def is_below(self, candles: pd.DataFrame, period: int = 21) -> bool:
        """Check if price is below EMA."""
        ema = self.calculate(candles, period)

        if len(ema) == 0:
            return False

        return float(candles['close'].iloc[-1]) < float(ema.iloc[-1])