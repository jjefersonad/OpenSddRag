"""Middleware-level CORS tests for the management API.

Spec refs:
    fix-production-cors-errors delta REQ-002 scenarios
    "Preflight from a configured dashboard origin accepted" /
    "Unlisted origin receives no allow-origin header"
    fix-production-cors-errors delta REQ-015/REQ-016 (announce_cors_origins)
"""

import logging

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

DASH = "http://cidurb-data.projetos.monitora.info:3001"
OTHER = "http://localhost:5173"


@pytest.fixture()
def cors_app():
    """Minimal app wrapped with wire_cors and a multi-origin web_origin."""
    from opensddrag.web.deps import wire_cors

    async def ping(request):
        return JSONResponse({"pong": True})

    class FakeSettings:
        web_origin = f"{DASH}, {OTHER}"

    app = Starlette(
        routes=[Route("/api/v1/projects", ping, methods=["GET", "OPTIONS"])],
        middleware=wire_cors(FakeSettings()),
    )
    return TestClient(app)


def test_preflight_from_configured_origin_is_admitted(cors_app):
    # WHEN an OPTIONS preflight arrives from a configured WEB_ORIGIN value
    resp = cors_app.options(
        "/api/v1/projects",
        headers={"Origin": DASH, "Access-Control-Request-Method": "GET"},
    )
    # THEN the middleware SHALL echo that origin so the browser admits
    #     the following cross-origin request.
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == DASH
    allow_headers = resp.headers["access-control-allow-headers"]
    assert "authorization" in allow_headers.lower()


def test_preflight_from_unlisted_origin_gets_no_header(cors_app):
    # WHEN an OPTIONS preflight arrives from an Origin NOT in WEB_ORIGIN
    other_origin = "http://evil.example.com"
    resp = cors_app.options(
        "/api/v1/projects",
        headers={
            "Origin": other_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    # THEN the response MUST NOT include Access-Control-Allow-Origin:
    #     the browser keeps blocking the request.
    headers = {str(k).lower(): v for k, v in resp.headers.items()}
    for header, value in headers.items():
        if header == "access-control-allow-origin":
            assert value != other_origin
    assert "access-control-allow-origin" not in headers


# ── announce_cors_origins (REQ-016 startup announcement) ────────────────────


def test_announce_lists_every_configured_origin(caplog):
    # WHEN the server starts with a non-default multi-origin WEB_ORIGIN
    # THEN exactly one log entry MUST list every allowed origin (INFO).
    from opensddrag.web.deps import announce_cors_origins

    class FakeSettings:
        web_origin = f"{DASH}, {OTHER}"

    with caplog.at_level(logging.INFO, logger="opensddrag.web.deps"):
        announce_cors_origins(FakeSettings())

    cors_records = [r for r in caplog.records if "CORS allowed origins" in r.message]
    assert len(cors_records) == 1
    assert DASH in cors_records[0].message
    assert OTHER in cors_records[0].message
    assert cors_records[0].levelno == logging.INFO


def test_announce_warns_when_allowlist_is_localhost_default(caplog):
    # WHEN WEB_ORIGIN is unset (effective allowlist == the localhost default)
    # THEN the single entry MUST be a WARNING so the stale default is
    #     scannable in production logs.
    from opensddrag.web.deps import announce_cors_origins

    class FakeSettings:
        web_origin = "http://localhost:3001"

    with caplog.at_level(logging.WARNING, logger="opensddrag.web.deps"):
        announce_cors_origins(FakeSettings())

    cors_records = [r for r in caplog.records if "CORS allowed origins" in r.message]
    assert len(cors_records) == 1
    assert "http://localhost:3001" in cors_records[0].message
    assert cors_records[0].levelno == logging.WARNING