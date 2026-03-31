"""API endpoints for managing user watchlists."""

import logging
from typing import List

from api.services.watchlist_service import (
    AddWatchlistItem,
    CreateWatchlist,
    UpdateWatchlist,
    UpdateWatchlistItem,
    Watchlist,
    WatchlistItem,
    get_watchlist_service,
)
from api.utils.auth_middleware import AuthUser, get_authenticated_user
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/watchlists",
    tags=["watchlists"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=Watchlist, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    watchlist_data: CreateWatchlist,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Create a new watchlist for the authenticated user.

    Requires authentication.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        watchlist = await watchlist_service.create_watchlist(
            user_id=current_user.user_id, watchlist_data=watchlist_data
        )
        return watchlist
    except Exception as e:
        logger.error(f"Failed to create watchlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create watchlist: {str(e)}",
        )


@router.get("", response_model=List[Watchlist])
async def get_user_watchlists(
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Get all watchlists for the authenticated user.

    Returns watchlists ordered by default status (default first) and creation date.
    Requires authentication.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        watchlists = await watchlist_service.get_user_watchlists(
            user_id=current_user.user_id
        )
        return watchlists
    except Exception as e:
        logger.error(f"Failed to get watchlists: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watchlists: {str(e)}",
        )


@router.get("/{watchlist_id}", response_model=Watchlist)
async def get_watchlist(
    watchlist_id: int,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Get a specific watchlist with all its items.

    Requires authentication and watchlist must belong to the user.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        watchlist = await watchlist_service.get_watchlist(
            user_id=current_user.user_id, watchlist_id=watchlist_id
        )

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watchlist {watchlist_id} not found",
            )

        return watchlist
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get watchlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watchlist: {str(e)}",
        )


@router.put("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
    watchlist_id: int,
    updates: UpdateWatchlist,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Update a watchlist's name, description, or default status.

    Requires authentication and watchlist must belong to the user.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        watchlist = await watchlist_service.update_watchlist(
            user_id=current_user.user_id, watchlist_id=watchlist_id, updates=updates
        )

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watchlist {watchlist_id} not found",
            )

        return watchlist
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update watchlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watchlist: {str(e)}",
        )


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: int,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Delete a watchlist and all its items.

    Requires authentication and watchlist must belong to the user.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        success = await watchlist_service.delete_watchlist(
            user_id=current_user.user_id, watchlist_id=watchlist_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watchlist {watchlist_id} not found",
            )

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete watchlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete watchlist: {str(e)}",
        )


@router.post("/{watchlist_id}/items", response_model=WatchlistItem, status_code=status.HTTP_201_CREATED)
async def add_item_to_watchlist(
    watchlist_id: int,
    item_data: AddWatchlistItem,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Add an asset to a watchlist.

    Requires authentication and watchlist must belong to the user.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        item = await watchlist_service.add_item_to_watchlist(
            user_id=current_user.user_id, watchlist_id=watchlist_id, item_data=item_data
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watchlist {watchlist_id} not found",
            )

        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add item to watchlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item to watchlist: {str(e)}",
        )


@router.put("/items/{item_id}", response_model=WatchlistItem)
async def update_watchlist_item(
    item_id: int,
    updates: UpdateWatchlistItem,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Update a watchlist item's notes, alerts, or target correlation.

    Requires authentication and item must belong to user's watchlist.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        item = await watchlist_service.update_watchlist_item(
            user_id=current_user.user_id, item_id=item_id, updates=updates
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watchlist item {item_id} not found",
            )

        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update watchlist item: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watchlist item: {str(e)}",
        )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_watchlist(
    item_id: int,
    current_user: AuthUser = Depends(get_authenticated_user),
):
    """
    Remove an item from a watchlist.

    Requires authentication and item must belong to user's watchlist.
    """
    watchlist_service = get_watchlist_service()
    if not watchlist_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Watchlist service not available",
        )

    try:
        success = await watchlist_service.remove_item_from_watchlist(
            user_id=current_user.user_id, item_id=item_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watchlist item {item_id} not found",
            )

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove item from watchlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove item from watchlist: {str(e)}",
        )
