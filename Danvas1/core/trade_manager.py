"""
Danvas1 - Trade Manager
Version: 1.0.0

Manages trade execution, position management, and order tracking.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
import time


class TradeManager:
    """
    Manages all trade operations.

    Responsibilities:
    - Open and close positions
    - Set and adjust stop loss / take profit
    - Handle partial exits
    - Track trade state
    - Manage breakeven transitions
    """

    def __init__(self, config: Dict, bybit_client, execution_engine, risk_manager):
        """
        Initialize Trade Manager.

        Args:
            config: Bot configuration dictionary
            bybit_client: Bybit API client
            execution_engine: Order execution engine
            risk_manager: Risk management module
        """
        self.logger = logging.getLogger("Danvas1.TradeManager")
        self.config = config
        self.bybit = bybit_client
        self.execution = execution_engine
        self.risk = risk_manager

        # Trade state tracking
        self.open_trades = {}  # symbol -> trade info

        self.logger.info("Trade Manager initialized")

    def open_position(self, symbol: str, direction: str, entry_price: float,
                      position_size: float, stop_loss: float, take_profit: float,
                      reason: str = '') -> Dict:
        """
        Open a new position.

        Args:
            symbol: Trading symbol
            direction: 'long' or 'short'
            entry_price: Entry price
            position_size: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            reason: Trade reason

        Returns:
            Result dictionary with success status
        """
        result = {
            'success': False,
            'message': '',
            'order_id': None,
            'entry_price': None
        }

        try:
            # Validate parameters
            if direction not in ['long', 'short']:
                result['message'] = f"Invalid direction: {direction}"
                return result

            if position_size <= 0:
                result['message'] = f"Invalid position size: {position_size}"
                return result

            # Execute market order
            order_result = self.execution.place_order(
                symbol=symbol,
                side=direction,
                order_type='Market',
                qty=position_size
            )

            if not order_result['success']:
                result['message'] = order_result.get('message', 'Order failed')
                return result

            order_id = order_result['order_id']
            actual_entry = order_result.get('fill_price', entry_price)

            # Set stop loss
            sl_result = self.execution.set_stop_loss(
                symbol=symbol,
                side='Sell' if direction == 'long' else 'Buy',
                stop_price=stop_loss,
                qty=position_size
            )

            if not sl_result['success']:
                self.logger.warning(f"Failed to set SL for {symbol}: {sl_result.get('message')}")
                # Try to close position if SL fails
                self._emergency_close(symbol)
                result['message'] = "Failed to set SL, position closed"
                return result

            # Set take profit
            tp_result = self.execution.set_take_profit(
                symbol=symbol,
                side='Sell' if direction == 'long' else 'Buy',
                stop_price=take_profit,
                qty=position_size
            )

            if not tp_result['success']:
                self.logger.warning(f"Failed to set TP for {symbol}: {tp_result.get('message')}")

            # Record trade
            self.open_trades[symbol] = {
                'order_id': order_id,
                'direction': direction,
                'entry_price': actual_entry,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'open_time': datetime.now(),
                'reason': reason,
                'sl_order_id': sl_result.get('order_id'),
                'tp_order_id': tp_result.get('order_id'),
                'breakeven_triggered': False,
                'partial_tp_triggered': False
            }

            # Update risk manager
            self.risk.record_trade(symbol)

            self.logger.info(
                f"Position opened: {symbol} {direction.upper()} @ {actual_entry:.4f} "
                f"Size: {position_size} SL: {stop_loss:.4f} TP: {take_profit:.4f}"
            )

            result['success'] = True
            result['message'] = 'Position opened successfully'
            result['entry_price'] = actual_entry

            return result

        except Exception as e:
            self.logger.error(f"Error opening position for {symbol}: {e}")
            result['message'] = str(e)
            return result

    def close_position(self, symbol: str, reason: str = '') -> Dict:
        """
        Close an existing position.

        Args:
            symbol: Trading symbol
            reason: Close reason

        Returns:
            Result dictionary
        """
        result = {'success': False, 'message': '', 'pnl': 0}

        try:
            if symbol not in self.open_trades:
                result['message'] = f"No open position for {symbol}"
                return result

            trade = self.open_trades[symbol]

            # Get current position from exchange
            position = self.bybit.get_position(symbol)
            if not position or position.get('size', 0) == 0:
                self._cleanup_trade(symbol)
                result['success'] = True
                result['message'] = 'Position already closed'
                return result

            # Place market close order
            close_side = 'Sell' if trade['direction'] == 'long' else 'Buy'

            close_result = self.execution.place_order(
                symbol=symbol,
                side=close_side,
                order_type='Market',
                qty=position['size']
            )

            if close_result['success']:
                pnl = self._calculate_pnl(symbol, trade, close_result.get('fill_price'))

                # Update consecutive losses
                if pnl < 0:
                    self.risk.record_loss()
                else:
                    self.risk.record_win()

                self.logger.info(
                    f"Position closed: {symbol} {trade['direction']} "
                    f"PnL: {pnl:.2f} Reason: {reason}"
                )

                result['success'] = True
                result['pnl'] = pnl
                result['message'] = 'Position closed successfully'

                self._cleanup_trade(symbol)
            else:
                result['message'] = close_result.get('message', 'Close failed')

        except Exception as e:
            self.logger.error(f"Error closing position for {symbol}: {e}")
            result['message'] = str(e)

        return result

    def check_partial_tp(self, symbol: str, current_price: float, position: Dict):
        """
        Check and execute partial take profit levels.

        Args:
            symbol: Trading symbol
            current_price: Current price
            position: Position data
        """
        if not self.config['execution'].get('enable_partial_tp', True):
            return

        if symbol not in self.open_trades:
            return

        trade = self.open_trades[symbol]

        # Check TP levels
        tp_levels = self.config['execution'].get('tp_levels', [])

        for level in tp_levels:
            tp_price = level.get('price')
            close_pct = level.get('close_pct', 0.33)

            if tp_price and not trade.get(f'tp{level["index"]}_triggered'):
                # Check if price reached TP level
                if trade['direction'] == 'long' and current_price >= tp_price:
                    self._execute_partial_tp(symbol, close_pct)
                    trade[f'tp{level["index"]}_triggered'] = True
                elif trade['direction'] == 'short' and current_price <= tp_price:
                    self._execute_partial_tp(symbol, close_pct)
                    trade[f'tp{level["index"]}_triggered'] = True

    def _execute_partial_tp(self, symbol: str, close_pct: float):
        """Execute partial take profit."""
        try:
            trade = self.open_trades[symbol]
            current_position = self.bybit.get_position(symbol)

            if not current_position or current_position.get('size', 0) == 0:
                return

            close_qty = current_position['size'] * close_pct
            close_side = 'Sell' if trade['direction'] == 'long' else 'Buy'

            self.execution.place_order(
                symbol=symbol,
                side=close_side,
                order_type='Market',
                qty=close_qty
            )

            self.logger.info(
                f"Partial TP executed: {symbol} {close_pct*100:.0f}% "
                f"Closed: {close_qty:.4f}"
            )

        except Exception as e:
            self.logger.error(f"Error executing partial TP: {e}")

    def check_breakeven(self, symbol: str, current_price: float, position: Dict):
        """
        Move stop loss to breakeven when position is profitable.

        Args:
            symbol: Trading symbol
            current_price: Current price
            position: Position data
        """
        if symbol not in self.open_trades:
            return

        trade = self.open_trades[symbol]

        if trade.get('breakeven_triggered'):
            return

        entry_price = trade['entry_price']
        stop_loss = trade['stop_loss']
        direction = trade['direction']

        # Calculate profit at current price
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price

        # Move to breakeven when profit exceeds 2x risk (1:2 RR reached)
        risk_pct = abs(stop_loss - entry_price) / entry_price
        breakeven_threshold = risk_pct * 2

        if profit_pct >= breakeven_threshold:
            # Move SL to breakeven + small buffer
            buffer = entry_price * 0.001  # 0.1% buffer

            if direction == 'long':
                new_sl = entry_price + buffer
            else:
                new_sl = entry_price - buffer

            # Update stop loss
            self.execution.modify_stop_loss(symbol, new_sl)

            trade['breakeven_triggered'] = True
            trade['stop_loss'] = new_sl

            self.logger.info(
                f"Breakeven set: {symbol} SL moved to {new_sl:.4f} "
                f"(Profit: {profit_pct*100:.2f}%)"
            )

    def check_early_exit(self, symbol: str, current_price: float, position: Dict):
        """
        Check for early exit conditions.

        Args:
            symbol: Trading symbol
            current_price: Current price
            position: Position data
        """
        if symbol not in self.open_trades:
            return

        trade = self.open_trades[symbol]

        # Get candles for pattern analysis
        candles = self.bybit.get_klines(symbol, '15m', limit=20)
        if not candles:
            return

        direction = trade['direction']
        entry_price = trade['entry_price']

        # Check for reversal patterns
        reversal = self._detect_reversal(candles, direction)

        if reversal:
            # Check if price moved against us
            if direction == 'long' and current_price < entry_price:
                self.close_position(symbol, reason=f'Early exit: {reversal}')
            elif direction == 'short' and current_price > entry_price:
                self.close_position(symbol, reason=f'Early exit: {reversal}')

    def _detect_reversal(self, candles: List[Dict], direction: str) -> Optional[str]:
        """Detect potential reversal patterns."""
        if len(candles) < 5:
            return None

        # Get last few candles
        recent = candles[-5:]

        # Check for rejection candle
        if direction == 'long':
            # Bearish engulfing
            if (recent[-2]['close'] < recent[-2]['open'] and
                recent[-1]['close'] > recent[-1]['open'] and
                recent[-1]['close'] > recent[-2]['open'] and
                recent[-1]['open'] < recent[-2]['close']):
                return 'Bearish engulfing'

            # Shooting star
            if (recent[-1]['high'] > recent[-2]['high'] and
                recent[-1]['close'] < recent[-1]['open'] and
                recent[-1]['high'] - max(recent[-1]['close'], recent[-1]['open']) >
                min(recent[-1]['close'], recent[-1]['open']) - recent[-1]['low']):
                return 'Shooting star'

        else:  # short
            # Bullish engulfing
            if (recent[-2]['close'] > recent[-2]['open'] and
                recent[-1]['close'] < recent[-1]['open'] and
                recent[-1]['close'] < recent[-2]['open'] and
                recent[-1]['open'] > recent[-2]['close']):
                return 'Bullish engulfing'

            # Hammer
            if (recent[-1]['low'] < recent[-2]['low'] and
                recent[-1]['close'] > recent[-1]['open'] and
                recent[-1]['open'] < recent[-1]['close'] and
                recent[-1]['high'] - recent[-1]['close'] <
                recent[-1]['open'] - recent[-1]['low']):
                return 'Hammer'

        return None

    def _calculate_pnl(self, symbol: str, trade: Dict, exit_price: float) -> float:
        """Calculate realized PnL for a trade."""
        entry = trade['entry_price']
        direction = trade['direction']
        size = trade['position_size']

        if direction == 'long':
            pnl = (exit_price - entry) * size
        else:
            pnl = (entry - exit_price) * size

        # Subtract fees
        fee_rate = self.config['backtesting'].get('fee_rate', 0.00055)
        fees = (entry + exit_price) * size * fee_rate

        return pnl - fees

    def _cleanup_trade(self, symbol: str):
        """Clean up trade data after position is closed."""
        if symbol in self.open_trades:
            del self.open_trades[symbol]

    def _emergency_close(self, symbol: str):
        """Emergency close for a position."""
        try:
            position = self.bybit.get_position(symbol)
            if position and position.get('size', 0) > 0:
                close_side = 'Sell' if position.get('side') == 'Buy' else 'Buy'
                self.execution.place_order(
                    symbol=symbol,
                    side=close_side,
                    order_type='Market',
                    qty=position['size']
                )
        except Exception as e:
            self.logger.error(f"Emergency close failed for {symbol}: {e}")

    def get_open_trades(self) -> Dict:
        """Get all open trades."""
        return self.open_trades.copy()

    def get_trade(self, symbol: str) -> Optional[Dict]:
        """Get trade info for a symbol."""
        return self.open_trades.get(symbol)