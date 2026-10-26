import os
import pytest

@pytest.mark.asyncio
async def test_container_runs_as_non_root_user():
    """
    Security Audit Task P6-2: Verify backend application does not execute as root (UID 0).
    Ensures container root isolation and non-root execution (appuser: UID 1000).
    """
    current_uid = os.getuid()
    current_gid = os.getgid()

    # Must NOT be root
    assert current_uid != 0, f"Vulnerability P6-2: Container process running as privileged root (UID {current_uid})"
    assert current_gid != 0, f"Vulnerability P6-2: Container process running as privileged root group (GID {current_gid})"
    assert current_uid == 1000, f"Expected non-root appuser UID 1000, got {current_uid}"
