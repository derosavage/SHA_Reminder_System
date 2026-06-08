"""
Danvas1 - Strategy V1
Version: 1.0.0

Main trading strategy implementation.
Combines RSI, ATR, EMA, and multi-timeframe analysis for trade signals.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
import numpy as np


class StrategyV1:
    """
    Strategy V1 - Multi-timeframe RSI + ATR Strategy

    Entry conditions:
    - HTF trend aligned with direction
    - RSI in oversold/overbought zone
    - Support/Resistance or liquidity zone nearby
    - Confirmation candle formation

    Exit conditions:
    - ATR-based stop loss
    - Dynamic take profit levels
    - Early exit on reversal signals
    """

    def __init__(self, config: Dict, rsi_calc, atr_calc, ema_calc):
        """
        Initialize Strategy V1.

        Args:
            config: Bot configuration
            rsi_calc: RSI calculator instance
            atr_calc: ATR calculator instance
            ema_calc: EMA calculator instance
        """
        self.logger = logging.getLogger("Danvas1.StrategyV1")
        self.config = config
        self.rsi = rsi_calc
        self.atr = atr_calc
        self.ema = ema_calc

        # Strategy parameters
        self.rsi_period = config['strategy'].get('rsi_period', 14)
        self.rsi_oversold = config['strategy'].get('rsi_oversold', 30)
        self.rsi_overbought = config['strategy'].get('rsi_overbought', 70)
        self.atr_period = config['strategy'].get('atr_period', 14)

        # Signal tracking
        self.signal_history = []
        self.max_history = 100

        self.logger.info("Strategy V1 initialized")

    def analyze(self, symbol: str, htf_data: Dict, ltf_candles: pd.DataFrame) -> Dict:
        """
        Main strategy analysis.

        Args:
            symbol: Trading symbol
            htf_data: Higher timeframe analysis data
            ltf_candles: Lower timeframe candle data

        Returns:
            Analysis result with signals
        """
        result = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'signal': None,
            'confidence': 0,
            'reasons': []
        }

        try:
            if ltf_candles is None or len(ltf_candles) < 50:
                return result

            # Calculate indicators
            ltf_candles['rsi'] = self.rsi.calculate(ltf_candles)
            ltf_candles['atr'] = self.atr.calculate(ltf_candles)
            ltf_candles['ema_fast'] = self.ema.calculate(ltf_candles, 9)
            ltf_candles['ema_slow'] = self.ema.calculate(ltf_candles, 21)

            latest = ltf_candles.iloc[-1]

            # Check for signals
            long_signal = self._check_long_condition(htf_data, ltf_candles, latest)
            short_signal = self._check_short_condition(htf_data, ltf_candles, latest)

            if long_signal:
                result['signal'] = 'long'
                result['confidence'] = long_signal['confidence']
                result['reasons'] = long_signal['reasons']

            elif short_signal:
                result['signal'] = 'short'
                result['confidence'] = short_signal['confidence']
                result['reasons'] = short_signal['reasons']

            # Store signal
            if result['signal']:
                self._record_signal(symbol, result)

        except Exception as e:
            self.logger.error(f"Error in strategy analysis: {e}")

        return result

    def _check_long_condition(self, htf_data: Dict, ltf_df: pd.DataFrame,
                              latest: pd.Series) -> Optional[Dict]:
        """
        Check for long entry conditions.

        Returns:
            Signal dict or None
        """
        signal = {
            'direction': 'long',
            'confidence': 0,
            'reasons': []
        }

        # Check HTF trend (must be bullish)
        htf_trend = htf_data.get('trend', {}).get('direction', 'neutral')

        if htf_trend != 'bullish':
            return None

        signal['reasons'].append('HTF bullish trend')

        # Check RSI oversold
        rsi = float(latest['rsi'])

        if rsi >= self.rsi_oversold:
            signal['confidence'] += 0.3
            signal['reasons'].append(f'RSI oversold ({rsi:.1f})')
        elif rsi < 40:
            signal['confidence'] += 0.15
            signal['reasons'].append(f'RSI recovering ({rsi:.1f})')
        else:
            return None

        # Check EMA alignment
        ema_fast = float(latest['ema_fast'])
        ema_slow = float(latest['ema_slow'])
        close = float(latest['close'])

        if close > ema_fast > ema_slow:
            signal['confidence'] += 0.2
            signal['reasons'].append('EMA alignment bullish')

        # Check for bullish candle
        if self._is_bullish_candle(ltf_df.iloc[-1]):
            signal['confidence'] += 0.2
            signal['reasons'].append('Bullish candle')

        # Check momentum
        momentum = htf_data.get('momentum', {}).get('direction')

        if momentum == 'bullish':
            signal['confidence'] += 0.2
            signal['reasons'].append('Momentum aligned')

        # Minimum confidence threshold
        if signal['confidence'] < 0.7:
            return None

        # Calculate SL and TP
        atr = float(latest['atr'])

        signal['entry'] = close
        signal['stop_loss'] = close - (atr * self.config['strategy']['atr_multiplier_sl'])
        signal['take_profit'] = close + (atr * self.config['strategy']['atr_multiplier_tp'])
        signal['atr'] = atr

        return signal

    def _check_short_condition(self, htf_data: Dict, ltf_df: pd.DataFrame,
                               latest: pd.Series) -> Optional[Dict]:
        """
        Check for short entry conditions.

        Returns:
            Signal dict or None
        """
        signal = {
            'direction': 'short',
            'confidence': 0,
            'reasons': []
        }

        # Check HTF trend (must be bearish)
        htf_trend = htf_data.get('trend', {}).get('direction', 'neutral')

        if htf_trend != 'bearish':
            return None

        signal['reasons'].append('HTF bearish trend')

        # Check RSI overbought
        rsi = float(latest['rsi'])

        if rsi <= self.rsi_overbought:
            signal['confidence'] += 0.3
            signal['reasons'].append(f'RSI overbought ({rsi:.1f})')
        elif rsi > 60:
            signal['confidence'] += 0.15
            signal['reasons'].append(f'RSI weakening ({rsi:.1f})')
        else:
            return None

        # Check EMA alignment
        ema_fast = float(latest['ema_fast'])
        ema_slow = float(latest['ema_slow'])
        close = float(latest['close'])

        if close < ema_fast < ema_slow:
            signal['confidence'] += 0.2
            signal['reasons'].append('EMA alignment bearish')

        # Check for bearish candle
        if self._is_bearish_candle(ltf_df.iloc[-1]):
            signal['confidence'] += 0.2
            signal['reasons'].append('Bearish candle')

        # Check momentum
        momentum = htf_data.get('momentum', {}).get('direction')

        if momentum == 'bearish':
            signal['confidence'] += 0.2
            signal['reasons'].append('Momentum aligned')

        # Minimum confidence threshold
        if signal['confidence'] < 0.7:
            return None

        # Calculate SL and TP
        atr = float(latest['atr'])

        signal['entry'] = close
        signal['stop_loss'] = close + (atr * self.config['strategy']['atr_multiplier_sl'])
        signal['take_profit'] = close - (atr * self.config['strategy']['atr_multiplier_tp'])
        signal['atr'] = atr

        return signal

    def _is_bullish_candle(self, candle: pd.Series) -> bool:
        """Check if candle is bullish."""
        body = candle['close'] - candle['open']

        if body <= 0:
            return False

        # Check for bullish patterns
        upper_wick = candle['high'] - candle['close']
        lower_wick = candle['open'] - candle['low']

        # Hammer-like: small upper wick, long lower wick
        if lower_wick > body * 2 and upper_wick < body * 0.5:
            return True

        # Strong bullish: body > 70% of range
        total_range = candle['high'] - candle['low']

        if total_range > 0 and body / total_range > 0.7:
            return True

        return False

    def _is_bearish_candle(self, candle: pd.Series) -> bool:
        """Check if candle is bearish."""
        body = candle['open'] - candle['close']

        if body <= 0:
            return False

        upper_wick = candle['high'] - candle['open']
        lower_wick = candle['close'] - candle['low']

        # Shooting star-like: long upper wick, small lower wick
        if upper_wick > body * 2 and lower_wick < body * 0.5:
            return True

        # Strong bearish: body > 70% of range
        total_range = candle['high'] - candle['low']

        if total_range > 0 and body / total_range > 0.7:
            return True

        return False

    def _record_signal(self, symbol: str, signal: Dict):
        """Record signal for tracking."""
        self.signal_history.append({
            'symbol': symbol,
            'signal': signal['signal'],
            'confidence': signal['confidence'],
            'reasons': signal['reasons'],
            'timestamp': datetime.now()
        })

        # Limit history size
        if len(self.signal_history) > self.max_history:
            self.signal_history.pop(0)

    def get_recent_signals(self, count: int = 10) -> List[Dict]:
        """Get recent signals."""
        return self.signal_history[-count:]

    def get_last_signal_time(self) -> Optional[datetime]:
        """Get timestamp of last signal."""
        if self.signal_history:
            return self.signal_history[-1]['timestamp']
        return None

    def calculate_confluence(self, htf_data: Dict, ltf_df: pd.DataFrame) -> float:
        """
        Calculate confluence score for validation.

        Args:
            htf_data: HTF analysis data
            ltf_df: LTF candle data

        Returns:
            Confluence score (0-1)
        """
        score = 0.0
        factors = 0

        # Trend alignment
        if htf_data.get('trend', {}).get('direction') != 'neutral':
            score += 0.25
        factors += 1

        # RSI state
        latest = ltf_df.iloc[-1]
        rsi = float(latest['rsi'])

        if rsi < self.rsi_oversold or rsi > self.rsi_overbought:
            score += 0.25
        factors += 1

        # Momentum
        if htf_data.get('momentum', {}).get('direction') != 'neutral':
            score += 0.25
        factors += 1

        # Support/Resistance alignment
        levels = htf_data.get('levels', {})

        if levels and (levels.get('support') or levels.get('resistance')):
            score += 0.25
        factors += 1

        return score / factors if factors > 0 else 0.0