"""CLI tests for `opensddrag-server web` (cli REQ-001/REQ-002).

Spec refs:
    - web-management-system cli delta REQ-002 Scenario "Help lists web command".
    - REQ-001 Scenarios "Start web server" and "serve-ui flag override"
      (an explicit --serve-ui/--no-serve-ui beats the SERVE_WEB_UI setting).
"""

from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from opensddrag.cli.main import app as root_app
from opensddrag.mcp import server as srv

runner = CliRunner()


def test_root_help_lists_web_command() -> None:
    result = runner.invoke(root_app, ["--help"])
    assert result.exit_code == 0
    assert "web" in result.stdout


def test_web_command_shows_flags() -> None:
    result = runner.invoke(root_app, ["web", "--help"])
    assert result.exit_code == 0
    for flag in ("--port", "--host", "--serve-ui"):
        assert flag in result.stdout


def test_serve_ui_flag_overrides_env(monkeypatch) -> None:
    monkeypatch.setattr(srv, "settings", SimpleNamespace(serve_web_ui=False))

    # Explicit flag wins over the (false) setting.
    assert srv.resolve_serve_web_ui(True) is True
    assert srv.resolve_serve_web_ui(False) is False
    # No flag → fall back to the setting.
    assert srv.resolve_serve_web_ui(None) is False


def test_serve_ui_none_uses_env_true(monkeypatch) -> None:
    monkeypatch.setattr(srv, "settings", SimpleNamespace(serve_web_ui=True))
    assert srv.resolve_serve_web_ui(None) is True