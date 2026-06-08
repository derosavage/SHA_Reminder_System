"""
Danvas1 - Symbol Specifications
Version: 1.0.0

Manages symbol specifications and constraints for Bybit USDT perpetuals.
"""

import logging
from typing import Dict, Optional


class SymbolSpecs:
    """
    Symbol specifications and constraints.

    Responsibilities:
    - Store symbol-specific parameters
    - Validate order quantities
    - Calculate precision requirements
    """

    # Common symbol specs (can be fetched from API)
    DEFAULT_SPECS = {
        'BTCUSDT': {
            'price_precision': 2,
            'qty_precision': 3,
            'min_order_qty': 0.001,
            'max_order_qty': 100,
            'step': 0.001,
            'tick_size': 0.01,
            'min_order_usd': 5,
            'max_leverage': 100,
            'maintenance_margin_rate': 0.005
        },
        'ETHUSDT': {
            'price_precision': 2,
            'qty_precision': 3,
            'min_order_qty': 0.01,
            'max_order_qty': 1000,
            'step': 0.01,
            'tick_size': 0.01,
            'min_order_usd': 5,
            'max_leverage': 100,
            'maintenance_margin_rate': 0.005
        }
    }

    def __init__(self, bybit_client):
        """
        Initialize Symbol Specs.

        Args:
            bybit_client: Bybit API client
        """
        self.logger = logging.getLogger("Danvas1.SymbolSpecs")
        self.bybit = bybit_client

        # Cache for specs
        self._cache = {}

        self.logger.info("Symbol Specs initialized")

    def get_specs(self, symbol: str) -> Dict:
        """
        Get specs for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Symbol specifications dict
        """
        # Check cache first
        if symbol in self._cache:
            return self._cache[symbol]

        # Try to fetch from API
        specs = self.bybit.get_symbol_specs(symbol)

        if specs:
            self._cache[symbol] = specs
            return specs

        # Use defaults
        if symbol in self.DEFAULT_SPECS:
            return self.DEFAULT_SPECS[symbol]

        # Generic defaults
        return {
            'price_precision': 4,
            'qty_precision': 4,
            'min_order_qty': 0.001,
            'max_order_qty': 100,
            'step': 0.001,
            'tick_size': 0.0001,
            'min_order_usd': 5,
            'max_leverage': 50,
            'maintenance_margin_rate': 0.005
        }

    def validate_quantity(self, symbol: str, quantity: float) -> float:
        """
        Validate and round quantity to symbol precision.

        Args:
            symbol: Trading symbol
            quantity: Quantity to validate

        Returns:
            Rounded quantity
        """
        specs = self.get_specs(symbol)

        step = specs.get('step', 0.001)
        min_qty = specs.get('min_order_qty', 0.001)
        max_qty = specs.get('max_order_qty', 100)

        # Round to step
        rounded = round(quantity / step) * step

        # Apply limits
        rounded = max(min_qty, rounded)
        rounded = min(max_qty, rounded)

        return rounded

    def validate_price(self, symbol: str, price: float) -> float:
        """
        Validate and round price to symbol precision.

        Args:
            symbol: Trading symbol
            price: Price to validate

        Returns:
            Rounded price
        """
        specs = self.get_specs(symbol)

        tick_size = specs.get('tick_size', 0.01)

        # Round to tick size
        rounded = round(price / tick_size) * tick_size

        return rounded

    def calculate_max_leverage(self, symbol: str, account_equity: float) -> int:
        """
        Calculate maximum safe leverage based on position value.

        Args:
            symbol: Trading symbol
            account_equity: Account equity

        Returns:
            Recommended leverage
        """
        specs = self.get_specs(symbol)

        max_leverage = int(specs.get('max_leverage', 50))

        # Conservative limits based on position sizing
        if account_equity < 1000:
            return min(5, max_leverage)
        elif account_equity < 10000:
            return min(10, max_leverage)
        else:
            return min(20, max_leverage)

    def get_min_order_value(self, symbol: str) -> float:
        """Get minimum order value in USD."""
        specs = self.get_specs(symbol)

        return specs.get('min_order_usd', 5)

    def format_price(self, symbol: str, price: float) -> str:
        """Format price to string with correct precision."""
        specs = self.get_specs(symbol)

        precision = specs.get('price_precision', 4)

        return f"{price:.{precision}f}"

    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity to string with correct precision."""
        specs = self.get_specs(symbol)

        precision = specs.get('qty_precision', 3)

        return f"{quantity:.{precision}f}"

    def clear_cache(self):
        """Clear specs cache."""
        self._cache = {}