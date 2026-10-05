import re
from typing import List, Dict, Any, Optional
from engine.analyzer.models.function import FunctionInfo
from engine.analyzer.models.endpoint import APIEndpoint, APIParameter


class EndpointExtractor:
    """Extracts and normalizes REST API endpoints and parameter schemas from AST parsed function metadata."""

    # Match FastAPI route decorators: @app.get("/path"), @router.post('/path', ...), etc.
    FASTAPI_ROUTE_PATTERN = re.compile(
        r"@(?:app|router)\.(get|post|put|delete|patch|options|head)\(\s*[\"']([^\"']+)[\"']",
        re.IGNORECASE
    )

    # Match Flask route decorators: @app.route("/path", methods=["GET", "POST"])
    FLASK_ROUTE_PATTERN = re.compile(
        r"@app\.route\(\s*[\"']([^\"']+)[\"'](?:.*methods\s*=\s*\[([^\]]+)\])?",
        re.IGNORECASE
    )

    def extract_endpoints(self, functions: List[FunctionInfo], framework: str = "PYTHON_FASTAPI") -> List[APIEndpoint]:
        discovered_endpoints: List[APIEndpoint] = []

        for func in functions:
            for dec in func.decorators:
                endpoints = self._parse_decorator(dec, func, framework)
                discovered_endpoints.extend(endpoints)

        return discovered_endpoints

    def _parse_decorator(self, decorator_str: str, func: FunctionInfo, framework: str) -> List[APIEndpoint]:
        endpoints: List[APIEndpoint] = []

        # 1. Test FastAPI Decorator Pattern
        fastapi_match = self.FASTAPI_ROUTE_PATTERN.search(decorator_str)
        if fastapi_match:
            http_method = fastapi_match.group(1).upper()
            route_path = fastapi_match.group(2)
            params = self._normalize_parameters(func.parameters, route_path)

            endpoints.append(
                APIEndpoint(
                    method=http_method,
                    path=route_path,
                    function_name=func.name,
                    qualified_function_name=func.qualified_name,
                    parameters=params,
                    response_model=func.return_type,
                    file_path=func.file_path,
                    line_number=func.line_number,
                    framework="PYTHON_FASTAPI",
                    confidence=0.98,
                )
            )
            return endpoints

        # 2. Test Flask Decorator Pattern
        flask_match = self.FLASK_ROUTE_PATTERN.search(decorator_str)
        if flask_match:
            route_path = flask_match.group(1)
            methods_raw = flask_match.group(2)
            methods = ["GET"]

            if methods_raw:
                methods = [m.strip(" \"'") for m in methods_raw.split(",")]

            params = self._normalize_parameters(func.parameters, route_path)

            for method in methods:
                endpoints.append(
                    APIEndpoint(
                        method=method.upper(),
                        path=route_path,
                        function_name=func.name,
                        qualified_function_name=func.qualified_name,
                        parameters=params,
                        response_model=func.return_type,
                        file_path=func.file_path,
                        line_number=func.line_number,
                        framework="PYTHON_FLASK",
                        confidence=0.95,
                    )
                )
            return endpoints

        return endpoints

    def _normalize_parameters(self, raw_params: List[Dict[str, Any]], route_path: str) -> List[APIParameter]:
        # Extract path variable names from /users/{user_id} or /items/<int:item_id>
        path_vars = set(re.findall(r"\{([^:\}]+)(?::[^\}]+)?\}", route_path))
        path_vars.update(re.findall(r"<(?:\w+:)?(\w+)>", route_path))

        normalized: List[APIParameter] = []
        for p in raw_params:
            p_name = p["name"]
            p_type = p.get("type", "Any")
            required = p.get("required", True)
            default = p.get("default")

            if p_name in path_vars:
                location = "path"
            elif any(keyword in p_type.lower() for keyword in ["schema", "model", "body", "dict", "create", "update", "payload"]):
                location = "body"
            else:
                location = "query"

            normalized.append(
                APIParameter(
                    name=p_name,
                    type=p_type,
                    required=required,
                    location=location,
                    default=default,
                    source="ast",
                )
            )
        return normalized
