from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class FunctionInfo:
    name: str
    qualified_name: str
    file_path: str
    line_number: int
    parameters: List[Dict[str, Any]]
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    called_functions: List[str] = field(default_factory=list)
    is_async: bool = False
