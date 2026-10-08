"""
Dedicated Phase 5 Golden Target Application Fixture with Complex Business Logic.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Phase 5 Target Application", version="5.0.0")

# In-Memory State
ACCOUNTS = {"acc_123": {"balance": 500.0, "locked": False, "failed_attempts": 0}}
ORDERS = {"ord_99": {"amount": 1200.0, "status": "CANCELLED"}}


class WithdrawalRequest(BaseModel):
    account_id: str = Field(..., description="Account identifier")
    amount: float = Field(..., gt=0, description="Withdrawal amount")


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float
    require_2fa: bool = False


class VerifyRequest(BaseModel):
    account_id: str
    pin: str


@app.post("/withdraw")
def withdraw(req: WithdrawalRequest):
    """
    Withdraw funds from account.
    Business Rule: Users cannot withdraw more than their available balance.
    """
    if req.account_id not in ACCOUNTS:
        raise HTTPException(status_code=status.HTTP_44_NOT_FOUND, detail="Account not found")

    acc = ACCOUNTS[req.account_id]
    if acc["locked"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked")

    if req.amount > acc["balance"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Withdrawal amount {req.amount} exceeds available balance {acc['balance']}"
        )

    acc["balance"] -= req.amount
    return {"message": "Withdrawal successful", "new_balance": acc["balance"]}


@app.post("/orders/{order_id}/pay")
def pay_order(order_id: str, amount: float):
    """
    Pay an existing order.
    Business Rule: A cancelled order cannot be paid. Payment cannot exceed order amount.
    """
    if order_id not in ORDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = ORDERS[order_id]
    if order["status"] == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pay a cancelled order"
        )

    if amount > order["amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment exceeds total order amount"
        )

    order["status"] = "PAID"
    return {"message": "Order paid successfully", "status": order["status"]}


@app.post("/transfers")
def transfer(req: TransferRequest):
    """
    Transfer funds between accounts.
    Business Rule: Transactions above 50,000 require two-factor confirmation (require_2fa=True).
    """
    if req.amount > 50000 and not req.require_2fa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Large transactions above 50,000 require two-factor confirmation (require_2fa=True)"
        )
    return {"message": "Transfer processed", "amount": req.amount}


@app.post("/users/{account_id}/verify")
def verify_user(account_id: str, req: VerifyRequest):
    """
    Verify user pin.
    Business Rule: Three failed verification attempts lock the account.
    """
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    acc = ACCOUNTS[account_id]
    if acc["locked"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is locked")

    if req.pin != "1234":
        acc["failed_attempts"] += 1
        if acc["failed_attempts"] >= 3:
            acc["locked"] = True
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked due to 3 failed attempts")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")

    acc["failed_attempts"] = 0
    return {"message": "Verification successful"}
