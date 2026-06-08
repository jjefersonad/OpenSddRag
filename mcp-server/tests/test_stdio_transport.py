"""Verify that stdio transport does not load the auth middleware."""

import inspect

from opensddrag.mcp import server as server_module


def test_stdio_has_no_auth_middleware():
    """The _main_stdio function must not reference AuthMiddleware."""
    source = inspect.getsource(server_module._main_stdio)
    assert "AuthMiddleware" not in source


def test_sse_references_auth_middleware():
    """The _main_sse function must reference AuthMiddleware when auth is enabled."""
    source = inspect.getsource(server_module._main_sse)
    assert "AuthMiddleware" in source
    assert "auth_enabled" in source
