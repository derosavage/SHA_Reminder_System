#!/usr/bin/env python3
"""
Monitor script: summarizes recent strategy signals, orders, and exchange state.
Run from project root with the shared venv python.
"""
import sys
from pathlib import Path
import re
import os
from dotenv import load_dotenv

# ensure project root on path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from exchange.bybit_client import BybitClient

LOG_DIR = project_root / 'logs'
BOT_LOG = LOG_DIR / 'bot.log'
BYBIT_LOG = LOG_DIR / 'BybitClient.log'
TRADES_CSV = LOG_DIR / 'trades_live.csv'

TAIL_LINES = 400

PATTERNS = [
    r"\bSignal\b",
    r"Entry:",
    r"Take profit",
    r"Stop loss",
    r"placed order",
    r"Order placed",
    r"Order filled",
    r"orderId",
    r"retCode",
    r"get_positions",
]


def tail(path: Path, n: int = 200):
    if not path.exists():
        return []
    with open(path, 'rb') as f:
        # Read in chunks from end
        avg_line_length = 200
        to_read = n * avg_line_length
        try:
            f.seek(-to_read, 2)
        except OSError:
            f.seek(0)
        data = f.read().decode(errors='replace')
    lines = data.splitlines()
    return lines[-n:]


def search_lines(lines, patterns):
    found = []
    for i, line in enumerate(lines):
        for p in patterns:
            if re.search(p, line, flags=re.IGNORECASE):
                found.append((i + 1, p, line))
                break
    return found


def summarize_logs():
    bot_lines = tail(BOT_LOG, TAIL_LINES)
    bybit_lines = tail(BYBIT_LOG, TAIL_LINES)

    bot_matches = search_lines(bot_lines, PATTERNS)
    bybit_matches = search_lines(bybit_lines, PATTERNS)

    print('--- Recent Strategy/Engine Matches (bot.log) ---')
    if bot_matches:
        for idx, pat, line in bot_matches[-20:]:
            print(line)
    else:
        print('No recent signal/order lines found in bot.log')

    print('\n--- Recent Bybit Client Matches (BybitClient.log) ---')
    if bybit_matches:
        for idx, pat, line in bybit_matches[-20:]:
            print(line)
    else:
        print('No recent bybit matches found')

    print('\n--- Last 10 lines of bot.log ---')
    for l in bot_lines[-10:]:
        print(l)

    print('\n--- Last 10 lines of BybitClient.log ---')
    for l in bybit_lines[-10:]:
        print(l)


def check_exchange():
    load_dotenv(dotenv_path=project_root / '.env')
    api_key = os.getenv('BYBIT_API_KEY', '')
    api_secret = os.getenv('BYBIT_API_SECRET', '')
    testnet = os.getenv('BYBIT_TESTNET', 'false').lower() == 'true'

    client = BybitClient(api_key=api_key, api_secret=api_secret, testnet=testnet)

    print('\n--- Exchange State ---')
    try:
        wb = client.get_wallet_balance()
        print('Wallet balance:', wb)
    except Exception as e:
        print('Wallet check failed:', e)

    try:
        positions = client.get_positions()
        print('Positions:', positions)
    except Exception as e:
        print('Positions check failed:', e)

    try:
        orders = client.get_open_orders()
        print('Open orders:', orders)
    except Exception as e:
        print('Open orders check failed:', e)


def check_trades_csv():
    if not TRADES_CSV.exists():
        print('\nNo trades CSV found at logs/trades_live.csv')
        return
    with open(TRADES_CSV, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    print(f'\n--- trades_live.csv last {min(10, len(lines))} lines ---')
    for l in lines[-10:]:
        print(l)


if __name__ == '__main__':
    summarize_logs()
    check_exchange()
    check_trades_csv()
