# Danvas1 - Professional USDT Perpetual Trading Bot

**Version**: 1.0.0
**Market**: Bybit USDT Perpetual Futures
**Trading**: Long/Short with multi-timeframe analysis

---

## Quick Start

### 1. Setup Environment

```powershell
cd C:\TradingBots\Danvas1
.\setup_env.ps1
```

### 2. Configure API Keys

Edit `.env` file:
```
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=false
```

### 3. Run the Bot

```powershell
# Live trading
.\scripts\run.ps1

# Or with health monitoring
.\scripts\healthcheck.ps1

# With auto-restart
.\scripts\supervisor_launch.ps1
```

---

## Features

### Core Capabilities
- Multi-timeframe analysis (1H, 4H, 12H, D)
- RSI-based signal generation
- ATR-based stop loss and take profit
- Dynamic position sizing
- Partial TP exits
- Breakeven management

### Risk Management
- 20% risk per trade (configurable)
- Daily drawdown limits
- Consecutive loss limits
- Trade cooldown periods
- Minimum R/R ratio enforcement
- Liquidation avoidance

### Safety Features
- Retry logic for API calls
- Auto-reconnect on disconnect
- Order verification
- Duplicate prevention
- Emergency close logic
- Health monitoring

---

## Configuration

Edit `config/settings.json` to customize:

```json
{
    "trading": {
        "default_symbol": "BTCUSDT",
        "scan_symbols": ["BTCUSDT", "ETHUSDT"],
        "max_concurrent_trades": 3,
        "default_leverage": 5
    },
    "risk_management": {
        "risk_percent": 0.20,
        "max_daily_drawdown": 0.05,
        "max_consecutive_losses": 3
    },
    "strategy": {
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "atr_multiplier_sl": 2.5,
        "atr_multiplier_tp": 4.0
    }
}
```

---

## Strategy Overview

### Entry Conditions (LONG)
1. HTF bullish trend (price > EMA50 > EMA200)
2. RSI oversold (< 30)
3. Support/liquidity zone nearby
4. Bullish confirmation candle
5. Momentum aligned

### Entry Conditions (SHORT)
1. HTF bearish trend (price < EMA50 < EMA200)
2. RSI overbought (> 70)
3. Resistance/liquidity zone nearby
4. Bearish confirmation candle
5. Momentum aligned

### Minimum Requirements
- Confluence Score: 3+
- Risk/Reward Ratio: 2:1 minimum
- ATR-based SL and TP

---

## Directory Structure

```
Danvas1/
├── bot.py              # Main entry point
├── .env                # API credentials
├── requirements.txt    # Python dependencies
├── config/
│   └── settings.json   # Configuration
├── core/               # Core modules
├── strategies/         # Trading strategies
├── analysis/           # Market analysis
├── indicators/         # Technical indicators
├── exchange/           # Exchange integration
├── data/               # Data storage
├── logs/               # Log files
├── scripts/            # PowerShell scripts
├── tests/              # Unit tests
└── docs/               # Documentation
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `run.ps1` | Start the bot |
| `healthcheck.ps1` | Monitor health |
| `restart.ps1` | Restart safely |
| `stop.ps1` | Stop gracefully |
| `supervisor_launch.ps1` | Auto-restart on failure |

---

## Monitoring

### View Logs
```powershell
Get-Content logs\bot.log -Tail 50
```

### Check Status
```powershell
.\scripts\healthcheck.ps1
```

### View Trades
```powershell
Import-Csv logs\trades_live.csv
```

---

## Versioning

- **Danvas1**: Initial release (current)
- Future improvements → Danvas2, Danvas3, etc.

Never overwrite stable versions. Rollback capability always maintained.

---

## Risk Warning

**IMPORTANT**: Trading futures involves substantial risk of loss. This bot is designed to assist in systematic trading but does not guarantee profits. Always:
- Use proper position sizing
- Monitor the bot regularly
- Understand the risks involved
- Never trade more than you can afford to lose

---

## Support

For issues and questions:
1. Check `docs/troubleshooting.md`
2. Review `docs/architecture.md`
3. Check logs in `logs/` directory
4. Verify configuration in `config/settings.json`

---

**Capital preservation is the highest priority.**