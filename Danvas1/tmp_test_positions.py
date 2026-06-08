from exchange.bybit_client import BybitClient
c = BybitClient(testnet=True)
print('Testing get_positions...')
res = c.get_positions()
print('Result:', res)
