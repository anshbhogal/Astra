"""
ASTRA Engine - Phase 6 SQL & Database Error Log Parser
Parses SQLSTATE codes and database constraint errors into normalized ParsedException evidence.
"""

import re
from typing import Optional, List
from engine.analysis.models import ParsedException, StackFrame
from engine.analysis.parsers.base import BaseStackTraceParser


# SQLSTATE Code Mapping
SQLSTATE_MAPPING = {
    "23505": "UniqueConstraintViolation",
    "23503": "ForeignKeyViolation",
    "23502": "NotNullViolation",
    "23514": "CheckConstraintViolation",
    "40P01": "DeadlockDetected",
    "08006": "ConnectionFailure",
    "08001": "ConnectionFailure",
    "57014": "QueryTimeout",
    "42P01": "UndefinedTable",
    "42703": "UndefinedColumn",
}

SQL_MESSAGE_PATTERNS = [
    (re.compile(r'duplicate key value violates unique constraint\s+["\'](?P<constraint>[^"\']+)["\']', re.I), "UniqueConstraintViolation"),
    (re.compile(r'violates foreign key constraint\s+["\'](?P<constraint>[^"\']+)["\']', re.I), "ForeignKeyViolation"),
    (re.compile(r'null value in column\s+["\'](?P<col>[^"\']+)["\']\s+violates not-null constraint', re.I), "NotNullViolation"),
    (re.compile(r'deadlock detected', re.I), "DeadlockDetected"),
    (re.compile(r'could not connect to server|connection refused', re.I), "ConnectionFailure"),
    (re.compile(r'canceling statement due to statement timeout', re.I), "QueryTimeout"),
]

# Regex for SQLSTATE
SQLSTATE_REGEX = re.compile(r'(?:sqlstate|SQLSTATE|code|state)\s*[:=]?\s*["\']?(?P<code>[0-9A-Z]{5})["\']?', re.I)


class SqlErrorParser(BaseStackTraceParser):
    """Parses Database & SQL exception logs, giving primary precedence to SQLSTATE codes."""

    def parse(self, raw_trace: str) -> Optional[ParsedException]:
        if not raw_trace:
            return None

        sql_state = None
        exception_type = "DatabaseError"
        message = raw_trace.strip()

        # 1. Primary Check: Search for SQLSTATE code
        sqlstate_match = SQLSTATE_REGEX.search(raw_trace)
        if sqlstate_match:
            sql_state = sqlstate_match.group("code").upper()
            if sql_state in SQLSTATE_MAPPING:
                exception_type = SQLSTATE_MAPPING[sql_state]

        # 2. Secondary Check: Message pattern matching
        if exception_type == "DatabaseError":
            for pattern, exc_type in SQL_MESSAGE_PATTERNS:
                if pattern.search(raw_trace):
                    exception_type = exc_type
                    break

        if sql_state is None and exception_type == "DatabaseError" and not any(kw in raw_trace.lower() for kw in ["sql", "constraint", "database", "postgres", "mysql", "sqlite", "relation"]):
            return None

        return ParsedException(
            exception_type=exception_type,
            message=message,
            frames=[],
            language="sql",
            raw_trace_hash=self.compute_hash(raw_trace),
            sql_state=sql_state,
        )
