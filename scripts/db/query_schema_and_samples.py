import sys, os
from pprint import pprint

# Ensure backend/api is importable as package 'api'
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
backend_dir = os.path.join(repo_root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.utils.supabase_client import get_supabase_client


def main():
    supa = get_supabase_client()
    if not supa:
        print('❌ Supabase client not initialized')
        return 1

    print('✅ Connected to Supabase')

    # Assets: columns and sample
    assets = supa.client.table('assets').select('*').limit(3).execute()
    print('\nAssets: sample rows =', len(assets.data or []))
    if assets.data:
        print('Assets columns:', list(assets.data[0].keys()))
        pprint(assets.data)

    # Check fields presence and common patterns
    aset = supa.client.table('assets').select('symbol,yfinance_ticker,is_active').limit(10).execute()
    print('\nAssets (symbol,yfinance_ticker,is_active):')
    pprint(aset.data)

    # Look for AAPL variants
    aapl_plain = supa.client.table('assets').select('id,symbol,yfinance_ticker').eq('symbol', 'AAPL').execute()
    aapl_us = supa.client.table('assets').select('id,symbol,yfinance_ticker').eq('symbol', 'AAPL.US').execute()
    print('\nLookup AAPL:')
    print('AAPL ->', aapl_plain.data)
    print('AAPL.US ->', aapl_us.data)

    # price_history sample
    ph = supa.client.table('price_history').select('*').limit(1).execute()
    print('\nprice_history: sample rows =', len(ph.data or []))
    if ph.data:
        print('price_history columns:', list(ph.data[0].keys()))
        pprint(ph.data)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
