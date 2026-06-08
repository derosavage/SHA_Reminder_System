from dotenv import load_dotenv
import os
load_dotenv()
from exchange.bybit_client import BybitClient
c = BybitClient(api_key=os.getenv('BYBIT_API_KEY'), api_secret=os.getenv('BYBIT_API_SECRET'), testnet=os.getenv('BYBIT_TESTNET','false').lower()=='true')
print('get_open_orders ->')
print(c.get_open_orders())
