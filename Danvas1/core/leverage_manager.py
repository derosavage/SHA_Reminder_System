"""
Danvas1 - Leverage Manager
Version: 1.0.0

Manages leverage settings for trading positions.
"""

import logging
from typing import Dict, Optional


class LeverageManager:
    """
    Manages leverage settings for positions.

    Responsibilities:
    - Set leverage for symbols
    - Validate leverage limits
    - Handle leverage changes
    - Manage cross/isolated margin
    """

    def __init__(self, config: Dict, bybit_client):
        """
        Initialize Leverage Manager.

        Args:
            config: Bot configuration
            bybit_client: Bybit API client
        """
        self.logger = logging.getLogger("Danvas1.LeverageManager")
        self.config = config
        self.bybit = bybit_client

        # Leverage settings
        self.default_leverage = config['trading'].get('default_leverage', 5)
        self.max_leverage = config['trading'].get('max_leverage', 10)

        # Current leverage cache
        self.leverage_cache = {}

        self.logger.info(
            f"Leverage Manager initialized - Default: {self.default_leverage}x, "
            f"Max: {self.max_leverage}x"
        )

    def set_leverage(self, symbol: str, direction: str = None,
                     leverage: int = None, margin_mode: str = 'isolated') -> Dict:
        """
        Set leverage for a symbol.

        Args:
            symbol: Trading symbol
            direction: 'long' or 'short' (optional)
            leverage: Leverage level (optional, uses default)
            margin_mode: 'isolated' or 'cross'

        Returns:
            Result dictionary
        """
        result = {
            'success': False,
            'message': '',
            'leverage': None
        }

        try:
            # Use default leverage if not specified
            if leverage is None:
                leverage = self.default_leverage

            # Validate leverage
            if leverage > self.max_leverage:
                leverage = self.max_leverage
                self.logger.warning(
                    f"Leverage capped at {self.max_leverage}x for {symbol}"
                )

            if leverage < 1:
                leverage = 1

            # Set leverage via API
            set_result = self.bybit.set_leverage(
                symbol=symbol,
                buy_leverage=leverage if direction != 'short' else self.default_leverage,
                sell_leverage=leverage if direction != 'long' else self.default_leverage,
                margin_mode=margin_mode
            )

            if set_result:
                self.leverage_cache[symbol] = {
                    'leverage': leverage,
                    'margin_mode': margin_mode,
                    'direction': direction
                }

                result['success'] = True
                result['leverage'] = leverage
                result['message'] = f'Leverage set to {leverage}x'

                self.logger.info(
                    f"Leverage set: {symbol} {leverage}x ({margin_mode})"
                )
            else:
                result['message'] = 'Failed to set leverage'

        except Exception as e:
            self.logger.error(f"Error setting leverage for {symbol}: {e}")
            result['message'] = str(e)

        return result

    def get_leverage(self, symbol: str) -> Optional[int]:
        """Get current leverage for a symbol."""
        if symbol in self.leverage_cache:
            return self.leverage_cache[symbol]['leverage']

        try:
            position = self.bybit.get_position(symbol)
            if position:
                return position.get('leverage', self.default_leverage)

        except Exception as e:
            self.logger.error(f"Error getting leverage: {e}")

        return self.default_leverage

    def validate_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Validate if leverage is acceptable.

        Returns:
            Validation result with approved status
        """
        result = {'approved': True, 'reason': ''}

        # Check max limit
        if leverage > self.max_leverage:
            result['approved'] = False
            result['reason'] = f'Leverage {leverage}x exceeds maximum {self.max_leverage}x'
            return result

        # Check minimum
        if leverage < 1:
            result['approved'] = False
            result['reason'] = 'Leverage must be at least 1x'
            return result

        # Get symbol max leverage from specs
        specs = self.bybit.get_symbol_specs(symbol)

        if specs:
            symbol_max = specs.get('max_leverage', self.max_leverage)

            if leverage > symbol_max:
                result['approved'] = False
                result['reason'] = f'Symbol max leverage is {symbol_max}x'
                return result

        return result

    def adjust_leverage_for_volatility(self, symbol: str, atr_pct: float) -> int:
        """
        Adjust leverage based on volatility.

        Args:
            symbol: Trading symbol
            atr_pct: ATR as percentage of price

        Returns:
            Adjusted leverage level
        """
        # High volatility = lower leverage
        if atr_pct > 5:  # > 5% daily range
            return min(3, self.default_leverage)
        elif atr_pct > 3:  # > 3% daily range
            return min(5, self.default_leverage)
        elif atr_pct > 1.5:  # > 1.5% daily range
            return min(7, self.default_leverage)
        else:  # Low volatility
            return self.default_leverage

    def switch_margin_mode(self, symbol: str, mode: str = 'isolated') -> Dict:
        """
        Switch margin mode for a symbol.

        Args:
            symbol: Trading symbol
            mode: 'isolated' or 'cross'

        Returns:
            Result dictionary
        """
        result = {'success': False, 'message': ''}

        try:
            switch_result = self.bybit.switch_margin_mode(
                symbol=symbol,
                margin_mode=mode
            )

            if switch_result:
                result['success'] = True
                result['message'] = f'Margin mode switched to {mode}'

                self.logger.info(f"Margin mode: {symbol} -> {mode}")

            else:
                result['message'] = 'Failed to switch margin mode'

        except Exception as e:
            self.logger.error(f"Error switching margin mode: {e}")
            result['message'] = str(e)

        return result

    def get_margin_info(self, symbol: str) -> Dict:
        """Get margin information for a symbol."""
        try:
            position = self.bybit.get_position(symbol)

            if position:
                return {
                    'margin_mode': position.get('margin_mode', 'isolated'),
                    'leverage': position.get('leverage', self.default_leverage),
                    'isolated_margin': position.get('isolated_margin', 0),
                    'position_margin': position.get('position_margin', 0),
                    'liq_price': position.get('liq_price')
                }

        except Exception as e:
            self.logger.error(f"Error getting margin info: {e}")

        return {}

    def calculate_max_position_size(self, symbol: str, leverage: int = None) -> float:
        """
        Calculate maximum position size based on leverage.

        Args:
            symbol: Trading symbol
            leverage: Leverage level (optional)

        Returns:
            Maximum position size in quote currency
        """
        if leverage is None:
            leverage = self.get_leverage(symbol)

        try:
            balance = self.bybit.get_wallet_balance()
            equity = float(balance.get('equity', 0))

            if equity <= 0:
                return 0.0

            # Max position = equity * leverage
            max_position = equity * leverage

            # Apply max margin usage limit
            max_usage = self.config['risk_management'].get(
                'max_margin_usage_percent', 0.5
            )

            return max_position * max_usage

        except Exception as e:
            self.logger.error(f"Error calculating max position: {e}")
            return 0.0

    def reset_to_default(self, symbol: str):
        """Reset leverage to default for a symbol."""
        self.set_leverage(symbol, leverage=self.default_leverage)

    def get_cache(self) -> Dict:
        """Get leverage cache."""
        return self.leverage_cache.copy()

    def clear_cache(self):
        """Clear leverage cache."""
        self.leverage_cache = {}