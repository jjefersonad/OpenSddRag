"""Server bootstrap and shutdown helpers.

Wraps DB lifecycle functions so that `mcp/server.py` has zero
`from opensddrag.db` imports, satisfying the layer-boundary rule in
mcp-server-internals-spec REQ-005.
"""

from opensddrag.cli._seeds import seed_sdd_skills
from opensddrag.db.connection import close_pool, run_migrations


async def bootstrap(warmup_fn=None) -> None:
    await run_migrations()
    await seed_sdd_skills()
    if warmup_fn is not None:
        warmup_fn()


async def shutdown() -> None:
    await close_pool()
