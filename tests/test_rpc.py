import sys
sys.path.append('backend')
from dotenv import load_dotenv
load_dotenv()
import pytest
from api.utils.supabase_client import get_supabase_client


def test_rpc_get_top_cointegrated_pairs_smoke():
    supa = get_supabase_client()
    if supa is None:
        pytest.skip("Supabase not configured (DATA_BACKEND=sqlite or no SUPABASE_URL)")
    res = supa.client.rpc('get_top_cointegrated_pairs', {
        'p_limit': 1,
        'p_granularity': 'daily',
        'p_min_score': 60.0
    }).execute()
    # Basic shape checks
    assert hasattr(res, 'data')
