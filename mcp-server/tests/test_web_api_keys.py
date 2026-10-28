"""SqlManagementService API-key management (dashboard keys page)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from opensddrag.core.domain.errors import (
    ManagementValidationError,
    ResourceNotFoundError,
)
from opensddrag.db import api_key_repository, project_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.project import ProjectCreate


def _svc() -> SqlManagementService:
    return SqlManagementService()


async def _make_project(prefix: str):
    suffix = uuid4().hex[:8]
    project = await project_repository.create_project(
        ProjectCreate(slug=f"{prefix}-{suffix}", name=f"{prefix}-{suffix}")
    )
    return project


async def _delete_project(project) -> None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM projects WHERE id = %s", (str(project.id),)
            )


@pytest.mark.asyncio
async def test_create_list_revoke_api_key_roundtrip():
    project = await _make_project("keys-web")
    svc = _svc()
    try:
        created = await svc.create_api_key("dashboard test", project.slug, None)
        assert created["key"]
        assert created["prefix"] == created["key"][:8]
        assert created["project_slug"] == project.slug
        assert created["status"] == "active"
        assert "key_hash" not in created

        listed = await svc.list_api_keys(project.slug, include_revoked=False)
        assert [k["id"] for k in listed] == [created["id"]]
        assert "key" not in listed[0]
        assert "key_hash" not in listed[0]

        hidden = await api_key_repository.lookup_by_hash(created["key"])
        assert hidden is not None

        revoked = await svc.revoke_api_key(created["id"])
        assert revoked["status"] == "revoked"
        assert await api_key_repository.lookup_by_hash(created["key"]) is not None
        after = await svc.list_api_keys(project.slug, include_revoked=False)
        assert after == []
    finally:
        await _delete_project(project)


@pytest.mark.asyncio
async def test_create_api_key_unknown_project_404():
    with pytest.raises(ResourceNotFoundError):
        await _svc().create_api_key("x", "does-not-exist")


@pytest.mark.asyncio
async def test_revoke_unknown_key_404():
    with pytest.raises(ResourceNotFoundError):
        await _svc().revoke_api_key("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_list_api_keys_items_carry_fields_and_hide_secrets():
    """REQ-001: every item listed through the service carries the full
    DTO — id, prefix, description, project_slug, timestamps and derived
    status — and never leaks the plaintext `key` or `key_hash`.
    """
    project = await _make_project("keys-shape")
    svc = _svc()
    global_created = await svc.create_api_key("shape global", None, None)
    scoped_created = await svc.create_api_key("shape scoped", project.slug, None)
    try:
        listed = await svc.list_api_keys(include_revoked=False)
        assert listed
        for item in listed:
            assert set(item) == {
                "id",
                "prefix",
                "description",
                "project_slug",
                "created_at",
                "expires_at",
                "revoked_at",
                "status",
            }
        listed_ids = {item["id"] for item in listed}
        assert {global_created["id"], scoped_created["id"]} <= listed_ids
        by_id = {item["id"]: item for item in listed}
        assert by_id[global_created["id"]]["project_slug"] is None
        assert by_id[scoped_created["id"]]["project_slug"] == project.slug
        assert all(item["description"] for item in listed)
        assert all(item["created_at"] for item in listed)
        assert all(item["revoked_at"] is None for item in listed)
    finally:
        await svc.revoke_api_key(global_created["id"])
        await _delete_project(project)


@pytest.mark.asyncio
async def test_list_api_keys_default_omits_revoked_and_scope_rules():
    """REQ-004: the service default (`include_revoked=False`) omits
    revoked rows, `include_revoked=True` shows them again, and
    `scope=global` combined with a project slug is a validation error.
    """
    project = await _make_project("keys-scope")
    svc = _svc()
    live = await svc.create_api_key("scope live", project.slug, None)
    dead = await svc.create_api_key("scope dead", project.slug, None)
    await svc.revoke_api_key(dead["id"])
    try:
        listed = await svc.list_api_keys(project.slug)
        assert {item["id"] for item in listed} == {live["id"]}

        explicit = await svc.list_api_keys(project.slug, include_revoked=True)
        assert {item["id"] for item in explicit} == {live["id"], dead["id"]}
        dead_row = next(item for item in explicit if item["id"] == dead["id"])
        assert dead_row["status"] == "revoked"

        with pytest.raises(ManagementValidationError):
            await svc.list_api_keys(project.slug, scope="global")

        globals_only = await svc.list_api_keys(scope="global")
        assert all(item["project_slug"] is None for item in globals_only)
    finally:
        await svc.revoke_api_key(live["id"])
        await _delete_project(project)


@pytest.mark.asyncio
async def test_create_api_key_scoped_shape_and_lookup():
    """REQ-002: a project-scoped create returns a 64-char hex `key`
    (once), `prefix` matching the key, `project_slug` and
    `status=active`, never `key_hash`, and the plaintext hash-looks-up
    to the stored row.
    """
    project = await _make_project("keys-create")
    svc = _svc()
    try:
        created = await svc.create_api_key("scoped shape", project.slug, None)
        assert len(created["key"]) == 64
        assert all(c in "0123456789abcdef" for c in created["key"])
        assert created["prefix"] == created["key"][:8]
        assert created["project_slug"] == project.slug
        assert created["status"] == "active"
        assert "key_hash" not in created
        listed = await svc.list_api_keys(project.slug)
        assert "key" not in listed[0]

        found = await api_key_repository.lookup_by_hash(created["key"])
        assert found is not None
        assert str(found.id) == created["id"]
    finally:
        await _delete_project(project)


@pytest.mark.asyncio
async def test_create_api_key_global_and_unknown_slug():
    """REQ-002: creating without a project slug yields a global key
    (`project_slug` null) whose plaintext is returned once; creating
    with an unknown slug raises not-found and persists no row; a
    malformed `expires_at` raises a validation error.
    """
    svc = _svc()
    before_ids = {
        k.id for k in await api_key_repository.list_keys(include_revoked=True)
    }

    created = await svc.create_api_key("global shape", None, None)
    assert created["project_slug"] is None
    assert len(created["key"]) == 64
    try:
        with pytest.raises(ResourceNotFoundError):
            await svc.create_api_key("unknown slug", "keys-create-nope-does-not-exist", None)
        after_ids = {
            k.id for k in await api_key_repository.list_keys(include_revoked=True)
        }
        assert after_ids == before_ids | {UUID(created["id"])}

        with pytest.raises(ManagementValidationError):
            await svc.create_api_key("bad expiry", None, "not-a-date")
    finally:
        await svc.revoke_api_key(created["id"])


@pytest.mark.asyncio
async def test_revoke_api_key_is_idempotent_and_not_found_paths():
    """REQ-003: soft revoke keeps the row and marks it `revoked`; a
    second revoke of the same id returns the same record; unknown ids
    and non-UUID ids are not-found.
    """
    project = await _make_project("keys-revoke")
    svc = _svc()
    created = await svc.create_api_key("revoke idem", project.slug, None)
    try:
        first = await svc.revoke_api_key(created["id"])
        assert first["status"] == "revoked"
        assert first["revoked_at"] is not None

        second = await svc.revoke_api_key(created["id"])
        assert second["id"] == created["id"]
        assert second["status"] == "revoked"
        assert second["revoked_at"] == first["revoked_at"]

        with pytest.raises(ResourceNotFoundError):
            await svc.revoke_api_key(str(uuid4()))
        with pytest.raises(ResourceNotFoundError):
            await svc.revoke_api_key("not-a-uuid")
    finally:
        await _delete_project(project)


@pytest.mark.asyncio
async def test_service_revoke_invalidates_plaintext_for_middleware():
    """REQ-003: after a dashboard revoke the plaintext must fail
    `lookup_by_hash` + `is_valid` — the exact pair `AuthMiddleware`
    applies on `/mcp` — so the old Bearer gets HTTP 401.
    """
    svc = _svc()
    created = await svc.create_api_key("revoke invalidates", None, None)
    stored = await api_key_repository.lookup_by_hash(created["key"])
    assert stored is not None
    assert api_key_repository.is_valid(stored)

    revoked = await svc.revoke_api_key(created["id"])
    assert "key" not in revoked  # REQ-001: revoke payload never leaks
    assert "key_hash" not in revoked

    revoked_lookup = await api_key_repository.lookup_by_hash(created["key"])
    assert revoked_lookup is not None  # row remains
    assert not api_key_repository.is_valid(revoked_lookup)  # → 401 at /mcp
