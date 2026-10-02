# Phase 2 — Project & Repository Analyzer Implementation Guide

> **Module Focus:** Git Integration, Static Code Analysis (AST & Tree-Sitter), API Route Discovery, Parameter Extraction, and Project Knowledge Graph Construction.

---

## 1. Phase Overview & Objectives

Phase 2 builds Astra's first intelligent component: the **Project Analyzer**. Given a target Git repository, this module clones the code, auto-detects languages/frameworks, parses source code using Abstract Syntax Trees (AST) and Tree-Sitter, extracts API routes and function definitions, and constructs a structured **Project Knowledge Graph**.

### Key Deliverables
1. **Git Synchronization Engine:** Secure Git repository cloner supporting local repos, public GitHub repos, and private repos via Personal Access Tokens (PAT).
2. **Language & Framework Detector:** Automated scanner determining languages (Python, TypeScript, JavaScript, Java) and frameworks (FastAPI, Flask, Express, Spring).
3. **AST Static Code Parser:** Python AST and Tree-Sitter analyzers extracting functions, classes, decorators, parameter signatures, and exception handlers.
4. **REST API Endpoint Extractor:** Schema extractor deriving HTTP method, path URL, path parameters, request bodies, query params, and response status codes directly from code annotations.
5. **Project Knowledge Graph (PKG) Builder:** Directed graph structure mapping relationships between endpoints, functions, database models, and utilities.

---

## 2. Technical Stack Specifications

- **Git Client:** `GitPython` `3.1+` for clone, checkout, and commit diff operations.
- **Python AST Engine:** Built-in Python `ast` module with `ast.NodeVisitor` subclassing.
- **Polyglot Parser:** `tree-sitter` with language bindings for JavaScript, TypeScript, and Java.
- **Graph Engine:** `networkx` for representing in-memory project dependency graphs.

---

## 3. Architecture & Data Flow

```text
Target Git Repository
         │
         ▼
┌──────────────────┐
│  Git Sync Engine │ Clones to isolated workspace
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Framework Engine │ Scans requirements.txt, pyproject.toml, package.json
└────────┬─────────┘
         ▼
┌──────────────────┐
│  AST / Tree-     │ Parses source code into abstract syntax trees
│  Sitter Engine   │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Route Extractor  │ Extracts @app.get(), @app.post(), parameters, types
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Knowledge Graph  │ Produces graph mapping Endpoints -> Handler -> Service -> DB
└──────────────────┘
```

---

## 4. AST Static Code Parsing Engine (`engine/analyzer/ast_parser.py`)

Below is the production-grade Python AST visitor for discovering FastAPI and Flask routes:

```python
import ast
from typing import List, Dict, Any

class RouteExtractorVisitor(ast.NodeVisitor):
    def __init__(self):
        self.routes: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Scan decorators for FastAPI router patterns (@app.get, @router.post, etc.)
        for decorator in node.decorator_list:
            method, path = self._extract_route_decorator(decorator)
            if method and path:
                parameters = self._extract_parameters(node.args)
                return_type = ast.unparse(node.returns) if node.returns else "Any"
                docstring = ast.get_docstring(node) or ""
                
                self.routes.append({
                    "function_name": node.name,
                    "method": method.upper(),
                    "endpoint": path,
                    "parameters": parameters,
                    "return_type": return_type,
                    "docstring": docstring,
                    "line_number": node.lineno
                })
        self.generic_visit(node)

    def _extract_route_decorator(self, decorator) -> tuple:
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Attribute):
                if func.attr.lower() in ["get", "post", "put", "delete", "patch"]:
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        return (func.attr, decorator.args[0].value)
        return (None, None)

    def _extract_parameters(self, args: ast.arguments) -> List[Dict[str, Any]]:
        params = []
        for arg in args.args:
            if arg.arg in ["self", "cls"]:
                continue
            param_type = ast.unparse(arg.annotation) if arg.annotation else "str"
            params.append({
                "name": arg.arg,
                "type": param_type,
                "required": True
            })
        return params

def parse_python_file(file_content: str) -> List[Dict[str, Any]]:
    tree = ast.parse(file_content)
    visitor = RouteExtractorVisitor()
    visitor.visit(tree)
    return visitor.routes
```

---

## 5. Project Knowledge Graph Construction (`engine/analyzer/knowledge_graph.py`)

The Project Knowledge Graph represents dependencies between HTTP routes, Python functions, data models, and database calls:

```python
import networkx as nx
from typing import Dict, Any

class ProjectKnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_endpoint_node(self, endpoint: str, method: str, handler_func: str):
        node_id = f"endpoint:{method}:{endpoint}"
        self.graph.add_node(node_id, type="ENDPOINT", method=method, path=endpoint, handler=handler_func)
        self.graph.add_node(f"func:{handler_func}", type="FUNCTION", name=handler_func)
        self.graph.add_edge(node_id, f"func:{handler_func}", relation="HANDLED_BY")

    def add_dependency_edge(self, source_func: str, target_component: str, relation_type: str = "CALLS"):
        self.graph.add_node(f"func:{source_func}", type="FUNCTION", name=source_func)
        self.graph.add_node(f"comp:{target_component}", type="COMPONENT", name=target_component)
        self.graph.add_edge(f"func:{source_func}", f"comp:{target_component}", relation=relation_type)

    def export_graph_json(self) -> Dict[str, Any]:
        return nx.node_link_data(self.graph)
```

---

## 6. Output Schema Definitions (`backend/app/schemas/analyzer.py`)

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class APIParameterSchema(BaseModel):
    name: str
    type: str
    required: bool
    default: Optional[Any] = None

class APIEndpointSchema(BaseModel):
    method: str
    endpoint: str
    function_name: str
    parameters: List[APIParameterSchema]
    return_type: str
    docstring: Optional[str] = None
    file_path: str
    line_number: int

class AnalysisResultSchema(BaseModel):
    project_id: str
    detected_language: str
    detected_framework: str
    total_files_scanned: int
    endpoints: List[APIEndpointSchema]
    knowledge_graph: Dict[str, Any]
```

---

## 7. API Endpoints (`backend/app/api/v1/analyzer.py`)

- `POST /projects/{id}/analyze` — Triggers Git clone, scans workspace, executes AST extraction, and saves analysis results into PostgreSQL.
- `GET /projects/{id}/analysis` — Retrieves the latest project analysis summary.
- `GET /projects/{id}/endpoints` — Returns all extracted API endpoints with their parameter schemas.
- `GET /projects/{id}/graph` — Returns the JSON representation of the Project Knowledge Graph for rendering on the React dashboard.

---

## 8. Verification & Test Plan

1. **AST Parser Unit Tests:**
   - Execute `pytest engine/tests/test_ast_parser.py` against sample FastAPI files (`@app.get("/users/{id}")`, `@app.post("/items")`). Verify 100% extraction accuracy for endpoint paths, methods, parameter names, and types.
2. **Polyglot Tree-Sitter Test:**
   - Execute parser against Express.js sample app (`app.get('/api/v1/products', handler)`). Verify method and route extraction.
3. **Repository Integration Test:**
   - Clone a public FastAPI GitHub repository using `POST /projects/{id}/analyze`. Ensure endpoints are stored in database and knowledge graph nodes match extracted source files.
