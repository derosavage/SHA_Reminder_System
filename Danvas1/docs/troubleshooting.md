# Danvas1 - Troubleshooting Guide

## Common Issues and Solutions

### 1. Bot Won't Start

**Symptoms:**
- Error: "Python virtual environment not found"
- Error: "API credentials not configured"

**Solutions:**
1. Run setup_env.ps1 to create virtual environment
2. Copy .env.example to .env and fill in API credentials
3. Verify Python path in scripts

**PowerShell:**
```powershell
cd C:\TradingBots\Danvas1
.\setup_env.ps1
# Edit .env with your API keys
.\scripts\run.ps1
```

### 2. API Connection Failed

**Symptoms:**
- Error: "Connection test failed"
- Error: "Invalid API key"

**Solutions:**
1. Verify API key and secret in .env
2. Check if API key has trading permissions
3. Ensure testnet setting is correct (false for mainnet)
4. Check network connectivity

**Test API Connection:**
```powershell
C:\TradingBots\_shared_venv\Scripts\python.exe -c "
from pybit.unified_trading import HTTP
import os
client = HTTP(api_key=os.getenv('BYBIT_API_KEY'), api_secret=os.getenv('BYBIT_API_SECRET'))
print(client.get_wallet_balance(accountType='UNIFIED'))
"
```

### 3. Order Execution Failed

**Symptoms:**
- Error: "Insufficient margin"
- Error: "Order quantity below minimum"

**Solutions:**
1. Check account balance
2. Verify symbol specs in settings.json
3. Adjust position size
4. Reduce leverage

**Debug Order:**
```python
from exchange.bybit_client import BybitClient
client = BybitClient(api_key, api_secret)
specs = client.get_symbol_specs("BTCUSDT")
print(specs)
```

### 4. Positions Not Opening

**Symptoms:**
- Bot running but no trades
- Signal detected but not executed

**Solutions:**
1. Check daily drawdown limit
2. Check consecutive loss limit
3. Verify trade cooldown
4. Check margin availability

**Check Status:**
```powershell
python bot.py --status
```

### 5. Stop Loss Not Triggering

**Symptoms:**
- Position open without SL
- Error in logs about SL order

**Solutions:**
1. Check API permissions for conditional orders
2. Verify order type settings
3. Check network latency

**Manual SL Check:**
```python
# Check open orders
client.get_open_orders("BTCUSDT")
```

### 6. High Slippage on Execution

**Symptoms:**
- Entry price significantly different from signal
- Unexpected losses

**Solutions:**
1. Reduce position size
2. Use limit orders instead of market
3. Avoid high volatility periods
4. Check spread filter settings

### 7. Bot Crashing During Trading

**Symptoms:**
- Unexpected shutdown
- No graceful exit

**Solutions:**
1. Run healthcheck.ps1 to monitor
2. Check logs for errors
3. Verify error handling in code
4. Use supervisor_launch.ps1 for auto-restart

**View Recent Logs:**
```powershell
Get-Content logs\bot.log -Tail 50
```

### 8. WebSocket Connection Issues

**Symptoms:**
- Data lagging
- Connection drops
- Reconnection loops

**Solutions:**
1. Check internet stability
2. Increase heartbeat interval
3. Verify firewall settings
4. Enable auto-reconnect in settings.json

### 9. Performance Issues

**Symptoms:**
- Bot running slow
- Delayed signal detection

**Solutions:**
1. Reduce number of symbols to scan
2. Optimize cache settings
3. Increase scan interval
4. Check system resources

### 10. Risk Management Not Working

**Symptoms:**
- Position too large
- Drawdown exceeded

**Solutions:**
1. Verify risk_percent in settings.json
2. Check margin calculations
3. Review position sizing logic

## Diagnostic Commands

### Check Bot Status
```powershell
# View running processes
Get-Process python* | Where-Object {$_.CommandLine -like "*Danvas1*"}

# Check health
.\scripts\healthcheck.ps1
```

### View Logs
```powershell
# All logs
Get-Content logs\bot.log

# Errors only
Select-String -Path logs\bot.log -Pattern "ERROR"

# Trades only
Import-Csv logs\trades_live.csv
```

### Test Configuration
```powershell
# Validate JSON config
Get-Content config\settings.json | ConvertFrom-Json

# Test imports
python -c "from core.engine import TradingEngine; print('OK')"
```

## Emergency Procedures

### 1. Close All Positions Immediately

```powershell
.\scripts\stop.ps1 -Force
```

Or manually via Bybit interface.

### 2. Stop Bot and Reset

```powershell
.\scripts\stop.ps1
# Edit settings.json
.\scripts\restart.ps1
```

### 3. Restore to Previous Version

```powershell
# Backup current
Copy-Item Danvas1 Danvas1_backup

# Switch to previous version
Copy-Item DanvasStable Danvas1

# Clear cache
Remove-Item data\cache\* -Force
```

### 4. Check Account Status

1. Login to Bybit
2. Check open positions
3. Verify balance
4. Cancel all open orders

## Support Resources

- Logs: `logs/bot.log`
- Trade History: `logs/trades_live.csv`
- Error Log: `logs/errors.log`
- Configuration: `config/settings.json`

## Getting Help

When reporting issues, include:
1. Error message from logs
2. Bot version (check settings.json)
3. Configuration (mask API keys)
4. Steps to reproduce
5. System environment