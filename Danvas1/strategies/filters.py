"""
Danvas1 - Signal Filters
Version: 1.0.0

Applies additional filters to validate trade signals before execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd


class SignalFilters:
    """
    Signal validation filters.

    Responsibilities:
    - Filter out low-quality signals
    - Validate market conditions
    - Check session timing
    - Verify technical criteria
    """

    def __init__(self, config: Dict):
        """
        Initialize Signal Filters.

        Args:
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.Filters")
        self.config = config

        self.logger.info("Signal Filters initialized")

    def validate(self, signal: Dict, market_data: Dict) -> Dict:
        """
        Validate a signal against all filters.

        Args:
            signal: Trading signal
            market_data: Current market data

        Returns:
            Validation result with approved/rejected status
        """
        result = {
            'approved': True,
            'rejected': False,
            'reasons': []
        }

        # Check volatility filter
        vol_check = self._check_volatility(market_data)
        if not vol_check['passed']:
            result['approved'] = False
            result['rejected'] = True
            result['reasons'].append(vol_check['reason'])

        # Check liquidity filter
        liq_check = self._check_liquidity(market_data)
        if not liq_check['passed']:
            result['approved'] = False
            result['rejected'] = True
            result['reasons'].append(liq_check['reason'])

        # Check session filter
        session_check = self._check_trading_session()
        if not session_check['passed']:
            result['approved'] = False
            result['rejected'] = True
            result['reasons'].append(session_check['reason'])

        # Check spread filter
        spread_check = self._check_spread(market_data)
        if not spread_check['passed']:
            result['approved'] = False
            result['rejected'] = True
            result['reasons'].append(spread_check['reason'])

        # Check momentum filter
        mom_check = self._check_momentum(market_data)
        if not mom_check['passed']:
            result['approved'] = False
            result['rejected'] = True
            result['reasons'].append(mom_check['reason'])

        if result['rejected']:
            self.logger.info(f"Signal rejected: {result['reasons']}")

        return result

    def _check_volatility(self, market_data: Dict) -> Dict:
        """
        Check if volatility is adequate for trading.

        Returns:
            Filter result
        """
        result = {'passed': True, 'reason': ''}

        try:
            candles = market_data.get('candles', [])

            if len(candles) < 20:
                result['passed'] = False
                result['reason'] = 'Insufficient data for volatility check'
                return result

            # Calculate recent ATR
            highs = [c['high'] for c in candles[-20:]]
            lows = [c['low'] for c in candles[-20:]]
            closes = [c['close'] for c in candles[-20:]]

            trs = []
            for i in range(1, len(candles[-20:])):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                trs.append(tr)

            atr = sum(trs) / len(trs) if trs else 0
            current_price = closes[-1]

            # ATR as percentage of price
            atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

            # Minimum volatility requirement
            min_volatility = 0.5  # 0.5% minimum

            if atr_pct < min_volatility:
                result['passed'] = False
                result['reason'] = f'Low volatility ({atr_pct:.2f}% < {min_volatility}%)'

            # Maximum volatility check (avoid choppy markets)
            max_volatility = 5.0  # 5% maximum

            if atr_pct > max_volatility:
                result['passed'] = False
                result['reason'] = f'High volatility ({atr_pct:.2f}% > {max_volatility}%)'

        except Exception as e:
            self.logger.error(f"Error in volatility check: {e}")

        return result

    def _check_liquidity(self, market_data: Dict) -> Dict:
        """
        Check if market has adequate liquidity.

        Returns:
            Filter result
        """
        result = {'passed': True, 'reason': ''}

        try:
            orderbook = market_data.get('orderbook')

            if not orderbook:
                result['passed'] = False
                result['reason'] = 'No orderbook data'
                return result

            # Check bid/ask spread
            bid = orderbook.get('bid1', 0)
            ask = orderbook.get('ask1', 0)

            if bid > 0 and ask > 0:
                spread_pct = ((ask - bid) / ((bid + ask) / 2)) * 100

                if spread_pct > 0.5:  # More than 0.5% spread
                    result['passed'] = False
                    result['reason'] = f'Wide spread ({spread_pct:.2f}%)'

            # Check order book depth
            bid_volume = sum(orderbook.get(f'bid{i}', 0) for i in range(1, 6))
            ask_volume = sum(orderbook.get(f'ask{i}', 0) for i in range(1, 6))

            if bid_volume < 1000 or ask_volume < 1000:  # Arbitrary threshold
                result['passed'] = False
                result['reason'] = 'Low order book depth'

        except Exception as e:
            self.logger.error(f"Error in liquidity check: {e}")

        return result

    def _check_trading_session(self) -> Dict:
        """
        Check if current time is suitable for trading.

        Returns:
            Filter result
        """
        result = {'passed': True, 'reason': ''}

        try:
            now = datetime.now()

            # Avoid trading during low liquidity periods
            # Weekend (Saturday/Sunday)
            if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
                result['passed'] = False
                result['reason'] = 'Weekend - low liquidity'
                return result

            # Late Friday (after 22:00 UTC)
            if now.weekday() == 4 and now.hour >= 22:
                result['passed'] = False
                result['reason'] = 'Late Friday - weekend approaching'
                return result

            # Late Sunday (before 02:00 UTC)
            if now.weekday() == 6 and now.hour < 2:
                result['passed'] = False
                result['reason'] = 'Sunday early - market opening'
                return result

        except Exception as e:
            self.logger.error(f"Error in session check: {e}")

        return result

    def _check_spread(self, market_data: Dict) -> Dict:
        """
        Check bid/ask spread is acceptable.

        Returns:
            Filter result
        """
        result = {'passed': True, 'reason': ''}

        try:
            ticker = market_data.get('ticker', {})

            if not ticker:
                return result

            bid = ticker.get('bid1', 0)
            ask = ticker.get('ask1', 0)

            if bid > 0 and ask > 0:
                spread_pct = ((ask - bid) / ((bid + ask) / 2)) * 100

                max_spread = self.config['execution'].get('max_slippage_percent', 0.3)

                if spread_pct > max_spread:
                    result['passed'] = False
                    result['reason'] = f'Spread too wide ({spread_pct:.2f}% > {max_spread}%)'

        except Exception as e:
            self.logger.error(f"Error in spread check: {e}")

        return result

    def _check_momentum(self, market_data: Dict) -> Dict:
        """
        Check if momentum is strong enough.

        Returns:
            Filter result
        """
        result = {'passed': True, 'reason': ''}

        try:
            candles = market_data.get('candles', [])

            if len(candles) < 10:
                return result

            # Check recent candle momentum
            recent = candles[-10:]

            # Count directional candles
            bullish = 0
            bearish = 0

            for i, candle in enumerate(recent):
                if i == 0:
                    continue

                body = candle['close'] - candle['open']

                if body > 0:
                    bullish += 1
                elif body < 0:
                    bearish += 1

            # Momentum ratio
            total = bullish + bearish

            if total > 0:
                bull_ratio = bullish / total

                # Require 60%+ directional candles
                if bull_ratio < 0.4 or bull_ratio > 0.6:
                    result['passed'] = False
                    result['reason'] = f'Weak momentum ({bull_ratio:.0%} directional)'
                    return result

            # Check volume trend
            recent_volumes = [c.get('volume', 0) for c in recent[-5:]]

            if recent_volumes:
                avg_vol = sum(recent_volumes) / len(recent_volumes)

                if recent_volumes[-1] < avg_vol * 0.5:
                    result['passed'] = False
                    result['reason'] = 'Declining volume'

        except Exception as e:
            self.logger.error(f"Error in momentum check: {e}")

        return result

    def check_reversal_filter(self, candles: list) -> Dict:
        """
        Check for reversal candle patterns.

        Returns:
            Filter result
        """
        result = {'passed': True, 'reversal_detected': False, 'type': ''}

        try:
            if len(candles) < 3:
                return result

            recent = candles[-3:]

            # Check for engulfing patterns
            if self._is_engulfing(recent):
                result['reversal_detected'] = True
                result['type'] = 'engulfing'
                return result

            # Check for doji
            if self._is_doji(recent[-1]):
                result['reversal_detected'] = True
                result['type'] = 'doji'
                return result

            # Check for hammer/shooting star
            if self._is_hammer_like(recent[-1]):
                result['reversal_detected'] = True
                result['type'] = 'pin_bar'
                return result

        except Exception as e:
            self.logger.error(f"Error in reversal filter: {e}")

        return result

    def _is_engulfing(self, candles: list) -> bool:
        """Check for engulfing pattern."""
        if len(candles) < 2:
            return False

        c1 = candles[-2]
        c2 = candles[-1]

        # Previous candle bearish
        prev_bearish = c1['close'] < c1['open']

        # Current candle bullish
        curr_bullish = c2['close'] > c2['open']

        # Bullish engulfing
        if prev_bearish and curr_bullish:
            if (c2['close'] > c1['open'] and
                c2['open'] < c1['close']):
                return True

        # Previous candle bullish
        prev_bullish = c1['close'] > c1['open']

        # Current candle bearish
        curr_bearish = c2['close'] < c2['open']

        # Bearish engulfing
        if prev_bullish and curr_bearish:
            if (c2['close'] < c1['open'] and
                c2['open'] > c1['close']):
                return True

        return False

    def _is_doji(self, candle: dict) -> bool:
        """Check for doji pattern."""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']

        if total_range > 0 and body / total_range < 0.1:
            return True

        return False

    def _is_hammer_like(self, candle: dict) -> bool:
        """Check for hammer or shooting star pattern."""
        body = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']

        total_range = candle['high'] - candle['low']

        if total_range == 0:
            return False

        # Hammer: long lower wick, small body at top
        if lower_wick > body * 2 and upper_wick < body:
            return True

        # Shooting star: long upper wick, small body at bottom
        if upper_wick > body * 2 and lower_wick < body:
            return True

        return False