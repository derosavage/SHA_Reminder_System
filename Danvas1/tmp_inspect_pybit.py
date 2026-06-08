from pybit.unified_trading import HTTP
import inspect

print('get_positions signature:', inspect.signature(HTTP.get_positions))
print('get_position exists:', hasattr(HTTP, 'get_position'))
print('get_kline signature:', inspect.signature(HTTP.get_kline))
print('get_wallet_balance signature:', inspect.signature(HTTP.get_wallet_balance))
print('\nget_positions doc:\n', HTTP.get_positions.__doc__)
