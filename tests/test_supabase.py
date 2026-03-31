#!/usr/bin/env python3
"""
Supabase Connection Test Script
Tests connection to Supabase and explores available tables/data
"""

import os
import sys

# Add backend to path
sys.path.append('backend')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import Supabase client
from api.utils.supabase_client import get_supabase_client

def main():
    print('=== Testing Supabase Connection ===')

    # Get client
    client = get_supabase_client()
    if not client:
        print('❌ Failed to initialize Supabase client')
        return

    print('✅ Supabase client initialized successfully')
    print(f'   URL: {client.url[:50]}...')

    # Test basic connection and explore tables
    print('\n=== Exploring Database Tables ===')

    tables_to_check = [
        'precomputed_analysis',
        'precomputed_correlations',
        'correlation_matrices',
        'top_pairs_screening'
    ]

    for table in tables_to_check:
        try:
            # Try to get a count of records
            result = client.client.table(table).select('*', count='exact').limit(1).execute()
            count = getattr(result, 'count', 'unknown')
            print(f'📊 {table}: {count} records')

            # If records exist, show sample
            if hasattr(result, 'data') and result.data and len(result.data) > 0:
                print(f'   Sample record keys: {list(result.data[0].keys())}')

        except Exception as e:
            print(f'❌ {table}: Error - {str(e)}')

    print('\n=== Testing Data Retrieval ===')

    # Test correlation matrix retrieval
    try:
        corr_data = client.get_correlation_matrix('daily', 'spearman', 48)  # 48 hours
        if corr_data:
            print('✅ Found recent correlation matrix data')
            assets = corr_data.get('assets', [])
            print(f'   Assets: {len(assets)}')
            print(f'   Granularity: {corr_data.get("granularity")}')
            print(f'   Method: {corr_data.get("method")}')
            print(f'   Date range: {corr_data.get("start_date")} to {corr_data.get("end_date")}')

            # Show sample assets
            if assets:
                print(f'   Sample assets: {assets[:5]}...')
        else:
            print('❌ No recent correlation matrix data found')
    except Exception as e:
        print(f'❌ Error retrieving correlation matrix: {str(e)}')

    # Test top pairs retrieval
    try:
        top_pairs = client.get_top_pairs('daily', 'spearman', 48)
        if top_pairs:
            print(f'✅ Found {len(top_pairs)} top pairs')
            if len(top_pairs) > 0:
                sample_pair = top_pairs[0]
                print(f'   Sample pair: {sample_pair.get("asset1_symbol")} vs {sample_pair.get("asset2_symbol")} (corr: {sample_pair.get("correlation", "N/A")})')

                # Show top 3 pairs
                print('   Top 3 pairs:')
                for i, pair in enumerate(top_pairs[:3]):
                    print(f'     {i+1}. {pair.get("asset1_symbol")} ↔ {pair.get("asset2_symbol")}: {pair.get("correlation", "N/A"):.3f}')
        else:
            print('❌ No top pairs data found')
    except Exception as e:
        print(f'❌ Error retrieving top pairs: {str(e)}')

    print('\n=== Connection Test Complete ===')

if __name__ == '__main__':
    main()
