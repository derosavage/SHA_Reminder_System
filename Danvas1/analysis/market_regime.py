"""
Danvas1 - Market Regime Analyzer
Version: 1.0.0

Identifies and tracks market regimes (trending, ranging, volatile).
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class MarketRegime:
    """
    Analyzes and identifies market regimes.

    Regimes:
    - TRENDING: Strong directional movement
    - RANGING: Sideways price action
    - VOLATILE: High amplitude, unclear direction
    - BREAKOUT: Transition between regimes
    """

    def __init__(self, config: Dict):
        """
        Initialize Market Regime Analyzer.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.MarketRegime")
        self.config = config

        # Regime detection parameters
        self.trend_threshold = 0.7  # ADX threshold for trending
        self.range_threshold = 40   # ADX threshold for ranging
        self.min_periods = 20

        self.logger.info("Market Regime Analyzer initialized")

    def analyze(self, candles: pd.DataFrame) -> Dict:
        """
        Analyze market regime.

        Args:
            candles: Candlestick data

        Returns:
            Regime analysis result
        """
        if candles is None or len(candles) < self.min_periods:
            return {'regime': 'unknown', 'confidence': 0, 'details': {}}

        result = {
            'regime': 'unknown',
            'confidence': 0,
            'details': {},
            'timestamp': datetime.now()
        }

        try:
            # Calculate ADX
            adx = self._calculate_adx(candles)

            # Calculate momentum
            momentum = self._calculate_momentum(candles)

            # Calculate volatility
            volatility = self._calculate_regime_volatility(candles)

            # Determine regime
            if adx >= self.trend_threshold:
                result['regime'] = 'trending'
                result['confidence'] = min(adx / 100, 1.0)
            elif adx <= self.range_threshold:
                result['regime'] = 'ranging'
                result['confidence'] = 1 - (adx / 100)
            else:
                result['regime'] = 'volatile'
                result['confidence'] = 0.5

            result['details'] = {
                'adx': adx,
                'momentum': momentum,
                'volatility': volatility,
                'trend_direction': momentum['direction']
            }

        except Exception as e:
            self.logger.error(f"Error analyzing market regime: {e}")

        return result

    def _calculate_adx(self, candles: pd.DataFrame) -> float:
        """Calculate Average Directional Index."""
        try:
            # Calculate True Range
            high = candles['high']
            low = candles['low']
            close = candles['close']

            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            # Calculate Directional Movement
            plus_dm = high.diff()
            minus_dm = -low.diff()

            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0

            # Calculate smoothed DM
            plus_dm_smooth = plus_dm.rolling(14).mean()
            minus_dm_smooth = minus_dm.rolling(14).mean()

            # Calculate DI
            plus_di = 100 * (plus_dm_smooth / atr)
            minus_di = 100 * (minus_dm_smooth / atr)

            # Calculate DX
            di_sum = plus_di + minus_di
            di_diff = abs(plus_di - minus_di)

            dx = 100 * (di_diff / di_sum)

            # ADX is smoothed DX
            adx = dx.rolling(14).mean().iloc[-1]

            return float(adx) if not np.isnan(adx) else 50.0

        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return 50.0

    def _calculate_momentum(self, candles: pd.DataFrame) -> Dict:
        """Calculate momentum indicators."""
        try:
            close = candles['close']

            # Simple momentum
            roc = ((close.iloc[-1] - close.iloc[-14]) / close.iloc[-14]) * 100

            # Direction
            if roc > 2:
                direction = 'bullish'
            elif roc < -2:
                direction = 'bearish'
            else:
                direction = 'neutral'

            return {
                'rate_of_change': float(roc),
                'direction': direction,
                'strength': abs(roc) / 10  # Normalize to 0-1
            }

        except Exception as e:
            self.logger.error(f"Error calculating momentum: {e}")
            return {'rate_of_change': 0, 'direction': 'neutral', 'strength': 0}

    def _calculate_regime_volatility(self, candles: pd.DataFrame) -> Dict:
        """Calculate volatility metrics for regime."""
        try:
            returns = candles['close'].pct_change().dropna()

            return {
                'std_dev': float(returns.std()),
                'avg_range_pct': float(
                    ((candles['high'] - candles['low']) / candles['close']).mean()
                ),
                'relative_volatility': 'high' if returns.std() > 0.02 else 'low'
            }

        except Exception as e:
            self.logger.error(f"Error calculating volatility: {e}")
            return {'std_dev': 0, 'avg_range_pct': 0, 'relative_volatility': 'unknown'}

    def get_regime_parameters(self, regime: str) -> Dict:
        """
        Get recommended parameters for a regime.

        Args:
            regime: Market regime

        Returns:
            Recommended parameters
        """
        if regime == 'trending':
            return {
                'atr_multiplier_sl': 2.0,
                'atr_multiplier_tp': 3.5,
                'min_confluence': 3,
                'signal_strength_threshold': 0.75
            }
        elif regime == 'ranging':
            return {
                'atr_multiplier_sl': 2.5,
                'atr_multiplier_tp': 4.0,
                'min_confluence': 4,
                'signal_strength_threshold': 0.85
            }
        elif regime == 'volatile':
            return {
                'atr_multiplier_sl': 3.0,
                'atr_multiplier_tp': 5.0,
                'min_confluence': 4,
                'signal_strength_threshold': 0.9
            }
        else:
            return {
                'atr_multiplier_sl': 2.5,
                'atr_multiplier_tp': 4.0,
                'min_confluence': 3,
                'signal_strength_threshold': 0.8
            }

    def detect_breakout(self, candles: pd.DataFrame,
                        lookback: int = 20) -> Dict:
        """
        Detect potential breakout conditions.

        Args:
            candles: Candlestick data
            lookback: Periods to look back

        Returns:
            Breakout detection result
        """
        result = {
            'breakout': False,
            'direction': None,
            'strength': 0,
            'reason': ''
        }

        try:
            if len(candles) < lookback:
                return result

            recent = candles.iloc[-lookback:]

            # Calculate Bollinger Bands
            sma = recent['close'].mean()
            std = recent['close'].std()

            upper_band = sma + (2 * std)
            lower_band = sma - (2 * std)

            current_close = candles['close'].iloc[-1]

            # Check for breakout
            if current_close > upper_band:
                result['breakout'] = True
                result['direction'] = 'bullish'
                result['strength'] = (current_close - upper_band) / upper_band
                result['reason'] = 'Above upper Bollinger Band'

            elif current_close < lower_band:
                result['breakout'] = True
                result['direction'] = 'bearish'
                result['strength'] = (lower_band - current_close) / lower_band
                result['reason'] = 'Below lower Bollinger Band'

        except Exception as e:
            self.logger.error(f"Error detecting breakout: {e}")

        return result

    def is_safe_to_trade(self, regime: str) -> bool:
        """
        Check if it's safe to trade in current regime.

        Args:
            regime: Current market regime

        Returns:
            Boolean indicating if trading is safe
        """
        if regime == 'trending':
            return True
        elif regime == 'ranging':
            return True
        elif regime == 'volatile':
            return False
        else:
            return False