import uuid
from datetime import datetime, timedelta, timezone

import pytest

from opensddrag.db import api_key_repository, project_repository
from opensddrag.db.connection import get_conn
from opensddrag.models.project import ProjectCreate


@pytest.mark.asyncio
async def test_create_and_lookup_key():
    key_record, plaintext = await api_key_repository.create_key(description="test key")
    assert len(plaintext) == 64  # 32 bytes hex-encoded
    assert key_record.key_prefix == plaintext[:8]
    assert key_record.project_id is None
    assert key_record.revoked_at is None

    found = await api_key_repository.lookup_by_hash(plaintext)
    assert found is not None
    assert found.id == key_record.id

    # Clean up
    await api_key_repository.revoke_key(key_record.id)


@pytest.mark.asyncio
async def test_lookup_unknown_key_returns_none():
    result = await api_key_repository.lookup_by_hash("nonexistent_key_that_will_never_match")
    assert result is None


@pytest.mark.asyncio
async def test_revoke_key():
    key_record, plaintext = await api_key_repository.create_key(description="revoke test")
    assert api_key_repository.is_valid(key_record)

    revoked = await api_key_repository.revoke_key(key_record.id)
    assert revoked is not None
    assert revoked.revoked_at is not None
    assert not api_key_repository.is_valid(revoked)


@pytest.mark.asyncio
async def test_revoke_idempotent():
    key_record, _ = await api_key_repository.create_key(description="idempotent revoke")
    await api_key_repository.revoke_key(key_record.id)
    # Revoking again should not raise and still returns the key
    result = await api_key_repository.revoke_key(key_record.id)
    assert result is not None
    assert result.revoked_at is not None


@pytest.mark.asyncio
async def test_expired_key_is_invalid():
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    key_record, _ = await api_key_repository.create_key(description="expired", expires_at=past)
    assert not api_key_repository.is_valid(key_record)

    # Clean up
    await api_key_repository.revoke_key(key_record.id)


@pytest.mark.asyncio
async def test_list_keys():
    key_record, _ = await api_key_repository.create_key(description="list test")
    keys = await api_key_repository.list_keys()
    ids = [k.id for k in keys]
    assert key_record.id in ids

    # Clean up
    await api_key_repository.revoke_key(key_record.id)


async def _make_project() -> "uuid.UUID":
    """Create a throwaway project and return its id.

    Fresh projects have brand-new UUIDs that no pre-existing key
    references, so per-project assertions are robust against leftover
    keys from other tests.
    """
    suffix = uuid.uuid4().hex[:8]
    project = await project_repository.create_project(
        ProjectCreate(slug=f"list-keys-test-{suffix}", name=f"list-keys-test-{suffix}")
    )
    return project.id


async def _delete_projects(*project_ids: "uuid.UUID") -> None:
    """Delete test projects; `api_keys.project_id` CASCADEs, removing
    the keys bound to them (see migration 002_api_keys.sql).
    """
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            for pid in project_ids:
                await cur.execute("DELETE FROM projects WHERE id = %s", (str(pid),))


@pytest.mark.asyncio
async def test_list_keys_strict_project_filter():
    """Regression guard for `fix-multitenant-deploy-regressions`
    (api-key-listing-spec REQ-001). A project filter scopes results to
    that project only — global (`project_id IS NULL`) keys never leak
    into a filtered listing, and two distinct projects report distinct
    sets. Before the fix, `list_keys` used `WHERE project_id = %s OR
    project_id IS NULL`, so every `--project X` returned the same list.
    """
    project_a = await _make_project()
    project_b = await _make_project()
    project_empty = await _make_project()  # a project with no bound keys

    global_key, _ = await api_key_repository.create_key(description="strict-global")
    key_a, _ = await api_key_repository.create_key(
        description="strict-a", project_id=project_a
    )
    key_b, _ = await api_key_repository.create_key(
        description="strict-b", project_id=project_b
    )

    try:
        # Scenario: "Filtering by a project without bound keys" — empty
        # regardless of how many global keys exist.
        assert await api_key_repository.list_keys(project_id=project_empty) == []

        # Scenario: "Two different projects return different sets" — each
        # returns only its own key, never the other's and never globals.
        a_keys = await api_key_repository.list_keys(project_id=project_a)
        b_keys = await api_key_repository.list_keys(project_id=project_b)
        assert [k.id for k in a_keys] == [key_a.id]
        assert [k.id for k in b_keys] == [key_b.id]
        assert global_key.id not in {k.id for k in a_keys}
        assert global_key.id not in {k.id for k in b_keys}

        # Scenario: "Global keys still listed unfiltered" — the
        # unfiltered call returns everything (global + project-bound).
        all_ids = {k.id for k in await api_key_repository.list_keys(project_id=None)}
        assert {global_key.id, key_a.id, key_b.id} <= all_ids
    finally:
        # Deleting the projects cascades to key_a / key_b; revoke the
        # global key (soft) as the sibling tests do.
        await api_key_repository.revoke_key(global_key.id)
        await _delete_projects(project_a, project_b, project_empty)
