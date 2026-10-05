import pytest
from engine.analyzer.parsers.python_ast import PythonASTParser
from engine.analyzer.endpoint_extractor import EndpointExtractor

SAMPLE_ROUTER_CODE = """
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

@router.get("/items/{item_id}")
async def get_item(item_id: int, q: str = None):
    return {"item_id": item_id}

@router.post("/items")
async def create_item(payload: dict):
    return payload
"""


def test_endpoint_extractor():
    parser = PythonASTParser()
    functions = parser.parse_file("router.py", SAMPLE_ROUTER_CODE)

    extractor = EndpointExtractor()
    endpoints = extractor.extract_endpoints(functions, framework="PYTHON_FASTAPI")

    assert len(endpoints) == 2

    get_ep = next(e for e in endpoints if e.method == "GET")
    assert get_ep.path == "/items/{item_id}"
    assert len(get_ep.parameters) == 2

    path_param = next(p for p in get_ep.parameters if p.name == "item_id")
    assert path_param.location == "path"

    query_param = next(p for p in get_ep.parameters if p.name == "q")
    assert query_param.location == "query"

    post_ep = next(e for e in endpoints if e.method == "POST")
    assert post_ep.path == "/items"
    body_param = post_ep.parameters[0]
    assert body_param.location == "body"
