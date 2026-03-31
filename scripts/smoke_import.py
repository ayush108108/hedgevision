import sys
from pathlib import Path
from pprint import pprint

# Simulate CI pipeline sys.path insertion, prefer making `api` a top-level package
repo_root = Path(__file__).parent.parent
base_backend = repo_root / 'backend'
# Insert backend so the package `api` is importable (avoid inserting backend/api)
sys.path.insert(0, str(base_backend.resolve()))
print('Inserted into sys.path:', sys.path[0])

modules_to_test = [
    'api.utils.supabase_client',
    'api.services.correlation_service',
    'api.services.analytics_service',
    'api.services.pipeline_service',
    'api.main'
]

results = {}
for mod in modules_to_test:
    try:
        __import__(mod)
        results[mod] = 'OK'
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        results[mod] = f'{type(e).__name__}: {e}\n{tb}'

pprint(results)
