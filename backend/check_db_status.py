#!/usr/bin/env python3
"""
Quick DB status check
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / "api" / ".env"
load_dotenv(env_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("❌ Supabase credentials not found")
    exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

try:
    # Check connection by getting table count
    result = supabase.table('information_schema.tables').select('table_name').eq('table_schema', 'public').execute()
    tables = [row['table_name'] for row in result.data]
    print(f"✅ Connected to Supabase. Found {len(tables)} tables in public schema.")
    
    if 'price_history_eod' in tables:
        # Get row count
        count_result = supabase.table('price_history_eod').select('*', count='exact').limit(1).execute()
        print(f"📊 price_history_eod has {count_result.count} rows.")
    else:
        print("⚠️ price_history_eod table not found.")
        
except Exception as e:
    print(f"❌ DB connection failed: {e}")