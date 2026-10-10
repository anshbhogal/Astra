"""Banking Benchmark Microservice containing Injected Bugs BUG-BANK-001 through BUG-BANK-013."""

from decimal import Decimal
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response

from benchmark_apps.base_app import BenchmarkEnvironment, create_benchmark_app

app = create_benchmark_app("Benchmark Banking API", version="1.0.0")

# In-memory database setup
_db = sqlite3.connect(":memory:", check_same_thread=False)
_cursor = _db.cursor()
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        holder_name TEXT,
        balance REAL,
        status TEXT DEFAULT 'ACTIVE',
        daily_withdrawn REAL DEFAULT 0.0
    )
""")
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS transfers (
        id TEXT PRIMARY KEY,
        from_account TEXT,
        to_account TEXT,
        amount REAL,
        status TEXT
    )
""")

# Seed initial accounts
_cursor.execute("INSERT OR REPLACE INTO accounts VALUES ('acc_1', 'Alice Banking', 1000.0, 'ACTIVE', 0.0)")
_cursor.execute("INSERT OR REPLACE INTO accounts VALUES ('acc_2', 'Bob Banking', 500.0, 'ACTIVE', 0.0)")
_cursor.execute("INSERT OR REPLACE INTO accounts VALUES ('acc_frozen', 'Charlie Frozen', 1000.0, 'FROZEN', 0.0)")
_cursor.execute("INSERT OR REPLACE INTO accounts VALUES ('acc_a', 'Account Alpha', 500.0, 'ACTIVE', 0.0)")
_cursor.execute("INSERT OR REPLACE INTO accounts VALUES ('acc_b', 'Account Beta', 100.0, 'ACTIVE', 0.0)")
_db.commit()


def reset_banking_db():
    _cursor.execute("UPDATE accounts SET balance = 1000.0, status = 'ACTIVE', daily_withdrawn = 0.0 WHERE id = 'acc_1'")
    _cursor.execute("UPDATE accounts SET balance = 500.0, status = 'ACTIVE', daily_withdrawn = 0.0 WHERE id = 'acc_2'")
    _cursor.execute("UPDATE accounts SET balance = 1000.0, status = 'FROZEN', daily_withdrawn = 0.0 WHERE id = 'acc_frozen'")
    _cursor.execute("UPDATE accounts SET balance = 500.0, status = 'ACTIVE', daily_withdrawn = 0.0 WHERE id = 'acc_a'")
    _cursor.execute("UPDATE accounts SET balance = 100.0, status = 'ACTIVE', daily_withdrawn = 0.0 WHERE id = 'acc_b'")
    _cursor.execute("DELETE FROM transfers")
    _db.commit()


@app.get("/api/v1/banking/health")
async def health():
    return {"status": "HEALTHY", "service": "banking"}


@app.get("/api/v1/accounts")
async def list_accounts():
    _cursor.execute("SELECT id, holder_name, balance, status FROM accounts")
    rows = _cursor.fetchall()
    return [{"id": r[0], "holder_name": r[1], "balance": r[2], "status": r[3]} for r in rows]


@app.get("/api/v1/accounts/{account_id}/balance")
async def get_balance(account_id: str):
    _cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    row = _cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": 200, "account_id": account_id, "balance": row[0]}


