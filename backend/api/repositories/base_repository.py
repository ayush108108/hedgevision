"""
Base Repository Pattern Implementation

This module provides the base repository class that all specific repositories
should inherit from. It encapsulates common database operations and follows
the Repository Pattern for clean separation of concerns.

Architecture:
- Repositories handle ALL database access
- Services use repositories (no direct DB access)
- Enables easy testing with mock repositories
- Centralizes query optimization
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from supabase import Client

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Generic type for entity


class BaseRepository(Generic[T], ABC):
    """
    Base repository class providing common CRUD operations.

    All repository classes should inherit from this and implement
    the abstract methods for their specific entity type.
    """

    def __init__(self, supabase_client: Client, table_name: str):
        """
        Initialize repository with Supabase client and table name.

        Args:
            supabase_client: Authenticated Supabase client
            table_name: Name of the database table
        """
        self.supabase = supabase_client
        self.table_name = table_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_by_id(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single entity by ID.

        Args:
            entity_id: Primary key ID

        Returns:
            Entity dict or None if not found
        """
        try:
            response = (
                self.supabase.table(self.table_name)
                .select("*")
                .eq("id", entity_id)
                .single()
                .execute()
            )

            return response.data if response.data else None

        except Exception as e:
            self.logger.error(f"Error getting {self.table_name} by id {entity_id}: {e}")
            return None

    def get_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all entities with optional pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of entity dicts
        """
        try:
            query = self.supabase.table(self.table_name).select("*")

            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error getting all {self.table_name}: {e}")
            return []

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new entity.

        Args:
            data: Entity data to insert

        Returns:
            Created entity dict or None on failure
        """
        try:
            response = self.supabase.table(self.table_name).insert(data).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            self.logger.error(f"Error creating {self.table_name}: {e}")
            return None

    def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing entity.

        Args:
            entity_id: Primary key ID
            data: Fields to update

        Returns:
            Updated entity dict or None on failure
        """
        try:
            response = (
                self.supabase.table(self.table_name)
                .update(data)
                .eq("id", entity_id)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as e:
            self.logger.error(f"Error updating {self.table_name} id {entity_id}: {e}")
            return None

    def delete(self, entity_id: int) -> bool:
        """
        Delete an entity by ID.

        Args:
            entity_id: Primary key ID

        Returns:
            True if deleted, False on failure
        """
        try:
            self.supabase.table(self.table_name).delete().eq("id", entity_id).execute()

            return True

        except Exception as e:
            self.logger.error(f"Error deleting {self.table_name} id {entity_id}: {e}")
            return False

    def exists(self, entity_id: int) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            entity_id: Primary key ID

        Returns:
            True if exists, False otherwise
        """
        try:
            response = (
                self.supabase.table(self.table_name)
                .select("id")
                .eq("id", entity_id)
                .single()
                .execute()
            )

            return response.data is not None

        except Exception:
            return False

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filters.

        Args:
            filters: Optional filter conditions

        Returns:
            Count of matching entities
        """
        try:
            query = self.supabase.table(self.table_name).select("id", count="exact")

            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            response = query.execute()
            return response.count if hasattr(response, "count") else 0

        except Exception as e:
            self.logger.error(f"Error counting {self.table_name}: {e}")
            return 0

    def find_by(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find entities matching filter criteria.

        Args:
            filters: Filter conditions (key-value pairs)
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Column to sort by
            ascending: Sort direction

        Returns:
            List of matching entity dicts
        """
        try:
            query = self.supabase.table(self.table_name).select("*")

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=not ascending)

            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            self.logger.error(
                f"Error finding {self.table_name} by filters {filters}: {e}"
            )
            return []

    def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single entity matching filter criteria.

        Args:
            filters: Filter conditions (key-value pairs)

        Returns:
            Entity dict or None if not found
        """
        results = self.find_by(filters, limit=1)
        return results[0] if results else None

    def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple entities in a single operation.

        Args:
            data_list: List of entity data dicts

        Returns:
            List of created entity dicts
        """
        try:
            response = self.supabase.table(self.table_name).insert(data_list).execute()

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error bulk creating {self.table_name}: {e}")
            return []

    def upsert(
        self, data: Dict[str, Any], on_conflict: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Insert or update entity (upsert operation).

        Args:
            data: Entity data
            on_conflict: Column name(s) for conflict resolution

        Returns:
            Created/updated entity dict or None on failure
        """
        try:
            query = self.supabase.table(self.table_name).upsert(data)

            if on_conflict:
                query = query.on_conflict(on_conflict)

            response = query.execute()
            return response.data[0] if response.data else None

        except Exception as e:
            self.logger.error(f"Error upserting {self.table_name}: {e}")
            return None

    @abstractmethod
    def to_entity(self, data: Dict[str, Any]) -> T:
        """
        Convert database dict to entity object.

        Subclasses must implement this to provide entity-specific conversion.

        Args:
            data: Raw database record

        Returns:
            Typed entity object
        """

    @abstractmethod
    def to_dict(self, entity: T) -> Dict[str, Any]:
        """
        Convert entity object to database dict.

        Subclasses must implement this to provide entity-specific conversion.

        Args:
            entity: Typed entity object

        Returns:
            Database-compatible dict
        """
