"""Unit tests for `_resolve_project_id` — no DB required.

Spec refs:
    fix-multitenant-project-resolution-tool-project-resolution-spec
    REQ-001: explicit slug wins over caller slug and env
    REQ-002: caller-bound slug used when no explicit slug, env not consulted
    REQ-003 (implicit): env fallback applies for stdio callers (caller_slug=None)
    REQ-004 (implicit): ProjectNotResolvableError raised when nothing resolves
"""

from __future__ import annotations

import unittest.mock as mock
from uuid import UUID

import pytest

from opensddrag.core.domain.errors import ProjectNotResolvableError
from opensddrag.infrastructure.pg.tool_executors import _resolve_project_id

_FAKE_UUID = UUID("aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb")

_REQUIRE_PATH = (
    "opensddrag.infrastructure.pg.tool_executors.project_repository.require_project"
)
_SETTINGS_PATH = "opensddrag.infrastructure.pg.tool_executors.settings"


def _fake_project(slug: str):
    p = mock.MagicMock()
    p.id = _FAKE_UUID
    p.slug = slug
    return p


@pytest.mark.asyncio
async def test_explicit_slug_wins():
    """REQ-001: slug='foo' is resolved; caller_slug and env are ignored."""
    with mock.patch(
        _REQUIRE_PATH,
        new=mock.AsyncMock(return_value=_fake_project("foo")),
    ) as require_mock:
        result = await _resolve_project_id("foo", "caller-slug")

    require_mock.assert_awaited_once_with("foo")
    assert result == _FAKE_UUID


@pytest.mark.asyncio
async def test_caller_slug_used_when_no_explicit_slug():
    """REQ-002: caller_slug='bar' is resolved when slug=None; env is not consulted."""
    with (
        mock.patch(
            _REQUIRE_PATH,
            new=mock.AsyncMock(return_value=_fake_project("bar")),
        ) as require_mock,
        mock.patch(_SETTINGS_PATH) as settings_mock,
    ):
        settings_mock.opensddrag_project = "env-project"
        result = await _resolve_project_id(None, "bar")

    require_mock.assert_awaited_once_with("bar")
    assert result == _FAKE_UUID


@pytest.mark.asyncio
async def test_env_fallback_used_for_stdio_caller():
    """stdio path: slug=None, caller_slug=None → env 'baz' is resolved."""
    with (
        mock.patch(
            _REQUIRE_PATH,
            new=mock.AsyncMock(return_value=_fake_project("baz")),
        ) as require_mock,
        mock.patch(_SETTINGS_PATH) as settings_mock,
    ):
        settings_mock.opensddrag_project = "baz"
        result = await _resolve_project_id(None, None)

    require_mock.assert_awaited_once_with("baz")
    assert result == _FAKE_UUID


@pytest.mark.asyncio
async def test_project_not_resolvable_error_raised():
    """No resolvable project fails loudly with an actionable message."""
    with mock.patch(_SETTINGS_PATH) as settings_mock:
        settings_mock.opensddrag_project = None

        with pytest.raises(ProjectNotResolvableError, match="project_slug|api key"):
            await _resolve_project_id(None, None)
