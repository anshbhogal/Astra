# ASTRA Route Authorization Matrix

| HTTP Method | Route Path | Auth Dependency | Role / Access Requirement | Verified Status |
|---|---|---|---|---|
| `GET` | `/health` | None | Public (Liveness probe) | Allowed Public |
| `GET` | `/health/ready` | None | Public (Readiness probe) | Allowed Public |
| `GET` | `/api/v1/health` | None | Public (Liveness probe) | Allowed Public |
| `GET` | `/api/v1/health/ready` | None | Public (Readiness probe) | Allowed Public |
| `POST` | `/api/v1/auth/login` | None | Public (Credential verification) | Allowed Public |
| `POST` | `/api/v1/auth/register` | None | Public (Self-registration) | Allowed Public |
| `POST` | `/api/v1/auth/change-password` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/auth/me` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/webhooks/github` | Webhook HMAC Signature | GitHub Webhook Secret Signature (`X-Hub-Signature-256`) | Enforced |
| `POST` | `/api/v1/repair/webhooks/github/pr-merged` | Webhook HMAC Signature | GitHub Webhook Secret Signature (`X-Hub-Signature-256`) | Enforced |
| `GET` | `/api/v1/admin/users` | `get_current_user` | `ADMIN` only (`require_admin`) | Enforced |
| `POST` | `/api/v1/admin/users` | `get_current_user` | `ADMIN` only (`require_admin`) | Enforced |
| `GET` | `/api/v1/admin/users/pending` | `get_current_user` | `ADMIN` only (`require_admin`) | Enforced |
| `DELETE` | `/api/v1/admin/users/{user_id}` | `get_current_user` | `ADMIN` only (`require_admin`) | Enforced |
| `POST` | `/api/v1/admin/users/{user_id}/approve` | `get_current_user` | `ADMIN` only (`require_admin`) | Enforced |
| `POST` | `/api/v1/admin/users/{user_id}/reject` | `get_current_user` | `ADMIN` only (`require_admin`) | Enforced |
| `GET` | `/api/v1/projects/` | `get_current_user` | Any authenticated user (returns only accessible projects) | Enforced |
| `POST` | `/api/v1/projects/` | `get_current_user` | `ADMIN`, `DEVELOPER` | Enforced |
| `GET` | `/api/v1/projects/{project_id}` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `PUT` | `/api/v1/projects/{project_id}` | `get_current_user` | `ADMIN` or Project Owner | Enforced |
| `DELETE` | `/api/v1/projects/{project_id}` | `get_current_user` | `ADMIN` or Project Owner | Enforced |
| `GET` | `/api/v1/projects/{project_id}/members` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/members` | `get_current_user` | `ADMIN` or Project Owner | Enforced |
| `PUT` | `/api/v1/projects/{project_id}/members` | `get_current_user` | `ADMIN` or Project Owner | Enforced |
| `DELETE` | `/api/v1/projects/{project_id}/members/{user_id}` | `get_current_user` | `ADMIN` or Project Owner | Enforced |
| `GET` | `/api/v1/projects/{project_id}/analysis` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/analyze` | `get_current_user` | `ADMIN`, `DEVELOPER`, `TESTER` + `get_project_or_403` | Enforced |
| `GET` | `/api/v1/projects/{project_id}/endpoints` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/functions` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/graph` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/code/tree` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/code/file` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `PUT` | `/api/v1/projects/{project_id}/code/file` | `get_current_user` | `ADMIN`, `DEVELOPER` + `get_project_or_403` | Enforced |
| `POST` | `/api/v1/projects/{project_id}/code/file` | `get_current_user` | `ADMIN`, `DEVELOPER` + `get_project_or_403` | Enforced |
| `DELETE` | `/api/v1/projects/{project_id}/code/file` | `get_current_user` | `ADMIN`, `DEVELOPER` + `get_project_or_403` | Enforced |
| `GET` | `/api/v1/projects/{project_id}/code/defects` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/code/run-tests` | `get_current_user` | `ADMIN`, `DEVELOPER`, `TESTER` + `get_project_or_403` | Enforced |
| `GET` | `/api/v1/projects/{project_id}/defects` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/defects/{defect_id}/comments` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/defects/{defect_id}/comments` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `PATCH` | `/api/v1/projects/{project_id}/defects/{defect_id}/status` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/ml/flaky-tests` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/ml/flaky-tests/{test_case_id}/quarantine` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/ml/healing-candidates` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/ml/healing-candidates/{candidate_id}/apply` | `get_current_user` | `ADMIN`, `DEVELOPER` + `get_project_or_403` | Enforced |
| `POST` | `/api/v1/projects/{project_id}/ml/healing-candidates/{candidate_id}/rollback` | `get_current_user` | `ADMIN`, `DEVELOPER` + `get_project_or_403` | Enforced |
| `GET` | `/api/v1/projects/{project_id}/ml/prioritize` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/ml/train` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/notifications` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/notifications` | `get_current_user` | `ADMIN` or Project Owner (`get_project_or_403`) | Enforced |
| `POST` | `/api/v1/notifications/{channel_id}/test` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/projects/{project_id}/regression/analyses` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/regression/analyze` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/regression/analyses/{analysis_id}` | `get_current_user` | Any authenticated user with project membership | Enforced |
| `GET` | `/api/v1/projects/{project_id}/requirements` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/requirements/traceability` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/requirements/upload` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `PATCH` | `/api/v1/projects/{project_id}/requirements/{requirement_id}/review` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/runs/{run_id}/failure-analysis` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/runs/{run_id}/failure-analysis/analyze` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/sandbox/available-port` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/sandbox/start` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/sandbox/status` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/sandbox/stop` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/test-runs` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/test-runs` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/test-suites` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/test-suites/generate` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/test-suites/generate-advanced` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/projects/{project_id}/unit-tests/run` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/projects/{project_id}/webhooks/logs` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/analytics/overview` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/analytics/projects/{project_id}` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `POST` | `/api/v1/analytics/projects/{project_id}/reports` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/analytics/projects/{project_id}/reports` | `get_current_user` | `get_project_or_403` (Admin, Owner, Assigned Member) | Enforced |
| `GET` | `/api/v1/analytics/reports/{report_id}/export` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/benchmarks/bugs` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/benchmarks/bugs/{bug_id}/trace` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/benchmarks/latest` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/benchmarks/matrix` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/benchmarks/run` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/benchmarks/runs` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/benchmarks/runs/{run_id}` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/benchmarks/runs/matrix` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/generation-jobs/{job_id}` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/generation-jobs/{job_id}/cancel` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/tasks/{task_id}` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/tasks/test` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/test-runs/{test_run_id}` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/test-runs/{test_run_id}/cancel` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/test-runs/{test_run_id}/results` | `get_current_user` | Any authenticated user | Enforced |
| `GET` | `/api/v1/test-suites/{suite_id}/cases` | `get_current_user` | Any authenticated user | Enforced |
| `POST` | `/api/v1/repair/defects/{defect_id}/trigger` | `get_current_user` | `ADMIN`, `DEVELOPER` + defect project access (P0-3) | Pending P0-3 |
| `GET` | `/api/v1/repair/defects/{defect_id}/candidates` | `get_current_user` | defect project access (P0-3) | Pending P0-3 |
| `POST` | `/api/v1/repair/candidates/{candidate_id}/authorize-pr` | `get_current_user` | `ADMIN`, `DEVELOPER` + defect project access (P0-3) | Pending P0-3 |
| `GET` | `/api/v1/repair/jobs/{job_id}` | `get_current_user` | defect project access (P0-3) | Pending P0-3 |
