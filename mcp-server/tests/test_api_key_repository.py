from datetime import datetime, timedelta, timezone

import pytest

from opensddrag.db import api_key_repository


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
