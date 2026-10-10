"""E-Commerce Benchmark Microservice containing Injected Bugs BUG-ECOM-001 through BUG-ECOM-015."""

import asyncio
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response

from benchmark_apps.base_app import BenchmarkEnvironment, create_benchmark_app

app = create_benchmark_app("Benchmark E-Commerce API", version="1.0.0")

# In-memory database setup
_db = sqlite3.connect(":memory:", check_same_thread=False)
_cursor = _db.cursor()
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT,
        price REAL,
        stock INTEGER,
        is_deleted INTEGER DEFAULT 0
    )
""")
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        total REAL,
        status TEXT,
        shipping_zip TEXT
    )
""")
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        order_id TEXT,
        amount REAL,
        idempotency_key TEXT
    )
""")

# Seed initial products
_cursor.execute("INSERT OR REPLACE INTO products VALUES ('prod_1', 'Wireless Mouse', 25.0, 10, 0)")
_cursor.execute("INSERT OR REPLACE INTO products VALUES ('prod_2', 'Mechanical Keyboard', 80.0, 5, 0)")
_cursor.execute("INSERT OR REPLACE INTO products VALUES ('prod_deleted_99', 'Discontinued Cable', 10.0, 0, 1)")
_cursor.execute("INSERT OR REPLACE INTO orders VALUES ('ord_alice_1', 'user_alice', 100.0, 'PLACED', '94105')")
_db.commit()


def reset_ecommerce_db():
    _cursor.execute("DELETE FROM orders WHERE id != 'ord_alice_1'")
    _cursor.execute("DELETE FROM payments")
    _cursor.execute("UPDATE products SET stock = 10 WHERE id = 'prod_1'")
    _cursor.execute("UPDATE products SET stock = 5 WHERE id = 'prod_2'")
    _cursor.execute("UPDATE orders SET status = 'PLACED' WHERE id = 'ord_alice_1'")
    _db.commit()


@app.get("/api/v1/ecommerce/health")
async def health():
    return {"status": "HEALTHY", "service": "ecommerce"}


@app.get("/api/v1/products")
async def list_products(request: Request, min_price: Optional[str] = None):
    # BUG-ECOM-013: Passing string 'cheap' to numeric filter raises unhandled ValueError -> 500
    if min_price is not None:
        if BenchmarkEnvironment.is_bug_active("BUG-ECOM-013"):
            filter_val = float(min_price)  # Crashes on non-numeric strings like 'cheap'
        else:
            try:
                filter_val = float(min_price)
            except ValueError:
                raise HTTPException(status_code=422, detail="min_price must be a valid float")
        _cursor.execute("SELECT id, name, price, stock FROM products WHERE price >= ? AND is_deleted = 0", (filter_val,))
    else:
        _cursor.execute("SELECT id, name, price, stock FROM products WHERE is_deleted = 0")

    rows = _cursor.fetchall()
    return [{"id": r[0], "name": r[1], "price": r[2], "stock": r[3]} for r in rows]


@app.get("/api/v1/products/search")
async def search_products(q: str = ""):
    # BUG-ECOM-007: Search parameter with SQL quote triggers unhandled query crash 500
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-007"):
        query = f"SELECT id, name, price FROM products WHERE name LIKE '{q}' AND is_deleted = 0"
        _cursor.execute(query)
        rows = _cursor.fetchall()
    else:
        _cursor.execute("SELECT id, name, price FROM products WHERE name LIKE ? AND is_deleted = 0", (f"%{q}%",))
        rows = _cursor.fetchall()

    return [{"id": r[0], "name": r[1], "price": r[2]} for r in rows]


@app.get("/api/v1/products/{product_id}")
async def get_product(product_id: str):
    _cursor.execute("SELECT id, name, price, stock, is_deleted FROM products WHERE id = ?", (product_id,))
    row = _cursor.fetchone()

    # BUG-ECOM-014: Soft-deleted product query raises AttributeError -> 500
    if row and row[4] == 1:
        if BenchmarkEnvironment.is_bug_active("BUG-ECOM-014"):
            deleted_obj = None
            return {"name": deleted_obj.name}  # AttributeError: 'NoneType' object has no attribute 'name'
        else:
            raise HTTPException(status_code=404, detail="Product not found")

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"id": row[0], "name": row[1], "price": row[2], "stock": row[3]}


@app.post("/api/v1/orders", status_code=201)
async def create_order(request: Request):
    payload = await request.json()
    product_id = payload.get("product_id", "")
    quantity = payload.get("quantity", 1)

    _cursor.execute("SELECT stock, price FROM products WHERE id = ?", (product_id,))
    row = _cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    current_stock, price = row[0], row[1]

    # BUG-ECOM-001: Quantity > stock decrements inventory into negative stock (e.g. -5)
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-001"):
        new_stock = current_stock - quantity
        _cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
        _db.commit()
        return {"status": 201, "order_id": str(uuid.uuid4()), "stock_remaining": new_stock}
    else:
        if quantity > current_stock:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        new_stock = current_stock - quantity
        _cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
        _db.commit()
        return {"status": 201, "order_id": str(uuid.uuid4()), "stock_remaining": new_stock}


@app.post("/api/v1/orders/calculate")
async def calculate_order(request: Request):
    payload = await request.json()
    quantity = payload.get("quantity", 1)

    # BUG-ECOM-002: Integer overflow simulation on quantity 10^9
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-002"):
        if quantity >= 1000000000:
            return {"status": 200, "total": -14859384.0}
    else:
        if quantity > 100000:
            raise HTTPException(status_code=422, detail="Quantity exceeds maximum allowable limit")

    return {"status": 200, "total": float(quantity * 25.0)}


@app.post("/api/v1/checkout")
async def checkout(request: Request):
    payload = await request.json()
    items = payload.get("items", [{"product_id": "prod_1", "quantity": 1}])
    shipping_zip = payload.get("shipping_zip")

    # BUG-ECOM-004: Empty cart returns 200 OK
    if len(items) == 0:
        if BenchmarkEnvironment.is_bug_active("BUG-ECOM-004"):
            return {"status": 200, "order_id": "ord_empty", "total": 0.0}
        else:
            raise HTTPException(status_code=400, detail="Cannot checkout empty cart")

    # BUG-ECOM-003: Missing shipping_zip crashes with unhandled 500 AttributeError
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-003"):
        formatted_zip = shipping_zip.strip()  # Crashes if None
    else:
        formatted_zip = shipping_zip.strip() if shipping_zip else "00000"

    return {"status": 200, "order_id": "ord_ok", "shipping_zip": formatted_zip}


@app.post("/api/v1/coupons/apply")
async def apply_coupon(request: Request):
    payload = await request.json()
    cart_total = payload.get("cart_total", 100.0)
    coupon_code = payload.get("coupon_code", "")

    # BUG-ECOM-005: SUPER200 discounts 200% causing negative payable total
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-005") and coupon_code == "SUPER200":
        return {"status": 200, "discounted_total": -100.0}

    if coupon_code == "SUPER200":
        raise HTTPException(status_code=400, detail="Invalid discount rate exceeding 100%")

    return {"status": 200, "discounted_total": cart_total * 0.9}


@app.post("/api/v1/payments/process")
async def process_payment(request: Request):
    payload = await request.json()
    amount = payload.get("amount", 100.0)
    from_curr = payload.get("from_currency", "USD")
    to_curr = payload.get("to_currency", "JPY")

    # BUG-ECOM-006: USD to JPY processed 1:1 without exchange rate
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-006") and from_curr == "USD" and to_curr == "JPY":
        return {"status": 200, "converted_amount": amount}

    rate = 150.0 if from_curr == "USD" and to_curr == "JPY" else 1.0
    return {"status": 200, "converted_amount": amount * rate}


@app.get("/api/v1/products/{product_id}/recommendations")
async def get_recommendations(product_id: str):
    # BUG-ECOM-008: Sleeps 0.20s exceeding SLA timeout
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-008"):
        await asyncio.sleep(0.20)

    return {"status": 200, "recommendations": ["prod_1", "prod_2"]}


@app.post("/api/v1/payments/charge")
async def charge_payment(request: Request):
    payload = await request.json()
    order_id = payload.get("order_id", "ord_1")
    amount = payload.get("amount", 200.0)

    # BUG-ECOM-009: Concurrent double charge without idempotency key
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-009"):
        _cursor.execute("INSERT INTO payments VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), order_id, amount, None))
        _db.commit()
        _cursor.execute("SELECT COUNT(*) FROM payments WHERE order_id = ?", (order_id,))
        count = _cursor.fetchone()[0]
        return {"status": 200, "charges_count": count, "total_debited": amount * count}
    else:
        _cursor.execute("SELECT COUNT(*) FROM payments WHERE order_id = ?", (order_id,))
        if _cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=409, detail="Duplicate charge detected")
        _cursor.execute("INSERT INTO payments VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), order_id, amount, "idemp_1"))
        _db.commit()
        return {"status": 200, "charges_count": 1, "total_debited": amount}


@app.post("/api/v1/orders/{order_id}/cancel")
async def cancel_order(order_id: str, request: Request):
    user_header = request.headers.get("X-User-Id", "user_alice")

    # BUG-ECOM-010: Any user can cancel arbitrary user's order (IDOR)
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-010"):
        _cursor.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
        _db.commit()
        return {"status": 200, "status": "CANCELLED"}
    else:
        _cursor.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        row = _cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        if row[0] != user_header:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot cancel order of another user")
        _cursor.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
        _db.commit()
        return {"status": 200, "status": "CANCELLED"}


@app.post("/api/v1/products/{product_id}/reviews", status_code=201)
async def add_review(product_id: str, request: Request):
    payload = await request.json()
    rating = payload.get("rating", 5)

    # BUG-ECOM-011: Accepts rating 6 or -1 (valid 1 to 5)
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-011"):
        return {"status": 201, "review_id": str(uuid.uuid4()), "rating": rating}
    else:
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=422, detail="Rating must be between 1 and 5")
        return {"status": 201, "review_id": str(uuid.uuid4()), "rating": rating}


@app.patch("/api/v1/orders/{order_id}/status")
async def update_order_status(order_id: str, request: Request):
    payload = await request.json()
    new_status = payload.get("status", "")

    # BUG-ECOM-012: Transition from CANCELLED to DELIVERED allowed
    if BenchmarkEnvironment.is_bug_active("BUG-ECOM-012"):
        return {"status": 200, "status": new_status}
    else:
        _cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = _cursor.fetchone()
        if row and row[0] == "CANCELLED" and new_status == "DELIVERED":
            raise HTTPException(status_code=400, detail="Illegal state transition from CANCELLED to DELIVERED")
        return {"status": 200, "status": new_status}


@app.post("/api/v1/orders/batch")
async def batch_orders(request: Request):
    payload = await request.json()
    batch_list = payload.get("batch_orders", [])

    # BUG-ECOM-015: Zero-item batch triggers zero division
    if len(batch_list) == 0:
        if BenchmarkEnvironment.is_bug_active("BUG-ECOM-015"):
            zero_div = 100 // len(batch_list)
        else:
            raise HTTPException(status_code=400, detail="Batch orders cannot be empty")

    return {"status": 200, "processed_count": len(batch_list)}
