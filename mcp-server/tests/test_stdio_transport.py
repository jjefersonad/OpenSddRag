"""Verify the transport-level auth wiring.

* stdio: the process must not reference ``AuthMiddleware``.
* SSE / HTTP: ``_main_sse`` assembles the app through ``build_http_app``,
  which applies ``AuthMiddleware`` to the ``/mcp`` mount when auth is
  enabled (``auth_enabled``).

The auth wiring moved from ``_main_sse`` into ``build_http_app`` as part of
``web-management-system`` (mcp-server REQ-016); asserting only on
``_main_sse``'s source is no longer valid.
"""

import inspect

from opensddrag.mcp import server as server_module


def test_stdio_has_no_auth_middleware():
    """The _main_stdio function must not reference AuthMiddleware."""
    source = inspect.getsource(server_module._main_stdio)
    assert "AuthMiddleware" not in source


def test_sse_references_auth_middleware():
    """_main_sse delegates to build_http_app, which wires AuthMiddleware."""
    sse_source = inspect.getsource(server_module._main_sse)
    assert "build_http_app" in sse_source

    app_source = inspect.getsource(server_module.build_http_app)
    assert "AuthMiddleware" in app_source
    assert "auth_enabled" in app_source
