"""
Danvas1 - Risk Manager
Version: 1.0.0

Handles risk management, position sizing, and trade validation.
Capital preservation is the highest priority.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import math


class RiskManager:
    """
    Manages all risk-related operations.

    Responsibilities:
    - Position sizing based on risk
    - Daily drawdown tracking
    - Trade cooldown management
    - Risk validation
    - Capital preservation
    """

    def __init__(self, config: Dict, bybit_client):
        """
        Initialize Risk Manager.

        Args:
            config: Bot configuration dictionary
            bybit_client: Bybit API client
        """
        self.logger = logging.getLogger("Danvas1.RiskManager")
        self.config = config
        self.bybit = bybit_client

        # Risk parameters
        self.risk_percent = config['risk_management']['risk_percent']  # 20% default
        self.max_daily_drawdown = config['risk_management']['max_daily_drawdown']  # 5% default
        self.max_consecutive_losses = config['risk_management']['max_consecutive_losses']
        self.trade_cooldown = config['risk_management']['trade_cooldown_minutes']
        self.min_rr_ratio = config['risk_management']['min_risk_reward_ratio']

        # State tracking
        self.daily_starting_equity = 0
        self.last_trade_time = {}  # Per symbol
        self.consecutive_losses = 0
        self.last_reset_date = datetime.now().date()

        self.logger.info(f"Risk Manager initialized - Risk per trade: {self.risk_percent * 100}%")

    def get_equity(self) -> float:
        """Get current account equity."""
        try:
            balance = self.bybit.get_wallet_balance()
            if balance:
                return float(balance.get('equity', 0))
            return 0.0
        except Exception as e:
            self.logger.error(f"Failed to get equity: {e}")
            return 0.0

    def get_available_margin(self) -> float:
        """Get available margin for trading."""
        try:
            balance = self.bybit.get_wallet_balance()
            if balance:
                return float(balance.get('availableToBorrow', 0))
            return 0.0
        except Exception as e:
            self.logger.error(f"Failed to get available margin: {e}")
            return 0.0

    def calculate_position_size(self, symbol: str, entry_price: float,
                                stop_loss: float, direction: str) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            symbol: Trading symbol
            entry_price: Planned entry price
            stop_loss: Stop loss price
            direction: 'long' or 'short'

        Returns:
            Position size in quote currency (USDT)
        """
        try:
            equity = self.get_equity()

            if equity <= 0:
                self.logger.warning("No equity available for position sizing")
                return 0.0

            # Calculate risk amount
            risk_amount = equity * self.risk_percent

            # Calculate price distance to SL
            if direction == 'long':
                sl_distance = entry_price - stop_loss
            else:
                sl_distance = stop_loss - entry_price

            if sl_distance <= 0:
                self.logger.warning(f"Invalid SL distance for {symbol}")
                return 0.0

            # Calculate position size (in quote currency)
            position_size = risk_amount / sl_distance

            # Apply max margin usage
            max_margin_usage = self.config['risk_management'].get('max_margin_usage_percent', 0.5)
            available_margin = self.get_available_margin()
            max_position_value = available_margin * max_margin_usage

            position_size = min(position_size, max_position_value)

            # Round to symbol precision
            position_size = self._round_to_precision(symbol, position_size)

            # Minimum check
            min_order = self.bybit.get_min_order_size(symbol)
            if position_size < min_order:
                self.logger.debug(f"Position size {position_size} below minimum {min_order}")
                return 0.0

            self.logger.info(
                f"Position sizing for {symbol}: "
                f"Equity={equity:.2f}, Risk={risk_amount:.2f}, "
                f"SL distance={sl_distance:.2f}, Size={position_size:.2f}"
            )

            return position_size

        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0

    def _round_to_precision(self, symbol: str, value: float) -> float:
        """Round value to symbol's precision."""
        # Get symbol specs
        specs = self.bybit.get_symbol_specs(symbol)

        if specs:
            # Round to lot size precision
            step_size = specs.get('lot_size_filter', {}).get('step', 0.001)
            value = math.floor(value / step_size) * step_size

        return value

    def validate_signal(self, symbol: str, signal: Dict, market_data: Dict) -> Dict:
        """
        Validate if a signal meets risk management criteria.

        Args:
            symbol: Trading symbol
            signal: Trading signal
            market_data: Current market data

        Returns:
            Validation result with 'approved' boolean and 'reason'
        """
        result = {'approved': False, 'reason': ''}

        try:
            # Check if already in cooldown
            if not self.can_trade(symbol):
                result['reason'] = 'Trade cooldown active'
                return result

            # Check daily drawdown
            equity = self.get_equity()
            daily_loss = self.daily_starting_equity - equity if self.daily_starting_equity > 0 else 0

            if daily_loss > self.max_daily_drawdown * self.daily_starting_equity:
                result['reason'] = f"Daily drawdown limit exceeded ({daily_loss:.2f})"
                self.logger.warning(result['reason'])
                return result

            # Check consecutive losses
            if self.consecutive_losses >= self.max_consecutive_losses:
                result['reason'] = f"Max consecutive losses reached ({self.consecutive_losses})"
                self.logger.warning(result['reason'])
                return result

            # Check risk/reward ratio
            rr_ratio = signal.get('rr_ratio', 0)
            if rr_ratio < self.min_rr_ratio:
                result['reason'] = f"Risk/Reward ratio {rr_ratio:.2f} below minimum {self.min_rr_ratio}"
                return result

            # Check margin availability
            position_size = signal.get('position_size', 0)
            available_margin = self.get_available_margin()

            if position_size > available_margin * 0.5:  # Use max 50% of available
                result['reason'] = "Insufficient margin for position"
                return result

            # Check symbol liquidity
            ticker = market_data.get('ticker', {})
            if ticker:
                spread = abs(ticker.get('bid1', 0) - ticker.get('ask1', 0))
                mid_price = (ticker.get('bid1', 0) + ticker.get('ask1', 0)) / 2

                if mid_price > 0:
                    spread_pct = (spread / mid_price) * 100
                    if spread_pct > 0.5:  # More than 0.5% spread
                        result['reason'] = f"Low liquidity (spread: {spread_pct:.2f}%)"
                        return result

            # Check volatility
            candles = market_data.get('candles', [])
            if len(candles) < 20:
                result['reason'] = "Insufficient data for volatility check"
                return result

            # All checks passed
            result['approved'] = True
            result['reason'] = 'All risk checks passed'

            return result

        except Exception as e:
            self.logger.error(f"Error validating signal: {e}")
            result['reason'] = f'Validation error: {e}'
            return result

    def can_trade(self, symbol: str) -> bool:
        """Check if we can trade this symbol (cooldown check)."""
        if symbol not in self.last_trade_time:
            return True

        last_time = self.last_trade_time[symbol]
        elapsed = datetime.now() - last_time

        return elapsed.total_seconds() / 60 >= self.trade_cooldown

    def record_trade(self, symbol: str):
        """Record a trade for cooldown tracking."""
        self.last_trade_time[symbol] = datetime.now()

    def record_win(self):
        """Record a winning trade."""
        self.consecutive_losses = 0
        self.logger.info("Trade won - resetting consecutive losses counter")

    def record_loss(self):
        """Record a losing trade."""
        self.consecutive_losses += 1
        self.logger.warning(f"Trade lost - consecutive losses: {self.consecutive_losses}")

    def reset_daily(self):
        """Reset daily tracking metrics."""
        self.daily_starting_equity = self.get_equity()
        self.consecutive_losses = 0
        self.last_reset_date = datetime.now().date()
        self.logger.info("Daily risk metrics reset")

    def check_daily_reset(self):
        """Check if we need to reset for a new day."""
        current_date = datetime.now().date()

        if current_date > self.last_reset_date:
            self.reset_daily()

    def get_risk_stats(self) -> Dict:
        """Get current risk statistics."""
        return {
            'equity': self.get_equity(),
            'available_margin': self.get_available_margin(),
            'consecutive_losses': self.consecutive_losses,
            'daily_loss': self.daily_starting_equity - self.get_equity() if self.daily_starting_equity > 0 else 0,
            'last_trades': {s: t.isoformat() for s, t in self.last_trade_time.items()}
        }

    def check_liquidation_risk(self, symbol: str, entry_price: float,
                              position_size: float, leverage: int) -> Dict:
        """
        Check liquidation risk for a potential trade.

        Returns:
            Dict with liquidation price and risk assessment
        """
        try:
            specs = self.bybit.get_symbol_specs(symbol)
            if not specs:
                return {'risk': 'unknown'}

            # Get maintenance margin rate
            mm_rate = specs.get('maintenance_margin_rate', 0.005)  # 0.5% default

            # Calculate liquidation price
            if leverage > 0:
                margin_ratio = 1 / leverage
                liquidation_buffer = margin_ratio - mm_rate

                # For long position
                liq_price_long = entry_price * (1 - liquidation_buffer)
                # For short position
                liq_price_short = entry_price * (1 + liquidation_buffer)

                return {
                    'leverage': leverage,
                    'liquidation_long': liq_price_long,
                    'liquidation_short': liq_price_short,
                    'risk': 'low' if liquidation_buffer > 0.02 else 'medium' if liquidation_buffer > 0.01 else 'high'
                }

        except Exception as e:
            self.logger.error(f"Error calculating liquidation risk: {e}")

        return {'risk': 'unknown'}

    def validate_stop_loss(self, symbol: str, entry_price: float,
                           stop_loss: float, direction: str) -> Dict:
        """
        Validate stop loss placement.

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Proposed stop loss
            direction: 'long' or 'short'

        Returns:
            Validation result
        """
        try:
            # Calculate SL distance
            if direction == 'long':
                sl_distance = entry_price - stop_loss
            else:
                sl_distance = stop_loss - entry_price

            if sl_distance <= 0:
                return {'valid': False, 'reason': 'SL is on wrong side of entry'}

            # Get ATR for relative check
            candles = self.bybit.get_klines(symbol, '15m', limit=50)
            if candles:
                # Simple ATR calculation
                highs = [c['high'] for c in candles]
                lows = [c['low'] for c in candles]
                closes = [c['close'] for c in candles]

                trs = []
                for i in range(1, len(candles)):
                    tr = max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i-1]),
                        abs(lows[i] - closes[i-1])
                    )
                    trs.append(tr)

                atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else trs[-1]

                # SL should be at least 1 ATR away
                min_sl_distance = atr * 1.0

                if sl_distance < min_sl_distance:
                    return {
                        'valid': False,
                        'reason': f'SL too tight ({sl_distance:.2f} < {min_sl_distance:.2f} min)'
                    }

            # Check against liquidation distance
            leverage = self.config['trading'].get('default_leverage', 5)
            margin_ratio = 1 / leverage

            if sl_distance / entry_price > margin_ratio * 0.8:
                return {
                    'valid': False,
                    'reason': 'SL too close to liquidation zone'
                }

            return {'valid': True, 'reason': 'SL placement valid'}

        except Exception as e:
            self.logger.error(f"Error validating SL: {e}")
            return {'valid': False, 'reason': str(e)}