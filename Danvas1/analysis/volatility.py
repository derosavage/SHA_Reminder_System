"""
Danvas1 - Volatility Analyzer
Version: 1.0.0

Analyzes and quantifies market volatility for position sizing and risk management.
"""

import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd


class VolatilityAnalyzer:
    """
    Volatility analysis for trading decisions.

    Responsibilities:
    - Calculate volatility metrics
    - Assess if volatility is adequate for trading
    - Adjust position sizing based on volatility
    - Identify volatility regime changes
    """

    def __init__(self, config: Dict):
        """
        Initialize Volatility Analyzer.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.Volatility")
        self.config = config

        self.atr_period = config['strategy'].get('atr_period', 14)

        self.logger.info("Volatility Analyzer initialized")

    def calculate_atr(self, candles: pd.DataFrame, period: int = None) -> float:
        """
        Calculate Average True Range.

        Args:
            candles: Candlestick data
            period: ATR period (optional)

        Returns:
            ATR value
        """
        if period is None:
            period = self.atr_period

        if candles is None or len(candles) < period + 1:
            return 0.0

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
            atr = tr.rolling(period).mean().iloc[-1]

            return float(atr) if not np.isnan(atr) else 0.0

        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.0

    def calculate_atr_pct(self, candles: pd.DataFrame) -> float:
        """
        Calculate ATR as percentage of price.

        Args:
            candles: Candlestick data

        Returns:
            ATR percentage
        """
        if candles is None or len(candles) < 2:
            return 0.0

        try:
            atr = self.calculate_atr(candles)
            current_price = candles['close'].iloc[-1]

            if current_price > 0:
                return (atr / current_price) * 100

        except Exception as e:
            self.logger.error(f"Error calculating ATR%: {e}")

        return 0.0

    def assess(self, candles: pd.DataFrame) -> str:
        """
        Assess volatility level.

        Args:
            candles: Candlestick data

        Returns:
            Volatility assessment: 'low', 'medium', 'high', 'extreme'
        """
        atr_pct = self.calculate_atr_pct(candles)

        if atr_pct < 1.0:
            return 'low'
        elif atr_pct < 2.5:
            return 'medium'
        elif atr_pct < 5.0:
            return 'high'
        else:
            return 'extreme'

    def is_adequate(self, candles: pd.DataFrame, min_pct: float = 0.5) -> bool:
        """
        Check if volatility is adequate for trading.

        Args:
            candles: Candlestick data
            min_pct: Minimum ATR% required

        Returns:
            Boolean indicating if volatility is adequate
        """
        atr_pct = self.calculate_atr_pct(candles)

        # Must have minimum volatility for stops to work
        return atr_pct >= min_pct

    def get_volatility_score(self, candles: pd.DataFrame) -> float:
        """
        Get normalized volatility score (0-1).

        Args:
            candles: Candlestick data

        Returns:
            Volatility score
        """
        atr_pct = self.calculate_atr_pct(candles)

        # Normalize: 0% = 0, 5%+ = 1
        score = min(atr_pct / 5.0, 1.0)

        return score

    def calculate_volatility_ratio(self, candles: pd.DataFrame,
                                   short_period: int = 5,
                                   long_period: int = 20) -> float:
        """
        Calculate short vs long term volatility ratio.

        Args:
            candles: Candlestick data
            short_period: Short period for comparison
            long_period: Long period for comparison

        Returns:
            Volatility ratio
        """
        try:
            short_atr = self.calculate_atr(candles, short_period)
            long_atr = self.calculate_atr(candles, long_period)

            if long_atr > 0:
                return short_atr / long_atr

        except Exception as e:
            self.logger.error(f"Error calculating volatility ratio: {e}")

        return 1.0

    def detect_volatility_regime_change(self, candles: pd.DataFrame) -> Dict:
        """
        Detect changes in volatility regime.

        Args:
            candles: Candlestick data

        Returns:
            Regime change analysis
        """
        result = {
            'change_detected': False,
            'direction': None,
            'strength': 0,
            'current_regime': 'unknown',
            'previous_regime': 'unknown'
        }

        try:
            if len(candles) < 50:
                return result

            # Compare recent volatility to historical
            recent_atr_pct = self.calculate_atr_pct(candles.iloc[-10:])
            historical_atr_pct = self.calculate_atr_pct(candles.iloc[-50:-10])

            if historical_atr_pct > 0:
                ratio = recent_atr_pct / historical_atr_pct

                # Significant change
                if ratio > 1.5:
                    result['change_detected'] = True
                    result['direction'] = 'increase'
                    result['strength'] = ratio - 1
                    result['current_regime'] = 'high'
                    result['previous_regime'] = 'normal'

                elif ratio < 0.67:
                    result['change_detected'] = True
                    result['direction'] = 'decrease'
                    result['strength'] = 1 - ratio
                    result['current_regime'] = 'low'
                    result['previous_regime'] = 'normal'

        except Exception as e:
            self.logger.error(f"Error detecting volatility regime change: {e}")

        return result

    def calculate_panic_index(self, candles: pd.DataFrame) -> float:
        """
        Calculate a volatility-based panic index.

        Higher values indicate potential panic/volatility spike.

        Args:
            candles: Candlestick data

        Returns:
            Panic index (0-100)
        """
        try:
            if len(candles) < 20:
                return 0

            # Recent returns
            returns = candles['close'].pct_change().dropna().iloc[-20:]

            # Calculate metrics
            volatility = returns.std()
            max_loss = returns.min()
            avg_volume = candles['volume'].iloc[-20:].mean()
            recent_volume = candles['volume'].iloc[-1]

            # Panic indicators
            vol_score = min(volatility * 100, 100)
            loss_score = min(abs(min_loss) * 200, 50)
            volume_score = min((recent_volume / avg_volume) * 50, 50) if avg_volume > 0 else 0

            panic_index = vol_score + loss_score + volume_score

            return min(panic_index, 100)

        except Exception as e:
            self.logger.error(f"Error calculating panic index: {e}")
            return 0

    def get_adjusted_position_size(self, base_size: float,
                                   candles: pd.DataFrame,
                                   target_vol_pct: float = 2.0) -> float:
        """
        Adjust position size based on current volatility.

        Args:
            base_size: Base position size
            candles: Candlestick data
            target_vol_pct: Target volatility percentage

        Returns:
            Adjusted position size
        """
        try:
            current_atr_pct = self.calculate_atr_pct(candles)

            if current_atr_pct > 0:
                # Reduce size when volatility is high
                ratio = target_vol_pct / current_atr_pct

                adjusted_size = base_size * min(ratio, 1.0)

                return adjusted_size

        except Exception as e:
            self.logger.error(f"Error adjusting position size: {e}")

        return base_size

    def calculate_dynamic_stop_distance(self, candles: pd.DataFrame,
                                        base_multiplier: float = 2.5) -> float:
        """
        Calculate dynamic stop loss distance based on volatility.

        Args:
            candles: Candlestick data
            base_multiplier: Base ATR multiplier

        Returns:
            Stop distance in price units
        """
        try:
            atr = self.calculate_atr(candles)
            atr_pct = self.calculate_atr_pct(candles)

            # Adjust multiplier based on volatility
            if atr_pct > 4:  # Very volatile
                multiplier = base_multiplier * 1.5
            elif atr_pct > 2.5:  # High volatility
                multiplier = base_multiplier * 1.25
            elif atr_pct < 1:  # Low volatility
                multiplier = base_multiplier * 0.75
            else:
                multiplier = base_multiplier

            return atr * multiplier

        except Exception as e:
            self.logger.error(f"Error calculating dynamic stop: {e}")
            return 0

    def is_volatility_spike(self, candles: pd.DataFrame,
                           threshold: float = 2.0) -> bool:
        """
        Detect if current volatility is a spike compared to recent history.

        Args:
            candles: Candlestick data
            threshold: Ratio threshold for spike detection

        Returns:
            Boolean indicating if volatility spike detected
        """
        try:
            if len(candles) < 30:
                return False

            recent_vol = self.calculate_atr_pct(candles.iloc[-10:])
            historical_vol = self.calculate_atr_pct(candles.iloc[-30:-10])

            if historical_vol > 0:
                ratio = recent_vol / historical_vol

                return ratio >= threshold

        except Exception as e:
            self.logger.error(f"Error detecting volatility spike: {e}")

        return False