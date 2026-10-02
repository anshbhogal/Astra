# Phase 8 — Regression Testing & Impact Analysis Module Implementation Guide

> **Module Focus:** Git Diff Parser, Code Change Impact Analysis, Knowledge Graph Caller Tracing, Targeted Regression Test Selector, and Selective Suite Orchestrator.

---

## 1. Phase Overview & Objectives

Phase 8 equips Astra with intelligent **Selective Regression Testing**. Running an entire test suite of 2,000 test cases on every small commit is inefficient. When a developer pushes a git commit, Astra parses the modified code files, traces impacted functions using the Project Knowledge Graph, and dynamically selects and executes **only the impacted test cases**.

### Key Deliverables
1. **Git Diff Parser Engine:** Scanner analyzing `git diff` outputs to identify modified files, deleted functions, and altered line ranges.
2. **Impact Analysis Core:** Knowledge graph walker tracing function call graphs (`modified file` -> `function` -> `caller endpoint` -> `affected test case`).
3. **Dynamic Regression Selector:** Test selector filtering the full project test suite into a minimal, targeted subset guaranteed to cover the changed code paths.
4. **Incremental Suite Orchestrator:** Two-tier execution runner: Tier 1 executes impacted tests immediately; Tier 2 executes full regression suite asynchronously.
5. **Change Telemetry Schema:** Database models capturing commit hashes, modified file manifests, and change impact scores.

---

## 2. Technical Stack Specifications

- **Git Diff Analysis:** `GitPython` commit diff inspection.
- **Graph Traversal:** `networkx` predecessor / successor searching on Project Knowledge Graph.

---

## 3. Architecture & Impact Flow

```text
Git Commit / PR Push
         │
         ▼
┌─────────────────────────┐
│ Git Diff Parser Engine  │ Identifies modified file: auth.py (line 42)
└────────┬────────────────┘
         ▼
┌─────────────────────────┐
│ AST Knowledge Graph     │ Traces dependencies: auth.py -> authenticate_user()
│ Traversal Core          │                      -> POST /login
└────────┬────────────────┘
         ▼
┌─────────────────────────┐
│ Dynamic Test Selector   │ Maps endpoint POST /login -> [TC-LOGIN-001, TC-LOGIN-002]
└────────┬────────────────┘
         ▼
┌─────────────────────────┐
│ Tier 1 Targeted Runner  │ Executes 4 impacted tests in 2 seconds (Skipped 1,996 tests)
└─────────────────────────┘
```

---

## 4. Git Diff Parser (`engine/regression/diff_parser.py`)

```python
import git
from typing import List, Dict, Any

class GitDiffParser:
    def __init__(self, repo_path: str):
        self.repo = git.Repo(repo_path)

    def parse_commit_diff(self, commit_hash: str = "HEAD~1") -> List[Dict[str, Any]]:
        changed_files = []
        commit = self.repo.commit(commit_hash)
        diffs = commit.diff(commit.parents[0] if commit.parents else git.NULL_TREE)

        for diff in diffs:
            if diff.b_path and diff.b_path.endswith(".py"):
                changed_files.append({
                    "file_path": diff.b_path,
                    "change_type": diff.change_type, # 'M' (modified), 'A' (added), 'D' (deleted)
                    "a_blob": diff.a_path,
                    "b_blob": diff.b_path
                })
        return changed_files
```

---

## 5. Impact Analysis & Knowledge Graph Mapper (`engine/regression/impact_analyzer.py`)

```python
import networkx as nx
from typing import List, Dict, Any, Set

class ImpactAnalyzer:
    def __init__(self, knowledge_graph_dict: Dict[str, Any]):
        self.graph = nx.node_link_graph(knowledge_graph_dict)

    def find_affected_endpoints(self, modified_files: List[str]) -> Set[str]:
        affected_endpoints = set()

        for modified_file in modified_files:
            # 1. Search for function nodes in Knowledge Graph originating from modified file
            for node, attrs in self.graph.nodes(data=True):
                if attrs.get("type") == "ENDPOINT":
                    # Check if handler function or dependency originates from modified file
                    handler = attrs.get("handler", "")
                    if modified_file in handler or self._is_dependent(node, modified_file):
                        affected_endpoints.add(attrs.get("path"))

        return affected_endpoints

    def _is_dependent(self, endpoint_node: str, modified_file: str) -> bool:
        """Walks graph backwards from endpoint to check if it depends on modified file components."""
        try:
            descendants = nx.descendants(self.graph, endpoint_node)
            for desc in descendants:
                if modified_file in desc:
                    return True
        except Exception:
            pass
        return False
```

---

## 6. Dynamic Test Case Selector (`engine/regression/selector.py`)

```python
from typing import List, Dict, Any, Set

class DynamicTestSelector:
    @staticmethod
    def select_tests_for_execution(all_test_cases: List[Dict[str, Any]], affected_endpoints: Set[str]) -> List[Dict[str, Any]]:
        selected_tests = []
        
        # If no specific endpoint impact found, return empty or fallback to top priority tests
        if not affected_endpoints:
            return all_test_cases[:5]  # Fallback to top 5 sanity tests

        for test in all_test_cases:
            if test.get("endpoint") in affected_endpoints:
                test["regression_reason"] = f"Impacted by code changes in endpoint {test.get('endpoint')}"
                selected_tests.append(test)

        return selected_tests
```

---

## 7. API Controllers (`backend/app/api/v1/regression.py`)

- `POST /regression/impact-analysis` — Accepts commit hash or PR branch name; executes `GitDiffParser` and returns list of impacted source files and endpoints.
- `POST /regression/run` — Triggers dynamic test selection and dispatches Celery execution tasks for impacted test cases only.
- `GET /projects/{id}/regression-history` — Retrieves telemetry on historical regression runs, number of skipped tests, and time saved.

---

## 8. Verification & Test Plan

1. **Git Diff Line Extractor Test:**
   - Modify line 15 in `auth.py`. Run `parse_commit_diff()`. Verify system isolates `auth.py` in returned modified files list.
2. **Knowledge Graph Impact Tracing Test:**
   - Pass modified file `backend/services/auth_service.py` to `ImpactAnalyzer`. Verify graph traversal correctly flags endpoint `/login` as affected.
3. **Execution Speed Benchmarking Test:**
   - Given a suite of 100 test cases, modify a single isolated endpoint (`/health`). Run dynamic test selector. Verify selector picks only 2 health-check test cases, achieving a 98% execution reduction.
