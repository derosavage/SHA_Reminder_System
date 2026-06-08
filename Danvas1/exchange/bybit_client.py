"""
Danvas1 - Bybit Client
Version: 1.0.0

Unified Bybit API client for trading operations.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from pybit.unified_trading import HTTP, WebSocket
from pathlib import Path
import json


class BybitClient:
    """
    Bybit API client wrapper.

    Responsibilities:
    - Handle all API communications
    - Manage authentication
    - Provide unified interface for trading
    - Handle errors and retries
    """

    def __init__(self, api_key: str = '', api_secret: str = '',
                 testnet: bool = False, recv_window: int = 5000):
        """
        Initialize Bybit Client.

        Args:
            api_key: API key
            api_secret: API secret
            testnet: Use testnet
            recv_window: Request window
        """
        self.logger = logging.getLogger("Danvas1.BybitClient")
        self.api_key = api_key
        self.api_secret = api_secret
        self.recv_window = recv_window
        self.testnet = testnet

        # Initialize HTTP session
        self.http = HTTP(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet
        )

        # WebSocket session (lazy initialization)
        self.ws = None
        self.ws_subscriptions = []

        self.logger.info(f"Bybit Client initialized (Testnet: {testnet})")

    def _http_request(self, method_names, *args, **kwargs):
        """Call the first available HTTP method from a list of names."""
        for method_name in method_names:
            if hasattr(self.http, method_name):
                self.logger.debug(
                    f"HTTP request: {method_name} args={args} kwargs={kwargs}"
                )
                response = getattr(self.http, method_name)(*args, **kwargs)
                self.logger.debug(
                    f"HTTP response from {method_name}: {response}"
                )
                return response
        raise AttributeError(
            f"'HTTP' object has no attribute any of {method_names}"
        )

    def test_connection(self) -> bool:
        """Test API connection."""
        try:
            response = self.http.get_wallet_balance(accountType="UNIFIED")
            return response.get('retCode', -1) == 0
        except Exception as e:
            msg = str(e).replace('\u2192', '->').encode('ascii', 'replace').decode('ascii')
            self.logger.error(f"Connection test failed: {msg}")
            return False

    # ========== Market Data ==========

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get current ticker data.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data dict
        """
        try:
            response = self.http.get_tickers(
                category="linear",
                symbol=symbol
            )

            if response.get('retCode') == 0:
                result = response.get('result', {})
                items = result.get('list') or response.get('list') or []
                if items:
                    return items[0]

            return None

        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {e}")
            return None

    def get_klines(self, symbol: str, interval: str,
                   limit: int = 200, start_time: int = None) -> Optional[List[Dict]]:
        """
        Get candlestick/kline data.

        Args:
            symbol: Trading symbol
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, etc.)
            limit: Number of candles
            start_time: Start timestamp (ms)

        Returns:
            List of candle dicts
        """
        try:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'interval': interval,
                'limit': min(limit, 1000)
            }

            if start_time:
                params['startTime'] = start_time

            response = self.http.get_kline(**params)

            if response.get('retCode') == 0:
                result = response.get('result', {})
                candles = result.get('list') or response.get('list') or []

                # Reverse to chronological order
                candles = candles[::-1]

                # Format candles
                formatted = []
                for c in candles:
                    formatted.append({
                        'timestamp': datetime.fromtimestamp(int(c[0]) / 1000),
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4]),
                        'volume': float(c[5]),
                        'turnover': float(c[6]) if len(c) > 6 else 0
                    })

                return formatted

            return None

        except Exception as e:
            self.logger.error(f"Error getting klines for {symbol}: {e}")
            return None

    def get_orderbook(self, symbol: str, limit: int = 50) -> Optional[Dict]:
        """
        Get orderbook data.

        Args:
            symbol: Trading symbol
            limit: Order book depth

        Returns:
            Order book dict
        """
        try:
            response = self.http.get_orderbook(
                category='linear',
                symbol=symbol,
                limit=limit
            )

            if response.get('retCode') == 0:
                data = response.get('result', response)

                def _ob_price(level, idx):
                    try: return float(level[idx]) if len(level) > idx else 0
                    except: return 0
                def _ob_vol(level):
                    try: return float(level[1]) if len(level) > 1 else 0
                    except: return 0
                bids = data.get('b', [])
                asks = data.get('a', [])
                return {
                    'bid1': _ob_price(bids[0], 0) if bids else 0,
                    'bid2': _ob_price(bids[1], 0) if len(bids) > 1 else 0,
                    'bid3': _ob_price(bids[2], 0) if len(bids) > 2 else 0,
                    'bid4': _ob_price(bids[3], 0) if len(bids) > 3 else 0,
                    'bid5': _ob_price(bids[4], 0) if len(bids) > 4 else 0,
                    'ask1': _ob_price(asks[0], 0) if asks else 0,
                    'ask2': _ob_price(asks[1], 0) if len(asks) > 1 else 0,
                    'ask3': _ob_price(asks[2], 0) if len(asks) > 2 else 0,
                    'ask4': _ob_price(asks[3], 0) if len(asks) > 3 else 0,
                    'ask5': _ob_price(asks[4], 0) if len(asks) > 4 else 0,
                    'bid_volume1': _ob_vol(bids[0]) if bids else 0,
                    'ask_volume1': _ob_vol(asks[0]) if asks else 0,
                }

            return None

        except Exception as e:
            self.logger.error(f"Error getting orderbook for {symbol}: {e}")
            return None

    # ========== Trading Operations ==========

    def place_order(self, symbol: str, side: str, order_type: str,
                   qty: float, price: float = None,
                   reduce_only: bool = False) -> Optional[Dict]:
        """
        Place an order.

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            order_type: 'Market' or 'Limit'
            qty: Order quantity
            price: Limit price (optional)
            reduce_only: Only reduce position

        Returns:
            Order result dict
        """
        try:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': side,
                'orderType': order_type,
                'qty': str(qty),
                'reduceOnly': reduce_only
            }

            if price:
                params['price'] = str(price)

            response = self.http.place_order(**params)

            if response.get('retCode') == 0:
                return {
                    'order_id': response.get('orderId'),
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'price': price,
                    'status': 'open'
                }

            self.logger.error(f"Order failed: {response}")
            return None

        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None

    def place_conditional_order(self, symbol: str, side: str,
                              trigger_price: float, qty: float,
                              order_type: str = 'Market',
                              reduce_only: bool = True) -> Optional[Dict]:
        """
        Place a conditional order (SL/TP).

        Args:
            symbol: Trading symbol
            side: 'Buy' or 'Sell'
            trigger_price: Trigger price
            qty: Order quantity
            order_type: Order type
            reduce_only: Only reduce position

        Returns:
            Order result dict
        """
        try:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': side,
                'triggerPrice': str(trigger_price),
                'qty': str(qty),
                'triggerBy': 'LastPrice',
                'orderType': order_type,
                'reduceOnly': reduce_only
            }

            # Set trigger direction based on side
            if side == 'Buy':
                params['triggerDirection'] = 1  # Trigger when price rises to trigger price
            else:
                params['triggerDirection'] = 2  # Trigger when price drops to trigger price

            response = self.http.place_order(**params)

            if response.get('retCode') == 0:
                return {
                    'order_id': response.get('orderId'),
                    'symbol': symbol,
                    'side': side,
                    'trigger_price': trigger_price,
                    'qty': qty,
                    'type': 'conditional'
                }

            self.logger.error(f"Conditional order failed: {response}")
            return None

        except Exception as e:
            self.logger.error(f"Error placing conditional order: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details."""
        try:
            response = self.http.get_order(category='linear', orderId=order_id)

            if response.get('retCode') == 0:
                return response.get('list', [{}])[0]

            return None

        except Exception as e:
            self.logger.error(f"Error getting order {order_id}: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            response = self.http.cancel_order(
                category='linear',
                orderId=order_id
            )

            return response.get('retCode') == 0

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get open orders."""
        try:
            base_params = {'category': 'linear'}

            # If a symbol is provided, prefer symbol-specific query
            if symbol:
                base_params['symbol'] = symbol

            # Try multiple possible method names for different pybit versions
            method_names = ['get_open_orders', 'get_orders', 'get_active_orders', 'get_realtime_orders', 'get_realtime_order']

            response = None

            # If no symbol, some endpoints require a settlement parameter (settleCoin)
            settle_keys = ['settleCoin', 'settle_coin', 'settlementCoin', 'settlement_coin']

            # Try with symbol first (if provided)
            try:
                self.logger.debug(f"Attempting get_open_orders with params: {base_params}")
                response = self._http_request(method_names, **base_params)
            except Exception as e:
                self.logger.debug(f"Initial get_open_orders attempt failed: {e}")
                response = None

            # If response indicates missing params or was None, try adding settlement keys
            if response is None or (isinstance(response, dict) and response.get('retCode') == 10001):
                for key in settle_keys:
                    params = base_params.copy()
                    params[key] = 'USDT'
                    try:
                        self.logger.debug(f"Attempting get_open_orders with param {key}=USDT")
                        response = self._http_request(method_names, **params)
                    except Exception as e:
                        self.logger.debug(f"get_open_orders with {key} raised: {e}")
                        response = None

                    if response and not (isinstance(response, dict) and response.get('retCode') == 10001):
                        break

            if not response:
                return []

            # Normalize response shapes (v5 sometimes nests result.list)
            try:
                if response.get('retCode') == 0:
                    # try common locations for orders list
                    orders = []
                    if isinstance(response.get('result'), dict):
                        orders = response['result'].get('list') or response['result'].get('orders') or []
                    orders = orders or response.get('list') or response.get('data') or []

                    return orders

                self.logger.error(f"get_open_orders returned error: {response}")
                return []
            except Exception as e:
                self.logger.error(f"Error parsing get_open_orders response: {e} -- raw: {response}")
                return []

        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return []

    # ========== Position Management ==========

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position dict or None
        """
        try:
            params = {'category': 'linear', 'symbol': symbol}

            # Prefer a symbol-specific request; try a direct call first
            response = self._http_request(['get_positions', 'get_position'], **params)
            self.logger.debug(
                f"get_position response for {symbol}: {response}"
            )

            if response.get('retCode') == 0:
                positions = response.get('list', [])

                for pos in positions:
                    if pos.get('symbol') == symbol and float(pos.get('size', 0)) > 0:
                        return {
                            'symbol': pos['symbol'],
                            'size': float(pos['size']),
                            'side': pos['side'],
                            'entry_price': float(pos.get('entryPrice', 0)),
                            'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                            'leverage': float(pos.get('leverage', 0)),
                            'liq_price': float(pos.get('liqPrice', 0)),
                            'margin': float(pos.get('positionMargin', 0)),
                            'isolated_margin': float(pos.get('isolatedMargin', 0))
                        }

            if response.get('retCode') != 0:
                self.logger.error(
                    f"get_position failed for {symbol}: {response}"
                )

            # If not found or empty, return None
            return None

        except Exception as e:
            msg = str(e).replace('\u2192', '->').encode('ascii', 'replace').decode('ascii')
            self.logger.error(f"Error getting position for {symbol}: {msg}")
            return None

    def get_positions(self) -> List[Dict]:
        """Get all positions."""
        try:
            base_params = {'category': 'linear'}

            # Try multiple spellings/keys for the settlement parameter to be robust
            settle_keys = ['settleCoin', 'settle_coin', 'settlementCoin', 'settlement_coin', 'settleCurrency', 'settle_currency']

            response = None
            for key in settle_keys:
                params = base_params.copy()
                params[key] = 'USDT'
                try:
                    self.logger.debug(f"Attempting get_positions with param {key}=USDT")
                    response = self._http_request(['get_positions', 'get_position'], **params)
                except Exception as e:
                    self.logger.debug(f"get_positions attempt with {key} raised: {e}")
                    response = None

                if response:
                    # If API indicates missing params, try next key
                    if response.get('retCode') == 10001:
                        self.logger.debug(f"API returned ErrCode 10001 with key {key}, trying next key")
                        response = None
                        continue

                    break

            # Final attempt without settlement param (legacy behavior)
            if response is None:
                try:
                    self.logger.debug("Attempting get_positions without settlement param")
                    response = self._http_request(['get_positions', 'get_position'], **base_params)
                except Exception as e:
                    self.logger.error(f"Final get_positions attempt failed: {e}")
                    # As a robust fallback, try per-symbol queries using configured symbols
                    try:
                        project_root = Path(__file__).resolve().parents[1]
                        cfg_file = project_root / 'config' / 'settings.json'
                        if cfg_file.exists():
                            with open(cfg_file, 'r', encoding='utf-8') as f:
                                cfg = json.load(f)
                                symbols = cfg.get('trading', {}).get('scan_symbols', [])
                                positions = []
                                for sym in symbols:
                                    pos = self.get_position(sym)
                                    if pos:
                                        positions.append(pos)
                                return positions
                    except Exception as e2:
                        self.logger.debug(f"Fallback per-symbol positions failed: {e2}")

                    return []

            if response.get('retCode') == 0:
                positions = []

                for pos in response.get('list', []):
                    if float(pos.get('size', 0)) > 0:
                        positions.append({
                            'symbol': pos.get('symbol'),
                            'size': float(pos.get('size', 0)),
                            'side': pos.get('side'),
                            'entry_price': float(pos.get('entryPrice', 0)),
                            'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                            'leverage': float(pos.get('leverage', 0)),
                            'liq_price': float(pos.get('liqPrice', 0))
                        })

                return positions

            self.logger.error(f"get_positions response: {response}")

            # If API specifically asks for symbol or settleCoin, fall back to per-symbol queries
            if response.get('retCode') == 10001:
                self.logger.debug("Bulk positions returned ErrCode 10001; falling back to per-symbol queries")
                try:
                    project_root = Path(__file__).resolve().parents[1]
                    cfg_file = project_root / 'config' / 'settings.json'
                    if cfg_file.exists():
                        with open(cfg_file, 'r', encoding='utf-8') as f:
                            cfg = json.load(f)
                            symbols = cfg.get('trading', {}).get('scan_symbols', [])
                            positions = []
                            for sym in symbols:
                                pos = self.get_position(sym)
                                if pos:
                                    positions.append(pos)
                            return positions
                except Exception as e2:
                    self.logger.debug(f"Fallback per-symbol positions failed: {e2}")

            # Non-zero return code -> log and return empty
            return []

        except Exception as e:
            msg = str(e).replace('\u2192', '->').encode('ascii', 'replace').decode('ascii')
            self.logger.error(f"Error getting positions: {msg}")
            return []

    # ========== Account Operations ==========

    def get_wallet_balance(self) -> Optional[Dict]:
        """Get wallet/balance information."""
        try:
            response = self.http.get_wallet_balance(accountType='UNIFIED')

            if response.get('retCode') != 0:
                return None

            # Support Bybit v5 shape: response.result.list[0]
            wallet_list = response.get('result', {}).get('list') or response.get('list')
            if not wallet_list:
                return None

            wallet_item = wallet_list[0]
            coin_entries = wallet_item.get('coin', [])

            def parse_number(value, default=0.0):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default

            if coin_entries:
                for coin in coin_entries:
                    if coin.get('coin') == 'USDT':
                        return {
                            'equity': parse_number(coin.get('equity', 0)),
                            'availableToBorrow': parse_number(coin.get('availableToWithdraw', 0)),
                            'totalOrderIm': parse_number(coin.get('totalOrderIM', 0)),
                            'totalPositionIM': parse_number(coin.get('totalPositionIM', 0)),
                        }

            # Fallback when USDT coin data is not returned in the coin list,
            # but total equity/balance fields are available at the account level.

            total_equity = wallet_item.get('totalEquity')
            if total_equity is None:
                total_equity = wallet_item.get('totalMarginBalance')

            if total_equity is not None:
                available = wallet_item.get('totalAvailableBalance')
                if available is None:
                    available = wallet_item.get('totalWalletBalance')
                return {
                    'equity': parse_number(total_equity),
                    'availableToBorrow': parse_number(available),
                    'totalOrderIm': parse_number(wallet_item.get('totalOrderIM', 0)),
                    'totalPositionIM': parse_number(wallet_item.get('totalPositionIM', 0)),
                }

            return None

        except Exception as e:
            msg = str(e).replace('\u2192', '->').encode('ascii', 'replace').decode('ascii')
            self.logger.error(f"Error getting wallet balance: {msg}")
            return None

    def set_leverage(self, symbol: str, buy_leverage: int,
                    sell_leverage: int = None,
                    margin_mode: str = 'isolated') -> bool:
        """
        Set leverage for a symbol.

        Args:
            symbol: Trading symbol
            buy_leverage: Buy side leverage
            sell_leverage: Sell side leverage
            margin_mode: 'isolated' or 'cross'

        Returns:
            Success boolean
        """
        try:
            if sell_leverage is None:
                sell_leverage = buy_leverage

            response = self.http.set_leverage(
                category='linear',
                symbol=symbol,
                buyLeverage=str(buy_leverage),
                sellLeverage=str(sell_leverage)
            )

            return response.get('retCode') == 0

        except Exception as e:
            self.logger.error(f"Error setting leverage: {e}")
            return False

    def switch_margin_mode(self, symbol: str, margin_mode: str = 'isolated') -> bool:
        """Switch margin mode."""
        try:
            response = self.http.switch_margin_mode(
                category='linear',
                symbol=symbol,
                tradeMode=1 if margin_mode == 'isolated' else 0
            )

            return response.get('retCode') == 0

        except Exception as e:
            self.logger.error(f"Error switching margin mode: {e}")
            return False

    # ========== Symbol Information ==========

    def get_symbol_specs(self, symbol: str) -> Optional[Dict]:
        """Get symbol specifications."""
        try:
            response = self.http.get_instruments_info(category='linear', symbol=symbol)

            if response.get('retCode') == 0:
                info = response.get('list', [{}])[0]

                lot_size_filter = info.get('lotSizeFilter', {})

                return {
                    'symbol': symbol,
                    'price_precision': info.get('pricePrecision', 2),
                    'qty_precision': info.get('quantityPrecision', 3),
                    'min_order_qty': float(lot_size_filter.get('minOrderQty', 0)),
                    'max_order_qty': float(lot_size_filter.get('maxOrderQty', 0)),
                    'step': float(lot_size_filter.get('step', 0.001)),
                    'tick_size': float(info.get('priceFilter', {}).get('tickSize', 0.01)),
                    'min_order_usd': float(lot_size_filter.get('minOrderAmt', 0)),
                    'max_leverage': float(info.get('maxLeverage', 10)),
                    'maintenance_margin_rate': float(info.get('mmp', 0.005))
                }

            return None

        except Exception as e:
            self.logger.error(f"Error getting symbol specs: {e}")
            return None

    def get_min_order_size(self, symbol: str) -> float:
        """Get minimum order size for symbol."""
        specs = self.get_symbol_specs(symbol)

        if specs:
            return specs.get('min_order_qty', 0.001)

        return 0.001

    # ========== WebSocket ==========

    def init_websocket(self):
        """Initialize WebSocket connection."""
        if self.ws is None:
            self.ws = WebSocket(
                testnet=self.testnet,
                channel_type="linear"
            )

    def subscribe(self, subscriptions: List[Dict], callback):
        """
        Subscribe to WebSocket topics.

        Args:
            subscriptions: List of subscription dicts
            callback: Callback function
        """
        if self.ws is None:
            self.init_websocket()

        for sub in subscriptions:
            self.ws.subscribe(**sub, callback=callback)
            self.ws_subscriptions.append(sub)

    def start_websocket(self):
        """Start WebSocket connection."""
        if self.ws:
            self.ws.start()

    def stop_websocket(self):
        """Stop WebSocket connection."""
        if self.ws:
            self.ws.stop()
            self.ws = None