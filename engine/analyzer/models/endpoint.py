from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal


@dataclass
class APIParameter:
    name: str
    type: Optional[str] = "Any"
    required: bool = True
    location: Literal["path", "query", "header", "body", "unknown"] = "unknown"
    default: Optional[str] = None
    source: str = "ast"


@dataclass
class APIEndpoint:
    method: str
    path: str
    function_name: str
    qualified_function_name: Optional[str] = None
    parameters: List[APIParameter] = field(default_factory=list)
    request_model: Optional[str] = None
    response_model: Optional[str] = None
    file_path: str = ""
    line_number: int = 1
    framework: str = "FASTAPI"
    confidence: float = 0.98
