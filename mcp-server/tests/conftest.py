import os

import pytest_asyncio

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://opensddrag:opensddrag@localhost:54326/opensddrag",
)
os.environ.setdefault("AUTH_ENABLED", "true")

from opensddrag.db.connection import close_pool, get_pool


@pytest_asyncio.fixture(autouse=True, scope="session")
async def db_pool():
    await get_pool()
    yield
    await close_pool()
