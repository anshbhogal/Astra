"""Regression Service Layer.
Orchestrates Phase 8 AST analysis, PKG reachability, test impact mapping, safety gate evaluation,
and DB persistence of selective execution runs.
"""

import uuid
import hashlib
from typing import List, Dict, Any, Optional
import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    Project, TestCase, TestRun, TestResult,
    RegressionAnalysisModel, CodeChangeManifestModel, EndpointImpactRecordModel, SelectiveExecutionRunModel,
    RegressionAnalysisStatus, ExecutionTier
)
from engine.regression.git_diff_parser import GitDiffParser, FileDiff
from engine.regression.ast_change_analyzer import ASTChangeAnalyzer
from engine.regression.impact_analyzer import PKGImpactAnalyzer
from engine.regression.test_impact_mapper import TestImpactMapper
from engine.regression.safety_gate import SafetyGate
from engine.regression.selective_selector import SelectiveSelector
from engine.regression.evaluators import RegressionOracleEvaluator


class RegressionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_regression_impact(
        self,
        project_id: uuid.UUID,
        base_commit: str,
        target_commit: str,
        target_branch: Optional[str] = "main",
        diff_text: Optional[str] = None,
        old_sources: Optional[Dict[str, str]] = None,
        new_sources: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Runs multi-stage selective regression analysis and persists manifest and impact records."""
        # 1. Generate fingerprint
        raw_fingerprint = f"{project_id}:{base_commit}:{target_commit}:{diff_text or ''}"
        analysis_fingerprint = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()[:32]

        # 2. Parse Git Diff
        diff_parser = GitDiffParser()
        file_diffs = diff_parser.parse_diff(diff_text or "")

        # 3. Analyze AST Symbol changes
        ast_analyzer = ASTChangeAnalyzer()
        all_changed_symbols = []
        all_changed_files = []

        old_srcs = old_sources or {}
        new_srcs = new_sources or {}

        for fd in file_diffs:
            all_changed_files.append(fd.new_path)
            if fd.old_path:
                all_changed_files.append(fd.old_path)

            old_code = old_srcs.get(fd.old_path or fd.new_path)
            new_code = new_srcs.get(fd.new_path)

            changed_syms = ast_analyzer.analyze_file_diff(fd, old_source=old_code, new_source=new_code)
            fd.changed_symbols = changed_syms
            for cs in changed_syms:
                all_changed_symbols.append(cs.symbol_id)

        # 4. Load or build PKG graph for project
        graph = await self._build_project_graph(project_id)

        # 5. Compute PKG reachability
        impact_analyzer = PKGImpactAnalyzer(max_depth=5, decay_factor=0.9)
        impacted_endpoints = impact_analyzer.compute_impact(
            graph,
            changed_symbols=all_changed_symbols,
            changed_files=all_changed_files,
        )

        # 6. Fetch project TestCases from DB
        tc_stmt = select(TestCase).where(TestCase.project_id == project_id)
        tc_result = await self.db.execute(tc_stmt)
        test_case_records = list(tc_result.scalars().all())

        test_cases_data = []
        for tc in test_case_records:
            test_cases_data.append({
                "id": str(tc.id),
                "name": tc.name,
                "endpoint": tc.endpoint,
                "method": tc.method,
                "tags": tc.tags if isinstance(tc.tags, list) else [],
                "avg_duration_ms": 120.0,
            })

        # 7. Map impacted endpoints to test cases
        impact_mapper = TestImpactMapper()
        mapped_tests = impact_mapper.map_impacted_tests(impacted_endpoints, test_cases_data)

        # 8. Evaluate Safety Gate
        safety_gate = SafetyGate(fallback_to_full_suite_on_trigger=False)
        targeted_ids = {m.test_case_id for m in mapped_tests}
        safety_result = safety_gate.evaluate_safety(
            file_diffs=file_diffs,
            all_test_cases=test_cases_data,
            targeted_test_ids=targeted_ids,
            pkg_node_count=graph.number_of_nodes(),
        )

        # 9. Dynamic Tiered Selective Selector
        selector = SelectiveSelector()
        selection_res = selector.select_tests(
            analysis_fingerprint=analysis_fingerprint,
            all_test_cases=test_cases_data,
            mapped_impacted_tests=mapped_tests,
            safety_result=safety_result,
        )

        # 10. Persist DB records
        analysis_record = RegressionAnalysisModel(
            project_id=project_id,
            analysis_fingerprint=analysis_fingerprint,
            base_commit=base_commit,
            target_commit=target_commit,
            target_branch=target_branch,
            pkg_snapshot_version="v1.0",
            total_modified_files=len(file_diffs),
            total_modified_symbols=len(all_changed_symbols),
            total_impacted_endpoints=len(impacted_endpoints),
            total_suite_tests=selection_res.total_suite_tests,
            selected_tier1_count=selection_res.selected_tier1_count,
            deferred_tier2_count=selection_res.deferred_tier2_count,
            test_reduction_percent=selection_res.test_reduction_percent,
            estimated_time_avoided_ms=selection_res.estimated_time_avoided_ms,
            impact_confidence=selection_res.impact_confidence,
            safety_expansion_triggered=selection_res.safety_expansion_triggered,
            status=RegressionAnalysisStatus.COMPLETED,
            analysis_warnings=selection_res.analysis_warnings,
        )
        self.db.add(analysis_record)
        await self.db.flush()

        # Code Change Manifests
        for fd in file_diffs:
            manifest = CodeChangeManifestModel(
                regression_analysis_id=analysis_record.id,
                old_path=fd.old_path,
                new_path=fd.new_path,
                change_type=fd.change_type,
                rename_similarity=fd.rename_similarity,
                modified_lines=fd.added_lines + fd.deleted_lines,
                modified_symbols=[cs.symbol_id for cs in fd.changed_symbols],
                change_category=fd.change_category,
            )
            self.db.add(manifest)

        # Endpoint Impact Records
        for ep in impacted_endpoints:
            ep_rec = EndpointImpactRecordModel(
                regression_analysis_id=analysis_record.id,
                endpoint_id=ep.endpoint_id,
                path=ep.path,
                method=ep.method,
                impact_distance=ep.impact_distance,
                confidence_score=ep.confidence_score,
                impact_type=ep.impact_type,
                impact_path_trace=ep.impact_path_trace,
                dependency_edge_types=ep.dependency_edge_types,
            )
            self.db.add(ep_rec)

        await self.db.commit()

        return {
            "analysis_id": str(analysis_record.id),
            "project_id": str(project_id),
            "analysis_fingerprint": analysis_fingerprint,
            "status": "COMPLETED",
            "summary": {
                "total_modified_files": len(file_diffs),
                "total_modified_symbols": len(all_changed_symbols),
                "total_impacted_endpoints": len(impacted_endpoints),
                "total_suite_tests": selection_res.total_suite_tests,
                "selected_tier1_count": selection_res.selected_tier1_count,
                "deferred_tier2_count": selection_res.deferred_tier2_count,
                "test_reduction_percent": selection_res.test_reduction_percent,
                "estimated_time_avoided_ms": selection_res.estimated_time_avoided_ms,
                "impact_confidence": selection_res.impact_confidence,
                "safety_expansion_triggered": selection_res.safety_expansion_triggered,
            },
            "tier1_tests": [t.__dict__ for t in selection_res.tier1_test_details],
            "tier2_tests": [t.__dict__ for t in selection_res.tier2_test_details],
            "warnings": selection_res.analysis_warnings,
        }

    async def get_analysis_by_id(self, analysis_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        stmt = select(RegressionAnalysisModel).where(RegressionAnalysisModel.id == analysis_id)
        res = await self.db.execute(stmt)
        analysis = res.scalar_one_or_none()
        if not analysis:
            return None

        # Fetch manifests
        m_stmt = select(CodeChangeManifestModel).where(CodeChangeManifestModel.regression_analysis_id == analysis_id)
        m_res = await self.db.execute(m_stmt)
        manifests = list(m_res.scalars().all())

        # Fetch endpoint impacts
        ep_stmt = select(EndpointImpactRecordModel).where(EndpointImpactRecordModel.regression_analysis_id == analysis_id)
        ep_res = await self.db.execute(ep_stmt)
        ep_impacts = list(ep_res.scalars().all())

        return {
            "id": str(analysis.id),
            "project_id": str(analysis.project_id),
            "analysis_fingerprint": analysis.analysis_fingerprint,
            "base_commit": analysis.base_commit,
            "target_commit": analysis.target_commit,
            "target_branch": analysis.target_branch,
            "total_modified_files": analysis.total_modified_files,
            "total_modified_symbols": analysis.total_modified_symbols,
            "total_impacted_endpoints": analysis.total_impacted_endpoints,
            "total_suite_tests": analysis.total_suite_tests,
            "selected_tier1_count": analysis.selected_tier1_count,
            "deferred_tier2_count": analysis.deferred_tier2_count,
            "test_reduction_percent": analysis.test_reduction_percent,
            "estimated_time_avoided_ms": analysis.estimated_time_avoided_ms,
            "impact_confidence": analysis.impact_confidence,
            "safety_expansion_triggered": analysis.safety_expansion_triggered,
            "status": analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status),
            "manifests": [
                {
                    "old_path": m.old_path,
                    "new_path": m.new_path,
                    "change_type": m.change_type,
                    "change_category": m.change_category,
                    "modified_symbols": m.modified_symbols,
                }
                for m in manifests
            ],
            "impacted_endpoints": [
                {
                    "endpoint_id": ep.endpoint_id,
                    "path": ep.path,
                    "method": ep.method,
                    "impact_distance": ep.impact_distance,
                    "confidence_score": ep.confidence_score,
                    "impact_type": ep.impact_type,
                    "impact_path_trace": ep.impact_path_trace,
                }
                for ep in ep_impacts
            ],
            "created_at": analysis.created_at.isoformat(),
        }

    async def list_project_analyses(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        stmt = select(RegressionAnalysisModel).where(
            RegressionAnalysisModel.project_id == project_id
        ).order_by(RegressionAnalysisModel.created_at.desc())
        res = await self.db.execute(stmt)
        analyses = list(res.scalars().all())

        return [
            {
                "id": str(a.id),
                "analysis_fingerprint": a.analysis_fingerprint,
                "base_commit": a.base_commit,
                "target_commit": a.target_commit,
                "total_modified_files": a.total_modified_files,
                "total_impacted_endpoints": a.total_impacted_endpoints,
                "selected_tier1_count": a.selected_tier1_count,
                "test_reduction_percent": a.test_reduction_percent,
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "created_at": a.created_at.isoformat(),
            }
            for a in analyses
        ]

    async def _build_project_graph(self, project_id: uuid.UUID) -> nx.DiGraph:
        graph = nx.DiGraph()
        tc_stmt = select(TestCase).where(TestCase.project_id == project_id)
        tc_res = await self.db.execute(tc_stmt)
        test_cases = list(tc_res.scalars().all())

        for tc in test_cases:
            if tc.endpoint and tc.method:
                ep_node = f"endpoint:{tc.method.upper()}:{tc.endpoint}"
                graph.add_node(ep_node, type="ENDPOINT", properties={"method": tc.method.upper(), "path": tc.endpoint})
                func_node = f"func:{tc.name}:handler"
                graph.add_node(func_node, type="FUNCTION", properties={"qualified_name": tc.name, "file_path": tc.endpoint})
                graph.add_edge(ep_node, func_node, relationship="HANDLED_BY", confidence=1.0)

        return graph
