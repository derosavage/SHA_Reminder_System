# Danvas1 - Architecture Documentation

## Overview

Danvas1 is a professional-grade, modular trading bot designed for autonomous 24/7 operation on the Bybit USDT Perpetual Futures market. The system emphasizes capital preservation, disciplined risk management, and explainable trading decisions.

## System Architecture

```
Danvas1/
├── bot.py                 # Main entry point
├── config/
│   └── settings.json      # Configuration file
├── core/
│   ├── engine.py          # Main orchestrator
│   ├── strategy_manager.py # Strategy management
│   ├── risk_manager.py    # Risk management
│   ├── trade_manager.py   # Trade execution
│   ├── execution_engine.py # Order execution
│   ├── position_manager.py # Position tracking
│   └── leverage_manager.py # Leverage management
├── strategies/
│   ├── strategy_v1.py     # Main strategy
│   └── filters.py         # Signal filters
├── analysis/
│   ├── market_regime.py   # Market regime detection
│   ├── volatility.py      # Volatility analysis
│   ├── trend_detection.py # Trend analysis
│   ├── momentum.py        # Momentum analysis
│   └── structure.py       # Structure analysis
├── indicators/
│   ├── ema.py             # EMA calculator
│   ├── atr.py             # ATR calculator
│   ├── rsi.py             # RSI calculator
│   ├── volume.py          # Volume analyzer
│   └── custom_indicators.py # Custom indicators
├── exchange/
│   ├── bybit_client.py    # Bybit API client
│   ├── symbol_specs.py    # Symbol specifications
│   ├── order_execution.py # Order execution
│   ├── account_manager.py # Account management
│   └── websocket_manager.py # WebSocket handling
├── data/
│   └── data_manager.py    # Data management
├── logs/
│   └── logger.py          # Logging setup
└── scripts/
    ├── run.ps1            # Run script
    ├── healthcheck.ps1     # Health monitoring
    ├── restart.ps1        # Restart script
    ├── stop.ps1           # Stop script
    └── supervisor_launch.ps1 # Auto-restart supervisor
```

## Core Components

### 1. Trading Engine (`engine.py`)

The central orchestrator that manages all components and coordinates the trading workflow.

**Responsibilities:**
- Initialize all subsystems
- Coordinate trading loop
- Manage symbol scanning
- Handle errors and recovery
- Maintain health monitoring

**Key Methods:**
- `start()` - Start the engine
- `stop()` - Stop the engine gracefully
- `pause()` / `resume()` - Control trading
- `_main_trading_loop()` - Main trading cycle
- `_scan_symbol()` - Analyze and trade symbols

### 2. Strategy Manager (`strategy_manager.py`)

Manages trading strategies and generates signals based on multi-timeframe analysis.

**Responsibilities:**
- Multi-timeframe analysis
- Signal generation with confluence
- Entry/exit condition evaluation

**Key Methods:**
- `analyze_htf()` - Higher timeframe analysis
- `check_signals()` - Signal detection
- `_calculate_confluence()` - Confluence scoring

### 3. Risk Manager (`risk_manager.py`)

Handles all risk-related operations with capital preservation as the highest priority.

**Responsibilities:**
- Position sizing based on risk
- Daily drawdown tracking
- Trade cooldown management
- Risk validation

**Key Methods:**
- `calculate_position_size()` - Risk-based sizing
- `validate_signal()` - Risk validation
- `get_equity()` - Account equity check
- `check_liquidation_risk()` - Liquidation analysis

### 4. Trade Manager (`trade_manager.py`)

Manages trade execution and position management.

**Responsibilities:**
- Open and close positions
- Set and adjust SL/TP
- Handle partial exits
- Track trade state

**Key Methods:**
- `open_position()` - Open new trade
- `close_position()` - Close existing trade
- `check_partial_tp()` - Partial take profit
- `check_breakeven()` - Breakeven management

## Trading Strategy

### Entry Conditions

LONG:
1. HTF bullish trend
2. RSI in oversold zone (< 30)
3. Price at support/liquidity zone
4. Bullish confirmation candle
5. Momentum aligned

SHORT:
1. HTF bearish trend
2. RSI in overbought zone (> 70)
3. Price at resistance/liquidity zone
4. Bearish confirmation candle
5. Momentum aligned

### Minimum Confluence Score: 3

### Risk/Reward Ratio: Minimum 2:1

### Stop Loss: ATR-based (2.5x default)

### Take Profit: ATR-based (4.0x default)

## Data Flow

```
User Input → Engine → Strategy Manager → Signal Detection
                                            ↓
                                        Risk Manager
                                            ↓
                                        Trade Manager
                                            ↓
                                    Execution Engine
                                            ↓
                                    Bybit API Client
                                            ↓
                                    Bybit Exchange
```

## Error Handling

1. **API Failures**: Retry logic with exponential backoff
2. **Order Failures**: Validation and automatic retry
3. **Connection Issues**: Auto-reconnect mechanism
4. **Position Errors**: Emergency close logic

## Logging

All trades and events are logged to:
- `logs/bot.log` - General bot logs
- `logs/trades_live.csv` - Trade history
- `logs/errors.log` - Error logs

## Versioning

All improvements increment version number:
- Danvas1 → Danvas2 → Danvas3

Never overwrite stable versions.
Rollback capability always maintained.

## Safety Features

1. Retry logic with configurable attempts
2. Timestamp synchronization
3. Internet recovery
4. API failure handling
5. Auto-reconnect
6. Order verification
7. Duplicate prevention
8. Liquidation avoidance
9. Emergency close logic
10. Healthcheck system