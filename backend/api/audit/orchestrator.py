"""
Main orchestrator for AI audit framework
Coordinates data collection, analysis, and reporting
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from api.audit.collectors import DataCollector
from api.audit.config import AlertLevel, AuditConfig
from api.audit.providers import get_llm_provider
from api.audit.reporters import AuditReporter

logger = logging.getLogger(__name__)


class AuditOrchestrator:
    """Orchestrates the AI audit process"""

    def __init__(self, config: AuditConfig = None):
        self.config = config or AuditConfig.from_env()
        self.collector = DataCollector(self.config)
        self.reporter = AuditReporter(self.config)

        # Initialize primary and fallback providers
        self.primary_provider = get_llm_provider(
            self.config.primary_provider, self.config
        )
        self.fallback_provider = (
            get_llm_provider(self.config.fallback_provider, self.config)
            if self.config.fallback_provider
            else None
        )

    async def run_full_audit(self) -> Dict[str, Any]:
        """
        Run a comprehensive audit of codebase, data, and logs

        Returns:
            Dictionary containing all audit results
        """
        if not self.config.enabled:
            logger.info("AI audit is disabled")
            return {"status": "disabled"}

        # Generate unique trace ID for this audit run
        trace_id = str(uuid.uuid4())
        logger.info(f"Starting comprehensive AI audit with trace ID: {trace_id}")
        start_time = datetime.utcnow()

        try:
            # Collect all context with trace ID
            context = await self.collector.collect_all_context()
            context["_trace_id"] = trace_id

            # Extract and aggregate all collection errors
            collection_errors = []
            for context_type, context_data in context.items():
                if context_type == "timestamp" or context_type == "_trace_id":
                    continue
                if isinstance(context_data, dict) and "errors" in context_data:
                    collection_errors.extend(context_data["errors"])

            # Run analysis on different aspects
            results = {
                "timestamp": start_time.isoformat(),
                "trace_id": trace_id,
                "codebase_analysis": await self._analyze_codebase(context["codebase"]),
                "data_analysis": await self._analyze_data(context["database"]),
                "log_analysis": await self._analyze_logs(context["logs"]),
                "calculation_analysis": await self._analyze_calculations(
                    context["calculations"]
                ),
            }

            # Add collection errors to results if any
            if collection_errors:
                results["collection_errors"] = collection_errors
                logger.warning(f"Audit {trace_id} completed with {len(collection_errors)} collection errors")

            # Generate comprehensive report
            report = await self.reporter.generate_report(results)

            # Send alerts if needed
            await self._send_alerts(results)

            # Save report
            await self.reporter.save_report(report)

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Audit {trace_id} completed in {duration:.2f}s")

            return {
                "status": "completed",
                "duration_seconds": duration,
                "report_path": report.get("file_path"),
                "summary": report.get("summary"),
                "collection_errors": len(collection_errors) if collection_errors else 0,
                "trace_id": trace_id,
            }

        except Exception as e:
            logger.error(f"Audit {trace_id} failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "trace_id": trace_id}

    async def run_targeted_audit(
        self, audit_type: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a targeted audit on a specific aspect

        Args:
            audit_type: Type of audit (codebase, data, logs, calculations)
            context: Optional pre-collected context

        Returns:
            Audit results
        """
        # Generate unique trace ID for this audit run
        trace_id = str(uuid.uuid4())
        logger.info(f"Starting {audit_type} audit with trace ID: {trace_id}")

        if context is None:
            # Collect context based on audit type
            if audit_type == "codebase":
                context = await self.collector.collect_codebase_context()
            elif audit_type == "data":
                context = await self.collector.collect_database_context()
            elif audit_type == "logs":
                context = await self.collector.collect_log_context()
            elif audit_type == "calculations":
                context = await self.collector.collect_calculation_context()
            else:
                raise ValueError(f"Unknown audit type: {audit_type}")

        # Add trace ID to context
        context["_trace_id"] = trace_id

        # Run analysis
        if audit_type == "codebase":
            result = await self._analyze_codebase(context)
        elif audit_type == "data":
            result = await self._analyze_data(context)
        elif audit_type == "logs":
            result = await self._analyze_logs(context)
        elif audit_type == "calculations":
            result = await self._analyze_calculations(context)
        else:
            raise ValueError(f"Unknown audit type: {audit_type}")

        # Add trace ID to result
        result["trace_id"] = trace_id
        logger.info(f"Audit {trace_id} ({audit_type}) completed")

        return result

    async def _analyze_codebase(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze codebase for issues"""
        logger.info("Analyzing codebase...")
        return await self._run_analysis(context, "codebase")

    async def _analyze_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze database data for issues"""
        logger.info("Analyzing database data...")
        return await self._run_analysis(context, "data")

    async def _analyze_logs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze logs for issues"""
        logger.info("Analyzing logs...")
        return await self._run_analysis(context, "logs")

    async def _analyze_calculations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze calculations for accuracy"""
        logger.info("Analyzing calculations...")
        return await self._run_analysis(context, "calculations")

    async def _run_analysis(
        self, context: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """Run analysis using primary provider with fallback"""
        try:
            result = await self.primary_provider.analyze(context, analysis_type)
            result["provider_used"] = self.config.primary_provider.value
            return result

        except Exception as e:
            logger.error(
                f"Primary provider failed: {e}, trying fallback...", exc_info=True
            )

            if self.fallback_provider:
                try:
                    result = await self.fallback_provider.analyze(context, analysis_type)
                    result["provider_used"] = self.config.fallback_provider.value
                    result["fallback_used"] = True
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
                    return {
                        "error": f"Both providers failed. Primary: {e}, Fallback: {fallback_error}",
                        "status": "failed",
                    }
            else:
                return {"error": str(e), "status": "failed"}

    async def _send_alerts(self, results: Dict[str, Any]):
        """Send alerts based on audit results"""
        # Extract all issues
        all_issues = []
        for analysis_type, analysis_result in results.items():
            if analysis_type == "timestamp":
                continue

            issues = analysis_result.get("issues", [])
            all_issues.extend(issues)

        # Filter by severity threshold
        critical_issues = [
            issue
            for issue in all_issues
            if self._get_severity_level(issue.get("severity", "LOW"))
            >= self._get_severity_level(self.config.alert_threshold.value)
        ]

        if critical_issues:
            logger.warning(f"Found {len(critical_issues)} critical issues")

            # Send notifications
            if self.config.slack_webhook:
                await self._send_slack_alert(critical_issues)

            if self.config.email_alerts:
                await self._send_email_alert(critical_issues)

    def _get_severity_level(self, severity: str) -> int:
        """Convert severity string to numeric level"""
        levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return levels.get(severity.upper(), 0)

    async def _send_slack_alert(self, issues: List[Dict[str, Any]]):
        """Send alert to Slack"""
        # TODO: Implement Slack webhook integration
        logger.info(f"Would send Slack alert for {len(issues)} issues")

    async def _send_email_alert(self, issues: List[Dict[str, Any]]):
        """Send alert via email"""
        # TODO: Implement email alert
        logger.info(f"Would send email alert for {len(issues)} issues")

    async def monitor_logs_realtime(self):
        """Monitor logs in real-time and analyze anomalies"""
        if not self.config.realtime_logs:
            logger.info("Real-time log monitoring is disabled")
            return

        logger.info("Starting real-time log monitoring...")

        # TODO: Implement real-time log monitoring with file watchers
        # This would use watchdog or similar to monitor log files
        # and trigger analysis when patterns are detected
        pass


# Convenience function for quick audits
async def run_audit(audit_type: str = "full", config: AuditConfig = None) -> Dict[str, Any]:
    """
    Convenience function to run an audit

    Args:
        audit_type: Type of audit (full, codebase, data, logs, calculations)
        config: Optional audit configuration

    Returns:
        Audit results
    """
    orchestrator = AuditOrchestrator(config)

    if audit_type == "full":
        return await orchestrator.run_full_audit()
    else:
        return await orchestrator.run_targeted_audit(audit_type)
