"""
Danvas1 - Trading Engine
Version: 1.0.0

Main orchestrator for the trading bot. Manages all components and coordinates
the trading workflow.
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_manager import StrategyManager
from core.risk_manager import RiskManager
from core.trade_manager import TradeManager
from core.execution_engine import ExecutionEngine
from core.position_manager import PositionManager
from core.leverage_manager import LeverageManager
from exchange.bybit_client import BybitClient
from exchange.websocket_manager import WebSocketManager
from analysis.market_regime import MarketRegime
from analysis.volatility import VolatilityAnalyzer
from indicators.rsi import RSICalculator
from indicators.atr import ATRCalculator
from indicators.ema import EMACalculator


class TradingEngine:
    """
    Main trading engine that orchestrates all components.

    Responsibilities:
    - Initialize all subsystems
    - Coordinate trading workflow
    - Manage symbol scanning
    - Handle errors and recovery
    - Maintain health monitoring
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the trading engine.

        Args:
            config_path: Path to settings.json, defaults to config/settings.json
        """
        self.logger = self._setup_logging()
        self.config_path = config_path or str(project_root / "config" / "settings.json")
        self.config = self._load_config()

        # Initialize state
        self.is_running = False
        self.is_paused = False
        self.last_health_check = None
        self.daily_pnl = 0.0
        self.consecutive_losses = 0

        # Load environment variables
        load_dotenv()

        # Initialize components
        self._initialize_components()

        # Register signal handlers
        self._register_signal_handlers()

        self.logger.info("=" * 60)
        self.logger.info("DANVAS1 TRADING ENGINE INITIALIZED")
        self.logger.info(f"Version: {self.config.get('version', '1.0.0')}")
        self.logger.info(f"Symbols: {self.config['trading']['scan_symbols']}")
        self.logger.info(f"Risk per trade: {self.config['risk_management']['risk_percent'] * 100}%")
        self.logger.info("=" * 60)

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the engine."""
        log_dir = project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "bot.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        logger = logging.getLogger("Danvas1.Engine")
        return logger

    def _load_config(self) -> Dict:
        """Load configuration from settings.json."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def _initialize_components(self):
        """Initialize all trading components."""
        self.logger.info("Initializing trading components...")

        # Exchange client
        api_key = os.getenv("BYBIT_API_KEY", "")
        api_secret = os.getenv("BYBIT_API_SECRET", "")
        testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

        self.bybit = BybitClient(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet
        )

        # Core managers
        self.risk_manager = RiskManager(self.config, self.bybit)
        self.position_manager = PositionManager(self.config, self.bybit)
        self.leverage_manager = LeverageManager(self.config, self.bybit)
        self.execution_engine = ExecutionEngine(self.bybit, self.config)
        self.trade_manager = TradeManager(
            self.config, self.bybit, self.execution_engine, self.risk_manager
        )
        self.strategy_manager = StrategyManager(self.config, self.bybit)

        # Analysis tools
        self.market_regime = MarketRegime(self.config)
        self.volatility = VolatilityAnalyzer(self.config)

        # WebSocket for live data
        self.ws_manager = WebSocketManager(self.bybit)

        self.logger.info("All components initialized successfully")

    def _register_signal_handlers(self):
        """Register handlers for graceful shutdown."""
        import signal

        def signal_handler(signum, frame):
            self.logger.warning(f"Received signal {signum}, initiating shutdown...")
            self.stop()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def start(self):
        """Start the trading engine."""
        if self.is_running:
            self.logger.warning("Engine is already running")
            return

        self.logger.info("=" * 60)
        self.logger.info("STARTING DANVAS1 TRADING ENGINE")
        self.logger.info("=" * 60)

        self.is_running = True

        # Main trading loop
        try:
            self._main_trading_loop()
        except Exception as e:
            self.logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
        finally:
            self._cleanup()

    def stop(self):
        """Stop the trading engine gracefully."""
        self.logger.info("Stopping trading engine...")
        self.is_running = False

        # Close all positions
        self._close_all_positions()

        # Disconnect WebSocket
        self.ws_manager.disconnect()

        self.logger.info("Engine stopped successfully")

    def pause(self):
        """Pause trading without closing positions."""
        self.logger.info("Trading PAUSED - positions kept open")
        self.is_paused = True

    def resume(self):
        """Resume trading after pause."""
        self.logger.info("Trading RESUMED")
        self.is_paused = False

    def _main_trading_loop(self):
        """Main trading loop that scans symbols and executes trades."""
        scan_interval = self.config['safety'].get('watchdog_interval_seconds', 60)

        while self.is_running:
            try:
                # Health check
                self._health_check()

                if self.is_paused:
                    time.sleep(scan_interval)
                    continue

                # Reset daily PnL if new day
                self._check_daily_reset()

                # Scan symbols for opportunities
                for symbol in self.config['trading']['scan_symbols']:
                    if not self.is_running:
                        break

                    self._scan_symbol(symbol)
                    time.sleep(2)  # Rate limiting

                # Update positions
                self._update_positions()

                # Sleep until next scan
                time.sleep(scan_interval)

            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}", exc_info=True)
                time.sleep(30)

    def _scan_symbol(self, symbol: str):
        """
        Scan a symbol for trading opportunities.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
        """
        self.logger.debug(f"Scanning {symbol}...")

        try:
            # Check if we can trade this symbol
            if not self._can_trade_symbol(symbol):
                return

            # Get current market data
            market_data = self._get_market_data(symbol)
            if market_data is None:
                return

            # Analyze higher timeframes
            htf_analysis = self.strategy_manager.analyze_htf(symbol)

            # Check for trading signals
            signal = self.strategy_manager.check_signals(symbol, htf_analysis, market_data)

            if signal and signal['action'] in ['long', 'short']:
                self.logger.info(f"Signal detected for {symbol}: {signal}")

                # Validate signal with risk manager
                validation = self.risk_manager.validate_signal(symbol, signal, market_data)

                if validation['approved']:
                    self._execute_trade(symbol, signal, market_data)
                else:
                    self.logger.info(f"Signal rejected: {validation['reason']}")

        except Exception as e:
            self.logger.error(f"Error scanning {symbol}: {e}")

    def _get_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch current market data for a symbol."""
        try:
            # Get candles
            candles = self.bybit.get_klines(
                symbol=symbol,
                interval=self.config['strategy']['ltf_timeframe'],
                limit=100
            )

            if candles is None or len(candles) < 50:
                return None

            # Get order book
            orderbook = self.bybit.get_orderbook(symbol)

            # Get ticker
            ticker = self.bybit.get_ticker(symbol)

            if ticker is None:
                return None

            return {
                'candles': candles,
                'orderbook': orderbook,
                'ticker': ticker,
                'timestamp': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            return None

    def _can_trade_symbol(self, symbol: str) -> bool:
        """Check if we can open a new trade for this symbol."""
        # Check concurrent trade limit
        open_positions = self.position_manager.get_open_positions()

        if len(open_positions) >= self.config['trading']['max_concurrent_trades']:
            self.logger.debug(f"Max concurrent trades reached: {len(open_positions)}")
            return False

        # Check if already have position in this symbol
        if any(p['symbol'] == symbol for p in open_positions):
            return False

        # Check daily drawdown
        if self.daily_pnl < -self.config['risk_management']['max_daily_drawdown'] * self.risk_manager.get_equity():
            self.logger.warning("Daily drawdown limit reached")
            return False

        # Check consecutive losses
        if self.consecutive_losses >= self.config['risk_management']['max_consecutive_losses']:
            self.logger.warning("Max consecutive losses reached")
            return False

        # Check cooldown
        if not self.risk_manager.can_trade(symbol):
            return False

        return True

    def _execute_trade(self, symbol: str, signal: Dict, market_data: Dict):
        """
        Execute a trade based on the signal.

        Args:
            symbol: Trading symbol
            signal: Trading signal dict
            market_data: Current market data
        """
        try:
            direction = signal['action']  # 'long' or 'short'
            entry_price = market_data['ticker']['last_price']

            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=signal.get('stop_loss'),
                direction=direction
            )

            if position_size <= 0:
                self.logger.warning(f"Invalid position size for {symbol}")
                return

            # Set leverage
            self.leverage_manager.set_leverage(symbol, direction)

            # Execute order
            result = self.trade_manager.open_position(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                position_size=position_size,
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
                reason=signal.get('reason', 'signal')
            )

            if result['success']:
                self.logger.info(f"Position opened: {symbol} {direction} @ {entry_price}")

                # Log trade
                self._log_trade(symbol, direction, entry_price, position_size, signal)
            else:
                self.logger.error(f"Failed to open position: {result['message']}")

        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")

    def _update_positions(self):
        """Update and manage all open positions."""
        try:
            open_positions = self.position_manager.get_open_positions()

            for position in open_positions:
                symbol = position['symbol']

                # Get current price
                ticker = self.bybit.get_ticker(symbol)
                if ticker is None:
                    continue

                current_price = ticker['last_price']

                # Check for partial TP
                self.trade_manager.check_partial_tp(symbol, current_price, position)

                # Update SL to breakeven if profitable
                self.trade_manager.check_breakeven(symbol, current_price, position)

                # Check for early exit
                self.trade_manager.check_early_exit(symbol, current_price, position)

        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")

    def _log_trade(self, symbol: str, direction: str, entry: float,
                   size: float, signal: Dict):
        """Log trade to CSV file."""
        try:
            trade_log = project_root / "logs" / "trades_live.csv"

            row = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry,
                'position_size': size,
                'stop_loss': signal.get('stop_loss'),
                'take_profit': signal.get('take_profit'),
                'reason': signal.get('reason'),
                'confluence_score': signal.get('confluence_score'),
                'equity': self.risk_manager.get_equity()
            }

            df = pd.DataFrame([row])

            if trade_log.exists():
                df.to_csv(trade_log, mode='a', header=False, index=False)
            else:
                df.to_csv(trade_log, mode='w', header=True, index=False)

        except Exception as e:
            self.logger.error(f"Failed to log trade: {e}")

    def _health_check(self):
        """Perform health check on all systems."""
        health = {
            'timestamp': datetime.now(),
            'api_connection': False,
            'positions_open': 0,
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses
        }

        try:
            # Check API connection
            health['api_connection'] = self.bybit.test_connection()

            # Get open positions count
            positions = self.position_manager.get_open_positions()
            health['positions_open'] = len(positions)

            # Update daily PnL
            total_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
            self.daily_pnl = total_pnl

            self.last_health_check = health

            self.logger.debug(f"Health check: {health}")

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")

    def _check_daily_reset(self):
        """Reset daily metrics at start of new day."""
        current_date = datetime.now().date()

        if hasattr(self, 'last_reset_date'):
            if current_date > self.last_reset_date:
                self.logger.info("New day - resetting daily metrics")
                self.daily_pnl = 0.0
                self.consecutive_losses = 0
                self.risk_manager.reset_daily()

        self.last_reset_date = current_date

    def _close_all_positions(self):
        """Close all open positions on shutdown."""
        self.logger.info("Closing all positions...")

        try:
            positions = self.position_manager.get_open_positions()

            for position in positions:
                symbol = position['symbol']

                # Market close
                self.trade_manager.close_position(symbol, reason='emergency_shutdown')

            self.logger.info("All positions closed")

        except Exception as e:
            self.logger.error(f"Error closing positions: {e}")

    def _cleanup(self):
        """Clean up resources on shutdown."""
        self.logger.info("Cleaning up resources...")

        # Disconnect WebSocket
        self.ws_manager.disconnect()

        # Save state
        self._save_state()

        self.logger.info("Cleanup complete")

    def _save_state(self):
        """Save current state for recovery."""
        state = {
            'timestamp': datetime.now().isoformat(),
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'open_positions': self.position_manager.get_open_positions()
        }

        try:
            state_file = project_root / "logs" / "state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def get_status(self) -> Dict:
        """Get current status of the trading engine."""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'open_positions': len(self.position_manager.get_open_positions()),
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'last_health_check': self.last_health_check,
            'equity': self.risk_manager.get_equity()
        }


def main():
    """Main entry point for the trading bot."""
    import argparse

    parser = argparse.ArgumentParser(description='Danvas1 Trading Bot')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--backtest', '-b', action='store_true', help='Run in backtest mode')

    args = parser.parse_args()

    # Initialize engine
    engine = TradingEngine(config_path=args.config)

    if args.backtest:
        # Run backtesting
        from backtests.backtest_engine import BacktestEngine
        backtest = BacktestEngine(engine.config)
        backtest.run()
    else:
        # Start live trading
        engine.start()


if __name__ == "__main__":
    main()