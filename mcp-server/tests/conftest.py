import os

import pytest
import pytest_asyncio

# ── Isolated test database wiring ────────────────────────────────────────────
#
# The `improve-retrieval-accuracy` change requires that the pytest suite
# always run against the isolated test database (`docker-compose.test.yml`,
# port 54327), never against the production data on port 54326. We honour two
# sources, in order:
#
#   1. `TEST_DATABASE_URL` (preferred — explicit per-environment override
#      from `.env.test` / CI).
#   2. The local default (54327) so the suite works out of the box when the
#      test DB is up but no env file has been sourced.
#
# Anything that resolves to the production port (54326) is rejected before the
# pool is opened — better to fail fast than to corrupt real data.
_test_db_url = os.environ.get("TEST_DATABASE_URL")
if _test_db_url:
    os.environ["DATABASE_URL"] = _test_db_url
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://opensddrag:opensddrag@localhost:54327/opensddrag_test",
)
os.environ.setdefault("AUTH_ENABLED", "true")

# Guard: refuse to run the suite against the production database. The
# `settings` object is imported here so we get the final, env-merged value.
from opensddrag.config import settings as _settings  # noqa: E402
from opensddrag.db.connection import close_pool, get_pool  # noqa: E402

_PRODUCTION_PORT = "54326"
if f":{_PRODUCTION_PORT}/" in _settings.database_url:
    raise RuntimeError(
        f"Refusing to run tests against production database "
        f"({_settings.database_url}). Set TEST_DATABASE_URL to the isolated "
        f"test DB (see .env.test.example) before running pytest."
    )


@pytest.fixture(scope="session", autouse=True)
def _assert_isolated_test_db():
    """Sanity-check the test suite is wired to a disposable DB, not prod.

    The connection URL must point to a port other than 54326 (the production
    `docker-compose.yml` default). This makes accidental prod-touching
    failures loud and immediate.
    """
    assert f":{_PRODUCTION_PORT}/" not in _settings.database_url, (
        f"Test suite is misconfigured: DATABASE_URL={_settings.database_url} "
        f"points to the production port. Set TEST_DATABASE_URL to the "
        f"isolated test DB (see .env.test.example)."
    )
    yield


@pytest_asyncio.fixture(autouse=True, scope="session")
async def db_pool():
    await get_pool()
    yield
    await close_pool()
