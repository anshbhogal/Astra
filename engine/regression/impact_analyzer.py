"""PKG Weighted Edge Reachability Impact Analyzer.
Traverses the Project Knowledge Graph from modified code symbols to reachable API endpoints.
Computes impact distance, path traces, and confidence scores across weighted edges.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
import networkx as nx


@dataclass
class ImpactedEndpoint:
    endpoint_id: str
    method: str
    path: str
    impact_distance: int
    confidence_score: float
    impact_type: str  # DIRECT, INDIRECT, BROKEN_CONTRACT, SCHEMA_PROPAGATED
    impact_path_trace: List[str] = field(default_factory=list)
    dependency_edge_types: List[str] = field(default_factory=list)


class PKGImpactAnalyzer:
    """Computes reachability from modified AST symbols/modules to API endpoints in NetworkX graphs."""

    EDGE_WEIGHTS = {
        "CALLS": 1.0,
        "ROUTE": 1.0,
        "HANDLED_BY": 1.0,
        "USES": 0.8,
        "INHERITS": 0.7,
        "IMPORTS": 0.5,
        "DEFINES": 0.5,
        "CONTAINS": 0.3,
    }

    def __init__(self, max_depth: int = 5, decay_factor: float = 0.9):
        self.max_depth = max_depth
        self.decay_factor = decay_factor

    def compute_impact(
        self,
        graph: nx.DiGraph,
        changed_symbols: List[str],
        changed_files: List[str],
    ) -> List[ImpactedEndpoint]:
        """Traces reachability from changed symbols/files to endpoint nodes in the graph."""
        impacted_endpoints_map: Dict[str, ImpactedEndpoint] = {}

        # 1. Resolve seed nodes in the graph
        seed_nodes = set()
        for sym in changed_symbols:
            # Match directly or by function name/id
            matched = self._find_matching_nodes(graph, sym, "FUNCTION")
            seed_nodes.update(matched)

        for filepath in changed_files:
            matched = self._find_matching_nodes(graph, filepath, "MODULE")
            seed_nodes.update(matched)

        if not seed_nodes:
            # Fallback: substring matching on all nodes
            for node_id, data in graph.nodes(data=True):
                label = data.get("label", "")
                prop_file = data.get("properties", {}).get("file_path", "")
                if any(cf in node_id or cf in label or cf in prop_file for cf in changed_files):
                    seed_nodes.add(node_id)

        # Reverse graph to search backwards from modified function to callers/endpoints if needed,
        # or traverse both forward and reverse depending on edge direction.
        # In PKG: Module -> DEFINES -> Func, Func -> CALLS -> Func, Endpoint -> HANDLED_BY -> Func
        # So to find Endpoint from Func, we search callers and reverse HANDLED_BY edges.
        rev_graph = graph.reverse(copy=False)

        for seed in seed_nodes:
            self._bfs_reachability(graph, rev_graph, seed, impacted_endpoints_map)

        return list(impacted_endpoints_map.values())

    def _find_matching_nodes(self, graph: nx.DiGraph, query: str, node_type: Optional[str] = None) -> List[str]:
        matched = []
        clean_q = query.replace("\\", "/")
        for node_id, data in graph.nodes(data=True):
            if node_type and data.get("type") != node_type:
                continue
            if query in node_id or clean_q in node_id:
                matched.append(node_id)
            elif "properties" in data:
                props = data["properties"]
                if clean_q in props.get("file_path", "") or query in props.get("qualified_name", ""):
                    matched.append(node_id)
        return matched

    def _bfs_reachability(
        self,
        graph: nx.DiGraph,
        rev_graph: nx.DiGraph,
        seed_node: str,
        result_map: Dict[str, ImpactedEndpoint],
    ):
        # BFS Queue item: (current_node, distance, current_confidence, path_trace, edge_types)
        queue = [(seed_node, 0, 1.0, [seed_node], [])]
        visited: Set[str] = set()

        while queue:
            curr_node, dist, conf, trace, edges = queue.pop(0)

            if curr_node in visited or dist > self.max_depth:
                continue
            visited.add(curr_node)

            node_data = graph.nodes.get(curr_node, {})
            node_type = node_data.get("type", "")

            # Check if this node is an ENDPOINT
            if node_type == "ENDPOINT" or curr_node.startswith("endpoint:"):
                props = node_data.get("properties", {})
                method = props.get("method") or self._parse_endpoint_method(curr_node)
                path = props.get("path") or self._parse_endpoint_path(curr_node)
                ep_id = f"{method.upper()}:{path}"

                impact_type = "DIRECT" if dist == 0 else ("INDIRECT" if dist <= 2 else "DEEP_DEPENDENCY")

                existing = result_map.get(ep_id)
                if not existing or conf > existing.confidence_score:
                    result_map[ep_id] = ImpactedEndpoint(
                        endpoint_id=ep_id,
                        method=method.upper(),
                        path=path,
                        impact_distance=dist,
                        confidence_score=round(conf, 4),
                        impact_type=impact_type,
                        impact_path_trace=trace,
                        dependency_edge_types=edges,
                    )

            # Traverse outgoing in rev_graph (which means incoming callers in forward graph)
            neighbors = list(rev_graph.neighbors(curr_node)) + list(graph.neighbors(curr_node))
            for nxt in neighbors:
                if nxt in visited:
                    continue

                # Determine relationship type
                rel_type = "CALLS"
                if graph.has_edge(curr_node, nxt):
                    rel_type = graph.edges[curr_node, nxt].get("relationship", "CALLS")
                elif graph.has_edge(nxt, curr_node):
                    rel_type = graph.edges[nxt, curr_node].get("relationship", "CALLS")

                weight = self.EDGE_WEIGHTS.get(rel_type, 0.8)
                next_conf = conf * weight * self.decay_factor
                queue.append((nxt, dist + 1, next_conf, trace + [nxt], edges + [rel_type]))

    def _parse_endpoint_method(self, node_id: str) -> str:
        parts = node_id.split(":")
        if len(parts) >= 2:
            return parts[1]
        return "GET"

    def _parse_endpoint_path(self, node_id: str) -> str:
        parts = node_id.split(":")
        if len(parts) >= 3:
            return parts[2]
        return "/"
