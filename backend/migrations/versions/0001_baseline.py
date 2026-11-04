"""Baseline: the law-firm schema as it stood before migrations were introduced.

A database that already has these tables should be marked with
`alembic stamp 0001`, not upgraded from nothing.

Revision ID: 0001
Revises:
"""
from pathlib import Path

from migrations.helpers import run_sql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0001_baseline.sql"


def upgrade() -> None:
    run_sql(SQL_FILE.read_text())


def downgrade() -> None:
    run_sql("""
        DROP VIEW IF EXISTS active_matters_view, locality_caseload_view, monthly_matter_stats,
            lawyer_performance_view, opposing_party_profile_view CASCADE;
        DROP TABLE IF EXISTS case_status_audit, evidence, statute_section, matter_type, case_lawyer,
            case_client, case_opposing_party, client_phone_no, opposing_party_phone_no, legal_case,
            court, client, opposing_party, lawyer, practice_group, location, pincode_area, users CASCADE;
        DROP FUNCTION IF EXISTS assign_lawyer_to_case(integer, integer, character varying, date);
        DROP FUNCTION IF EXISTS dispose_case(integer, integer);
        DROP FUNCTION IF EXISTS practice_group_report(integer);
        DROP FUNCTION IF EXISTS get_complete_case_details(integer);
        DROP FUNCTION IF EXISTS get_opposing_party_history(integer);
        DROP FUNCTION IF EXISTS search_cases(date, date, character varying, character varying);
        DROP FUNCTION IF EXISTS log_case_status_change();
        DROP FUNCTION IF EXISTS advance_case_on_evidence();
        DROP FUNCTION IF EXISTS mark_repeat_opposing_party();
        DROP FUNCTION IF EXISTS validate_legal_case_dates();
        DROP FUNCTION IF EXISTS validate_evidence_date();
    """)
