import networkx as nx
from typing import Dict, List, Any
from engine.analyzer.models.source_file import SourceFile
from engine.analyzer.models.function import FunctionInfo
from engine.analyzer.models.endpoint import APIEndpoint
from engine.analyzer.models.graph import GraphNode, GraphEdge


class ProjectKnowledgeGraph:
    """Directed Knowledge Graph mapping Project -> Module -> Function -> Endpoint relationships."""

    def __init__(self, repo_name: str = "project"):
        self.graph = nx.DiGraph()
        self.repo_name = repo_name

    def build(
        self,
        source_files: List[SourceFile],
        functions: List[FunctionInfo],
        endpoints: List[APIEndpoint]
    ) -> Dict[str, Any]:
        return self.build_graph(self.repo_name, source_files, functions, endpoints)

    def build_graph(
        self,
        project_name: str,
        source_files: List[SourceFile],
        functions: List[FunctionInfo],
        endpoints: List[APIEndpoint]
    ) -> Dict[str, Any]:
        self.graph.clear()

        # 1. Project Root Node
        project_node_id = f"project:{project_name}"
        self.graph.add_node(
            project_node_id,
            type="PROJECT",
            label=project_name,
            properties={"name": project_name}
        )

        # 2. Source File (Module) Nodes
        for sf in source_files:
            file_node_id = f"module:{sf.relative_path}"
            self.graph.add_node(
                file_node_id,
                type="MODULE",
                label=sf.relative_path,
                properties={"language": sf.language, "lines": sf.line_count}
            )
            self.graph.add_edge(project_node_id, file_node_id, relationship="CONTAINS", confidence=1.0)

        # 3. Function Nodes
        func_map: Dict[str, str] = {}
        for fn in functions:
            func_node_id = f"func:{fn.file_path}:{fn.qualified_name}"
            func_map[fn.name] = func_node_id
            func_map[fn.qualified_name] = func_node_id

            self.graph.add_node(
                func_node_id,
                type="FUNCTION",
                label=fn.name,
                properties={
                    "qualified_name": fn.qualified_name,
                    "file_path": fn.file_path,
                    "line_number": fn.line_number,
                    "is_async": fn.is_async,
                }
            )

            # Link Module -> Function
            rel_path = fn.file_path.replace("\\", "/")
            module_node_id = f"module:{rel_path}"
            if self.graph.has_node(module_node_id):
                self.graph.add_edge(module_node_id, func_node_id, relationship="DEFINES", confidence=1.0)

        # 4. Internal Function Call Edges & Cross-Module Dependencies
        for fn in functions:
            source_func_id = f"func:{fn.file_path}:{fn.qualified_name}"
            source_file = fn.file_path.replace("\\", "/")
            source_module_id = f"module:{source_file}"
            for called_name in fn.called_functions:
                if called_name in func_map:
                    target_func_id = func_map[called_name]
                    if source_func_id != target_func_id:
                        self.graph.add_edge(source_func_id, target_func_id, relationship="CALLS", confidence=0.90)

                        # Create high-level module-to-module dependency edge
                        target_func_data = self.graph.nodes.get(target_func_id, {})
                        target_file = target_func_data.get("properties", {}).get("file_path", "").replace("\\", "/")
                        target_module_id = f"module:{target_file}"
                        if target_file and source_module_id != target_module_id:
                            if self.graph.has_node(source_module_id) and self.graph.has_node(target_module_id):
                                self.graph.add_edge(source_module_id, target_module_id, relationship="DEPENDS_ON", confidence=0.85)

        # 5. Endpoint Nodes & HANDLED_BY Edges
        for ep in endpoints:
            ep_node_id = f"endpoint:{ep.method}:{ep.path}"
            self.graph.add_node(
                ep_node_id,
                type="ENDPOINT",
                label=f"{ep.method} {ep.path}",
                properties={
                    "method": ep.method,
                    "path": ep.path,
                    "framework": ep.framework,
                    "confidence": ep.confidence,
                }
            )

            # Link Endpoint -> Function Handler
            target_func_id = func_map.get(ep.function_name) or func_map.get(ep.qualified_function_name or "")
            if target_func_id:
                self.graph.add_edge(ep_node_id, target_func_id, relationship="HANDLED_BY", confidence=ep.confidence)

            # Link Module -> Endpoint
            if ep.file_path:
                ep_mod = ep.file_path.replace("\\", "/")
                ep_mod_id = f"module:{ep_mod}"
                if self.graph.has_node(ep_mod_id):
                    self.graph.add_edge(ep_mod_id, ep_node_id, relationship="EXPOSES", confidence=ep.confidence)

        return self.export_json()

    def export_json(self) -> Dict[str, Any]:
        """Export graph into serializable JSON payload."""
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "type": data.get("type", "UNKNOWN"),
                "label": data.get("label", node_id),
                "properties": data.get("properties", {}),
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "relationship": data.get("relationship", "RELATED_TO"),
                "confidence": data.get("confidence", 1.0),
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Alias for export_json."""
        return self.export_json()
