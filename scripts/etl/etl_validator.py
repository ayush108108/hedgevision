#!/usr/bin/env python3
"""
ETL Validation & Backup Management

Validates ETL pipeline results and manages backup data decisions.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from scripts.etl.etl_runner import ETLRunner


@dataclass
class ValidationResult:
    """Validation result with metrics and recommendations."""
    metric_name: str
    before_value: Any
    after_value: Any
    status: str  # 'improved', 'degraded', 'unchanged'
    recommendation: str


class ETLValidator(ETLRunner):
    """Validates ETL results and manages backup decisions."""

    def __init__(self, dry_run: bool = False):
        super().__init__("validator", dry_run)

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Get comprehensive data quality metrics."""
        sql = """
        SELECT
            'total_rows' as metric,
            COUNT(*) as value
        FROM public.price_history

        UNION ALL

        SELECT
            'suspect_rows' as metric,
            COUNT(*) as value
        FROM public.price_history
        WHERE is_suspect = true

        UNION ALL

        SELECT
            'clean_rows' as metric,
            COUNT(*) as value
        FROM public.price_history
        WHERE is_suspect IS DISTINCT FROM true

        UNION ALL

        SELECT
            'backup_rows' as metric,
            COUNT(*) as value
        FROM public.price_history_backup

        UNION ALL

        SELECT
            'assets_affected' as metric,
            COUNT(DISTINCT asset_id) as value
        FROM public.price_history
        WHERE is_suspect = true

        UNION ALL

        SELECT
            'avg_price_change_pct' as metric,
            AVG(ABS((close - LAG(close) OVER (PARTITION BY asset_id ORDER BY timestamp)) /
                    NULLIF(LAG(close) OVER (PARTITION BY asset_id ORDER BY timestamp), 0))) * 100 as value
        FROM public.price_history
        WHERE is_suspect IS DISTINCT FROM true

        UNION ALL

        SELECT
            'data_completeness' as metric,
            (COUNT(*) * 1.0 / (SELECT COUNT(*) FROM public.price_history)) * 100 as value
        FROM public.price_history
        WHERE close IS NOT NULL AND close > 0
        """
        results = self.execute_sql(sql)
        return {row['metric']: row['value'] for row in results}

    def validate_etl_results(self) -> List[ValidationResult]:
        """Validate ETL pipeline results with before/after comparison."""
        # Get current metrics
        current_metrics = self.get_data_quality_metrics()

        # Get backup metrics (represents "before" state)
        backup_sql = """
        SELECT
            'backup_total_rows' as metric,
            COUNT(*) as value
        FROM public.price_history_backup

        UNION ALL

        SELECT
            'backup_avg_price_change' as metric,
            AVG(ABS((close - LAG(close) OVER (PARTITION BY asset_id ORDER BY timestamp)) /
                    NULLIF(LAG(close) OVER (PARTITION BY asset_id ORDER BY timestamp), 0))) * 100 as value
        FROM public.price_history_backup
        """
        backup_results = self.execute_sql(backup_sql)
        backup_metrics = {row['metric']: row['value'] for row in backup_results}

        validations = []

        # Validate suspect row removal
        suspect_pct = (current_metrics.get('suspect_rows', 0) / max(current_metrics.get('total_rows', 1), 1)) * 100
        if suspect_pct < 5:
            status = 'improved'
            rec = "✅ Low suspect percentage - data cleaning successful"
        elif suspect_pct < 15:
            status = 'improved'
            rec = "⚠️ Moderate suspect percentage - review flagged data"
        else:
            status = 'degraded'
            rec = "❌ High suspect percentage - investigate flagging logic"

        validations.append(ValidationResult(
            'suspect_percentage', None, suspect_pct, status, rec
        ))

        # Validate data completeness
        completeness = current_metrics.get('data_completeness', 0)
        if completeness > 95:
            status = 'improved'
            rec = "✅ High data completeness maintained"
        elif completeness > 85:
            status = 'unchanged'
            rec = "⚠️ Moderate data completeness - some gaps remain"
        else:
            status = 'degraded'
            rec = "❌ Low data completeness - significant data loss"

        validations.append(ValidationResult(
            'data_completeness', None, completeness, status, rec
        ))

        # Validate price stability
        avg_change = current_metrics.get('avg_price_change_pct', 0)
        backup_change = backup_metrics.get('backup_avg_price_change', 0)

        if avg_change < backup_change * 0.8:
            status = 'improved'
            rec = "✅ Price volatility reduced - cleaning effective"
        elif avg_change > backup_change * 1.5:
            status = 'degraded'
            rec = "❌ Price volatility increased - review interpolation"
        else:
            status = 'unchanged'
            rec = "➡️ Price volatility stable"

        validations.append(ValidationResult(
            'price_volatility', backup_change, avg_change, status, rec
        ))

        return validations

    def get_backup_management_options(self) -> Dict[str, str]:
        """Get backup management recommendations."""
        metrics = self.get_data_quality_metrics()
        validations = self.validate_etl_results()

        suspect_rows = metrics.get('suspect_rows', 0)
        backup_rows = metrics.get('backup_rows', 0)
        total_rows = metrics.get('total_rows', 1)

        # Analyze validation results
        critical_issues = [v for v in validations if v.status == 'degraded']
        has_improvements = any(v.status == 'improved' for v in validations)

        options = {}

        if critical_issues:
            options['restore'] = "🔄 RESTORE: Critical data quality issues detected - restore from backup"
            options['investigate'] = "🔍 INVESTIGATE: Review flagging logic before proceeding"
        elif has_improvements and suspect_rows < total_rows * 0.1:
            options['archive'] = "📦 ARCHIVE: Data cleaning successful - archive backup for 90 days"
            options['delete'] = "🗑️ DELETE: High confidence in results - delete backup (irreversible)"
        else:
            options['keep'] = "💾 KEEP: Moderate confidence - retain backup for recovery"
            options['review'] = "👀 REVIEW: Manual inspection recommended before decisions"

        return options

    def execute_backup_action(self, action: str) -> bool:
        """Execute backup management action."""
        actions = {
            'archive': self._archive_backup,
            'delete': self._delete_backup,
            'restore': self._restore_backup,
            'keep': self._keep_backup
        }

        if action not in actions:
            print(f"❌ Unknown action: {action}")
            return False

        return actions[action]()

    def _archive_backup(self) -> bool:
        """Archive backup table (rename with timestamp)."""
        import time
        timestamp = int(time.time())

        sql = f"""
        ALTER TABLE public.price_history_backup
        RENAME TO price_history_backup_archived_{timestamp};
        """
        self.execute_sql(sql)
        print(f"✓ Backup archived as price_history_backup_archived_{timestamp}")
        return True

    def _delete_backup(self) -> bool:
        """Delete backup table (irreversible)."""
        confirm = input("⚠️  WARNING: This will permanently delete the backup table. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Backup deletion cancelled")
            return False

        sql = "DROP TABLE IF EXISTS public.price_history_backup;"
        self.execute_sql(sql)
        print("✓ Backup table deleted permanently")
        return True

    def _restore_backup(self) -> bool:
        """Restore data from backup."""
        print("🔄 Restoring data from backup...")

        # Reset suspect flags
        sql_reset = "UPDATE public.price_history SET is_suspect = false;"
        self.execute_sql(sql_reset)

        # Restore from backup (this would be complex - need to handle conflicts)
        print("⚠️  Restore operation requires manual intervention")
        print("   Please review backup data and manually restore as needed")
        return False

    def _keep_backup(self) -> bool:
        """Keep backup as-is."""
        print("✓ Backup retained for future recovery")
        return True

    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report."""
        metrics = self.get_data_quality_metrics()
        validations = self.validate_etl_results()
        backup_options = self.get_backup_management_options()

        report = []
        report.append("==========================================")
        report.append("     ETL VALIDATION REPORT")
        report.append("==========================================")
        report.append("")

        # Data Quality Metrics
        report.append("📊 DATA QUALITY METRICS:")
        report.append(f"   Total Rows: {metrics.get('total_rows', 0):,}")
        report.append(f"   Clean Rows: {metrics.get('clean_rows', 0):,}")
        report.append(f"   Suspect Rows: {metrics.get('suspect_rows', 0):,}")
        report.append(f"   Backup Rows: {metrics.get('backup_rows', 0):,}")
        report.append(f"   Assets Affected: {metrics.get('assets_affected', 0)}")
        report.append(f"   Avg Price Change: {metrics.get('avg_price_change_pct', 0):.2f}%")
        report.append(f"   Data Completeness: {metrics.get('data_completeness', 0):.1f}%")
        report.append("")

        # Validation Results
        report.append("🔍 VALIDATION RESULTS:")
        for validation in validations:
            status_icon = {'improved': '✅', 'degraded': '❌', 'unchanged': '➡️'}[validation.status]
            report.append(f"   {status_icon} {validation.metric_name}: {validation.recommendation}")
        report.append("")

        # Backup Management Options
        report.append("💾 BACKUP MANAGEMENT OPTIONS:")
        for action, description in backup_options.items():
            report.append(f"   {action.upper()}: {description}")
        report.append("")

        # Recommendations
        critical_issues = [v for v in validations if v.status == 'degraded']
        if critical_issues:
            report.append("🚨 CRITICAL ISSUES DETECTED:")
            report.append("   • Review suspect data flagging logic")
            report.append("   • Consider restoring from backup")
            report.append("   • Investigate data quality degradation")
        else:
            report.append("✅ VALIDATION PASSED:")
            report.append("   • Data cleaning completed successfully")
            report.append("   • Analytics views are ready for use")
            report.append("   • Proceed with backup management decision")

        return "\n".join(report)


def main():
    """CLI interface for ETL validation."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Validation & Backup Management")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--report", action="store_true", help="Generate validation report")
    parser.add_argument("--backup-action", choices=['archive', 'delete', 'restore', 'keep'],
                       help="Execute backup management action")

    args = parser.parse_args()

    validator = ETLValidator(dry_run=args.dry_run)

    if args.report:
        report = validator.generate_validation_report()
        print(report)
        return

    if args.backup_action:
        success = validator.execute_backup_action(args.backup_action)
        if success:
            print(f"✓ Backup action '{args.backup_action}' completed")
        else:
            print(f"✗ Backup action '{args.backup_action}' failed")
        return

    # Default: Show validation summary
    validations = validator.validate_etl_results()
    backup_options = validator.get_backup_management_options()

    print("🔍 ETL Validation Summary:")
    print("")

    for validation in validations:
        status_icon = {'improved': '✅', 'degraded': '❌', 'unchanged': '➡️'}[validation.status]
        print(f"   {status_icon} {validation.metric_name}: {validation.recommendation}")

    print("")
    print("💾 Backup Management Options:")
    for action, description in backup_options.items():
        print(f"   {action.upper()}: {description}")

    print("")
    print("Use --report for detailed validation report")
    print("Use --backup-action <action> to manage backup data")


if __name__ == "__main__":
    main()