@app.post("/api/v1/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    payload = await request.json()
    amount = payload.get("amount", 0.0)

    _cursor.execute("SELECT balance, status, daily_withdrawn FROM accounts WHERE id = ?", (account_id,))
    row = _cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")

    balance, status_val, daily_withdrawn = row[0], row[1], row[2]

    # BUG-BANK-007: Frozen account can still withdraw
    if not BenchmarkEnvironment.is_bug_active("BUG-BANK-007") and status_val == "FROZEN":
        raise HTTPException(status_code=403, detail="Account is frozen")

    # BUG-BANK-009: Daily withdrawal limit $1,000 bypassed under concurrent/multiple calls
    if not BenchmarkEnvironment.is_bug_active("BUG-BANK-009"):
        if daily_withdrawn + amount > 1000.0:
            raise HTTPException(status_code=400, detail="Daily withdrawal limit exceeded")

    # BUG-BANK-006: Insufficient funds returns HTTP 200 OK with {"error": "insufficient funds"}
    if amount > balance:
        if BenchmarkEnvironment.is_bug_active("BUG-BANK-006") and balance == 50.0 and amount == 100.0:
            return {"status": 200, "error": "insufficient funds"}

    # BUG-BANK-001: Overdraft beyond limit sets balance negative
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-001"):
        new_balance = balance - amount
        _cursor.execute("UPDATE accounts SET balance = ?, daily_withdrawn = ? WHERE id = ?", (new_balance, daily_withdrawn + amount, account_id))
        _db.commit()
        return {"status": 200, "balance": new_balance, "withdrawn": amount, "total_withdrawn_today": daily_withdrawn + amount}
    else:
        if amount > balance:
            raise HTTPException(status_code=400, detail="Insufficient balance for withdrawal")
        new_balance = balance - amount
        _cursor.execute("UPDATE accounts SET balance = ?, daily_withdrawn = ? WHERE id = ?", (new_balance, daily_withdrawn + amount, account_id))
        _db.commit()
        return {"status": 200, "balance": new_balance, "withdrawn": amount, "total_withdrawn_today": daily_withdrawn + amount}


@app.post("/api/v1/accounts/{account_id}/deposit")
async def deposit(account_id: str, request: Request):
    payload = await request.json()
    amount = payload.get("amount", 0.0)

    # BUG-BANK-004: Negative deposit allowed
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-004"):
        _cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
        _db.commit()
        _cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        return {"status": 200, "balance": _cursor.fetchone()[0]}
    else:
        if amount <= 0.0:
            raise HTTPException(status_code=422, detail="Deposit amount must be positive")
        _cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
        _db.commit()
        _cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        return {"status": 200, "balance": _cursor.fetchone()[0]}


@app.post("/api/v1/transfers")
async def transfer_money(request: Request):
    payload = await request.json()
    from_acc = payload.get("from_account", "")
    to_acc = payload.get("to_account", "")
    amount = payload.get("amount", 0.0)

    # BUG-BANK-003: Self-transfer credits double balance
    if from_acc == to_acc:
        if BenchmarkEnvironment.is_bug_active("BUG-BANK-003"):
            _cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, from_acc))
            _db.commit()
            _cursor.execute("SELECT balance FROM accounts WHERE id = ?", (from_acc,))
            return {"status": 200, "balance": _cursor.fetchone()[0]}
        else:
            raise HTTPException(status_code=400, detail="Cannot transfer to same account")

    # BUG-BANK-002: Transfer Account A -> B debits A, crashes before crediting B (money disappears)
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-002") and to_acc == "acc_b_crash":
        _cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_acc))
        _db.commit()
        # Simulated crash before credit
        return Response(
            content='{"status": 500, "error": "CrashBeforeCredit", "acc_a_debited": 200.0, "acc_b_credited": 0.0}',
            status_code=500,
            media_type="application/json"
        )

    # Standard clean transfer
    _cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_acc))
    _cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_acc))
    _db.commit()
    return {"status": 200, "transferred": amount}


@app.post("/api/v1/accounts/{account_id}/interest")
async def calculate_interest(account_id: str, request: Request):
    payload = await request.json()
    add_amount = payload.get("add_amount", 0.0)

    _cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    row = _cursor.fetchone()
    base_balance = row[0] if row else 0.0

    # BUG-BANK-005: Compounding using float instead of Decimal loses precision ($0.1 + $0.2 != $0.3)
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-005"):
        total = base_balance + add_amount  # produces 0.30000000000000004
        return {"status": 200, "total": total}
    else:
        dec_total = Decimal(str(base_balance)) + Decimal(str(add_amount))
        return {"status": 200, "total": str(dec_total.quantize(Decimal("0.01")))}


@app.post("/api/v1/loans/apply")
async def apply_loan(request: Request):
    payload = await request.json()
    rate = payload.get("interest_rate", 0.05)

    # BUG-BANK-008: Negative interest rate credits money to borrower
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-008") and rate < 0:
        return {"status": 200, "monthly_payment": -750.0}

    if rate <= 0:
        raise HTTPException(status_code=422, detail="Interest rate must be positive")

    return {"status": 200, "monthly_payment": 850.0}


@app.post("/api/v1/transfers/validate-routing")
async def validate_routing(request: Request):
    payload = await request.json()
    routing = payload.get("routing_number", "")

    # BUG-BANK-010: 8-digit invalid routing crashes with unhandled 500 AssertionError
    if len(routing) != 9:
        if BenchmarkEnvironment.is_bug_active("BUG-BANK-010"):
            assert len(routing) == 9, "Invalid ABA routing string"
        else:
            raise HTTPException(status_code=400, detail="Routing number must be exactly 9 digits")

    return {"status": 200, "valid": True}


@app.post("/api/v1/fx/convert")
async def fx_convert(request: Request):
    payload = await request.json()
    amount = payload.get("amount", 100.0)
    from_curr = payload.get("from_currency", "USD")
    to_curr = payload.get("to_currency", "EUR")

    # BUG-BANK-011: USD to EUR divides instead of multiplies
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-011") and from_curr == "USD" and to_curr == "EUR":
        return {"status": 200, "converted": 108.69}

    return {"status": 200, "converted": amount * 0.92}


@app.get("/api/v1/statements/download")
async def download_statement(file: str = "statement_2026.pdf"):
    # BUG-BANK-012: Path traversal allowed
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-012") and ".." in file:
        return {"status": 200, "content": "root:x:0:0:root:..."}

    if ".." in file:
        raise HTTPException(status_code=400, detail="Invalid statement filename or path traversal detected")

    return {"status": 200, "filename": file, "content": "PDF_BYTES_MOCK"}


@app.post("/api/v1/accounts/{account_id}/deposit-audited")
async def deposit_audited(account_id: str, request: Request):
    payload = await request.json()
    amount = payload.get("amount", 100.0)

    # BUG-BANK-013: Audit log failure rolls back legitimate deposit
    if BenchmarkEnvironment.is_bug_active("BUG-BANK-013"):
        raise HTTPException(status_code=500, detail="AuditLogWriteError: Failed to write audit log")

    return {"status": 200, "detail": "Deposit succeeded; audit logged asynchronously"}
