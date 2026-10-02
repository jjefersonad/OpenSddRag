"""Unit tests for the web-management-system config settings additions.

Spec refs:
    web-management-system mcp-server delta REQ-013 Scenario
    "Settings singleton extended" — MANAGEMENT_API_TOKEN / WEB_ORIGIN.
"""

from importlib import reload

import pytest


@pytest.fixture()
def fresh_settings(monkeypatch):
    """Reload config.py with a controlled environment and return fresh settings."""
    from opensddrag import config as config_module

    monkeypatch.delenv("MANAGEMENT_API_TOKEN", raising=False)
    monkeypatch.delenv("WEB_ORIGIN", raising=False)
    reload(config_module)
    yield config_module.settings
    reload(config_module)  # restore import-time state for other tests


def test_management_token_read_from_env(monkeypatch, fresh_settings):
    # WHEN MANAGEMENT_API_TOKEN is set in the environment...
    monkeypatch.setenv("MANAGEMENT_API_TOKEN", "abc")
    from opensddrag import config as config_module

    reload(config_module)
    try:
        # ...THEN settings.management_token equals that value.
        assert config_module.settings.management_token == "abc"
    finally:
        monkeypatch.delenv("MANAGEMENT_API_TOKEN", raising=False)
        reload(config_module)


def test_management_token_default_is_none(fresh_settings):
    # WHEN the env var is absent
    # THEN management_token MUST be None (fail-closed for the REST auth dependency).
    assert fresh_settings.management_token is None


def test_web_origin_default(fresh_settings):
    # WHEN WEB_ORIGIN is unset
    # THEN settings.web_origin MUST default to http://localhost:3001.
    assert fresh_settings.web_origin == "http://localhost:3001"