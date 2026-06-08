"""
Danvas1 - Volume Analyzer
Version: 1.0.0

Volume analysis for confirming trade signals.
"""

import logging
from typing import Optional
import pandas as pd


class VolumeAnalyzer:
    """
    Volume indicator calculations.

    Responsibilities:
    - Calculate volume-based indicators
    - Detect volume spikes
    - Analyze volume trends
    """

    def __init__(self, config: dict):
        """
        Initialize Volume Analyzer.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.Volume")
        self.config = config

        self.logger.info("Volume Analyzer initialized")

    def calculate_vwap(self, candles: pd.DataFrame) -> float:
        """
        Calculate Volume Weighted Average Price.

        Args:
            candles: Candlestick data

        Returns:
            VWAP value
        """
        try:
            if candles is None or 'volume' not in candles:
                return 0.0

            typical_price = (candles['high'] + candles['low'] + candles['close']) / 3

            cumulative_tp_volume = (typical_price * candles['volume']).sum()
            cumulative_volume = candles['volume'].sum()

            if cumulative_volume > 0:
                return float(cumulative_tp_volume / cumulative_volume)

            return 0.0

        except Exception as e:
            self.logger.error(f"Error calculating VWAP: {e}")
            return 0.0

    def get_volume_profile(self, candles: pd.DataFrame, bins: int = 20) -> dict:
        """
        Get volume profile for price levels.

        Args:
            candles: Candlestick data
            bins: Number of price bins

        Returns:
            Volume profile dict
        """
        try:
            if candles is None or 'volume' not in candles:
                return {}

            low = candles['low'].min()
            high = candles['high'].max()

            price_range = high - low

            if price_range == 0:
                return {}

            bin_size = price_range / bins

            profile = {}

            for i in range(bins):
                bin_low = low + (i * bin_size)
                bin_high = bin_low + bin_size

                # Filter candles in this price range
                in_range = (candles['low'] < bin_high) & (candles['high'] > bin_low)

                volume = candles.loc[in_range, 'volume'].sum()

                profile[f'{bin_low:.4f}_{bin_high:.4f}'] = float(volume)

            return profile

        except Exception as e:
            self.logger.error(f"Error calculating volume profile: {e}")
            return {}

    def analyze(self, candles: pd.DataFrame) -> str:
        """
        Analyze volume conditions.

        Args:
            candles: Candlestick data

        Returns:
            Volume assessment: 'low', 'normal', 'high', 'very_high'
        """
        try:
            if candles is None or 'volume' not in candles or len(candles) < 20:
                return 'unknown'

            recent_volume = candles['volume'].iloc[-5:].mean()
            avg_volume = candles['volume'].iloc[-20:].mean()

            if avg_volume == 0:
                return 'unknown'

            ratio = recent_volume / avg_volume

            if ratio < 0.5:
                return 'low'
            elif ratio < 1.5:
                return 'normal'
            elif ratio < 3.0:
                return 'high'
            else:
                return 'very_high'

        except Exception as e:
            self.logger.error(f"Error analyzing volume: {e}")
            return 'unknown'

    def is_volume_spike(self, candles: pd.DataFrame, threshold: float = 2.0) -> bool:
        """
        Detect volume spike.

        Args:
            candles: Candlestick data
            threshold: Spike threshold multiplier

        Returns:
            Boolean indicating if volume spike detected
        """
        try:
            if candles is None or 'volume' not in candles or len(candles) < 20:
                return False

            current_volume = float(candles['volume'].iloc[-1])
            avg_volume = candles['volume'].iloc[-20:-1].mean()

            if avg_volume > 0:
                return current_volume / avg_volume >= threshold

            return False

        except Exception as e:
            self.logger.error(f"Error detecting volume spike: {e}")
            return False

    def get_volume_ma(self, candles: pd.DataFrame, period: int = 20) -> float:
        """
        Get moving average of volume.

        Args:
            candles: Candlestick data
            period: MA period

        Returns:
            Volume MA value
        """
        try:
            if candles is None or 'volume' not in candles or len(candles) < period:
                return 0.0

            return float(candles['volume'].rolling(period).mean().iloc[-1])

        except Exception as e:
            self.logger.error(f"Error calculating volume MA: {e}")
            return 0.0

    def confirm_trend(self, candles: pd.DataFrame, direction: str) -> float:
        """
        Confirm trend with volume analysis.

        Args:
            candles: Candlestick data
            direction: 'bullish' or 'bearish'

        Returns:
            Confirmation score (0-1)
        """
        try:
            if candles is None or len(candles) < 10:
                return 0.5

            # Calculate volume trend
            recent = candles.iloc[-10:]

            if direction == 'bullish':
                # Check if price up days have higher volume
                up_days = recent[recent['close'] > recent['open']]
                down_days = recent[recent['close'] <= recent['open']]

                if len(down_days) == 0:
                    return 1.0

                up_vol_avg = up_days['volume'].mean() if len(up_days) > 0 else 0
                down_vol_avg = down_days['volume'].mean() if len(down_days) > 0 else 0

                if down_vol_avg > 0:
                    ratio = up_vol_avg / down_vol_avg
                    return min(ratio / 2, 1.0)

            else:  # bearish
                down_days = recent[recent['close'] < recent['open']]
                up_days = recent[recent['close'] >= recent['open']]

                if len(up_days) == 0:
                    return 1.0

                down_vol_avg = down_days['volume'].mean() if len(down_days) > 0 else 0
                up_vol_avg = up_days['volume'].mean() if len(up_days) > 0 else 0

                if up_vol_avg > 0:
                    ratio = down_vol_avg / up_vol_avg
                    return min(ratio / 2, 1.0)

            return 0.5

        except Exception as e:
            self.logger.error(f"Error confirming trend: {e}")
            return 0.5

    def is_volume_diverging(self, candles: pd.DataFrame) -> Optional[str]:
        """
        Detect volume divergence from price.

        Args:
            candles: Candlestick data

        Returns:
            'bullish', 'bearish', or None
        """
        try:
            if candles is None or len(candles) < 20:
                return None

            # Check last 5 candles
            recent = candles.iloc[-5:]

            # Price rising but volume falling
            price_change = recent['close'].iloc[-1] - recent['close'].iloc[0]
            vol_change = recent['volume'].iloc[-1] - recent['volume'].iloc[0]

            if price_change > 0 and vol_change < 0:
                return 'bearish'  # Price up, volume down

            # Price falling but volume rising
            if price_change < 0 and vol_change > 0:
                return 'bullish'  # Price down, volume up

            return None

        except Exception as e:
            self.logger.error(f"Error detecting volume divergence: {e}")
            return None