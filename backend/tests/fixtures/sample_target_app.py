"""
Sample FastAPI target application fixture for Phase 3.5 E2E hardening tests.
"""
from fastapi import FastAPI, Header, HTTPException, Response
import asyncio

app = FastAPI(title="ASTRA Hardening Target Fixture")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "target_fixture"}

@app.get("/items")
def get_items():
    return [{"id": 1, "name": "Widget A"}, {"id": 2, "name": "Widget B"}]

@app.post("/items", status_code=201)
def create_item(payload: dict):
    if "name" not in payload:
        raise HTTPException(status_code=422, detail="Missing required field: name")
    return {"id": 100, "name": payload["name"], "status": "created"}

@app.get("/slow")
async def slow_endpoint():
    await asyncio.sleep(2.0)
    return {"status": "delayed_ok"}

@app.get("/error500")
def internal_error():
    raise HTTPException(status_code=500, detail="Target Internal Error")

@app.get("/secured")
def secured_endpoint(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return {"status": "authenticated", "token_received": authorization}

@app.post("/echo-sensitive")
def echo_sensitive(payload: dict, authorization: str = Header(None), cookie: str = Header(None)):
    return {
        "received_headers": {
            "authorization": authorization,
            "cookie": cookie
        },
        "received_body": payload
    }
