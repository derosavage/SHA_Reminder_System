#!/usr/bin/env python3
"""
Danvas1 - Main Trading Bot Entry Point
Version: 1.0.0

Professional-grade USDT Perpetual trading bot for Bybit.
Capital preservation is the highest priority.
"""

import sys
import os
import argparse
import logging
import signal
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import core components
from core.engine import TradingEngine
from logs.logger import setup_logging


class BotApplication:
    """
    Main application class for Danvas1 trading bot.

    Responsibilities:
    - Initialize application
    - Handle CLI arguments
    - Manage bot lifecycle
    - Coordinate shutdown
    """

    def __init__(self, config_path: str = None, debug: bool = False):
        """
        Initialize the application.

        Args:
            config_path: Path to configuration file
            debug: Enable debug mode
        """
        self.config_path = config_path
        self.debug = debug
        self.engine = None
        self.logger = None

        # Setup
        self._setup_logging()
        self._register_signal_handlers()

    def _setup_logging(self):
        """Initialize logging system."""
        log_level = "DEBUG" if self.debug else "INFO"
        self.logger = setup_logging("Danvas1", log_level)["Engine"]

        self.logger.info("=" * 60)
        self.logger.info("DANVAS1 TRADING BOT - INITIALIZING")
        self.logger.info(f"Version: 1.0.0")
        self.logger.info(f"Python: {sys.version}")
        self.logger.info(f"Debug Mode: {self.debug}")
        self.logger.info("=" * 60)

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.warning(f"Received {signal_name}, initiating graceful shutdown...")
            self.shutdown()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def initialize(self) -> bool:
        """
        Initialize the trading engine.

        Returns:
            Success boolean
        """
        try:
            self.logger.info("Initializing trading engine...")

            # Initialize engine
            self.engine = TradingEngine(config_path=self.config_path)

            self.logger.info("Trading engine initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}", exc_info=True)
            return False

    def run(self, backtest: bool = False):
        """
        Run the trading bot.

        Args:
            backtest: Run in backtest mode
        """
        try:
            if backtest:
                self.logger.info("Starting backtest mode...")
                self._run_backtest()
            else:
                self.logger.info("Starting live trading mode...")
                self._run_live()

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Error during execution: {e}", exc_info=True)
        finally:
            self.shutdown()

    def _run_live(self):
        """Run in live trading mode."""
        self.logger.info("=" * 60)
        self.logger.info("LIVE TRADING MODE")
        self.logger.info("=" * 60)

        # Start the engine
        self.engine.start()

    def _run_backtest(self):
        """Run in backtest mode."""
        self.logger.info("=" * 60)
        self.logger.info("BACKTEST MODE")
        self.logger.info("=" * 60)

        try:
            # Import backtest module
            from backtests.backtest_engine import BacktestEngine

            # Create and run backtest
            backtest_engine = BacktestEngine(self.engine.config)
            results = backtest_engine.run()

            # Display results
            self._display_backtest_results(results)

        except ImportError as e:
            self.logger.error(f"Backtest module not available: {e}")
        except Exception as e:
            self.logger.error(f"Backtest error: {e}", exc_info=True)

    def _display_backtest_results(self, results: dict):
        """Display backtest results."""
        self.logger.info("=" * 60)
        self.logger.info("BACKTEST RESULTS")
        self.logger.info("=" * 60)

        if results:
            self.logger.info(f"Total Trades: {results.get('total_trades', 0)}")
            self.logger.info(f"Win Rate: {results.get('win_rate', 0):.2%}")
            self.logger.info(f"Profit Factor: {results.get('profit_factor', 0):.2f}")
            self.logger.info(f"Final Equity: ${results.get('final_equity', 0):.2f}")
            self.logger.info(f"Max Drawdown: {results.get('max_drawdown', 0):.2%}")
            self.logger.info(f"Total PnL: ${results.get('total_pnl', 0):.2f}")
        else:
            self.logger.warning("No backtest results available")

    def status(self) -> dict:
        """
        Get bot status.

        Returns:
            Status dictionary
        """
        if self.engine:
            return self.engine.get_status()
        return {
            'running': False,
            'initialized': False
        }

    def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Initiating shutdown...")

        if self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                self.logger.error(f"Error stopping engine: {e}")

        self.logger.info("Shutdown complete")
        sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Danvas1 - Professional USDT Perpetual Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bot.py                          # Start live trading
  python bot.py --backtest               # Run backtest
  python bot.py --status                 # Check bot status
  python bot.py --debug                  # Enable debug mode
  python bot.py -c custom_config.json    # Use custom config

For more information, see README.md
        """
    )

    parser.add_argument(
        '-c', '--config',
        help='Path to configuration file',
        default=None
    )

    parser.add_argument(
        '-b', '--backtest',
        action='store_true',
        help='Run in backtest mode'
    )

    parser.add_argument(
        '-s', '--status',
        action='store_true',
        help='Check bot status and exit'
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version='Danvas1 v1.0.0',
        help='Show version and exit'
    )

    args = parser.parse_args()

    # Handle status check
    if args.status:
        app = BotApplication(debug=args.debug)
        if app.initialize():
            status = app.status()
            print(f"Bot Status: {'Running' if status.get('running') else 'Not Running'}")
            print(f"Open Positions: {status.get('open_positions', 0)}")
            print(f"Equity: ${status.get('equity', 0):.2f}")
            print(f"Daily PnL: ${status.get('daily_pnl', 0):.2f}")
        else:
            print("Failed to initialize bot")
            sys.exit(1)

        sys.exit(0)

    # Create and run application
    app = BotApplication(config_path=args.config, debug=args.debug)

    if not app.initialize():
        print("ERROR: Failed to initialize trading bot")
        print("Check logs for details")
        sys.exit(1)

    app.run(backtest=args.backtest)


if __name__ == "__main__":
    main()