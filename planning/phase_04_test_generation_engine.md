# Phase 4 — Non-LLM Rule-Based Test & Data Generation Engine Implementation Guide

> **Module Focus:** OpenAPI Spec Parser, Boundary Value Analysis (BVA), Equivalence Partitioning (EP), AST Condition Mining, Synthetic Data Generator, and Non-LLM Test Case Compiler.

---

## 1. Phase Overview & Objectives

Phase 4 delivers one of Astra's core architectural advantages: **Deterministic, LLM-Independent Test Generation**. By analyzing AST code conditions, OpenAPI/Swagger specifications, and structural parameters, this module automatically synthesizes boundary, valid, negative, and invalid test cases without calling external AI services.

### Key Deliverables
1. **OpenAPI / Swagger Spec Processor:** Parser converting OpenAPI 3.0+ specs into internal parameter constraints (ranges, enums, regex patterns, required fields).
2. **Boundary Value Analysis (BVA) Engine:** Automated boundary generator producing `min-1`, `min`, `min+1`, `max-1`, `max`, and `max+1` test inputs for numerical and string parameters.
3. **AST Code Condition Miner:** Static analysis module scanning Python AST branches (`if age < 18:`, `if len(pwd) < 8:`) to derive exact boundary test inputs directly from source code.
4. **Synthetic Test Data Engine:** Deterministic generator outputting schema-compliant data, malformed payloads, boundary strings, empty/null values, and injection test vectors.
5. **Structured Test Compiler:** Engine assembling test inputs, headers, HTTP endpoints, and expected status codes into executable JSON test specs.

---

## 2. Architecture & Data Flow

```text
OpenAPI Spec / AST Code Analysis
               │
               ▼
┌─────────────────────────────┐
│ Constraint Extraction Core  │ Parses min, max, required, regex, if-conditions
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  Rule Engine (BVA + EP)     │ Computes boundary values: (min-1, min, min+1)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Synthetic Data Generator    │ Synthesizes valid, invalid, boundary & edge payloads
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Structured Test Compiler    │ Outputs JSON Executable Test Cases (TC-001...TC-N)
└─────────────────────────────┘
```

---

## 3. Boundary Value Analysis & Equivalence Partitioning Engine (`engine/generator/bva_engine.py`)

```python
from typing import List, Dict, Any

class BoundaryValueEngine:
    @staticmethod
    def generate_integer_boundaries(param_name: str, min_val: int = 0, max_val: int = 100) -> List[Dict[str, Any]]:
        """Generates 6 BVA test cases: min-1, min, min+1, max-1, max, max+1."""
        test_inputs = [
            {"label": "BELOW_MINIMUM", "val": min_val - 1, "expected_status": 400, "category": "boundary_invalid"},
            {"label": "EXACT_MINIMUM", "val": min_val, "expected_status": 200, "category": "boundary_valid"},
            {"label": "ABOVE_MINIMUM", "val": min_val + 1, "expected_status": 200, "category": "boundary_valid"},
            {"label": "BELOW_MAXIMUM", "val": max_val - 1, "expected_status": 200, "category": "boundary_valid"},
            {"label": "EXACT_MAXIMUM", "val": max_val, "expected_status": 200, "category": "boundary_valid"},
            {"label": "ABOVE_MAXIMUM", "val": max_val + 1, "expected_status": 400, "category": "boundary_invalid"},
        ]
        
        results = []
        for case in test_inputs:
            results.append({
                "parameter_name": param_name,
                "input_value": case["val"],
                "test_name": f"{param_name}_{case['label']}",
                "expected_status": case["expected_status"],
                "category": case["category"]
            })
        return results

    @staticmethod
    def generate_string_length_boundaries(param_name: str, min_len: int = 8, max_len: int = 32) -> List[Dict[str, Any]]:
        """Generates string length boundary payloads."""
        return [
            {"parameter_name": param_name, "input_value": "a" * (min_len - 1), "test_name": f"{param_name}_TOO_SHORT", "expected_status": 400},
            {"parameter_name": param_name, "input_value": "a" * min_len, "test_name": f"{param_name}_MIN_LENGTH", "expected_status": 200},
            {"parameter_name": param_name, "input_value": "a" * (min_len + 1), "test_name": f"{param_name}_VALID_LENGTH", "expected_status": 200},
            {"parameter_name": param_name, "input_value": "a" * max_len, "test_name": f"{param_name}_MAX_LENGTH", "expected_status": 200},
            {"parameter_name": param_name, "input_value": "a" * (max_len + 1), "test_name": f"{param_name}_TOO_LONG", "expected_status": 400},
        ]
```

---

## 4. AST Code Condition Miner (`engine/generator/ast_condition_miner.py`)

This component parses source code logic to discover boundary conditions directly from `if` statements:

