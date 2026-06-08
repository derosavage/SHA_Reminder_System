"""
Danvas1 - Order Execution
Version: 1.0.0

Handles order execution logic and validation.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class OrderExecution:
    """
    Order execution handling.

    Responsibilities:
    - Validate order parameters
    - Execute orders with proper formatting
    - Handle partial fills
    - Track order state
    """

    def __init__(self, bybit_client, config: Dict):
        """
        Initialize Order Execution.

        Args:
            bybit_client: Bybit API client
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.OrderExecution")
        self.bybit = bybit_client
        self.config = config

        # Order tracking
        self.pending_orders = {}
        self.executed_orders = []

        self.logger.info("Order Execution initialized")

    def execute_market_order(self, symbol: str, side: str,
                            quantity: float) -> Dict:
        """
        Execute a market order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            quantity: Order quantity

        Returns:
            Execution result
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None,
            'fill_price': None,
            'quantity': 0
        }

        try:
            # Validate quantity
            validated_qty = self._validate_quantity(symbol, quantity)

            if validated_qty <= 0:
                result['message'] = 'Invalid quantity'
                return result

            # Place order
            order = self.bybit.place_order(
                symbol=symbol,
                side=side,
                order_type='Market',
                qty=validated_qty
            )

            if order:
                result['success'] = True
                result['order_id'] = order.get('order_id')
                result['fill_price'] = order.get('fill_price')
                result['quantity'] = validated_qty

                self._track_order(order)

                self.logger.info(
                    f"Market order executed: {symbol} {side} {validated_qty}"
                )
            else:
                result['message'] = 'Order placement failed'

        except Exception as e:
            self.logger.error(f"Error executing market order: {e}")
            result['message'] = str(e)

        return result

    def execute_limit_order(self, symbol: str, side: str,
                           quantity: float, price: float) -> Dict:
        """
        Execute a limit order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            quantity: Order quantity
            price: Limit price

        Returns:
            Execution result
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None,
            'price': price
        }

        try:
            # Validate
            validated_qty = self._validate_quantity(symbol, quantity)
            validated_price = self._validate_price(symbol, price)

            if validated_qty <= 0:
                result['message'] = 'Invalid quantity'
                return result

            # Place order
            order = self.bybit.place_order(
                symbol=symbol,
                side=side,
                order_type='Limit',
                qty=validated_qty,
                price=validated_price
            )

            if order:
                result['success'] = True
                result['order_id'] = order.get('order_id')

                self._track_order(order)

                self.logger.info(
                    f"Limit order placed: {symbol} {side} {validated_qty} @ {validated_price}"
                )
            else:
                result['message'] = 'Order placement failed'

        except Exception as e:
            self.logger.error(f"Error executing limit order: {e}")
            result['message'] = str(e)

        return result

    def set_stop_loss(self, symbol: str, side: str,
                      stop_price: float, quantity: float) -> Dict:
        """
        Set stop loss order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            stop_price: Stop price
            quantity: Order quantity

        Returns:
            Result dict
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None
        }

        try:
            validated_qty = self._validate_quantity(symbol, quantity)
            validated_price = self._validate_price(symbol, stop_price)

            order = self.bybit.place_conditional_order(
                symbol=symbol,
                side=side,
                trigger_price=validated_price,
                qty=validated_qty,
                order_type='Market',
                reduce_only=True
            )

            if order:
                result['success'] = True
                result['order_id'] = order.get('order_id')

                self.logger.info(f"Stop loss set: {symbol} {side} @ {validated_price}")

            else:
                result['message'] = 'SL placement failed'

        except Exception as e:
            self.logger.error(f"Error setting stop loss: {e}")
            result['message'] = str(e)

        return result

    def set_take_profit(self, symbol: str, side: str,
                       trigger_price: float, quantity: float) -> Dict:
        """
        Set take profit order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            trigger_price: Trigger price
            quantity: Order quantity

        Returns:
            Result dict
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None
        }

        try:
            validated_qty = self._validate_quantity(symbol, quantity)
            validated_price = self._validate_price(symbol, trigger_price)

            order = self.bybit.place_conditional_order(
                symbol=symbol,
                side=side,
                trigger_price=validated_price,
                qty=validated_qty,
                order_type='Market',
                reduce_only=True
            )

            if order:
                result['success'] = True
                result['order_id'] = order.get('order_id')

                self.logger.info(f"Take profit set: {symbol} {side} @ {validated_price}")

            else:
                result['message'] = 'TP placement failed'

        except Exception as e:
            self.logger.error(f"Error setting take profit: {e}")
            result['message'] = str(e)

        return result

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order."""
        result = {'success': False, 'message': ''}

        try:
            success = self.bybit.cancel_order(order_id)

            if success:
                result['success'] = True

                # Remove from tracking
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]

            else:
                result['message'] = 'Cancel failed'

        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            result['message'] = str(e)

        return result

    def modify_order(self, order_id: str, new_price: float,
                    new_quantity: float = None) -> Dict:
        """Modify an existing order."""
        result = {'success': False, 'message': ''}

        try:
            # Cancel and replace
            self.bybit.cancel_order(order_id)

            # Get original order
            order = self.bybit.get_order(order_id)

            if order:
                # Place new order
                new_order = self.bybit.place_order(
                    symbol=order['symbol'],
                    side=order['side'],
                    order_type='Limit',
                    qty=new_quantity or float(order['qty']),
                    price=new_price
                )

                if new_order:
                    result['success'] = True
                    result['order_id'] = new_order.get('order_id')

        except Exception as e:
            self.logger.error(f"Error modifying order: {e}")
            result['message'] = str(e)

        return result

    def _validate_quantity(self, symbol: str, quantity: float) -> float:
        """Validate and round quantity."""
        try:
            specs = self.bybit.get_symbol_specs(symbol)

            if specs:
                step = specs.get('step', 0.001)
                min_qty = specs.get('min_order_qty', 0.001)
                max_qty = specs.get('max_order_qty', 100)

                # Round to step
                quantity = round(quantity / step) * step

                # Apply limits
                quantity = max(min_qty, quantity)
                quantity = min(max_qty, quantity)

            return quantity

        except Exception as e:
            self.logger.error(f"Error validating quantity: {e}")
            return 0.0

    def _validate_price(self, symbol: str, price: float) -> float:
        """Validate and round price."""
        try:
            specs = self.bybit.get_symbol_specs(symbol)

            if specs:
                tick_size = specs.get('tick_size', 0.01)

                # Round to tick size
                price = round(price / tick_size) * tick_size

            return price

        except Exception as e:
            self.logger.error(f"Error validating price: {e}")
            return 0.0

    def _track_order(self, order: Dict):
        """Track order in internal state."""
        order_id = order.get('order_id')

        if order_id:
            self.pending_orders[order_id] = {
                'order_id': order_id,
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'qty': order.get('qty'),
                'time': datetime.now()
            }

    def get_pending_count(self) -> int:
        """Get number of pending orders."""
        return len(self.pending_orders)

    def get_recent_fills(self, count: int = 10) -> List[Dict]:
        """Get recent order fills."""
        return self.executed_orders[-count:]

    def clear_stale_orders(self, max_age_minutes: int = 30):
        """Clear stale pending orders."""
        now = datetime.now()

        for order_id, order in list(self.pending_orders.items()):
            age = (now - order['time']).total_seconds() / 60

            if age > max_age_minutes:
                self.logger.warning(f"Clearing stale order: {order_id}")
                del self.pending_orders[order_id]