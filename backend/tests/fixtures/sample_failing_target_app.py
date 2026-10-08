"""
ASTRA Phase 6 Golden Target Application Fixture
Emits 10+ failure endpoints covering all Phase 6 taxonomic failure categories and evidence parsers.
"""

import time
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse

sample_failing_app = FastAPI(title="Phase 6 Golden Target App")


@sample_failing_app.get("/health")
def health():
    return {"status": "ok", "service": "golden_fixture"}


@sample_failing_app.get("/crash")
def server_crash():
    # Intentionally raises Python ZeroDivisionError for server crash trace parsing
    result = 1 / 0
    return {"result": result}


@sample_failing_app.post("/business-rule")
def business_rule_rejection(payload: dict):
    if payload.get("amount", 0) > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction limit exceeded: max allowed is $1000",
        )
    return {"status": "approved"}


@sample_failing_app.get("/schema-error")
def schema_error():
    # Intentionally omits 'total_amount' key to trigger JSONPath schema diff isolator
    return {"status": "success", "items": ["item1", "item2"]}


@sample_failing_app.get("/auth-required")
def auth_required():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid Authorization bearer token",
    )


@sample_failing_app.get("/forbidden")
def forbidden_access():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient role permissions: admin required",
    )


@sample_failing_app.get("/slow")
def slow_performance():
    time.sleep(1.5)
    return {"status": "completed", "duration_ms": 1500}


@sample_failing_app.get("/not-found-resource")
def missing_resource():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Requested order entity ID #9999 not found",
    )


@sample_failing_app.get("/db-error")
def database_error():
    # Simulates SQL unique constraint error with SQLSTATE 23505
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail='ERROR: duplicate key value violates unique constraint "users_email_key" (SQLSTATE 23505)',
    )


@sample_failing_app.get("/dependency-error")
def dependency_error():
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Downstream payment gateway unreachable",
    )
