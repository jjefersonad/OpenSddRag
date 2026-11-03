"""Config test for the docker-compose web service (REQ-006/REQ-007).

Runs `docker compose config` and asserts the web service + management env
passthrough are present with the documented defaults. Skips when Docker is
unavailable (CI without a daemon).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not available")
def test_compose_config_has_web_service_and_management_env() -> None:
    result = subprocess.run(
        ["docker", "compose", "config"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    text = result.stdout

    # REQ-006: web service + default port + API base URL arg
    assert "web:" in text
    assert "3001" in text
    assert "http://localhost:8000/api/v1" in text

    # REQ-007: management env passthrough on the mcp service
    assert "MANAGEMENT_API_TOKEN" in text
    assert "WEB_ORIGIN" in text
    assert "SERVE_WEB_UI" in text

    # REQ-008: restart policy
    assert "unless-stopped" in text
