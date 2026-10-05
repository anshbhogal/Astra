from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class GraphNode:
    id: str
    type: str  # PROJECT, MODULE, CLASS, FUNCTION, ENDPOINT, MODEL
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relationship: str  # CONTAINS, DEFINES, IMPORTS, HANDLED_BY, CALLS, USES_MODEL
    confidence: float = 1.0
