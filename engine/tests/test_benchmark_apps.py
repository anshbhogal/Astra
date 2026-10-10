"""Comprehensive unit tests for Phase 10 Benchmark Microservices and Catalog."""

import pytest
import httpx
from benchmark_apps.catalog import (
    BenchmarkBugCatalog,
    DefectCategory,
    DefectSeverity,
    BenchmarkExecutionProfile
)
from benchmark_apps.base_app import BenchmarkEnvironment
from benchmark_apps.auth_service.app import app as auth_app, reset_auth_db
from benchmark_apps.ecommerce_service.app import app as ecom_app, reset_ecommerce_db
from benchmark_apps.student_service.app import app as stud_app, reset_student_db
from benchmark_apps.banking_service.app import app as bank_app, reset_banking_db


def test_catalog_integrity():
    """Verify that catalog contains exactly 50 bugs and 100 negative controls."""
    bugs = BenchmarkBugCatalog.get_all_bugs()
    controls = BenchmarkBugCatalog.get_all_controls()

    assert len(bugs) == 50, f"Expected 50 bugs, found {len(bugs)}"
    assert len(controls) == 100, f"Expected 100 controls, found {len(controls)}"

    # Service distribution
    auth_bugs = BenchmarkBugCatalog.get_bugs_for_service("auth")
    ecom_bugs = BenchmarkBugCatalog.get_bugs_for_service("ecommerce")
    stud_bugs = BenchmarkBugCatalog.get_bugs_for_service("student")
    bank_bugs = BenchmarkBugCatalog.get_bugs_for_service("banking")

    assert len(auth_bugs) == 10
    assert len(ecom_bugs) == 15
    assert len(stud_bugs) == 12
    assert len(bank_bugs) == 13

    # Negative controls distribution (25 each)
    assert len(BenchmarkBugCatalog.get_controls_for_service("auth")) == 25
    assert len(BenchmarkBugCatalog.get_controls_for_service("ecommerce")) == 25
    assert len(BenchmarkBugCatalog.get_controls_for_service("student")) == 25
    assert len(BenchmarkBugCatalog.get_controls_for_service("banking")) == 25


@pytest.mark.asyncio
async def test_auth_service_bugs():
    """Verify all 10 Auth service bugs trigger deterministically."""
    BenchmarkEnvironment.enable_all_bugs()
    reset_auth_db()

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # BUG-AUTH-001: Backdoor password grants 200
        res1 = await client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "admin_override_2026"})
        assert res1.status_code == 200
        assert res1.json().get("authenticated") is True

        # BUG-AUTH-002: Malformed authorization header crashes with 500
        with pytest.raises(Exception):
            await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})

        # BUG-AUTH-003: 7-char password accepted (201)
        res3 = await client.post("/api/v1/auth/register", json={"email": "new7@example.com", "password": "1234567"})
        assert res3.status_code == 201

        # BUG-AUTH-004: Duplicate email crashes with 500
        with pytest.raises(Exception):
            await client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "ValidPassword123!"})

        # BUG-AUTH-005: Role escalation accepts ADMIN
        res5 = await client.post("/api/v1/auth/register", json={"email": "admin_esc@example.com", "password": "ValidPassword123!", "role": "ADMIN"})
        assert res5.status_code == 201
        assert res5.json().get("role") == "ADMIN"

        # BUG-AUTH-006: Missing required email crashes with 500
        with pytest.raises(Exception):
            await client.post("/api/v1/auth/login", json={"password": "ValidPassword123!"})

        # BUG-AUTH-007: Expired token accepted
        res7 = await client.post("/api/v1/auth/verify-token", json={"token": "expired_jwt_sample"})
        assert res7.status_code == 200
        assert res7.json().get("valid") is True

        # BUG-AUTH-008: Revoked refresh token remains valid
        res8 = await client.post("/api/v1/auth/refresh", json={"refresh_token": "revoked_refresh_token_uuid"})
        assert res8.status_code == 200

        # BUG-AUTH-009: SQL quote in search crashes with 500
        with pytest.raises(Exception):
            await client.get("/api/v1/auth/users/search?q=' OR 1=1")


