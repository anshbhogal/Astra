"""
Dedicated FastAPI Target App Fixture for Phase 4 Advanced Rule-Based Generator Testing.
Exposes endpoints testing integer/float BVA, string length/regex, EmailStr, UUID, Enum literals,
booleans, arrays, nested objects, and passive security probe inputs.
"""

from fastapi import FastAPI, Header, HTTPException, Query, Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from uuid import UUID

app = FastAPI(title="ASTRA Phase 4 Target Fixture")


class AddressSchema(BaseModel):
    city: str = Field(min_length=2, max_length=50)
    pincode: int = Field(ge=10000, le=99999)
    country: str = Field(default="IN")


class UserCreateSchema(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    age: int = Field(ge=18, le=60)
    score: float = Field(gt=0.0, lt=100.0)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    user_id: UUID
    role: Literal["user", "admin"]
    tags: List[str] = Field(min_length=1, max_length=5)
    address: Optional[AddressSchema] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "phase": 4}


@app.post("/users", status_code=201)
def create_user(user: UserCreateSchema):
    return {
        "id": str(user.user_id),
        "username": user.username,
        "age": user.age,
        "score": user.score,
        "email": user.email,
        "role": user.role,
        "tags": user.tags,
        "address": user.address.dict() if user.address else None,
        "status": "created"
    }


@app.get("/constrained/{item_id}")
def get_constrained(
    item_id: int = Path(ge=1, le=1000),
    page: int = Query(default=1, ge=1, le=100),
    limit: int = Query(default=20, ge=1, le=100)
):
    return {"item_id": item_id, "page": page, "limit": limit}


@app.get("/security-input")
def security_input(q: str = Query(...)):
    # Non-crashing resilience check: safely returns search query without executing SQL/Command
    return {"query": q, "status": "processed_safely"}
