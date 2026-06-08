"""
Danvas1 - Account Manager
Version: 1.0.0

Manages account operations and balance tracking.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List


class AccountManager:
    """
    Account management.

    Responsibilities:
    - Track account balance and equity
    - Monitor margin usage
    - Calculate unrealized PnL
    - Manage trading limits
    """

    def __init__(self, bybit_client, config: Dict):
        """
        Initialize Account Manager.

        Args:
            bybit_client: Bybit API client
            config: Bot configuration
        """
        self.logger = logging.getLogger("Danvas1.AccountManager")
        self.bybit = bybit_client
        self.config = config

        # Account state
        self.equity = 0.0
        self.available_balance = 0.0
        self.total_unrealized_pnl = 0.0
        self.used_margin = 0.0

        self.last_update = None

        self.logger.info("Account Manager initialized")

    def update(self) -> bool:
        """
        Update account state from exchange.

        Returns:
            Success boolean
        """
        try:
            balance = self.bybit.get_wallet_balance()

            if balance:
                self.equity = balance.get('equity', 0.0)
                self.available_balance = balance.get('availableToBorrow', 0.0)
                self.used_margin = balance.get('totalPositionIM', 0.0)
                self.last_update = datetime.now()

                return True

            return False

        except Exception as e:
            self.logger.error(f"Error updating account: {e}")
            return False

    def get_equity(self) -> float:
        """Get current equity."""
        if self.last_update is None or (datetime.now() - self.last_update).seconds > 60:
            self.update()

        return self.equity

    def get_available_balance(self) -> float:
        """Get available balance for trading."""
        if self.last_update is None or (datetime.now() - self.last_update).seconds > 60:
            self.update()

        return self.available_balance

    def get_margin_usage(self) -> float:
        """Get margin usage percentage."""
        if self.equity > 0:
            return (self.used_margin / self.equity) * 100

        return 0.0

    def update_positions(self) -> List[Dict]:
        """
        Update and return current positions.

        Returns:
            List of position dicts
        """
        try:
            positions = self.bybit.get_positions()

            self.total_unrealized_pnl = sum(
                p.get('unrealized_pnl', 0) for p in positions
            )

            return positions

        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
            return []

    def get_total_exposure(self, positions: List[Dict] = None) -> float:
        """
        Calculate total exposure across positions.

        Args:
            positions: List of positions (optional, will fetch if not provided)

        Returns:
            Total exposure in USD
        """
        if positions is None:
            positions = self.bybit.get_positions()

        total_exposure = 0.0

        for pos in positions:
            size = pos.get('size', 0)
            entry = pos.get('entry_price', 0)
            total_exposure += size * entry

        return total_exposure

    def can_open_position(self, position_value: float,
                         additional_leverage: float = 1.0) -> Dict:
        """
        Check if a new position can be opened.

        Args:
            position_value: Value of planned position
            additional_leverage: Additional leverage factor

        Returns:
            Validation result
        """
        result = {
            'can_open': False,
            'reason': '',
            'max_position': 0
        }

        equity = self.get_equity()
        available = self.get_available_balance()

        if equity <= 0:
            result['reason'] = 'No equity available'
            return result

        # Calculate max position
        max_leverage = self.config['trading'].get('max_leverage', 10)
        max_margin_usage = self.config['risk_management'].get(
            'max_margin_usage_percent', 0.5
        )

        max_position = min(
            available * max_leverage * max_margin_usage,
            equity * max_leverage
        )

        result['max_position'] = max_position

        if position_value > max_position:
            result['reason'] = f'Position size exceeds max ({position_value:.2f} > {max_position:.2f})'
            return result

        # Check margin usage after position
        current_exposure = self.get_total_exposure()
        new_exposure = current_exposure + position_value

        if new_exposure > equity * max_leverage * max_margin_usage:
            result['reason'] = 'Margin usage would exceed limit'
            return result

        result['can_open'] = True
        return result

    def calculate_max_risk_amount(self) -> float:
        """Calculate maximum amount to risk per trade."""
        equity = self.get_equity()
        risk_percent = self.config['risk_management'].get('risk_percent', 0.02)

        return equity * risk_percent

    def get_account_summary(self) -> Dict:
        """
        Get comprehensive account summary.

        Returns:
            Account summary dict
        """
        self.update()

        positions = self.update_positions()

        return {
            'equity': self.equity,
            'available_balance': self.available_balance,
            'used_margin': self.used_margin,
            'margin_usage_pct': self.get_margin_usage(),
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'open_positions': len(positions),
            'total_exposure': self.get_total_exposure(positions),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

    def check_daily_loss_limit(self, daily_loss: float) -> Dict:
        """
        Check if daily loss limit is reached.

        Args:
            daily_loss: Current daily loss

        Returns:
            Validation result
        """
        result = {'passed': True, 'reason': ''}

        max_drawdown = self.config['risk_management'].get('max_daily_drawdown', 0.05)
        starting_balance = self.config.get('starting_balance', self.equity)

        if starting_balance > 0:
            max_loss = starting_balance * max_drawdown

            if daily_loss >= max_loss:
                result['passed'] = False
                result['reason'] = f'Daily loss limit reached ({daily_loss:.2f} >= {max_loss:.2f})'

        return result

    def get_position_leverage_utilization(self, positions: List[Dict] = None) -> Dict:
        """
        Calculate leverage utilization across positions.

        Args:
            positions: List of positions

        Returns:
            Leverage utilization stats
        """
        if positions is None:
            positions = self.bybit.get_positions()

        total_exposure = 0.0
        total_margin = 0.0

        for pos in positions:
            size = pos.get('size', 0)
            entry = pos.get('entry_price', 0)
            margin = pos.get('margin', 0)

            total_exposure += size * entry
            total_margin += margin

        avg_leverage = total_exposure / total_margin if total_margin > 0 else 0

        return {
            'total_exposure': total_exposure,
            'total_margin': total_margin,
            'average_leverage': avg_leverage,
            'position_count': len(positions)
        }

    def reset_starting_balance(self):
        """Reset starting balance for daily tracking."""
        self.config['starting_balance'] = self.get_equity()
        self.logger.info(f"Starting balance reset to {self.config['starting_balance']:.2f}")