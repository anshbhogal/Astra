import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.domain import AnalysisStatus, AnalysisStage


class AnalysisTriggerRequest(BaseModel):
    branch: Optional[str] = Field(None, description="Optional branch override for repository analysis")


class DiscoveredEndpointResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    method: str
    path: str
    function_name: str
    parameters: List[Dict[str, Any]]
    request_model: Optional[str] = None
    response_model: Optional[str] = None
    framework: str
    confidence: float
    file_path: str
    line_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EndpointCatalogResponse(BaseModel):
    items: List[DiscoveredEndpointResponse]
    total: int
    page: int
    page_size: int


class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    type: str = "UNKNOWN"
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str
    type: Optional[str] = None
    relationship: Optional[str] = "RELATED_TO"
    confidence: Optional[float] = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class KnowledgeGraphResponse(BaseModel):
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: AnalysisStatus
    current_stage: AnalysisStage
    progress_percent: int
    repository_url: str
    branch: str
    commit_sha: Optional[str] = None
    detected_language: Optional[str] = None
    detected_framework: Optional[str] = None
    framework_confidence: float
    scanned_files_count: int
    parsed_files_count: int
    endpoint_count: int
    graph_node_count: int
    graph_edge_count: int
    analyzer_version: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
