"""Unit tests for the web management REST adapter DTOs (web/schemas.py).

Spec refs:
    web-management-system project-management delta REQ-002 Scenario
    "Invalid slug format" — slug `^[a-z0-9]+(-[a-z0-9]+)*$` (422 path).
    web-management-system web-api-management delta REQ-003 Scenario
    "Validation failure on create project" — error envelope shape.
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from opensddrag.web.schemas import ErrorEnvelope, ProjectCreate

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# ── Unit 1: ProjectCreate.slug validation (REQ-002 project-management) ───────


def test_project_create_rejects_invalid_slug() -> None:
    # WHEN a payload carries a slug that is not kebab-case ("My Project!")
    # THEN pydantic validation MUST fail (feeds HTTP 422 VALIDATION_ERROR).
    with pytest.raises(ValidationError) as exc_info:
        ProjectCreate(name="My Project", slug="My Project!", description="d")
    errors = exc_info.value.errors()
    assert any("slug" in str(e["loc"]) for e in errors), (
        f"expected a 'slug' field error, got: {errors}"
    )


def test_project_create_accepts_kebab_case_slugs() -> None:
    # WHEN slugs "demo" and "add-user-auth" are provided
    # THEN they MUST pass validation and normalize onto the model.
    ok1 = ProjectCreate(name="Demo", slug="demo", description="A demo project")
    assert ok1.slug == "demo"
    ok2 = ProjectCreate(name="Add", slug="add-user-auth", description="")
    assert ok2.slug == "add-user-auth"


def test_project_create_slug_pattern_via_regex_helper() -> None:
    # The canonical pattern the DTO enforces, exposed for router reuse.
    from opensddrag.web.schemas import SLUG_PATTERN

    assert SLUG_PATTERN.fullmatch("demo")
    assert SLUG_PATTERN.fullmatch("add-user-auth")
    assert not SLUG_PATTERN.fullmatch("My Project!")
    assert not SLUG_PATTERN.fullmatch("-demo")
    assert not SLUG_PATTERN.fullmatch("demo-")


# ── Unit 2: ErrorEnvelope serialization (REQ-003 web-api-management) ─────────


def test_error_envelope_shape() -> None:
    # The REST error envelope MUST mirror the MCP adapter envelope:
    # {"error": {"code": <UPPER_SNAKE>, "message": str, "details": optional}}.
    env = ErrorEnvelope(code="VALIDATION_ERROR", message="bad payload", details=["slug required"])
    data = env.to_struct()
    assert data == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "bad payload",
            "details": ["slug required"],
        }
    }


def test_error_envelope_without_details() -> None:
    # WHEN details is omitted
    # THEN the "details" key MUST not appear in the serialized envelope.
    env = ErrorEnvelope(code="NOT_FOUND", message="project does not exist")
    data = env.to_struct()
    assert "details" not in data["error"]
    assert data == {"error": {"code": "NOT_FOUND", "message": "project does not exist"}}