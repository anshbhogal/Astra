"""
ASTRA Engine - Phase 6 PKG Graph-Traversing Fault Localizer

Correlates normalized stack trace frames with Knowledge Graph nodes to output ranked candidate fault locations,
reasons, and attribution confidence metrics.
"""

from typing import List, Tuple, Optional, Any
from engine.analysis.models import ParsedException, StackFrame, FaultLocation, ReasoningType
from engine.analyzer.knowledge_graph import ProjectKnowledgeGraph


class FaultLocalizer:
    """Ranks candidate fault locations using stack frame normalization and PKG graph traversal."""

    def __init__(self, pkg: Optional[ProjectKnowledgeGraph] = None):
        self.pkg = pkg

    def localize(
        self,
        parsed_exception: Optional[ParsedException],
        analysis_commit_sha: Optional[str] = None,
        execution_commit_sha: Optional[str] = None,
    ) -> Tuple[List[FaultLocation], float, bool]:
        """
        Returns (fault_locations, attribution_confidence, source_mismatch).
        """
        # 1. Source Snapshot Validation
        source_mismatch = False
        confidence_mult = 1.0

        if analysis_commit_sha and execution_commit_sha and analysis_commit_sha != execution_commit_sha:
            source_mismatch = True
            confidence_mult = 0.70

        if not parsed_exception or not parsed_exception.frames:
            return [], 0.0 * confidence_mult, source_mismatch

        fault_locations: List[FaultLocation] = []

        # Filter project-internal frames
        project_frames = [f for f in parsed_exception.frames if f.is_in_project]
        if not project_frames:
            # Fallback to top frame even if outside project
            project_frames = parsed_exception.frames[:1]

        # 2. Frame-based Fault Location Generation
        for idx, frame in enumerate(project_frames):
            if idx == 0:
                reason = ReasoningType.EXCEPTION_ORIGIN
                base_conf = 0.95
            else:
                reason = ReasoningType.CALLER_FRAME
                base_conf = max(0.50, 0.85 - (idx * 0.10))

            conf = round(base_conf * confidence_mult, 2)
            pkg_node_id = self._find_pkg_func_node(frame.file_path, frame.function_name)

            fault_locations.append(
                FaultLocation(
                    file_path=frame.file_path,
                    line_number=frame.line_number,
                    function_name=frame.function_name,
                    confidence=conf,
                    reason=reason,
                    pkg_node_id=pkg_node_id,
                    code_context=frame.code_snippet,
                )
            )

        # 3. PKG Graph Traversal for Call-Chain Dependencies
        if self.pkg and self.pkg.graph and fault_locations:
            origin_node_id = fault_locations[0].pkg_node_id
            if origin_node_id and self.pkg.graph.has_node(origin_node_id):
                # Traverse outgoing CALLS edges
                for _, target_id, edge_data in self.pkg.graph.out_edges(origin_node_id, data=True):
                    if edge_data.get("relationship") == "CALLS":
                        node_props = self.pkg.graph.nodes[target_id].get("properties", {})
                        t_file = node_props.get("file_path", "")
                        t_line = node_props.get("line_number", 1)
                        t_func = node_props.get("qualified_name", "")

                        if t_file and not any(fl.file_path == t_file and fl.function_name == t_func for fl in fault_locations):
                            fault_locations.append(
                                FaultLocation(
                                    file_path=t_file,
                                    line_number=t_line,
                                    function_name=t_func,
                                    confidence=round(0.60 * confidence_mult, 2),
                                    reason=ReasoningType.DOWNSTREAM_DEPENDENCY,
                                    pkg_node_id=target_id,
                                    code_context="PKG Called Function Dependency",
                                )
                            )

        overall_attribution_conf = fault_locations[0].confidence if fault_locations else 0.0
        return fault_locations, overall_attribution_conf, source_mismatch

    def _find_pkg_func_node(self, file_path: str, function_name: str) -> Optional[str]:
        if not self.pkg or not self.pkg.graph:
            return None

        norm_path = file_path.replace("\\", "/").strip("/")

        for node_id, attrs in self.pkg.graph.nodes(data=True):
            if attrs.get("type") == "FUNCTION":
                props = attrs.get("properties", {})
                pkg_file = props.get("file_path", "").replace("\\", "/").strip("/")
                pkg_func = props.get("qualified_name", "") or attrs.get("label", "")

                if (norm_path and norm_path in pkg_file or pkg_file in norm_path) and (function_name in pkg_func or pkg_func in function_name):
                    return node_id
        return None
