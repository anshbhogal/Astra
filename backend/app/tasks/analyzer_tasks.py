import os
import shutil
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.domain import ProjectAnalysis, DiscoveredEndpoint, AnalysisStatus, AnalysisStage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from engine.analyzer.repo_cloner import GitRepoCloner
from engine.analyzer.file_scanner import FileScanner
from engine.analyzer.language_detector import LanguageDetector
from engine.analyzer.framework_detector import FrameworkDetector
from engine.analyzer.parsers.python_ast import PythonASTParser
from engine.analyzer.endpoint_extractor import EndpointExtractor
from engine.analyzer.knowledge_graph import ProjectKnowledgeGraph


def utc_now():
    return datetime.now(timezone.utc)


async def execute_analysis_pipeline(analysis_id_str: str) -> None:
    analysis_id = uuid.UUID(analysis_id_str)
    workspace_dir = f"/app/workspaces/{analysis_id}"
    repo_dir = os.path.join(workspace_dir, "repository")

    task_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TaskSessionLocal = async_sessionmaker(bind=task_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with TaskSessionLocal() as db:
            stmt = select(ProjectAnalysis).where(ProjectAnalysis.id == analysis_id)
            result = await db.execute(stmt)
            analysis = result.scalar_one_or_none()

            if not analysis:
                return

            try:
                # Stage 1: CLONING
                analysis.status = AnalysisStatus.RUNNING
                analysis.current_stage = AnalysisStage.CLONING
                analysis.progress_percent = 10
                analysis.started_at = utc_now()
                await db.commit()

                cloner = GitRepoCloner()
                clone_res = cloner.clone(repository_url=analysis.repository_url, destination_dir=repo_dir, branch=analysis.branch)
                analysis.commit_sha = clone_res.commit_sha
                analysis.branch = clone_res.branch

                # Stage 2: SCANNING
                analysis.current_stage = AnalysisStage.SCANNING
                analysis.progress_percent = 30
                await db.commit()

                scanner = FileScanner()
                source_files = scanner.scan(repo_dir)
                analysis.scanned_files_count = len(source_files)

                lang_detector = LanguageDetector()
                detected_lang, _ = lang_detector.detect_primary_language(source_files)
                analysis.detected_language = detected_lang

                framework_detector = FrameworkDetector()
                f_result = framework_detector.detect(repo_dir, source_files, detected_lang)
                analysis.detected_framework = f_result.framework
                analysis.framework_confidence = f_result.confidence

                # Stage 3: AST_PARSING
                analysis.current_stage = AnalysisStage.AST_PARSING
                analysis.progress_percent = 50
                await db.commit()

                python_parser = PythonASTParser()
                parsed_count = 0
                all_functions = []

                for sf in source_files:
                    if sf.language == "Python":
                        parsed_file = python_parser.parse(sf)
                        parsed_count += 1
                        all_functions.extend(parsed_file)

                analysis.parsed_files_count = parsed_count

                # Extract API Endpoints
                extractor = EndpointExtractor()
                api_endpoints = extractor.extract(all_functions, framework=f_result.framework, source_files=source_files)
                analysis.endpoint_count = len(api_endpoints)

                # Stage 4: GRAPH_BUILDING
                analysis.current_stage = AnalysisStage.GRAPH_BUILDING
                analysis.progress_percent = 75
                await db.commit()

                pkg = ProjectKnowledgeGraph(repo_name=analysis.repository_url.split("/")[-1])
                pkg.build(source_files, all_functions, api_endpoints)
                graph_json = pkg.to_dict()

                analysis.graph_node_count = len(graph_json.get("nodes", []))
                analysis.graph_edge_count = len(graph_json.get("edges", []))
                analysis.knowledge_graph = graph_json

                # Stage 5: PERSISTING & DB Record creation
                analysis.current_stage = AnalysisStage.PERSISTING
                analysis.progress_percent = 90
                await db.commit()

                # Insert DiscoveredEndpoints
                for ep in api_endpoints:
                    db_ep = DiscoveredEndpoint(
                        analysis_id=analysis.id,
                        method=ep.method,
                        path=ep.path,
                        function_name=ep.function_name,
                        parameters=[p.__dict__ if hasattr(p, "__dict__") else p for p in ep.parameters],
                        request_model=ep.request_model,
                        response_model=ep.response_model,
                        framework=ep.framework,
                        confidence=ep.confidence,
                        file_path=ep.file_path,
                        line_number=ep.line_number
                    )
                    db.add(db_ep)

                analysis.status = AnalysisStatus.COMPLETED
                analysis.current_stage = AnalysisStage.FINISHED
                analysis.progress_percent = 100
                analysis.completed_at = utc_now()
                await db.commit()

            except Exception as e:
                analysis.status = AnalysisStatus.FAILED
                analysis.error_message = str(e)
                analysis.completed_at = utc_now()
                await db.commit()
    finally:
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        await task_engine.dispose()


@celery_app.task(name="tasks.run_project_analysis_task")
def run_project_analysis_task(analysis_id_str: str) -> Dict[str, Any]:
    asyncio.run(execute_analysis_pipeline(analysis_id_str))
    return {"analysis_id": analysis_id_str, "status": "FINISHED"}
