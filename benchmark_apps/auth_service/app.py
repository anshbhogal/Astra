"""Auth Benchmark Microservice containing Injected Bugs BUG-AUTH-001 through BUG-AUTH-010."""

import asyncio
import sqlite3
import time
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from benchmark_apps.base_app import BenchmarkEnvironment, create_benchmark_app

app = create_benchmark_app("Benchmark Auth API", version="1.0.0")

# In-memory database setup
_db = sqlite3.connect(":memory:", check_same_thread=False)
_cursor = _db.cursor()
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password_hash TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'USER'
    )
""")
_cursor.execute("INSERT OR IGNORE INTO users (id, email, password_hash, full_name, role) VALUES (1, 'alice@example.com', 'hashed_pass_alice', 'Alice Smith', 'USER')")
_db.commit()

# Revoked token tracking
_revoked_tokens = {"revoked_refresh_token_uuid"}


def reset_auth_db():
    global _revoked_tokens
    _revoked_tokens = {"revoked_refresh_token_uuid"}
    _cursor.execute("DELETE FROM users WHERE id > 1")
    _db.commit()


@app.get("/api/v1/auth/health")
async def health():
    return {"status": "HEALTHY", "service": "auth"}


@app.post("/api/v1/auth/login")
async def login(request: Request):
    payload = await request.json()

    # BUG-AUTH-006: Missing required field email returns 500 KeyError instead of 422
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-006"):
        email = payload["email"]
    else:
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=422, detail="Field 'email' is required")

    password = payload.get("password", "")

    # BUG-AUTH-001: Backdoor password grants 200 OK
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-001") and password == "admin_override_2026":
        return {"status": 200, "authenticated": True, "token_type": "bearer", "access_token": "token_admin_override"}

    # Standard check
    _cursor.execute("SELECT id, email, role FROM users WHERE email = ?", (email,))
    row = _cursor.fetchone()
    if row and password == "ValidPassword123!":
        return {"status": 200, "authenticated": True, "access_token": f"jwt_token_for_{row[0]}", "role": row[2]}

    raise HTTPException(status_code=401, detail="Invalid email or password")


@app.get("/api/v1/auth/me")
async def get_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # BUG-AUTH-002: Malformed 'Authorization: Bearer ' crashes with unhandled 500
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-002"):
        parts = auth_header.split(" ")
        token = parts[1]  # Crashes if parts length < 2 or empty token
        if not token.strip():
            raise IndexError("list index out of range: token is empty")
    else:
        parts = auth_header.split(" ")
        if len(parts) != 2 or not parts[1].strip():
            raise HTTPException(status_code=401, detail="Invalid token header")
        token = parts[1]

    return {"status": 200, "user_id": 1, "email": "alice@example.com"}


@app.post("/api/v1/auth/register")
async def register(request: Request):
    payload = await request.json()
    email = payload.get("email", "")
    password = payload.get("password", "")
    full_name = payload.get("full_name", "")
    role = payload.get("role", "USER")

    # BUG-AUTH-003: Password length boundary accepts 7 chars (valid min is 8)
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-003"):
        if len(password) < 7:
            raise HTTPException(status_code=422, detail="Password too short")
    else:
        if len(password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # BUG-AUTH-005: Role escalation accepts ADMIN
    if not BenchmarkEnvironment.is_bug_active("BUG-AUTH-005"):
        if role != "USER":
            role = "USER"

    # BUG-AUTH-004: Duplicate email crashes with unhandled 500 instead of 409
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-004"):
        _cursor.execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (email, f"hash_{password}", full_name, role)
        )
        _db.commit()
    else:
        _cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if _cursor.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")
        _cursor.execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (email, f"hash_{password}", full_name, role)
        )
        _db.commit()

    return {"status": 201, "message": "User registered successfully", "role": role}


@app.post("/api/v1/auth/verify-token")
async def verify_token(request: Request):
    payload = await request.json()
    token = payload.get("token", "")

    # BUG-AUTH-007: Ignores expired claim
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-007") and "expired" in token:
        return {"status": 200, "valid": True}

    if "expired" in token:
        raise HTTPException(status_code=401, detail="Token expired")

    return {"status": 200, "valid": True}


@app.post("/api/v1/auth/refresh")
async def refresh_token(request: Request):
    payload = await request.json()
    refresh_token_val = payload.get("refresh_token", "")

    # BUG-AUTH-008: Revoked refresh token remains valid
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-008"):
        return {"status": 200, "access_token": "new_issued_token"}

    if refresh_token_val in _revoked_tokens:
        raise HTTPException(status_code=401, detail="Token revoked")

    return {"status": 200, "access_token": "new_issued_token"}


@app.get("/api/v1/auth/users/search")
async def search_users(q: str = ""):
    # BUG-AUTH-009: Unescaped SQL query string crash on quote
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-009"):
        raw_query = f"SELECT id, email, full_name FROM users WHERE email LIKE '{q}'"
        _cursor.execute(raw_query)
        rows = _cursor.fetchall()
        return {"status": 200, "results": rows}
    else:
        _cursor.execute("SELECT id, email, full_name FROM users WHERE email LIKE ?", (f"%{q}%",))
        rows = _cursor.fetchall()
        return {"status": 200, "results": rows}


@app.post("/api/v1/auth/verify-hash")
async def verify_hash(request: Request):
    payload = await request.json()

    # BUG-AUTH-010: Simulated SLA hang (sleeps 4.5s)
    if BenchmarkEnvironment.is_bug_active("BUG-AUTH-010"):
        await asyncio.sleep(4.5)

    return {"status": 200, "verified": True}