```python
import ast
from typing import List, Dict, Any

class ConditionMinerVisitor(ast.NodeVisitor):
    def __init__(self):
        self.conditions: List[Dict[str, Any]] = []

    def visit_If(self, node: ast.If):
        # Scan for binary comparisons like: if age < 18 or if len(password) < 8
        if isinstance(node.test, ast.Compare):
            left_expr = ast.unparse(node.test.left)
            for op, comparator in zip(node.test.ops, node.test.comparators):
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                    val = comparator.value
                    op_type = type(op).__name__
                    
                    self.conditions.append({
                        "expression": left_expr,
                        "operator": op_type,
                        "target_value": val,
                        "suggested_inputs": [val - 1, val, val + 1],
                        "line_number": node.lineno
                    })
        self.generic_visit(node)

def mine_conditions_from_code(source_code: str) -> List[Dict[str, Any]]:
    tree = ast.parse(source_code)
    visitor = ConditionMinerVisitor()
    visitor.visit(tree)
    return visitor.conditions
```

---

## 5. Synthetic Data Generator (`engine/generator/synthetic_data.py`)

```python
import uuid
import random
import string
from typing import Dict, Any

class SyntheticDataGenerator:
    @staticmethod
    def generate_valid_payload(schema: Dict[str, Any]) -> Dict[str, Any]:
        payload = {}
        properties = schema.get("properties", {})
        for field, details in properties.items():
            field_type = details.get("type", "string")
            if field_type == "string":
                if "email" in field.lower():
                    payload[field] = f"user_{uuid.uuid4().hex[:6]}@example.com"
                else:
                    payload[field] = "".join(random.choices(string.ascii_letters, k=10))
            elif field_type == "integer":
                payload[field] = random.randint(details.get("minimum", 1), details.get("maximum", 100))
            elif field_type == "boolean":
                payload[field] = True
        return payload

    @staticmethod
    def generate_negative_payloads(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        negative_cases = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # 1. Missing Required Field Tests
        for req_field in required:
            payload = SyntheticDataGenerator.generate_valid_payload(schema)
            payload.pop(req_field, None)
            negative_cases.append({
                "test_name": f"MISSING_REQUIRED_{req_field.upper()}",
                "payload": payload,
                "expected_status": 422
            })

        # 2. Invalid Type Tests
        for field in properties.keys():
            payload = SyntheticDataGenerator.generate_valid_payload(schema)
            payload[field] = ["invalid_array_type_instead_of_scalar"]
            negative_cases.append({
                "test_name": f"INVALID_TYPE_{field.upper()}",
                "payload": payload,
                "expected_status": 422
            })

        return negative_cases
```

---

## 6. Non-LLM Test Generator Orchestrator (`engine/generator/test_compiler.py`)

```python
from typing import List, Dict, Any
from engine.generator.bva_engine import BoundaryValueEngine
from engine.generator.synthetic_data import SyntheticDataGenerator

class RuleBasedTestGenerator:
    @staticmethod
    def generate_tests_for_endpoint(endpoint_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        test_cases = []
        endpoint = endpoint_meta["endpoint"]
        method = endpoint_meta["method"]
        params = endpoint_meta.get("parameters", [])

        # 1. Generate Baseline Valid Test Case
        valid_body = {}
        for p in params:
            if p["type"] in ["int", "integer"]:
                valid_body[p["name"]] = 25
            else:
                valid_body[p["name"]] = "valid_sample_text"

        test_cases.append({
            "id": f"TC-{endpoint_meta['function_name'].upper()}-001",
            "test_type": "FUNCTIONAL_HAPPY_PATH",
            "method": method,
            "endpoint": endpoint,
            "body": valid_body,
            "expected": {"status_code": 200}
        })

        # 2. Generate Boundary Value Test Cases
        tc_counter = 2
        for p in params:
            if p["type"] in ["int", "integer"]:
                bva_inputs = BoundaryValueEngine.generate_integer_boundaries(p["name"], min_val=1, max_val=100)
                for bva in bva_inputs:
                    body = valid_body.copy()
                    body[p["name"]] = bva["input_value"]
                    test_cases.append({
                        "id": f"TC-{endpoint_meta['function_name'].upper()}-{tc_counter:03d}",
                        "test_type": "BOUNDARY_VALUE_ANALYSIS",
                        "method": method,
                        "endpoint": endpoint,
                        "body": body,
                        "expected": {"status_code": bva["expected_status"]}
                    })
                    tc_counter += 1

        return test_cases
```

---

## 7. API Router Endpoints (`backend/app/api/v1/generator.py`)

- `POST /tests/generate/rule-based` — Accepts a `project_id`, parses extracted routes/AST, executes BVA + EP rules, and saves structured JSON test cases.
- `GET /projects/{id}/tests` — Retrieves generated test cases filtered by endpoint, test type (functional, boundary, negative), or priority.

---

## 8. Verification & Test Plan

1. **BVA Mathematical Accuracy Verification:**
   - Execute `pytest engine/tests/test_bva.py`. Ensure integer min=10, max=50 generates exactly 6 test inputs: `[9, 10, 11, 49, 50, 51]` with expected statuses `[400, 200, 200, 200, 200, 400]`.
2. **AST Condition Mining Test:**
   - Parse source snippet `if price > 500: return "error"`. Verify condition miner extracts threshold `500` and generates test inputs `499`, `500`, `501`.
3. **Zero-LLM Verification:**
   - Disconnect network access (mocking zero LLM availability). Run `POST /tests/generate/rule-based` against an analyzed FastAPI project. Verify 100% successful generation of structured, executable test cases.