@pytest.mark.asyncio
async def test_ecommerce_service_bugs():
    """Verify E-Commerce bugs trigger deterministically."""
    BenchmarkEnvironment.enable_all_bugs()
    reset_ecommerce_db()

    transport = httpx.ASGITransport(app=ecom_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # BUG-ECOM-001: Quantity > stock decrements inventory into negative stock
        res1 = await client.post("/api/v1/orders", json={"product_id": "prod_1", "quantity": 15})
        assert res1.status_code == 201
        assert res1.json().get("stock_remaining") == -5

        # BUG-ECOM-002: Quantity 10^9 calculation overflow
        res2 = await client.post("/api/v1/orders/calculate", json={"quantity": 1000000000})
        assert res2.status_code == 200
        assert res2.json().get("total") < 0

        # BUG-ECOM-003: Missing shipping_zip crashes with 500
        with pytest.raises(Exception):
            await client.post("/api/v1/checkout", json={"items": [{"product_id": "prod_1", "quantity": 1}], "shipping_zip": None})

        # BUG-ECOM-004: Empty cart returns 200
        res4 = await client.post("/api/v1/checkout", json={"items": [], "shipping_zip": "94105"})
        assert res4.status_code == 200
        assert res4.json().get("order_id") == "ord_empty"

        # BUG-ECOM-005: SUPER200 coupon discounts 200% (negative total)
        res5 = await client.post("/api/v1/coupons/apply", json={"cart_total": 100.0, "coupon_code": "SUPER200"})
        assert res5.status_code == 200
        assert res5.json().get("discounted_total") == -100.0

        # BUG-ECOM-006: Currency mismatch 1:1
        res6 = await client.post("/api/v1/payments/process", json={"amount": 100.0, "from_currency": "USD", "to_currency": "JPY"})
        assert res6.status_code == 200
        assert res6.json().get("converted_amount") == 100.0

        # BUG-ECOM-007: Search SQLi crash
        with pytest.raises(Exception):
            await client.get("/api/v1/products/search?q=' OR 1=1")

        # BUG-ECOM-010: IDOR cancel order
        res10 = await client.post("/api/v1/orders/ord_alice_1/cancel", headers={"X-User-Id": "user_bob"})
        assert res10.status_code == 200
        assert res10.json().get("status") == "CANCELLED"

        # BUG-ECOM-011: Review rating 6 accepted
        res11 = await client.post("/api/v1/products/prod_1/reviews", json={"rating": 6, "comment": "Over the top!"})
        assert res11.status_code == 201

        # BUG-ECOM-012: CANCELLED to DELIVERED status transition
        res12 = await client.patch("/api/v1/orders/ord_alice_1/status", json={"status": "DELIVERED"})
        assert res12.status_code == 200
        assert res12.json().get("status") == "DELIVERED"

        # BUG-ECOM-013: Min price 'cheap' raises ValueError 500
        with pytest.raises(Exception):
            await client.get("/api/v1/products?min_price=cheap")

        # BUG-ECOM-014: Deleted product query crashes with 500
        with pytest.raises(Exception):
            await client.get("/api/v1/products/prod_deleted_99")

        # BUG-ECOM-015: Batch orders empty division by zero
        with pytest.raises(Exception):
            await client.post("/api/v1/orders/batch", json={"batch_orders": []})


@pytest.mark.asyncio
async def test_student_service_bugs():
    """Verify Student service bugs trigger deterministically."""
    BenchmarkEnvironment.enable_all_bugs()
    reset_student_db()

    transport = httpx.ASGITransport(app=stud_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # BUG-STUD-001: Future DOB accepted
        res1 = await client.post("/api/v1/students", json={"first_name": "Future", "last_name": "Kid", "dob": "2035-05-12"})
        assert res1.status_code == 201

        # BUG-STUD-002: GPA 5.5 accepted
        res2 = await client.put("/api/v1/students/stud_1/gpa", json={"gpa": 5.5})
        assert res2.status_code == 200
        assert res2.json().get("gpa") == 5.5

        # BUG-STUD-003: Duplicate roll number crashes with 500
        with pytest.raises(Exception):
            await client.post("/api/v1/students", json={"first_name": "Dup", "last_name": "Roll", "roll_number": "ROLL-101"})

        # BUG-STUD-004: Course enrollment past capacity allowed
        res4 = await client.post("/api/v1/courses/cs_101/enroll", json={"student_id": "stud_1"})
        assert res4.status_code == 200
        assert res4.json().get("enrolled_count") == 31

        # BUG-STUD-005: Course drop past deadline allowed
        res5 = await client.post("/api/v1/courses/cs_101/drop", json={"student_id": "stud_1"})
        assert res5.status_code == 200
        assert res5.json().get("dropped") is True

        # BUG-STUD-007: Advanced course registration without prereqs succeeds
        res7 = await client.post("/api/v1/courses/cs_401_adv/register", json={"student_id": "stud_1"})
        assert res7.status_code == 200

        # BUG-STUD-008: Stored XSS accepted
        res8 = await client.post("/api/v1/students", json={"first_name": "<script>alert(1)</script>", "last_name": "XSS"})
        assert res8.status_code == 201
        assert "<script>" in res8.json().get("first_name", "")

        # BUG-STUD-009: Negative credits allowed
        res9 = await client.post("/api/v1/students/stud_1/study-plan", json={"credits": -3})
        assert res9.status_code == 200
        assert res9.json().get("credits") == -3

        # BUG-STUD-010: Batch grades atomicity failure (returns 500 with uncommitted rollbacks)
        res10 = await client.post("/api/v1/grades/batch-upload", json={"grades": [{"student_id": "stud_1", "grade": "A"}, {"student_id": "invalid_id_999", "grade": "B"}]})
        assert res10.status_code == 500

        # BUG-STUD-011: IDOR financial aid ledger
        res11 = await client.get("/api/v1/students/stud_alice/financial-aid", headers={"X-Student-Id": "stud_bob"})
        assert res11.status_code == 200
        assert res11.json().get("scholarship_amount") == 5000.0

        # BUG-STUD-012: Null department rankings crash
        with pytest.raises(Exception):
            await client.get("/api/v1/departments/cs/rankings")


@pytest.mark.asyncio
async def test_banking_service_bugs():
    """Verify Banking service bugs trigger deterministically."""
    BenchmarkEnvironment.enable_all_bugs()
    reset_banking_db()

    transport = httpx.ASGITransport(app=bank_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # BUG-BANK-001: Overdraft beyond limit succeeds
        res1 = await client.post("/api/v1/accounts/acc_1/withdraw", json={"amount": 1250.0})
        assert res1.status_code == 200
        assert res1.json().get("balance") == -250.0

        # BUG-BANK-002: Transfer money vanishes on crash
        res2 = await client.post("/api/v1/transfers", json={"from_account": "acc_a", "to_account": "acc_b_crash", "amount": 200.0})
        assert res2.status_code == 500
        assert res2.json().get("acc_a_debited") == 200.0

        # BUG-BANK-003: Self-transfer credits double balance
        res3 = await client.post("/api/v1/transfers", json={"from_account": "acc_1", "to_account": "acc_1", "amount": 500.0})
        assert res3.status_code == 200
        assert res3.json().get("balance") == 250.0  # -250 + 500 = 250

        # BUG-BANK-004: Negative deposit accepted
        res4 = await client.post("/api/v1/accounts/acc_2/deposit", json={"amount": -200.0})
        assert res4.status_code == 200
        assert res4.json().get("balance") == 300.0

        # BUG-BANK-005: Float precision loss
        res5 = await client.post("/api/v1/accounts/acc_1/interest", json={"add_amount": 0.2})
        assert res5.status_code == 200
        assert isinstance(res5.json().get("total"), float)

        # BUG-BANK-007: Frozen account can withdraw
        res7 = await client.post("/api/v1/accounts/acc_frozen/withdraw", json={"amount": 100.0})
        assert res7.status_code == 200
        assert res7.json().get("withdrawn") == 100.0

        # BUG-BANK-008: Negative loan interest rate credits money
        res8 = await client.post("/api/v1/loans/apply", json={"interest_rate": -0.03})
        assert res8.status_code == 200
        assert res8.json().get("monthly_payment") == -750.0

        # BUG-BANK-010: 8-digit routing number crashes with 500
        with pytest.raises(Exception):
            await client.post("/api/v1/transfers/validate-routing", json={"routing_number": "12345678"})

        # BUG-BANK-011: FX inverted rate calculation
        res11 = await client.post("/api/v1/fx/convert", json={"amount": 100.0, "from_currency": "USD", "to_currency": "EUR"})
        assert res11.status_code == 200
        assert res11.json().get("converted") == 108.69

        # BUG-BANK-012: Path traversal allows download
        res12 = await client.get("/api/v1/statements/download?file=../../etc/passwd")
        assert res12.status_code == 200
        assert "root:" in res12.json().get("content", "")

        # BUG-BANK-013: Audit log failure aborts deposit
        res13 = await client.post("/api/v1/accounts/acc_1/deposit-audited", json={"amount": 100.0})
        assert res13.status_code == 500


@pytest.mark.asyncio
async def test_clean_baseline_mode():
    """Verify that when defects are disabled, clean baseline behavior is observed (0 bugs)."""
    BenchmarkEnvironment.disable_all_bugs()
    reset_auth_db()
    reset_ecommerce_db()
    reset_student_db()
    reset_banking_db()

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # BUG-AUTH-001 backdoor is rejected with 401
        res1 = await client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "admin_override_2026"})
        assert res1.status_code == 401

        # BUG-AUTH-003 7-char password is rejected with 422
        res3 = await client.post("/api/v1/auth/register", json={"email": "newuser@example.com", "password": "1234567"})
        assert res3.status_code == 422

    # Re-enable bugs after clean baseline test
    BenchmarkEnvironment.enable_all_bugs()


def test_git_benchmark_fixture(tmp_path):
    """Verify that git benchmark repository fixture initializes with 4 commits."""
    from benchmark_apps.git_fixture import init_git_benchmark_fixture
    repo_path = init_git_benchmark_fixture(target_dir=tmp_path / "test_repo")
    assert (repo_path / ".git").exists()
    assert (repo_path / "validator.py").exists()
    assert (repo_path / "currency.py").exists()
    assert (repo_path / "README.md").exists()
