#!/usr/bin/env python3
"""
ETL Orchestrator

Runs all ETL phases in sequence with dependency management.
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from scripts.etl.etl_runner import ETLRunner


class ETLOrcestrator(ETLRunner):
    """Orchestrates all ETL phases."""

    def __init__(self, dry_run: bool = False):
        super().__init__("orchestrator", dry_run)
        self.phases = [
            "setup_flag",
            "backup",
            "clean_view",
            "fix"
        ]

    def run_phase(self, phase_name: str) -> bool:
        """Run a specific ETL phase."""
        try:
            if phase_name == "setup_flag":
                from scripts.etl.etl_phase1_setup_flag import SetupFlagETL
                etl = SetupFlagETL(self.dry_run)
            elif phase_name == "backup":
                from scripts.etl.etl_phase2_backup import BackupETL
                etl = BackupETL(self.dry_run)
            elif phase_name == "clean_view":
                from scripts.etl.etl_phase3_clean_view import CleanViewETL
                etl = CleanViewETL(self.dry_run)
            elif phase_name == "fix":
                from scripts.etl.etl_phase4_fix import FixETL
                etl = FixETL(self.dry_run)
            else:
                raise ValueError(f"Unknown phase: {phase_name}")

            success = etl.run_phase()
            if success:
                self.log_etl_progress(1, 'completed', f'Phase {phase_name} completed')
            else:
                self.log_etl_progress(0, 'failed', f'Phase {phase_name} failed')
            return success

        except Exception as e:
            self.log_etl_progress(0, 'failed', f'Phase {phase_name} error: {e}')
            return False

    def run_all_phases(self) -> bool:
        """Run all ETL phases in sequence."""
        print("🚀 Starting ETL Pipeline")

        for phase in self.phases:
            print(f"\n📋 Running Phase: {phase}")
            success = self.run_phase(phase)
            if not success:
                print(f"❌ ETL Pipeline failed at phase: {phase}")
                return False

        print("\n✅ ETL Pipeline completed successfully")
        return True

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        sql = """
        SELECT
            phase,
            status,
            rows_affected,
            started_at,
            completed_at,
            error_message
        FROM etl.etl_log
        WHERE pipeline_run_id = (
            SELECT MAX(pipeline_run_id)
            FROM etl.etl_log
        )
        ORDER BY started_at;
        """

        try:
            results = self.execute_sql(sql)
            return {
                "phases": results,
                "total_phases": len(self.phases),
                "completed_phases": len([r for r in results if r['status'] == 'completed'])
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--phase", help="Run specific phase only")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")

    args = parser.parse_args()

    orchestrator = ETLOrcestrator(dry_run=args.dry_run)

    if args.status:
        status = orchestrator.get_pipeline_status()
        print("ETL Pipeline Status:")
        if "error" in status:
            print(f"Error: {status['error']}")
        else:
            for phase in status["phases"]:
                print(f"  {phase['phase']}: {phase['status']} ({phase['rows_affected']} rows)")
        return

    if args.phase:
        success = orchestrator.run_phase(args.phase)
        if success:
            print(f"✓ Phase {args.phase} completed successfully")
        else:
            print(f"✗ Phase {args.phase} failed")
        sys.exit(0 if success else 1)

    # Run full pipeline
    success = orchestrator.run_all_phases()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()