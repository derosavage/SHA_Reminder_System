"""
Danvas1 - Position Manager
Version: 1.0.0

Manages position tracking and state management.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List


class PositionManager:
    """
    Manages position tracking and state.

    Responsibilities:
    - Track all open positions
    - Monitor position health
    - Calculate position metrics
    - Handle position updates
    """

    def __init__(self, config: Dict, bybit_client):
        """
        Initialize Position Manager.

        Args:
            config: Bot configuration
            bybit_client: Bybit API client
        """
        self.logger = logging.getLogger("Danvas1.PositionManager")
        self.config = config
        self.bybit = bybit_client

        # Position cache
        self.positions_cache = {}
        self.last_update = None

        self.logger.info("Position Manager initialized")

    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions.

        Returns:
            List of position dictionaries
        """
        try:
            all_positions = self.bybit.get_positions()

            if not all_positions:
                return []

            open_positions = [
                p for p in all_positions
                if p.get('size', 0) > 0
            ]

            # Update cache
            self.positions_cache = {p['symbol']: p for p in open_positions}
            self.last_update = datetime.now()

            return open_positions

        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return list(self.positions_cache.values())

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position dictionary or None
        """
        try:
            # Check cache first
            if symbol in self.positions_cache:
                return self.positions_cache[symbol]

            # Fetch from exchange
            position = self.bybit.get_position(symbol)

            if position:
                self.positions_cache[symbol] = position

            return position

        except Exception as e:
            self.logger.error(f"Error getting position for {symbol}: {e}")
            return self.positions_cache.get(symbol)

    def get_total_exposure(self) -> float:
        """Get total exposure across all positions."""
        try:
            positions = self.get_open_positions()

            total_exposure = 0.0
            for position in positions:
                size = position.get('size', 0)
                entry = position.get('entry_price', 0)
                total_exposure += size * entry

            return total_exposure

        except Exception as e:
            self.logger.error(f"Error calculating exposure: {e}")
            return 0.0

    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized PnL across all positions."""
        try:
            positions = self.get_open_positions()

            total_pnl = 0.0
            for position in positions:
                total_pnl += position.get('unrealized_pnl', 0)

            return total_pnl

        except Exception as e:
            self.logger.error(f"Error calculating unrealized PnL: {e}")
            return 0.0

    def get_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.get_open_positions())

    def is_position_open(self, symbol: str) -> bool:
        """Check if a position is open for a symbol."""
        position = self.get_position(symbol)
        return position is not None and position.get('size', 0) > 0

    def get_position_direction(self, symbol: str) -> Optional[str]:
        """Get direction of position ('long' or 'short')."""
        position = self.get_position(symbol)

        if position:
            side = position.get('side', '').lower()
            if side == 'buy':
                return 'long'
            elif side == 'sell':
                return 'short'

        return None

    def calculate_entry_price(self, symbol: str) -> Optional[float]:
        """Calculate average entry price for a symbol."""
        position = self.get_position(symbol)

        if position:
            return position.get('entry_price')

        return None

    def calculate_position_age(self, symbol: str) -> Optional[float]:
        """Calculate how long a position has been open (in hours)."""
        position = self.get_position(symbol)

        if position and 'open_time' in position:
            open_time = position['open_time']
            if isinstance(open_time, str):
                open_time = datetime.fromisoformat(open_time)

            age = (datetime.now() - open_time).total_seconds() / 3600
            return age

        return None

    def get_position_health(self, symbol: str) -> Dict:
        """
        Get health metrics for a position.

        Returns:
            Dictionary with health indicators
        """
        position = self.get_position(symbol)

        if not position or position.get('size', 0) == 0:
            return {'healthy': False, 'reason': 'No position'}

        health = {
            'healthy': True,
            'unrealized_pnl': position.get('unrealized_pnl', 0),
            'leverage': position.get('leverage', 1),
            'margin': position.get('isolated_margin', 0),
            'liq_price': position.get('liq_price'),
            'risk_ratio': 0
        }

        # Calculate risk ratio
        entry = position.get('entry_price', 0)
        liq = position.get('liq_price', 0)

        if entry > 0 and liq > 0:
            direction = self.get_position_direction(symbol)

            if direction == 'long':
                health['risk_ratio'] = abs(entry - liq) / entry
            else:
                health['risk_ratio'] = abs(liq - entry) / entry

            # Flag if risk is high
            if health['risk_ratio'] < 0.02:  # Less than 2% to liquidation
                health['healthy'] = False
                health['reason'] = 'High liquidation risk'

        return health

    def sync_positions(self):
        """Synchronize position cache with exchange."""
        try:
            positions = self.bybit.get_positions()

            self.positions_cache = {
                p['symbol']: p for p in positions
                if p.get('size', 0) > 0
            }

            self.last_update = datetime.now()

            self.logger.debug(
                f"Synced {len(self.positions_cache)} positions"
            )

        except Exception as e:
            self.logger.error(f"Error syncing positions: {e}")

    def clear_cache(self):
        """Clear position cache."""
        self.positions_cache = {}
        self.last_update = None

    def get_positions_summary(self) -> Dict:
        """Get summary of all positions."""
        positions = self.get_open_positions()

        if not positions:
            return {
                'count': 0,
                'total_exposure': 0,
                'total_pnl': 0,
                'long_count': 0,
                'short_count': 0
            }

        return {
            'count': len(positions),
            'total_exposure': self.get_total_exposure(),
            'total_pnl': self.get_total_unrealized_pnl(),
            'long_count': sum(1 for p in positions if p.get('side') == 'Buy'),
            'short_count': sum(1 for p in positions if p.get('side') == 'Sell'),
            'positions': [
                {
                    'symbol': p['symbol'],
                    'direction': 'long' if p.get('side') == 'Buy' else 'short',
                    'size': p.get('size', 0),
                    'entry': p.get('entry_price'),
                    'pnl': p.get('unrealized_pnl', 0)
                }
                for p in positions
            ]
        }