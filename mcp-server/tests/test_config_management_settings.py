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


def test_split_origins_multi(fresh_settings):
    # WHEN the raw value holds two comma-separated origins with whitespace
    # THEN split_origins MUST return both origins, trimmed.
    from opensddrag.config import split_origins

    assert split_origins("http://a:3001, http://b:5173") == [
        "http://a:3001",
        "http://b:5173",
    ]


def test_web_origins_default(fresh_settings):
    # WHEN WEB_ORIGIN is unset
    # THEN the web_origins allowlist MUST be exactly the default origin.
    assert fresh_settings.web_origins == ["http://localhost:3001"]


def test_web_origins_single_value(fresh_settings):
    # WHEN WEB_ORIGIN holds a single (non-default) origin...
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setenv("WEB_ORIGIN", "http://app.example.com")
        from opensddrag import config as config_module

        reload(config_module)
        # ...THEN the allowlist MUST contain exactly that one origin
        #     and the raw web_origin string field MUST stay unchanged.
        assert config_module.settings.web_origins == ["http://app.example.com"]
        assert config_module.settings.web_origin == "http://app.example.com"
    finally:
        reload(config_module)


def test_split_origins_hostile_input(fresh_settings):
    # WHEN the raw value carries empty segments and duplicates
    # THEN split_origins MUST return only the real origins (deduped,
    #     order of first occurrence preserved, no empty strings).
    from opensddrag.config import split_origins

    raw = "http://a:3001,, http://a:3001, ,http://b:3001"
    assert split_origins(raw) == ["http://a:3001", "http://b:3001"]