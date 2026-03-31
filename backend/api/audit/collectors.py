"""
Data collection module for AI audit framework
Gathers data from codebase, Supabase, and logs
"""
import glob
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List

from api.audit.config import AuditConfig
from api.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects data from various sources for AI analysis"""

    def __init__(self, config: AuditConfig):
        self.config = config
        self.supabase = get_supabase_client()

    async def collect_codebase_context(self) -> Dict[str, Any]:
        """Collect relevant code files from the codebase"""
        logger.info("Collecting codebase context...")

        code_files = {}
        errors = []
        patterns = [
            "backend/api/**/*.py",
            "backend/api/services/**/*.py",
            "backend/api/routers/**/*.py",
            "backend/api/utils/**/*.py",
            "scripts/**/*.py",
        ]

        for pattern in patterns:
            for file_path in glob.glob(
                os.path.join(self.config.codebase_root, pattern), recursive=True
            ):
                # Skip test files and migrations
                if "__pycache__" in file_path or "test_" in file_path:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        relative_path = os.path.relpath(
                            file_path, self.config.codebase_root
                        )
                        code_files[relative_path] = content
                except Exception as e:
                    error_msg = f"Could not read {file_path}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        logger.info(f"Collected {len(code_files)} code files")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during codebase collection")

        return {"files": code_files, "total_files": len(code_files), "errors": errors}

    async def collect_database_context(self) -> Dict[str, Any]:
        """Collect database schema and sample data from Supabase"""
        logger.info("Collecting database context...")

        errors = []
        context = {
            "schema": await self._get_database_schema(),
            "sample_data": await self._get_sample_data(),
            "table_stats": await self._get_table_statistics(),
        }

        # Aggregate errors from all database operations
        for key, value in context.items():
            if isinstance(value, dict) and "error" in value:
                errors.append(f"{key}: {value['error']}")

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during database collection")
            context["errors"] = errors

        return context

    async def _get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            # Get all tables
            tables_query = """
                SELECT 
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """

            # Get columns for each table
            columns_query = """
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """

            # For now, return a simplified schema
            # In production, execute these queries against Supabase
            schema_info = {
                "note": "Schema collection requires direct DB access",
                "tables": [
                    "assets",
                    "price_history",
                    "cointegration_scores",
                    "pair_trades",
                    "pair_spread_history",
                ],
            }

            return schema_info

        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {"error": str(e)}

    async def _get_sample_data(self) -> Dict[str, Any]:
        """Get sample data from key tables"""
        try:
            sample_data = {}
            tables = [
                "assets",
                "price_history",
                "cointegration_scores",
                "pair_trades",
                "pair_spread_history",
            ]

            sample_rate = self.config.data_sampling_rate
            limit = max(10, int(100 * sample_rate))  # At least 10 records

            for table in tables:
                try:
                    response = (
                        self.supabase.client.table(table)
                        .select("*")
                        .limit(limit)
                        .execute()
                    )

                    if response.data:
                        # Sample randomly if more data than needed
                        data = response.data
                        if len(data) > limit:
                            data = random.sample(data, limit)

                        sample_data[table] = {
                            "count": len(data),
                            "sample": data[:5],  # First 5 records for context
                            "schema": (
                                list(data[0].keys()) if data else []
                            ),  # Column names
                        }
                except Exception as e:
                    logger.warning(f"Could not sample {table}: {e}")
                    sample_data[table] = {"error": str(e)}

            return sample_data

        except Exception as e:
            logger.error(f"Error getting sample data: {e}")
            return {"error": str(e)}

    async def _get_table_statistics(self) -> Dict[str, Any]:
        """Get statistics about tables (row counts, sizes, etc.)"""
        try:
            stats = {}
            tables = [
                "assets",
                "price_history",
                "cointegration_scores",
                "pair_trades",
                "pair_spread_history",
            ]

            for table in tables:
                try:
                    # Get count
                    response = (
                        self.supabase.client.table(table)
                        .select("*", count="exact")
                        .limit(1)
                        .execute()
                    )

                    stats[table] = {
                        "row_count": response.count if hasattr(response, "count") else 0
                    }
                except Exception as e:
                    logger.warning(f"Could not get stats for {table}: {e}")
                    stats[table] = {"error": str(e)}

            return stats

        except Exception as e:
            logger.error(f"Error getting table statistics: {e}")
            return {"error": str(e)}

    async def collect_log_context(self) -> Dict[str, Any]:
        """Collect recent logs for analysis"""
        logger.info("Collecting log context...")

        logs = {"recent_logs": [], "error_logs": [], "warning_logs": []}
        errors = []

        for log_pattern in self.config.log_files:
            for log_file in glob.glob(log_pattern):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        # Read last 1000 lines
                        lines = f.readlines()[-1000:]

                        for line in lines:
                            line_lower = line.lower()
                            if "error" in line_lower:
                                logs["error_logs"].append(line.strip())
                            elif "warning" in line_lower:
                                logs["warning_logs"].append(line.strip())
                            else:
                                logs["recent_logs"].append(line.strip())

                except Exception as e:
                    error_msg = f"Could not read log file {log_file}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        # Limit to most recent
        logs["recent_logs"] = logs["recent_logs"][-200:]
        logs["error_logs"] = logs["error_logs"][-100:]
        logs["warning_logs"] = logs["warning_logs"][-100:]

        logger.info(
            f"Collected {len(logs['error_logs'])} errors, "
            f"{len(logs['warning_logs'])} warnings"
        )

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during log collection")
            logs["errors"] = errors

        return logs

    async def collect_calculation_context(self) -> Dict[str, Any]:
        """Collect context for calculation verification"""
        logger.info("Collecting calculation context...")

        errors = []
        context = {
            "cointegration_tests": await self._get_recent_cointegration_tests(),
            "spread_calculations": await self._get_recent_spread_data(),
            "price_data_integrity": await self._check_price_data_integrity(),
        }

        # Aggregate errors from calculation operations
        for key, value in context.items():
            if isinstance(value, dict) and "error" in value:
                errors.append(f"{key}: {value['error']}")
            elif isinstance(value, list) and not value:  # Empty lists indicate errors
                errors.append(f"{key}: No data retrieved")

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during calculation collection")
            context["errors"] = errors

        return context

    async def _get_recent_cointegration_tests(self) -> List[Dict[str, Any]]:
        """Get recent cointegration test results for verification"""
        try:
            response = (
                self.supabase.client.table("cointegration_scores")
                .select("*")
                .order("test_date", desc=True)
                .limit(20)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting cointegration tests: {e}")
            return []

    async def _get_recent_spread_data(self) -> List[Dict[str, Any]]:
        """Get recent spread calculations for verification"""
        try:
            response = (
                self.supabase.client.table("pair_spread_history")
                .select("*")
                .order("timestamp", desc=True)
                .limit(50)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting spread data: {e}")
            return []

    async def _check_price_data_integrity(self) -> Dict[str, Any]:
        """Check price data for anomalies"""
        try:
            # Get recent price data
            response = (
                self.supabase.client.table("price_history")
                .select("*")
                .order("timestamp", desc=True)
                .limit(1000)
                .execute()
            )

            if not response.data:
                return {"status": "no_data"}

            # Basic integrity checks
            data = response.data
            checks = {
                "total_records": len(data),
                "null_prices": sum(
                    1 for record in data if record.get("close") is None
                ),
                "negative_prices": sum(
                    1 for record in data if record.get("close", 0) < 0
                ),
                "zero_prices": sum(1 for record in data if record.get("close") == 0),
                "suspicious_volumes": sum(
                    1 for record in data if record.get("volume", 0) == 0
                ),
            }

            return checks

        except Exception as e:
            logger.error(f"Error checking price data integrity: {e}")
            return {"error": str(e)}

    async def collect_all_context(self) -> Dict[str, Any]:
        """Collect all available context for comprehensive audit"""
        logger.info("Collecting comprehensive audit context...")

        context = {
            "codebase": await self.collect_codebase_context(),
            "database": await self.collect_database_context(),
            "logs": await self.collect_log_context(),
            "calculations": await self.collect_calculation_context(),
            "timestamp": self._get_timestamp(),
        }

        return context

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.utcnow().isoformat()
