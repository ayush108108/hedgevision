"""
Supabase client for storing pre-computed pair analysis results.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from typing import Any as _AnyType

from .config import config

logger = logging.getLogger(__name__)
try:
    from supabase import create_client  # type: ignore
    SUPABASE_AVAILABLE = True
except ImportError:
    def create_client(*args: _AnyType, **kwargs: _AnyType):  # type: ignore
        raise ImportError("Supabase client not available. Install with: pip install supabase")
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available. Install with: pip install supabase")


class SupabaseClient:
    """Supabase client for pair analysis data storage."""

    def __init__(self):
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase client not available")

        self.url = config.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        # Use service role key for write operations (bypasses RLS)
        self.key = (
            config.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or config.get("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or config.get("SUPABASE_KEY")
            or os.getenv("SUPABASE_KEY")
            or config.get("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY/SUPABASE_ANON_KEY must be set"
            )

        # Instantiate Supabase client (dynamic import style)
        self.client = create_client(self.url, self.key)  # type: ignore
        self.model_version = config.get("MODEL_VERSION", "prod-v1")
        logger.info("Supabase client initialized successfully")

    def store_pair_analysis(self, pair_data: Dict[str, Any]) -> bool:
        """Store pair analysis results in Supabase."""
        try:
            # Transform to match precomputed_analysis schema
            analysis_record = {
                "asset1_symbol": pair_data.get("asset1"),
                "asset2_symbol": pair_data.get("asset2"),
                "analysis_data": pair_data,  # Store full data as JSONB
                "created_at": datetime.utcnow().isoformat(),
                "model_version": self.model_version,
            }

            try:
                result = (
                    self.client.table("precomputed_analysis")
                    .upsert(analysis_record)
                    .execute()
                )
            except Exception:
                # Backward compatibility for schemas without model_version column.
                analysis_record.pop("model_version", None)
                result = (
                    self.client.table("precomputed_analysis")
                    .upsert(analysis_record)
                    .execute()
                )

            if result.data:
                logger.info(
                    f"Stored pair analysis for {pair_data.get('asset1')} / {pair_data.get('asset2')}"
                )
                return True
            else:
                logger.error(f"Failed to store pair analysis: {result}")
                return False

        except Exception as e:
            logger.error(f"Error storing pair analysis: {str(e)}", exc_info=True)
            return False

    def get_pair_analysis(
        self, asset1: str, asset2: str, max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """Retrieve pair analysis from Supabase if recent enough."""
        try:
            # Calculate minimum timestamp for fresh data
            from api.utils.datetime_normalization import normalize_datetime_iso
            min_timestamp = datetime.utcnow() - timedelta(hours=max_age_hours)
            min_iso = normalize_datetime_iso(min_timestamp, assume="start") or min_timestamp.isoformat()

            query = (
                self.client.table("precomputed_analysis")
                .select("*")
                .eq("asset1_symbol", asset1)
                .eq("asset2_symbol", asset2)
                .gte("created_at", min_iso)
                .order("created_at", desc=True)
                .limit(1)
            )
            try:
                result = query.eq("model_version", self.model_version).execute()
            except Exception:
                result = query.execute()

            if result.data:
                logger.info(f"Retrieved cached pair analysis for {asset1} / {asset2}")
                # Extract analysis_data from the JSONB field
                return result.data[0].get("analysis_data", {})
            else:
                logger.info(f"No recent pair analysis found for {asset1} / {asset2}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving pair analysis: {str(e)}", exc_info=True)
            return None

    def store_correlation_matrix(self, matrix_data: Dict[str, Any]) -> bool:
        """Store correlation matrix results in Supabase."""
        try:
            # Map from service format to actual correlation_matrix table schema
            # Service provides: granularity, method, start_date, end_date, correlation_matrix, assets
            # Table has: calculation_method, window_days, matrix_date, correlation_matrix (Text/JSON)
            
            # Calculate window_days from date range if provided
            window_days = None
            start_date_str = matrix_data.get("start_date")
            end_date_str = matrix_data.get("end_date")
            if start_date_str and end_date_str:
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    window_days = (end - start).days
                except Exception:
                    window_days = 252  # default fallback
            else:
                window_days = 252
            
            import math
            import json

            def clean_floats(obj):
                if isinstance(obj, float):
                    return None if math.isnan(obj) or math.isinf(obj) else obj
                elif isinstance(obj, dict):
                    return {k: clean_floats(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_floats(i) for i in obj]
                return obj

            correlation_dict = matrix_data.get("correlation_matrix", {})
            safe_correlation = clean_floats(correlation_dict)

            mapped_data = {
                "calculation_method": matrix_data.get("method") or matrix_data.get("calculation_method", "pearson"),
                "window_days": window_days,
                # datetime imported at module level; add explicit reference to avoid analysis warning
                "matrix_date": end_date_str or datetime.utcnow().isoformat(),  # type: ignore[name-defined]
                # Send a JSON object instead of a JSON string: PostgREST/Postgres will accept
                # proper objects and avoid jsonb_each errors when performing JSON operators
                "correlation_matrix": safe_correlation,
                "model_version": self.model_version,
            }

            # Use upsert to handle existing records (update instead of failing on duplicate)
            try:
                result = (
                    self.client.table("correlation_matrix")
                    .upsert(
                        mapped_data,
                        on_conflict="matrix_date,window_days,calculation_method,model_version",
                    )
                    .execute()
                )
            except Exception:
                # Backward compatibility for schemas without model_version column.
                mapped_data.pop("model_version", None)
                result = (
                    self.client.table("correlation_matrix")
                    .upsert(mapped_data, on_conflict="matrix_date,window_days,calculation_method")
                    .execute()
                )

            if result.data:
                logger.info(
                    f"✅ Stored correlation matrix for method={mapped_data.get('calculation_method')}"
                )
                return True
            else:
                logger.error(f"Failed to store correlation matrix: {result}")
                return False

        except Exception as e:
            logger.error(f"Error storing correlation matrix: {str(e)}", exc_info=True)
            return False

    def get_correlation_matrix(
        self,
        granularity: str = "daily",
        method: str = "spearman",
        max_age_hours: int = 24,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve correlation matrix from Supabase if recent enough."""
        try:
            from api.utils.datetime_normalization import normalize_datetime_iso
            min_timestamp = datetime.utcnow() - timedelta(hours=max_age_hours)
            min_iso = normalize_datetime_iso(min_timestamp, assume="start") or min_timestamp.isoformat()

            # Use correlation_matrix table - map method to calculation_method
            query = (
                self.client.table("correlation_matrix")
                .select("*")
                .eq("calculation_method", method)
                .gte("calculation_timestamp", min_iso)
                .order("matrix_date", desc=True)
                .limit(1)
            )
            try:
                result = query.eq("model_version", self.model_version).execute()
            except Exception:
                result = query.execute()

            if result.data:
                # Map back to expected format for compatibility
                import json
                row = result.data[0]
                corr_matrix_raw = row.get("correlation_matrix", "{}")
                # Parse if string, otherwise use as-is
                if isinstance(corr_matrix_raw, str):
                    corr_matrix = json.loads(corr_matrix_raw)
                else:
                    corr_matrix = corr_matrix_raw
                
                mapped = {
                    "id": row.get("id"),
                    "method": row.get("calculation_method"),
                    "granularity": granularity,  # Not stored in table, pass through
                    "created_at": row.get("calculation_timestamp"),
                    "end_date": row.get("matrix_date"),
                    "correlation_matrix": corr_matrix,
                    "model_version": row.get("model_version", self.model_version),
                }
                logger.info(f"Retrieved cached correlation matrix for method={method}")
                return mapped
            else:
                logger.info(f"No recent correlation matrix found for method={method}")
                return None

        except Exception as e:
            logger.error(
                f"Error retrieving correlation matrix: {str(e)}", exc_info=True
            )
            return None

    def store_top_pairs(
        self,
        pairs_data: List[Dict[str, Any]],
        granularity: str = "daily",
        method: str = "spearman",
    ) -> bool:
        """
        Store top pairs screening results.
        NOTE: Deprecated - pairs are now derived from correlation_matrix dynamically.
        This method is kept for backward compatibility but does nothing.
        """
        logger.info(
            "store_top_pairs called but deprecated - pairs derived from correlation_matrix dynamically"
        )
        return True  # Return success to not break existing code

    def get_top_pairs(
        self,
        granularity: str = "daily",
        method: str = "spearman",
        max_age_hours: int = 24,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve top pairs by deriving them from correlation_matrix.
        NOTE: No longer queries precomputed_pairs (empty table).
        """
        try:
            # Get latest correlation matrix
            matrix_data = self.get_correlation_matrix(
                granularity, method, max_age_hours
            )

            if not matrix_data or "correlation_matrix" not in matrix_data:
                logger.info("No correlation matrix available to derive pairs")
                return None

            # Extract pairs from correlation matrix
            corr_matrix = matrix_data["correlation_matrix"]
            pairs = []

            # Convert matrix to list of pairs
            for asset1, correlations in corr_matrix.items():
                if isinstance(correlations, dict):
                    for asset2, corr_value in correlations.items():
                        if asset1 < asset2:  # Avoid duplicates (A-B and B-A)
                            pairs.append(
                                {
                                    "asset1_symbol": asset1,
                                    "asset2_symbol": asset2,
                                    "correlation": corr_value,
                                    "method": method,
                                    "abs_correlation": abs(corr_value),
                                }
                            )

            # Sort by absolute correlation descending
            pairs.sort(key=lambda x: x["abs_correlation"], reverse=True)

            logger.info(
                f"Derived {len(pairs)} pairs from correlation matrix (method={method})"
            )
            return pairs

        except Exception as e:
            logger.error(f"Error retrieving top pairs: {str(e)}", exc_info=True)
            return None

    def execute_sql(self, sql: str) -> Any:
        """Execute raw SQL query."""
        try:
            result = self.client.rpc('exec_sql', {'query': sql}).execute()
            logger.info(f"Executed SQL: {sql[:100]}...")
            return result
        except Exception as e:
            logger.error(f"Error executing SQL: {str(e)}", exc_info=True)
            return None


# Global Supabase client instance
_supabase_client = None


def get_supabase_client() -> Optional[SupabaseClient]:
    """Get the global Supabase client instance."""
    global _supabase_client

    # Local-first mode: do not require/initialize Supabase client.
    if config.get("DATA_BACKEND") == "sqlite":
        return None

    if not SUPABASE_AVAILABLE:
        logger.warning("Supabase not available")
        return None

    if _supabase_client is None:
        try:
            _supabase_client = SupabaseClient()
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            return None

    return _supabase_client
