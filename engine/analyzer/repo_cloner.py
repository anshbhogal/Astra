import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import git


@dataclass
class CloneResult:
    repository_path: Path
    commit_sha: str
    branch: str
    remote_url: str


class GitRepoCloner:
    """Secure Git repository synchronization and workspace isolation engine."""

    def __init__(self, max_size_mb: int = 250):
        self.max_size_mb = max_size_mb

    def clone(
        self,
        repository_url: str,
        destination_dir: Path,
        branch: Optional[str] = None,
    ) -> CloneResult:
        """Clone remote or local Git repository into isolated destination sandbox."""
        destination_path = Path(destination_dir).resolve()

        if destination_path.exists():
            shutil.rmtree(destination_path, ignore_errors=True)
        destination_path.mkdir(parents=True, exist_ok=True)

        clone_kwargs = {"depth": 1}
        if branch:
            clone_kwargs["branch"] = branch

        clone_env = os.environ.copy()
        clone_env["GIT_TERMINAL_PROMPT"] = "0"
        clone_env["GIT_SSL_NO_VERIFY"] = "true"

        try:
            repo = git.Repo.clone_from(
                url=repository_url,
                to_path=str(destination_path),
                env=clone_env,
                **clone_kwargs
            )
        except Exception as exc:
            # Clean up partial directory on clone failure
            shutil.rmtree(destination_path, ignore_errors=True)
            err_str = str(exc)
            if "could not read Username" in err_str or "terminal prompts disabled" in err_str or "Authentication failed" in err_str:
                raise RuntimeError(
                    f"Repository '{repository_url}' is private or requires authentication. "
                    "Please provide a GitHub Personal Access Token in the URL format: "
                    "https://<token>@github.com/username/repository.git"
                ) from exc
            raise RuntimeError(f"Git clone failed for '{repository_url}': {err_str}") from exc

        # Verify size limit
        total_size_bytes = sum(f.stat().st_size for f in destination_path.rglob('*') if f.is_file())
        size_mb = total_size_bytes / (1024 * 1024)
        if size_mb > self.max_size_mb:
            shutil.rmtree(destination_path, ignore_errors=True)
            raise ValueError(f"Repository size ({size_mb:.2f} MB) exceeds maximum limit ({self.max_size_mb} MB).")

        commit_sha = repo.head.commit.hexsha
        active_branch = branch or (repo.active_branch.name if not repo.head.is_detached else "main")

        return CloneResult(
            repository_path=destination_path,
            commit_sha=commit_sha,
            branch=active_branch,
            remote_url=repository_url,
        )

    def cleanup(self, destination_dir: Path) -> None:
        """Remove workspace sandbox directory."""
        dest = Path(destination_dir).resolve()
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
