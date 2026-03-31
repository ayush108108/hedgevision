"""
Report generation for AI audit framework
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from api.audit.config import AuditConfig

logger = logging.getLogger(__name__)


class AuditReporter:
    """Generates and saves audit reports"""

    def __init__(self, config: AuditConfig):
        self.config = config
        self._ensure_reports_directory()

    def _ensure_reports_directory(self):
        """Ensure the reports directory exists"""
        Path(self.config.audit_reports_dir).mkdir(parents=True, exist_ok=True)

    async def generate_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive audit report

        Args:
            results: Analysis results from all audit types

        Returns:
            Formatted report dictionary
        """
        report = {
            "metadata": {
                "timestamp": results.get("timestamp", datetime.utcnow().isoformat()),
                "trace_id": results.get("trace_id", "unknown"),
                "audit_version": "1.0.0",
                "config": {
                    "primary_provider": self.config.primary_provider.value,
                    "fallback_provider": (
                        self.config.fallback_provider.value
                        if self.config.fallback_provider
                        else None
                    ),
                    "data_sampling_rate": self.config.data_sampling_rate,
                },
            },
            "summary": self._generate_summary(results),
            "detailed_results": results,
            "recommendations": self._extract_recommendations(results),
            "critical_issues": self._extract_critical_issues(results),
        }

        # Include collection errors if present
        if "collection_errors" in results:
            report["collection_errors"] = results["collection_errors"]

        return report

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        total_issues = 0
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for analysis_type, analysis_result in results.items():
            if analysis_type == "timestamp":
                continue

            issues = analysis_result.get("issues", [])
            total_issues += len(issues)

            for issue in issues:
                severity = issue.get("severity", "LOW").upper()
                if severity in severity_counts:
                    severity_counts[severity] += 1

        return {
            "total_issues_found": total_issues,
            "severity_breakdown": severity_counts,
            "overall_health": self._calculate_health_score(severity_counts),
            "areas_analyzed": [
                k for k in results.keys() if k != "timestamp"
            ],
        }

    def _calculate_health_score(self, severity_counts: Dict[str, int]) -> str:
        """Calculate overall health score"""
        score = 100
        score -= severity_counts["CRITICAL"] * 25
        score -= severity_counts["HIGH"] * 10
        score -= severity_counts["MEDIUM"] * 5
        score -= severity_counts["LOW"] * 1

        score = max(0, score)

        if score >= 90:
            return "EXCELLENT"
        elif score >= 75:
            return "GOOD"
        elif score >= 50:
            return "FAIR"
        elif score >= 25:
            return "POOR"
        else:
            return "CRITICAL"

    def _extract_recommendations(self, results: Dict[str, Any]) -> list:
        """Extract all recommendations"""
        recommendations = []

        for analysis_type, analysis_result in results.items():
            if analysis_type == "timestamp":
                continue

            recs = analysis_result.get("recommendations", [])
            for rec in recs:
                recommendations.append(
                    {"source": analysis_type, "recommendation": rec}
                )

        return recommendations

    def _extract_critical_issues(self, results: Dict[str, Any]) -> list:
        """Extract critical and high severity issues"""
        critical_issues = []

        for analysis_type, analysis_result in results.items():
            if analysis_type == "timestamp":
                continue

            issues = analysis_result.get("issues", [])
            for issue in issues:
                severity = issue.get("severity", "LOW").upper()
                if severity in ["CRITICAL", "HIGH"]:
                    critical_issues.append(
                        {
                            "source": analysis_type,
                            "severity": severity,
                            "description": issue.get("description"),
                        }
                    )

        return critical_issues

    async def save_report(self, report: Dict[str, Any]) -> str:
        """
        Save report to disk in configured formats

        Returns:
            Path to saved report(s)
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        saved_files = []

        for format_type in self.config.report_formats:
            if format_type == "json":
                file_path = await self._save_json_report(report, timestamp)
                saved_files.append(file_path)
            elif format_type == "markdown":
                file_path = await self._save_markdown_report(report, timestamp)
                saved_files.append(file_path)

        report["file_path"] = saved_files[0] if saved_files else None
        logger.info(f"Saved audit report to: {saved_files}")

        return saved_files[0] if saved_files else None

    async def _save_json_report(self, report: Dict[str, Any], timestamp: str) -> str:
        """Save report as JSON"""
        file_path = Path(self.config.audit_reports_dir) / f"audit_{timestamp}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        return str(file_path)

    async def _save_markdown_report(self, report: Dict[str, Any], timestamp: str) -> str:
        """Save report as Markdown"""
        file_path = Path(self.config.audit_reports_dir) / f"audit_{timestamp}.md"

        markdown = self._format_markdown(report)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        return str(file_path)

    def _format_markdown(self, report: Dict[str, Any]) -> str:
        """Format report as Markdown"""
        summary = report["summary"]
        metadata = report["metadata"]

        md = f"""# HedgeVision AI Audit Report

**Generated:** {metadata["timestamp"]}  
**Trace ID:** {metadata.get("trace_id", "unknown")}  
**Audit Version:** {metadata["audit_version"]}  
**Primary Provider:** {metadata["config"]["primary_provider"]}  
**Data Sampling Rate:** {metadata["config"]["data_sampling_rate"] * 100}%

---

## Executive Summary

- **Overall Health:** {summary["overall_health"]}
- **Total Issues Found:** {summary["total_issues_found"]}
- **Areas Analyzed:** {", ".join(summary["areas_analyzed"])}

### Severity Breakdown
- 🔴 **CRITICAL:** {summary["severity_breakdown"]["CRITICAL"]}
- 🟠 **HIGH:** {summary["severity_breakdown"]["HIGH"]}
- 🟡 **MEDIUM:** {summary["severity_breakdown"]["MEDIUM"]}
- 🟢 **LOW:** {summary["severity_breakdown"]["LOW"]}

---

## Critical Issues

"""

        critical_issues = report.get("critical_issues", [])
        if critical_issues:
            for i, issue in enumerate(critical_issues, 1):
                md += f"""
### {i}. [{issue["severity"]}] {issue["source"]}
{issue["description"]}

"""
        else:
            md += "✅ No critical issues found.\n\n"

        # Add collection errors section if present
        collection_errors = report.get("collection_errors", [])
        if collection_errors:
            md += """
---

## Collection Errors

The following errors occurred during data collection:

"""
            for i, error in enumerate(collection_errors, 1):
                md += f"{i}. {error}\n"
            md += "\n*Note: These errors may affect the completeness of the audit analysis.*\n\n"

        md += """
---

## Recommendations

"""

        recommendations = report.get("recommendations", [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                md += f"{i}. **{rec['source']}**: {rec['recommendation']}\n"
        else:
            md += "No specific recommendations at this time.\n"

        md += """
---

## Detailed Analysis

For detailed analysis results, refer to the JSON report.

---

*This report was generated automatically by the HedgeVision AI Audit Framework*
"""

        return md
