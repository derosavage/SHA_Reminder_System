"""
Danvas1 - WebSocket Manager
Version: 1.0.0

Manages WebSocket connections for real-time data.
"""

import logging
from typing import Dict, List, Callable, Optional
import json


class WebSocketManager:
    """
    WebSocket connection manager.

    Responsibilities:
    - Manage WebSocket connections
    - Handle subscriptions
    - Process real-time data
    - Auto-reconnect on disconnect
    """

    def __init__(self, bybit_client):
        """
        Initialize WebSocket Manager.

        Args:
            bybit_client: Bybit API client
        """
        self.logger = logging.getLogger("Danvas1.WSManager")
        self.bybit = bybit_client

        self.ws = None
        self.subscriptions = {}
        self.callbacks = {}
        self.is_connected = False

        self.logger.info("WebSocket Manager initialized")

    def connect(self):
        """Connect to WebSocket."""
        try:
            self.bybit.init_websocket()
            self.ws = self.bybit.ws
            self.is_connected = True

            self.logger.info("WebSocket connected")

        except Exception as e:
            self.logger.error(f"Error connecting WebSocket: {e}")
            self.is_connected = False

    def disconnect(self):
        """Disconnect WebSocket."""
        try:
            if self.bybit:
                self.bybit.stop_websocket()

            self.is_connected = False
            self.logger.info("WebSocket disconnected")

        except Exception as e:
            self.logger.error(f"Error disconnecting WebSocket: {e}")

    def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Subscribe to ticker updates.

        Args:
            symbol: Trading symbol
            callback: Callback function
        """
        try:
            self.bybit.subscribe(
                subscriptions=[{
                    'category': 'linear',
                    'symbol': symbol,
                    'topic': 'tickers'
                }],
                callback=callback
            )

            self.subscriptions[f'ticker_{symbol}'] = {
                'type': 'ticker',
                'symbol': symbol
            }

            self.callbacks[f'ticker_{symbol}'] = callback

            self.logger.info(f"Subscribed to ticker: {symbol}")

        except Exception as e:
            self.logger.error(f"Error subscribing to ticker: {e}")

    def subscribe_orderbook(self, symbol: str, callback: Callable, depth: int = 50):
        """
        Subscribe to orderbook updates.

        Args:
            symbol: Trading symbol
            callback: Callback function
            depth: Order book depth
        """
        try:
            self.bybit.subscribe(
                subscriptions=[{
                    'category': 'linear',
                    'symbol': symbol,
                    'topic': 'orderbook',
                    'depth': depth
                }],
                callback=callback
            )

            self.subscriptions[f'orderbook_{symbol}'] = {
                'type': 'orderbook',
                'symbol': symbol,
                'depth': depth
            }

            self.callbacks[f'orderbook_{symbol}'] = callback

            self.logger.info(f"Subscribed to orderbook: {symbol}")

        except Exception as e:
            self.logger.error(f"Error subscribing to orderbook: {e}")

    def subscribe_trades(self, symbol: str, callback: Callable):
        """
        Subscribe to trade updates.

        Args:
            symbol: Trading symbol
            callback: Callback function
        """
        try:
            self.bybit.subscribe(
                subscriptions=[{
                    'category': 'linear',
                    'symbol': symbol,
                    'topic': 'publicTrade'
                }],
                callback=callback
            )

            self.subscriptions[f'trades_{symbol}'] = {
                'type': 'trades',
                'symbol': symbol
            }

            self.callbacks[f'trades_{symbol}'] = callback

            self.logger.info(f"Subscribed to trades: {symbol}")

        except Exception as e:
            self.logger.error(f"Error subscribing to trades: {e}")

    def subscribe_kline(self, symbol: str, interval: str, callback: Callable):
        """
        Subscribe to kline/candlestick updates.

        Args:
            symbol: Trading symbol
            interval: Timeframe (1m, 5m, 15m, etc.)
            callback: Callback function
        """
        try:
            self.bybit.subscribe(
                subscriptions=[{
                    'category': 'linear',
                    'symbol': symbol,
                    'topic': f'kline_{interval}'
                }],
                callback=callback
            )

            self.subscriptions[f'kline_{symbol}_{interval}'] = {
                'type': 'kline',
                'symbol': symbol,
                'interval': interval
            }

            self.callbacks[f'kline_{symbol}_{interval}'] = callback

            self.logger.info(f"Subscribed to kline: {symbol} {interval}")

        except Exception as e:
            self.logger.error(f"Error subscribing to kline: {e}")

    def unsubscribe(self, subscription_key: str):
        """
        Unsubscribe from a topic.

        Args:
            subscription_key: Subscription key
        """
        if subscription_key in self.subscriptions:
            del self.subscriptions[subscription_key]

        if subscription_key in self.callbacks:
            del self.callbacks[subscription_key]

        self.logger.info(f"Unsubscribed: {subscription_key}")

    def unsubscribe_all(self):
        """Unsubscribe from all topics."""
        self.subscriptions.clear()
        self.callbacks.clear()

        self.logger.info("Unsubscribed from all topics")

    def get_subscriptions(self) -> List[Dict]:
        """Get list of active subscriptions."""
        return list(self.subscriptions.values())

    def is_active(self) -> bool:
        """Check if WebSocket is active."""
        return self.is_connected

    def handle_message(self, message: Dict):
        """
        Handle incoming WebSocket message.

        Args:
            message: WebSocket message
        """
        try:
            topic = message.get('topic', '')

            # Find matching callback
            for key, callback in self.callbacks.items():
                if key in topic or topic in key:
                    callback(message.get('data', {}))
                    break

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def reconnect(self):
        """Reconnect WebSocket with existing subscriptions."""
        self.logger.info("Reconnecting WebSocket...")

        # Store subscriptions
        temp_subs = self.subscriptions.copy()
        temp_callbacks = self.callbacks.copy()

        # Disconnect
        self.disconnect()

        # Reconnect
        self.connect()

        # Resubscribe
        for key, sub in temp_subs.items():
            if key in temp_callbacks:
                callback = temp_callbacks[key]

                if sub['type'] == 'ticker':
                    self.subscribe_ticker(sub['symbol'], callback)
                elif sub['type'] == 'orderbook':
                    self.subscribe_orderbook(sub['symbol'], callback, sub.get('depth', 50))
                elif sub['type'] == 'trades':
                    self.subscribe_trades(sub['symbol'], callback)
                elif sub['type'] == 'kline':
                    self.subscribe_kline(sub['symbol'], sub['interval'], callback)

        self.logger.info("WebSocket reconnected")