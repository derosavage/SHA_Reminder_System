"""
Danvas1 - Execution Engine
Version: 1.0.0

Handles order execution, retry logic, and error handling.
"""

import logging
import time
from typing import Dict, Optional
from datetime import datetime


class ExecutionEngine:
    """
    Handles all order execution with retry logic and safety features.

    Responsibilities:
    - Place orders with retry logic
    - Handle API failures gracefully
    - Verify order fills
    - Prevent duplicate orders
    - Manage order modifications
    """

    def __init__(self, bybit_client, config: Dict):
        """
        Initialize Execution Engine.

        Args:
            bybit_client: Bybit API client
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.Execution")
        self.bybit = bybit_client
        self.config = config

        # Execution parameters
        self.max_retries = config['safety'].get('max_api_retries', 3)
        self.retry_delay = config['safety'].get('retry_delay_seconds', 5)
        self.fill_timeout = config['execution'].get('fill_timeout_seconds', 30)
        self.max_slippage = config['execution'].get('max_slippage_percent', 0.3)

        # Order tracking
        self.pending_orders = {}  # order_id -> order info
        self.last_order_id = None

        self.logger.info("Execution Engine initialized")

    def place_order(self, symbol: str, side: str, order_type: str,
                    qty: float, price: Optional[float] = None) -> Dict:
        """
        Place an order with retry logic.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            order_type: 'Market' or 'Limit'
            qty: Order quantity
            price: Limit price (optional for market orders)

        Returns:
            Result dictionary with success status and order details
        """
        result = {
            'success': False,
            'order_id': None,
            'fill_price': None,
            'message': ''
        }

        for attempt in range(self.max_retries):
            try:
                # Check for duplicate
                if self._is_duplicate_order(symbol, side, qty):
                    result['message'] = 'Duplicate order detected'
                    return result

                # Place order
                order_result = self.bybit.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    qty=qty,
                    price=price
                )

                if order_result and order_result.get('order_id'):
                    order_id = order_result['order_id']
                    self.last_order_id = order_id

                    # Track pending order
                    self.pending_orders[order_id] = {
                        'symbol': symbol,
                        'side': side,
                        'qty': qty,
                        'time': datetime.now()
                    }

                    # Wait for fill confirmation
                    if order_type == 'Market':
                        fill_result = self._wait_for_fill(order_id)

                        if fill_result['filled']:
                            result['success'] = True
                            result['order_id'] = order_id
                            result['fill_price'] = fill_result['fill_price']
                            result['message'] = 'Order filled'
                        else:
                            result['message'] = f'Fill timeout: {fill_result.get("message")}'
                    else:
                        result['success'] = True
                        result['order_id'] = order_id
                        result['message'] = 'Order placed'

                    self.logger.info(
                        f"Order placed: {symbol} {side} {qty} @ {price or 'MKT'} "
                        f"ID: {order_id}"
                    )

                    return result

            except Exception as e:
                self.logger.error(f"Order attempt {attempt + 1} failed: {e}")

            # Retry delay
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        result['message'] = f'Failed after {self.max_retries} attempts'
        self.logger.error(f"Order failed for {symbol}: {result['message']}")

        return result

    def _is_duplicate_order(self, symbol: str, side: str, qty: float) -> bool:
        """Check for duplicate orders within time window."""
        current_time = datetime.now()

        for order_id, order_info in list(self.pending_orders.items()):
            # Clean up old orders
            age = (current_time - order_info['time']).total_seconds()

            if age > 60:  # Older than 60 seconds
                del self.pending_orders[order_id]
                continue

            # Check for same symbol/side/qty
            if (order_info['symbol'] == symbol and
                order_info['side'] == side and
                order_info['qty'] == qty):
                return True

        return False

    def _wait_for_fill(self, order_id: str) -> Dict:
        """Wait for order to be filled."""
        start_time = time.time()

        while time.time() - start_time < self.fill_timeout:
            try:
                order_status = self.bybit.get_order(order_id)

                if order_status:
                    if order_status.get('status') == 'Filled':
                        return {
                            'filled': True,
                            'fill_price': order_status.get('avg_price')
                        }
                    elif order_status.get('status') == 'Cancelled':
                        return {
                            'filled': False,
                            'message': 'Order cancelled'
                        }

                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error checking order status: {e}")

        return {
            'filled': False,
            'message': 'Fill timeout'
        }

    def set_stop_loss(self, symbol: str, side: str, stop_price: float,
                      qty: float, reduce_only: bool = True) -> Dict:
        """
        Set stop loss order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            stop_price: Stop price
            qty: Order quantity
            reduce_only: Only reduce position

        Returns:
            Result dictionary
        """
        result = {
            'success': False,
            'order_id': None,
            'message': ''
        }

        for attempt in range(self.max_retries):
            try:
                # Place conditional order for stop loss
                sl_order = self.bybit.place_conditional_order(
                    symbol=symbol,
                    side=side,
                    trigger_price=stop_price,
                    qty=qty,
                    order_type='StopLoss',
                    reduce_only=reduce_only
                )

                if sl_order and sl_order.get('order_id'):
                    result['success'] = True
                    result['order_id'] = sl_order['order_id']
                    result['message'] = 'SL order placed'

                    self.logger.info(
                        f"SL set: {symbol} {side} @ {stop_price}"
                    )

                    return result

            except Exception as e:
                self.logger.error(f"SL order attempt {attempt + 1} failed: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        result['message'] = 'Failed to set SL'
        return result

    def set_take_profit(self, symbol: str, side: str, stop_price: float,
                        qty: float, reduce_only: bool = True) -> Dict:
        """
        Set take profit order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            stop_price: Take profit price
            qty: Order quantity
            reduce_only: Only reduce position

        Returns:
            Result dictionary
        """
        result = {
            'success': False,
            'order_id': None,
            'message': ''
        }

        for attempt in range(self.max_retries):
            try:
                # Place conditional order for take profit
                tp_order = self.bybit.place_conditional_order(
                    symbol=symbol,
                    side=side,
                    trigger_price=stop_price,
                    qty=qty,
                    order_type='TakeProfit',
                    reduce_only=reduce_only
                )

                if tp_order and tp_order.get('order_id'):
                    result['success'] = True
                    result['order_id'] = tp_order['order_id']
                    result['message'] = 'TP order placed'

                    self.logger.info(
                        f"TP set: {symbol} {side} @ {stop_price}"
                    )

                    return result

            except Exception as e:
                self.logger.error(f"TP order attempt {attempt + 1} failed: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        result['message'] = 'Failed to set TP'
        return result

    def modify_stop_loss(self, symbol: str, new_stop_price: float) -> Dict:
        """
        Modify existing stop loss order.

        Args:
            symbol: Trading symbol
            new_stop_price: New stop price

        Returns:
            Result dictionary
        """
        result = {
            'success': False,
            'message': ''
        }

        try:
            # Cancel existing SL orders
            open_orders = self.bybit.get_open_orders(symbol)

            for order in open_orders:
                if order.get('stop_loss'):
                    self.bybit.cancel_order(order['order_id'])
                    time.sleep(0.5)

            # Get current position
            position = self.bybit.get_position(symbol)
            if not position or position.get('size', 0) == 0:
                result['message'] = 'No position to set SL'
                return result

            # Set new SL
            direction = 'Sell' if position.get('side') == 'Buy' else 'Buy'

            return self.set_stop_loss(
                symbol=symbol,
                side=direction,
                stop_price=new_stop_price,
                qty=position['size']
            )

        except Exception as e:
            self.logger.error(f"Error modifying SL: {e}")
            result['message'] = str(e)

        return result

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order."""
        result = {'success': False, 'message': ''}

        try:
            cancel_result = self.bybit.cancel_order(order_id)

            if cancel_result:
                result['success'] = True
                result['message'] = 'Order cancelled'

                # Remove from pending
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            result['message'] = str(e)

        return result

    def cancel_all_orders(self, symbol: str) -> Dict:
        """Cancel all open orders for a symbol."""
        result = {'success': False, 'cancelled_count': 0, 'message': ''}

        try:
            open_orders = self.bybit.get_open_orders(symbol)

            for order in open_orders:
                self.bybit.cancel_order(order['order_id'])

            result['success'] = True
            result['cancelled_count'] = len(open_orders)
            result['message'] = f'Cancelled {len(open_orders)} orders'

            self.logger.info(f"Cancelled all orders for {symbol}")

        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")
            result['message'] = str(e)

        return result

    def verify_position(self, symbol: str) -> Dict:
        """Verify position matches expected state."""
        try:
            position = self.bybit.get_position(symbol)

            return {
                'exists': position is not None and position.get('size', 0) > 0,
                'size': position.get('size', 0) if position else 0,
                'side': position.get('side') if position else None,
                'entry_price': position.get('entry_price') if position else None,
                'unrealized_pnl': position.get('unrealized_pnl', 0) if position else 0
            }

        except Exception as e:
            self.logger.error(f"Error verifying position: {e}")
            return {'exists': False, 'error': str(e)}

    def get_pending_orders(self) -> Dict:
        """Get all pending orders."""
        return self.pending_orders.copy()

    def clear_stale_orders(self):
        """Clear orders that have been pending too long."""
        current_time = datetime.now()

        for order_id, order_info in list(self.pending_orders.items()):
            age = (current_time - order_info['time']).total_seconds()

            if age > 300:  # 5 minutes
                self.logger.warning(f"Clearing stale order: {order_id}")
                del self.pending_orders[order_id]