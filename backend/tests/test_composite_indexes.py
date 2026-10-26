"""Test composite indexes on high-frequency query columns (P3-2)."""
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain import Base, DiscoveredEndpoint, AuditLog, TestRun, TestResult

TestRun.__test__ = False
TestResult.__test__ = False


def test_domain_models_declare_composite_indexes():
    """Verify composite indexes are declared in SQLAlchemy metadata for domain models."""
    models_and_expected_indexes = {
        TestResult: ("idx_test_results_run_outcome", ["test_run_id", "outcome"]),
        TestRun: ("idx_test_runs_project_created", ["project_id", "created_at"]),
        DiscoveredEndpoint: ("idx_discovered_endpoints_analysis_method", ["analysis_id", "method"]),
        AuditLog: ("idx_audit_logs_action_created", ["action", "created_at"]),
    }

    for model, (idx_name, expected_cols) in models_and_expected_indexes.items():
        table = model.__table__
        matching_indexes = [idx for idx in table.indexes if idx.name == idx_name]
        assert len(matching_indexes) == 1, f"Expected index {idx_name} on {table.name}, found none"
        
        idx = matching_indexes[0]
        actual_cols = [c.name for c in idx.columns]
        assert actual_cols == expected_cols, f"Index {idx_name} columns mismatch: {actual_cols} != {expected_cols}"


@pytest.mark.asyncio
async def test_composite_indexes_exist_in_db(db_session: AsyncSession):
    """Verify that composite indexes can be inspected from the active database engine."""
    expected_indexes = {
        "test_results": "idx_test_results_run_outcome",
        "test_runs": "idx_test_runs_project_created",
        "discovered_endpoints": "idx_discovered_endpoints_analysis_method",
        "audit_logs": "idx_audit_logs_action_created",
    }

    def _inspect_indexes(connection):
        insp = inspect(connection)
        found = {}
        for table_name in expected_indexes.keys():
            indexes = insp.get_indexes(table_name)
            found[table_name] = [i["name"] for i in indexes]
        return found

    conn = await db_session.connection()
    found_indexes = await conn.run_sync(_inspect_indexes)

    for table_name, expected_idx in expected_indexes.items():
        assert expected_idx in found_indexes.get(table_name, []), (
            f"Index {expected_idx} missing from database table {table_name}. Found: {found_indexes.get(table_name)}"
        )
