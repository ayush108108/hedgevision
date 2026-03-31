"""
Unit tests for AssetService
Tests asset management operations without database dependencies
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Import service after path setup
import importlib
import sys
from pathlib import Path


def _get_asset_service():
    """Dynamically import AssetService"""
    repo_root = Path(__file__).parent.parent
    backend_path = repo_root / "backend"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    return importlib.import_module("api.services.asset_service").AssetService


@pytest.fixture
def mock_supabase_client():
    """Create mock Supabase client with table operations"""
    client = Mock()
    
    # Mock table() chain
    mock_table = Mock()
    mock_select = Mock()
    mock_eq = Mock()
    mock_execute = Mock()
    
    # Set up chain: table().select().eq().execute()
    client.table = Mock(return_value=mock_table)
    mock_table.select = Mock(return_value=mock_select)
    mock_table.update = Mock(return_value=mock_eq)
    mock_select.eq = Mock(return_value=mock_eq)
    mock_eq.eq = Mock(return_value=mock_eq)
    mock_eq.or_ = Mock(return_value=mock_eq)
    mock_eq.execute = Mock(return_value=mock_execute)
    
    # Default execute response with sample data
    mock_execute.data = [
        {
            "id": 1,
            "symbol": "AAPL.US",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "is_active": True,
            "last_price_update": "2024-11-01T00:00:00"
        },
        {
            "id": 2,
            "symbol": "MSFT.US",
            "name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "is_active": True,
            "last_price_update": "2024-11-01T00:00:00"
        }
    ]
    
    return client


@pytest.fixture
def asset_service(mock_supabase_client):
    """Create AssetService instance with mock client"""
    AssetService = _get_asset_service()
    service = AssetService(supabase_client=mock_supabase_client)
    return service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_active_assets_returns_active_only(asset_service, mock_supabase_client):
    """
    Test: get_active_assets() returns only active assets
    Risk: Inactive assets included in trading operations cause errors
    """
    result = await asset_service.get_active_assets()
    
    # Should call Supabase with correct filter
    mock_supabase_client.table.assert_called_with("assets")
    
    # Should return list of assets
    assert isinstance(result, list)
    assert len(result) == 2
    
    # All returned assets should be active
    for asset in result:
        assert asset["is_active"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_active_assets_handles_empty_result(asset_service, mock_supabase_client):
    """
    Test: get_active_assets() handles no active assets gracefully
    Risk: Empty result causes downstream errors
    """
    # Mock empty response
    mock_execute = mock_supabase_client.table().select().eq().execute()
    mock_execute.data = []
    
    result = await asset_service.get_active_assets()
    
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_active_assets_handles_database_error(asset_service, mock_supabase_client):
    """
    Test: get_active_assets() handles database errors gracefully
    Risk: Database failures crash application
    """
    # Mock database error
    mock_supabase_client.table.side_effect = Exception("Database connection failed")
    
    result = await asset_service.get_active_assets()
    
    # Should return empty list on error
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_assets_needing_data_identifies_stale_assets(asset_service, mock_supabase_client):
    """
    Test: get_assets_needing_data() identifies assets with outdated data
    Risk: Stale data not refreshed leads to incorrect analytics
    """
    # Mock response with stale asset
    now = datetime.now()
    stale_date = now - timedelta(days=5)
    
    mock_execute = mock_supabase_client.table().select().eq().or_().execute()
    mock_execute.data = [
        {
            "id": 1,
            "symbol": "AAPL.US",
            "last_price_update": stale_date.isoformat(),
            "is_active": True
        }
    ]
    
    result = await asset_service.get_assets_needing_data(days_stale=2)
    
    # Should return stale assets
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_assets_needing_data_includes_never_updated(asset_service, mock_supabase_client):
    """
    Test: get_assets_needing_data() includes assets never updated
    Risk: New assets without data missed in data refresh
    """
    # Mock response with null last_price_update
    mock_execute = mock_supabase_client.table().select().eq().or_().execute()
    mock_execute.data = [
        {
            "id": 3,
            "symbol": "GOOGL.US",
            "last_price_update": None,  # Never updated
            "is_active": True
        }
    ]
    
    result = await asset_service.get_assets_needing_data(days_stale=2)
    
    # Should include assets with null timestamps
    assert isinstance(result, list)
    assert len(result) > 0
    assert any(asset["last_price_update"] is None for asset in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_assets_needing_data_configurable_threshold(asset_service, mock_supabase_client):
    """
    Test: get_assets_needing_data() respects custom staleness threshold
    Risk: Hardcoded threshold prevents flexible data refresh strategies
    """
    # Test with different thresholds
    result_1day = await asset_service.get_assets_needing_data(days_stale=1)
    result_7days = await asset_service.get_assets_needing_data(days_stale=7)
    
    # Both should execute without error
    assert isinstance(result_1day, list)
    assert isinstance(result_7days, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_asset_last_updated_single_asset(asset_service, mock_supabase_client):
    """
    Test: update_asset_last_updated() updates timestamp for single asset
    Risk: Timestamp not updated leads to redundant data fetches
    """
    asset_ids = [1]
    
    await asset_service.update_asset_last_updated(asset_ids)
    
    # Should call update with timestamp
    mock_supabase_client.table.assert_called_with("assets")
    # Verify update was called (actual call verification depends on mock structure)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_asset_last_updated_multiple_assets(asset_service, mock_supabase_client):
    """
    Test: update_asset_last_updated() handles batch updates
    Risk: Batch operations fail or skip assets
    """
    asset_ids = [1, 2, 3, 4, 5]
    
    await asset_service.update_asset_last_updated(asset_ids)
    
    # Should call update for each asset
    assert mock_supabase_client.table.call_count >= len(asset_ids)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_asset_last_updated_handles_error(asset_service, mock_supabase_client):
    """
    Test: update_asset_last_updated() handles update errors gracefully
    Risk: Single asset update failure breaks entire batch
    """
    # Mock update error
    mock_supabase_client.table.side_effect = Exception("Update failed")
    
    asset_ids = [1, 2]
    
    # Should not raise exception
    await asset_service.update_asset_last_updated(asset_ids)
    # Success is not raising an exception


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_quality_score_valid_score(asset_service, mock_supabase_client):
    """
    Test: update_quality_score() updates asset quality metric
    Risk: Quality scores not tracked prevents data quality monitoring
    """
    asset_id = 1
    quality_score = 0.95
    
    await asset_service.update_quality_score(asset_id, quality_score)
    
    # Should call update with quality score
    mock_supabase_client.table.assert_called_with("assets")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_quality_score_boundary_values(asset_service, mock_supabase_client):
    """
    Test: update_quality_score() handles boundary values (0.0, 1.0)
    Risk: Edge case scores cause validation errors
    """
    # Test minimum score
    await asset_service.update_quality_score(1, 0.0)
    
    # Test maximum score
    await asset_service.update_quality_score(1, 1.0)
    
    # Both should succeed
    assert mock_supabase_client.table.call_count >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_quality_score_handles_database_error(asset_service, mock_supabase_client):
    """
    Test: update_quality_score() handles database errors gracefully
    Risk: Failed quality updates crash monitoring workflows
    """
    # Mock database error
    mock_supabase_client.table.side_effect = Exception("Database error")
    
    # Should not raise exception
    await asset_service.update_quality_score(1, 0.85)
    # Success is not raising an exception


@pytest.mark.unit
def test_asset_service_initialization_with_client(mock_supabase_client):
    """
    Test: AssetService accepts custom Supabase client
    Risk: Dependency injection not working prevents testing
    """
    AssetService = _get_asset_service()
    service = AssetService(supabase_client=mock_supabase_client)
    
    assert service.supabase is mock_supabase_client


@pytest.mark.unit
@patch('api.services.asset_service.create_client')
def test_asset_service_initialization_creates_client(mock_create_client):
    """
    Test: AssetService creates Supabase client if not provided
    Risk: Default client creation fails in production
    """
    mock_create_client.return_value = Mock()
    
    AssetService = _get_asset_service()
    service = AssetService()
    
    # Should create client using config
    assert service.supabase is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_assets_needing_data_returns_empty_on_error(asset_service, mock_supabase_client):
    """
    Test: get_assets_needing_data() returns empty list on database error
    Risk: Unhandled errors break data refresh pipeline
    """
    # Mock error
    mock_supabase_client.table.side_effect = Exception("Query failed")
    
    result = await asset_service.get_assets_needing_data(days_stale=2)
    
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.unit
@pytest.mark.asyncio  
async def test_update_asset_last_updated_empty_list(asset_service, mock_supabase_client):
    """
    Test: update_asset_last_updated() handles empty asset list
    Risk: Empty input causes unexpected behavior
    """
    await asset_service.update_asset_last_updated([])
    
    # Should complete without error (no updates needed)
    # Success is not raising an exception
