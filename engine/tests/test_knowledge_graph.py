import pytest
from engine.analyzer.models.source_file import SourceFile
from engine.analyzer.models.function import FunctionInfo
from engine.analyzer.models.endpoint import APIEndpoint, APIParameter
from engine.analyzer.knowledge_graph import ProjectKnowledgeGraph


def test_knowledge_graph_construction():
    pkg = ProjectKnowledgeGraph()

    source_files = [
        SourceFile(path="/app/main.py", relative_path="main.py", language="Python", size_bytes=1024, line_count=30)
    ]
    functions = [
        FunctionInfo(
            name="send_email",
            qualified_name="send_email",
            file_path="main.py",
            line_number=10,
            parameters=[{"name": "recipient", "type": "str", "required": True}],
            decorators=['@app.post("/send")'],
        )
    ]
    endpoints = [
        APIEndpoint(
            method="POST",
            path="/send",
            function_name="send_email",
            parameters=[APIParameter(name="recipient", type="str", location="body")],
            file_path="main.py",
            line_number=10,
        )
    ]

    graph_data = pkg.build_graph(
        project_name="Email SMTP",
        source_files=source_files,
        functions=functions,
        endpoints=endpoints,
    )

    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert graph_data["stats"]["node_count"] >= 3
    assert graph_data["stats"]["edge_count"] >= 2

    node_types = [n["type"] for n in graph_data["nodes"]]
    assert "PROJECT" in node_types
    assert "MODULE" in node_types
    assert "FUNCTION" in node_types
    assert "ENDPOINT" in node_types
