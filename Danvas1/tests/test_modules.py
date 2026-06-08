"""Test all Danvas1 modules."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import logging
logging.basicConfig(level=logging.CRITICAL)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

api_key = os.getenv('BYBIT_API_KEY', '')
api_secret = os.getenv('BYBIT_API_SECRET', '')
testnet = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'

print(f"API Key: {api_key[:6]}...{api_key[-4:]}")
print(f"Testnet: {testnet}")
print()

from exchange.bybit_client import BybitClient
client = BybitClient(api_key=api_key, api_secret=api_secret, testnet=testnet)

# 1. Connection
print("--- 1. CONNECTION ---")
r = client.test_connection()
print(f"   {'PASS' if r else 'FAIL'}")
print()

# 2. Wallet
print("--- 2. WALLET BALANCE ---")
bal = client.get_wallet_balance()
if bal:
    print(f"   Equity: {bal.get('equity', '?')} USDT")
    print(f"   Available: {bal.get('availableToBorrow', '?')} USDT")
else:
    print("   FAIL")
print()

# 3. Ticker
print("--- 3. TICKER BTCUSDT ---")
t = client.get_ticker('BTCUSDT')
if t:
    print(f"   Last: {t.get('lastPrice', '?')}")
    print(f"   24h chg: {t.get('change24h', '?')}%")
    print(f"   24h vol: {t.get('volume24h', '?')}")
else:
    print("   FAIL")
print()

# 4. Klines
print("--- 4. KLINES BTCUSDT 1H ---")
k = client.get_klines('BTCUSDT', '1h', limit=3)
if k:
    print(f"   Got {len(k)} candles")
    for c in k:
        print(f"   {c['timestamp']}: O={c['open']} H={c['high']} L={c['low']} C={c['close']}")
else:
    print("   FAIL")
print()

# 5. Orderbook
print("--- 5. ORDERBOOK BTCUSDT ---")
ob = client.get_orderbook('BTCUSDT')
if ob:
    print(f"   Bid: {ob.get('bid1', '?')} x {ob.get('bid_volume1', '?')}")
    print(f"   Ask: {ob.get('ask1', '?')} x {ob.get('ask_volume1', '?')}")
else:
    print("   FAIL")
print()

# 6. Positions
print("--- 6. POSITIONS ---")
pos = client.get_positions()
print(f"   Open: {len(pos)}")
for p in pos:
    print(f"   {p['symbol']} {p['side']} size={p['size']} entry={p['entry_price']}")
print()

# 7. Symbol specs
print("--- 7. SYMBOL SPECS BTCUSDT ---")
s = client.get_symbol_specs('BTCUSDT')
if s:
    print(f"   Min qty: {s.get('min_order_qty', '?')}")
    print(f"   Tick size: {s.get('tick_size', '?')}")
    print(f"   Max leverage: {s.get('max_leverage', '?')}x")
else:
    print("   FAIL")
print()

# 8. Strategy modules
print("--- 8. STRATEGY MODULES ---")
from strategies.strategy_v1 import StrategyV1
strat = StrategyV1({'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70})
print(f"   StrategyV1 initialised: PASS")

from strategies.filters import SignalFilters
filt = SignalFilters({})
print(f"   SignalFilters initialised: PASS")

from strategies.strategy_manager import StrategyManager
sm = StrategyManager({'strategy': {}}, client)
print(f"   StrategyManager initialised: PASS")
print()

# 9. Risk Manager
print("--- 9. RISK MANAGEMENT ---")
from core.risk_manager import RiskManager
rm = RiskManager({'risk_management': {'risk_percent': 0.2, 'max_daily_drawdown': 0.05, 'max_consecutive_losses': 3}})
print(f"   RiskManager initialised: PASS")
print()

# 10. Indicators
print("--- 10. INDICATORS ---")
from indicators.rsi import RsiCalculator
print(f"   RSI: PASS")
from indicators.atr import AtrCalculator
print(f"   ATR: PASS")
from indicators.ema import EmaCalculator
print(f"   EMA: PASS")

print()
print("=== ALL MODULES TESTED ===")
print(f"Results: Connection={r} | Wallet={'OK' if bal else 'FAIL'} | Ticker={'OK' if t else 'FAIL'} | Klines={'OK' if k else 'FAIL'} | Orderbook={'OK' if ob else 'FAIL'} | Positions={'OK' if pos else 'FAIL'}")