"""
Danvas1 - Structure Analysis
Version: 1.0.0

Analyzes market structure, support/resistance, and key levels.
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class StructureAnalyzer:
    """
    Market structure analysis.

    Responsibilities:
    - Identify support and resistance levels
    - Detect market structure (swing highs/lows)
    - Find liquidity zones
    - Analyze price action patterns
    """

    def __init__(self, config: Dict):
        """
        Initialize Structure Analyzer.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.Structure")
        self.config = config

        self.swing_lookback = 5

        self.logger.info("Structure Analyzer initialized")

    def find_support_resistance(self, candles: pd.DataFrame,
                                lookback: int = 50) -> Dict:
        """
        Find support and resistance levels.

        Args:
            candles: Candlestick data
            lookback: Number of candles to analyze

        Returns:
            S/R level analysis
        """
        result = {
            'resistance': [],
            'support': [],
            'pivots': {'high': [], 'low': []}
        }

        try:
            if candles is None or len(candles) < lookback:
                return result

            data = candles.iloc[-lookback:]

            highs = []
            lows = []

            # Find swing highs and lows
            for i in range(self.swing_lookback, len(data) - self.swing_lookback):
                # Swing high
                if self._is_swing_high(data, i):
                    highs.append(float(data['high'].iloc[i]))

                # Swing low
                if self._is_swing_low(data, i):
                    lows.append(float(data['low'].iloc[i]))

            # Group similar levels
            result['resistance'] = self._cluster_levels(highs, tolerance=0.002)
            result['support'] = self._cluster_levels(lows, tolerance=0.002)

            result['pivots'] = {
                'high': highs,
                'low': lows
            }

        except Exception as e:
            self.logger.error(f"Error finding S/R levels: {e}")

        return result

    def _is_swing_high(self, data: pd.DataFrame, idx: int) -> bool:
        """Check if index is a swing high."""
        for offset in range(1, self.swing_lookback + 1):
            if idx - offset < 0 or idx + offset >= len(data):
                return False

            if data['high'].iloc[idx] <= data['high'].iloc[idx - offset]:
                return False
            if data['high'].iloc[idx] <= data['high'].iloc[idx + offset]:
                return False

        return True

    def _is_swing_low(self, data: pd.DataFrame, idx: int) -> bool:
        """Check if index is a swing low."""
        for offset in range(1, self.swing_lookback + 1):
            if idx - offset < 0 or idx + offset >= len(data):
                return False

            if data['low'].iloc[idx] >= data['low'].iloc[idx - offset]:
                return False
            if data['low'].iloc[idx] >= data['low'].iloc[idx + offset]:
                return False

        return True

    def _cluster_levels(self, levels: List[float], tolerance: float = 0.002) -> List[float]:
        """
        Cluster similar price levels.

        Args:
            levels: List of price levels
            tolerance: Clustering tolerance (percentage)

        Returns:
            Clustered levels
        """
        if not levels:
            return []

        # Sort levels
        sorted_levels = sorted(levels)

        clusters = []
        current_cluster = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            # Check if within tolerance of cluster average
            avg = sum(current_cluster) / len(current_cluster)

            if abs(level - avg) / avg <= tolerance:
                current_cluster.append(level)
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [level]

        clusters.append(current_cluster)

        # Return average of each cluster
        return [sum(c) / len(c) for c in clusters]

    def find_liquidity_zones(self, candles: pd.DataFrame) -> Dict:
        """
        Find liquidity zones (areas of stop hunts).

        Args:
            candles: Candlestick data

        Returns:
            Liquidity zone analysis
        """
        result = {
            'zones': [],
            'bullish_liquidity': [],
            'bearish_liquidity': []
        }

        try:
            if candles is None or len(candles) < 30:
                return result

            # Find equal highs/lows (liquidity pools)
            highs = []
            lows = []

            for i in range(5, len(candles) - 5):
                # Check for equal highs
                if (candles['high'].iloc[i] >= candles['high'].iloc[i-1] * 0.999 and
                    candles['high'].iloc[i] <= candles['high'].iloc[i-1] * 1.001):
                    # Found equal high, check for wicks
                    wick_size = candles['high'].iloc[i] - max(candles['open'].iloc[i],
                                                             candles['close'].iloc[i])
                    body_size = abs(candles['close'].iloc[i] - candles['open'].iloc[i])

                    if wick_size > body_size * 2:
                        highs.append(float(candles['high'].iloc[i]))
                        result['bearish_liquidity'].append({
                            'price': float(candles['high'].iloc[i]),
                            'wick_size': float(wick_size),
                            'timestamp': candles.index[i]
                        })

                # Check for equal lows
                if (candles['low'].iloc[i] <= candles['low'].iloc[i-1] * 1.001 and
                    candles['low'].iloc[i] >= candles['low'].iloc[i-1] * 0.999):
                    wick_size = min(candles['open'].iloc[i],
                                   candles['close'].iloc[i]) - candles['low'].iloc[i]
                    body_size = abs(candles['close'].iloc[i] - candles['open'].iloc[i])

                    if wick_size > body_size * 2:
                        lows.append(float(candles['low'].iloc[i]))
                        result['bullish_liquidity'].append({
                            'price': float(candles['low'].iloc[i]),
                            'wick_size': float(wick_size),
                            'timestamp': candles.index[i]
                        })

            # Cluster liquidity zones
            result['zones'] = {
                'resistance': self._cluster_levels(highs, tolerance=0.001),
                'support': self._cluster_levels(lows, tolerance=0.001)
            }

        except Exception as e:
            self.logger.error(f"Error finding liquidity zones: {e}")

        return result

    def analyze_structure_break(self, candles: pd.DataFrame) -> Dict:
        """
        Detect market structure breaks.

        Args:
            candles: Candlestick data

        Returns:
            Structure break analysis
        """
        result = {
            'break_detected': False,
            'direction': None,
            'level': None,
            'strength': 0
        }

        try:
            if candles is None or len(candles) < 50:
                return result

            # Find recent structure
            sr_levels = self.find_support_resistance(candles, lookback=30)

            current_price = candles['close'].iloc[-1]

            # Check for S/R break
            if sr_levels['resistance']:
                nearest_resistance = min(sr_levels['resistance'])

                # Bullish break
                if current_price > nearest_resistance * 1.002:
                    result['break_detected'] = True
                    result['direction'] = 'bullish'
                    result['level'] = nearest_resistance
                    result['strength'] = (current_price - nearest_resistance) / nearest_resistance

            if sr_levels['support']:
                nearest_support = max(sr_levels['support'])

                # Bearish break
                if current_price < nearest_support * 0.998:
                    result['break_detected'] = True
                    result['direction'] = 'bearish'
                    result['level'] = nearest_support
                    result['strength'] = (nearest_support - current_price) / nearest_support

        except Exception as e:
            self.logger.error(f"Error analyzing structure break: {e}")

        return result

    def calculate_market_structure(self, candles: pd.DataFrame) -> Dict:
        """
        Calculate overall market structure.

        Args:
            candles: Candlestick data

        Returns:
            Market structure analysis
        """
        result = {
            'structure': 'unknown',
            'higher_highs': 0,
            'higher_lows': 0,
            'lower_highs': 0,
            'lower_lows': 0
        }

        try:
            if candles is None or len(candles) < 20:
                return result

            highs = candles['high'].iloc[-20:].values
            lows = candles['low'].iloc[-20:].values

            # Count structure patterns
            for i in range(2, len(highs) - 2):
                # Higher high
                if highs[i] > highs[i-1] > highs[i-2]:
                    result['higher_highs'] += 1

                # Lower high
                if highs[i] < highs[i-1] < highs[i-2]:
                    result['lower_highs'] += 1

                # Higher low
                if lows[i] > lows[i-1] > lows[i-2]:
                    result['higher_lows'] += 1

                # Lower low
                if lows[i] < lows[i-1] < lows[i-2]:
                    result['lower_lows'] += 1

            # Determine structure
            if result['higher_highs'] > result['lower_highs']:
                if result['higher_lows'] > result['lower_lows']:
                    result['structure'] = 'uptrend'
                else:
                    result['structure'] = 'weak_uptrend'
            elif result['lower_highs'] > result['higher_highs']:
                if result['lower_lows'] > result['higher_lows']:
                    result['structure'] = 'downtrend'
                else:
                    result['structure'] = 'weak_downtrend'
            else:
                result['structure'] = 'ranging'

        except Exception as e:
            self.logger.error(f"Error calculating market structure: {e}")

        return result

    def get_key_levels(self, candles: pd.DataFrame) -> Dict:
        """
        Get key price levels for trading.

        Args:
            candles: Candlestick data

        Returns:
            Key level analysis
        """
        result = {
            'key_levels': [],
            'nearest_support': None,
            'nearest_resistance': None,
            'pivot_points': {}
        }

        try:
            if candles is None or len(candles) < 20:
                return result

            current_price = candles['close'].iloc[-1]

            # Find S/R levels
            sr = self.find_support_resistance(candles, lookback=50)

            # Calculate pivot points
            last_high = candles['high'].iloc[-1]
            last_low = candles['low'].iloc[-1]
            last_close = candles['close'].iloc[-1]

            pivot = (last_high + last_low + last_close) / 3

            r1 = 2 * pivot - last_low
            r2 = pivot + (last_high - last_low)
            s1 = 2 * pivot - last_high
            s2 = pivot - (last_high - last_low)

            result['pivot_points'] = {
                'pivot': float(pivot),
                'r1': float(r1),
                'r2': float(r2),
                's1': float(s1),
                's2': float(s2)
            }

            # Find nearest support and resistance
            if sr['support']:
                supports = [s for s in sr['support'] if s < current_price]
                if supports:
                    result['nearest_support'] = max(supports)

            if sr['resistance']:
                resistances = [r for r in sr['resistance'] if r > current_price]
                if resistances:
                    result['nearest_resistance'] = min(resistances)

            # All key levels
            all_levels = sr['support'] + sr['resistance'] + list(result['pivot_points'].values())
            all_levels = [l for l in all_levels if l is not None]

            result['key_levels'] = sorted(all_levels)

        except Exception as e:
            self.logger.error(f"Error getting key levels: {e}")

        return result

    def is_near_key_level(self, price: float, levels: List[float],
                          threshold: float = 0.002) -> Tuple[bool, str]:
        """
        Check if price is near a key level.

        Args:
            price: Current price
            levels: List of key levels
            threshold: Distance threshold (percentage)

        Returns:
            Tuple of (is_near, level_type)
        """
        for level in levels:
            distance = abs(price - level) / level

            if distance <= threshold:
                if price > level:
                    return True, 'resistance'
                else:
                    return True, 'support'

        return False, ''