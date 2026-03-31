from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


class DummyTable:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self.last_payload = None

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        if self.name == 'assets':
            return SimpleNamespace(data=self.parent.assets_data)
        return SimpleNamespace(data=[])

    def update(self, payload):
        self.parent.last_update = {'table': self.name, 'payload': payload}
        return self

    def eq(self, key, val):
        # no-op: store condition
        self.parent.last_update['condition'] = (key, val)
        return self

    def insert(self, payload):
        self.parent.last_insert = {'table': self.name, 'payload': payload}
        return self


class SupabaseStub:
    def __init__(self):
        # default asset list
        self.assets_data = []
        self.last_update = None
        self.last_insert = None

    def table(self, name):
        return DummyTable(self, name)



@pytest.fixture()
def supabase_stub(monkeypatch):
    # Ensure backend path in import search
    repo_root = Path(__file__).parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    stub = SupabaseStub()
    monkeypatch.setenv('SUPABASE_URL', 'https://example')
    monkeypatch.setenv('SUPABASE_KEY', 'secret')
    # Ensure the backend.scripts module is importable so we can patch create_client
    monkeypatch.setattr('backend.scripts.validate_and_fix_yfinance_tickers.create_client', lambda *_: stub)
    return stub


def test_validate_and_fix_tickers_writes_audit_when_commit(supabase_stub):
    # Setup: a single asset with no yfinance_ticker will be inferred
    supabase_stub.assets_data = [
        {'id': 1, 'name': 'bitcoin', 'exchange': 'CRYPTO', 'yfinance_ticker': None}
    ]

    validate = importlib.import_module('backend.scripts.validate_and_fix_yfinance_tickers')

    # Call with commit and skip_validation to force update and audit write
    results = validate.validate_and_fix_tickers(commit=True, skip_validation=True)

    # Check results reflect a fixed ticker
    assert len(results['fixed']) == 1
    # Check that the supabase stub received an update call for assets
    assert supabase_stub.last_update is not None
    assert supabase_stub.last_update['table'] == 'assets'
    # Check that evidence for audit write exists
    assert supabase_stub.last_insert is not None
    assert supabase_stub.last_insert['table'] == 'assets_yf_audit'
    assert supabase_stub.last_insert['payload']['asset_id'] == 1
    assert supabase_stub.last_insert['payload']['new_ticker'] == 'BTC-USD'
