import pytest
from engine.analyzer.parsers.python_ast import PythonASTParser

SAMPLE_FASTAPI_CODE = """
from fastapi import FastAPI, Depends

app = FastAPI()

@app.get("/health")
def health_check():
    \"\"\"Basic health probe.\"\"\"
    return {"status": "healthy"}

@app.post("/users/{user_id}")
async def create_user_item(user_id: int, item_name: str, active: bool = True):
    \"\"\"Create user item endpoint.\"\"\"
    validate_item(item_name)
    return {"user_id": user_id, "item_name": item_name}

def validate_item(name: str):
    pass
"""


def test_python_ast_parser_extraction():
    parser = PythonASTParser()
    functions = parser.parse_file("main.py", SAMPLE_FASTAPI_CODE)

    assert len(functions) == 3

    # Check health_check function
    health_func = next(f for f in functions if f.name == "health_check")
    assert health_func.decorators == ['@app.get("/health")']
    assert health_func.docstring == "Basic health probe."

    # Check create_user_item async function
    user_func = next(f for f in functions if f.name == "create_user_item")
    assert user_func.is_async is True
    assert len(user_func.parameters) == 3
    assert user_func.parameters[0]["name"] == "user_id"
    assert user_func.parameters[0]["type"] == "int"
    assert user_func.parameters[2]["name"] == "active"
    assert user_func.parameters[2]["default"] == "True"
    assert "validate_item" in user_func.called_functions
