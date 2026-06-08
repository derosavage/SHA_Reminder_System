"""
Danvas1 - Strategy Manager
Version: 1.0.0

Manages trading strategies, generates signals, and handles multi-timeframe analysis.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from indicators.rsi import RSICalculator
from indicators.atr import ATRCalculator
from indicators.ema import EMACalculator
from indicators.volume import VolumeAnalyzer
from analysis.market_regime import MarketRegime
from analysis.volatility import VolatilityAnalyzer
from analysis.trend_detection import TrendDetector
from strategies.strategy_v1 import StrategyV1
from strategies.filters import SignalFilters


class StrategyManager:
    """
    Manages all trading strategies and signal generation.

    Responsibilities:
    - Multi-timeframe analysis
    - Signal generation with confluence
    - Strategy selection and management
    - Entry/exit condition evaluation
    """

    def __init__(self, config: Dict, bybit_client):
        """
        Initialize Strategy Manager.

        Args:
            config: Bot configuration dictionary
            bybit_client: Bybit API client
        """
        self.logger = logging.getLogger("Danvas1.StrategyManager")
        self.config = config
        self.bybit = bybit_client

        # Initialize indicators
        self.rsi_calc = RSICalculator(config)
        self.atr_calc = ATRCalculator(config)
        self.ema_calc = EMACalculator(config)
        self.volume_calc = VolumeAnalyzer(config)

        # Initialize analysis tools
        self.market_regime = MarketRegime(config)
        self.volatility = VolatilityAnalyzer(config)
        self.trend_detector = TrendDetector(config)

        # Initialize strategies
        self.strategies = {
            'v1': StrategyV1(config, self.rsi_calc, self.atr_calc, self.ema_calc)
        }
        self.active_strategy = self.strategies['v1']

        # Initialize filters
        self.filters = SignalFilters(config)

        self.logger.info("Strategy Manager initialized")

    def analyze_htf(self, symbol: str) -> Dict:
        """
        Perform higher timeframe analysis.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with HTF analysis results
        """
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'timeframes': {}
        }

        try:
            # Analyze each higher timeframe
            for tf in self.config['strategy']['htf_timeframes']:
                tf_analysis = self._analyze_single_tf(symbol, tf)
                analysis['timeframes'][tf] = tf_analysis

            # Determine overall trend
            analysis['trend'] = self._determine_overall_trend(analysis['timeframes'])

            # Find key levels
            analysis['levels'] = self._find_key_levels(symbol, analysis['timeframes'])

            # Assess momentum
            analysis['momentum'] = self._assess_momentum(analysis['timeframes'])

        except Exception as e:
            self.logger.error(f"Error in HTF analysis for {symbol}: {e}")

        return analysis

    def _analyze_single_tf(self, symbol: str, timeframe: str) -> Dict:
        """Analyze a single timeframe."""
        try:
            # Get candles
            candles = self.bybit.get_klines(symbol, timeframe, limit=100)

            if candles is None or len(candles) < 50:
                return {}

            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            # Calculate indicators
            df['rsi'] = self.rsi_calc.calculate(df)
            df['ema_50'] = self.ema_calc.calculate(df, 50)
            df['ema_200'] = self.ema_calc.calculate(df, 200)
            df['atr'] = self.atr_calc.calculate(df)

            # Get latest values
            latest = df.iloc[-1]

            return {
                'close': float(latest['close']),
                'rsi': float(latest['rsi']),
                'ema_50': float(latest['ema_50']),
                'ema_200': float(latest['ema_200']),
                'atr': float(latest['atr']),
                'trend': self._get_tf_trend(df),
                'rsi_state': self._get_rsi_state(float(latest['rsi'])),
                'volatility': self.volatility.assess(df)
            }

        except Exception as e:
            self.logger.error(f"Error analyzing {timeframe} for {symbol}: {e}")
            return {}

    def _get_tf_trend(self, df: pd.DataFrame) -> str:
        """Determine trend direction for timeframe."""
        if len(df) < 50:
            return 'neutral'

        latest = df.iloc[-1]
        ema_50 = latest['ema_50']
        ema_200 = latest['ema_200']
        close = latest['close']

        if close > ema_50 > ema_200:
            return 'bullish'
        elif close < ema_50 < ema_200:
            return 'bearish'
        else:
            return 'neutral'

    def _get_rsi_state(self, rsi: float) -> str:
        """Get RSI state based on thresholds."""
        if rsi < self.config['strategy']['rsi_oversold']:
            return 'oversold'
        elif rsi > self.config['strategy']['rsi_overbought']:
            return 'overbought'
        else:
            return 'neutral'

    def _determine_overall_trend(self, timeframes: Dict) -> Dict:
        """Determine overall trend across timeframes."""
        trend_count = {'bullish': 0, 'bearish': 0, 'neutral': 0}

        for tf, data in timeframes.items():
            if 'trend' in data:
                trend_count[data['trend']] += 1

        # Majority wins
        max_trend = max(trend_count, key=trend_count.get)

        # Calculate strength
        total = sum(trend_count.values())
        strength = trend_count[max_trend] / total if total > 0 else 0

        return {
            'direction': max_trend,
            'strength': strength,
            'breakdown': trend_count
        }

    def _find_key_levels(self, symbol: str, timeframes: Dict) -> Dict:
        """Find key support and resistance levels."""
        levels = {'support': [], 'resistance': []}

        try:
            # Get lower timeframe for precise levels
            ltf = self.config['strategy']['ltf_timeframe']
            candles = self.bybit.get_klines(symbol, ltf, limit=200)

            if candles is None or len(candles) < 50:
                return levels

            df = pd.DataFrame(candles)

            # Find swing highs and lows
            highs = df['high'].values
            lows = df['low'].values

            # Recent highs/lows (last 20 candles)
            recent_highs = sorted(highs[-20:], reverse=True)[:5]
            recent_lows = sorted(lows[-20:])[:5]

            levels['resistance'] = recent_highs
            levels['support'] = recent_lows

        except Exception as e:
            self.logger.error(f"Error finding key levels: {e}")

        return levels

    def _assess_momentum(self, timeframes: Dict) -> Dict:
        """Assess momentum across timeframes."""
        rsi_values = []
        trends = []

        for tf, data in timeframes.items():
            if 'rsi' in data:
                rsi_values.append(data['rsi'])
            if 'trend' in data:
                trends.append(data['trend'])

        avg_rsi = sum(rsi_values) / len(rsi_values) if rsi_values else 50

        # Count bullish vs bearish trends
        bullish_count = trends.count('bullish')
        bearish_count = trends.count('bearish')

        if bullish_count > bearish_count:
            momentum_dir = 'bullish'
        elif bearish_count > bullish_count:
            momentum_dir = 'bearish'
        else:
            momentum_dir = 'neutral'

        return {
            'direction': momentum_dir,
            'avg_rsi': avg_rsi,
            'strength': abs(avg_rsi - 50) / 50  # Normalize to 0-1
        }

    def check_signals(self, symbol: str, htf_analysis: Dict, market_data: Dict) -> Optional[Dict]:
        """
        Check for trading signals based on multi-timeframe analysis.

        Args:
            symbol: Trading symbol
            htf_analysis: Higher timeframe analysis results
            market_data: Current market data

        Returns:
            Signal dictionary or None if no signal
        """
        try:
            # Get LTF candles
            ltf = self.config['strategy']['ltf_timeframe']
            ltf_candles = market_data['candles']

            if ltf_candles is None or len(ltf_candles) < 50:
                return None

            df = pd.DataFrame(ltf_candles)

            # Calculate LTF indicators
            df['rsi'] = self.rsi_calc.calculate(df)
            df['atr'] = self.atr_calc.calculate(df)
            df['ema_fast'] = self.ema_calc.calculate(df, 9)
            df['ema_slow'] = self.ema_calc.calculate(df, 21)

            latest = df.iloc[-1]

            # Build confluence score
            confluence = self._calculate_confluence(
                symbol, htf_analysis, df, latest
            )

            # Check minimum confluence threshold
            min_threshold = self.config['strategy']['min_confluence_score']

            if confluence['score'] < min_threshold:
                return None

            # Determine direction
            direction = self._determine_signal_direction(
                htf_analysis, df, latest, confluence
            )

            if direction is None:
                return None

            # Calculate entry, SL, TP
            signal = self._build_signal(
                symbol, direction, htf_analysis, df, latest
            )

            return signal

        except Exception as e:
            self.logger.error(f"Error checking signals for {symbol}: {e}")
            return None

    def _calculate_confluence(self, symbol: str, htf: Dict, ltf_df: pd.DataFrame,
                              latest: pd.Series) -> Dict:
        """Calculate confluence score for a potential signal."""
        score = 0
        reasons = []

        # Check HTF trend alignment
        htf_trend = htf.get('trend', {}).get('direction', 'neutral')
        if htf_trend == 'bullish':
            score += 1
            reasons.append('HTF bullish trend')
        elif htf_trend == 'bearish':
            score += 1
            reasons.append('HTF bearish trend')

        # Check HTF RSI
        for tf, data in htf.get('timeframes', {}).items():
            rsi_state = data.get('rsi_state', 'neutral')
            if rsi_state == 'oversold':
                score += 0.5
                reasons.append(f'{tf} RSI oversold')
            elif rsi_state == 'overbought':
                score += 0.5
                reasons.append(f'{tf} RSI overbought')

        # Check momentum
        momentum = htf.get('momentum', {})
        if momentum.get('direction') in ['bullish', 'bearish']:
            score += 0.5
            reasons.append(f'Momentum {momentum["direction"]}')

        # Check volume
        volume_signal = self.volume_calc.analyze(ltf_df)
        if volume_signal in ['high', 'very_high']:
            score += 0.5
            reasons.append(f'High volume ({volume_signal})')

        # Check volatility
        volatility_ok = self.volatility.is_adequate(ltf_df)
        if volatility_ok:
            score += 0.5
            reasons.append('Adequate volatility')

        return {
            'score': score,
            'reasons': reasons
        }

    def _determine_signal_direction(self, htf: Dict, ltf_df: pd.DataFrame,
                                    latest: pd.Series, confluence: Dict) -> Optional[str]:
        """
        Determine signal direction based on analysis.

        Returns:
            'long', 'short', or None
        """
        htf_trend = htf.get('trend', {}).get('direction', 'neutral')
        htf_momentum = htf.get('momentum', {}).get('direction', 'neutral')

        # Get RSI state
        rsi = float(latest['rsi'])

        # LONG: Bullish HTF + RSI oversold
        if htf_trend == 'bullish' and rsi < self.config['strategy']['rsi_oversold']:
            if htf_momentum == 'bullish' or confluence['score'] >= 3:
                return 'long'

        # SHORT: Bearish HTF + RSI overbought
        if htf_trend == 'bearish' and rsi > self.config['strategy']['rsi_overbought']:
            if htf_momentum == 'bearish' or confluence['score'] >= 3:
                return 'short'

        return None

    def _build_signal(self, symbol: str, direction: str, htf: Dict,
                     ltf_df: pd.DataFrame, latest: pd.Series) -> Dict:
        """Build complete signal with entry, SL, TP."""
        current_price = float(latest['close'])
        atr = float(latest['atr'])

        sl_multiplier = self.config['strategy']['atr_multiplier_sl']
        tp_multiplier = self.config['strategy']['atr_multiplier_tp']

        if direction == 'long':
            stop_loss = current_price - (atr * sl_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
        else:  # short
            stop_loss = current_price + (atr * sl_multiplier)
            take_profit = current_price - (atr * tp_multiplier)

        # Validate risk/reward
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        rr_ratio = reward / risk if risk > 0 else 0

        min_rr = self.config['risk_management']['min_risk_reward_ratio']

        if rr_ratio < min_rr:
            # Adjust TP to meet minimum RR
            if direction == 'long':
                take_profit = current_price + (risk * min_rr)
            else:
                take_profit = current_price - (risk * min_rr)

        return {
            'symbol': symbol,
            'action': direction,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'atr': atr,
            'rsi': float(latest['rsi']),
            'confluence_score': self._calculate_confluence(
                symbol, htf, ltf_df, latest
            )['score'],
            'reason': f'{direction.upper()} signal',
            'htf_trend': htf.get('trend', {}).get('direction'),
            'rr_ratio': round(rr_ratio, 2),
            'timestamp': datetime.now()
        }

    def apply_filters(self, signal: Dict, market_data: Dict) -> Dict:
        """
        Apply signal filters to validate trade setup.

        Args:
            signal: Raw signal from strategy
            market_data: Current market data

        Returns:
            Filtered signal with approved/rejected status
        """
        return self.filters.validate(signal, market_data)

    def get_strategy_status(self) -> Dict:
        """Get current strategy status and statistics."""
        return {
            'active_strategy': 'v1',
            'signal_count': len(self.strategies['v1'].get_recent_signals()),
            'last_signal': self.strategies['v1'].get_last_signal_time()
        }