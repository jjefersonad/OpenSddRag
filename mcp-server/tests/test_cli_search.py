"""Regression tests for the `opensddrag-server search` CLI routing.

Capability: `cli-search-routing` of the `fix-cli-async-callback` change.

These tests guard two pre-existing bugs that were fixed together in
`cli/search.py`:

  1. **Ambiguous routing.** The `search` callback default used to accept a
     positional `query` Argument while the `artifacts` subcommand accepted
     the same positional. Click/typer routed the positional value as a
     *subcommand name*, so `search "query"` failed with
     `Error: No such command 'query'`. The fix removes every parameter from
     the callback (it is now help-on-empty).
  2. **The `async def`-never-awaited trap.** Making the subcommand
     `async def` does NOT work on the installed typer 0.26.7 / click 8.4.1:
     the coroutine is never awaited, so the search silently returns nothing
     (exit 0, `RuntimeWarning: coroutine ... was never awaited`). The
     subcommand is therefore a plain `def` that drives the async repository
     via `asyncio.run`, matching the other CLI modules.

The CLI is invoked in a real subprocess rather than via
`typer.testing.CliRunner`: the runner has a known incompatibility with the
async path on typer 0.26.7, and a subprocess exercises the exact entry point
a user hits.
"""

import os
import subprocess
import sys
from pathlib import Path

# NOTE: invocation entry point — see the change task `cli-3`.
# The console script installed by `[project.scripts]`
# (`opensddrag-server = opensddrag.cli.main:app`), resolved inside the same
# venv as the test interpreter. The change's task originally suggested
# `python -m opensddrag_server`, but no such module / `__main__` entry point
# exists; the console script is the real, user-facing invocation.
_CLI = Path(sys.executable).parent / "opensddrag-server"

# The subprocess does not inherit the in-process env mutation that
# `conftest.py` performs for the async suite, so the isolated test DB is
# passed explicitly. Honour `TEST_DATABASE_URL` (CI / `.env.test`) and fall
# back to the local test DB on port 54327 (`docker-compose.test.yml`).
_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql://opensddrag:opensddrag@localhost:54327/opensddrag_test",
    ),
)


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": _TEST_DB_URL}
    return subprocess.run(
        [str(_CLI), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_search_no_args_shows_usage():
    """`search` with no subcommand exits 0 and prints the help-on-empty
    usage line — it must never route the empty input as a subcommand.
    """
    proc = _run_cli("search")
    assert proc.returncode == 0, proc.stderr
    assert "artifacts" in proc.stdout
    assert "No such command" not in (proc.stdout + proc.stderr)


def test_search_artifacts_runs_and_is_awaited():
    """`search artifacts "<query>" --all` exits 0 with the async body
    actually executed — guarding BOTH the routing bug and the
    `async def`-never-awaited bug. `--all` is used so the test does not
    depend on any particular project being seeded in the test DB.
    """
    proc = _run_cli("search", "artifacts", "get_harness_checklist", "--all", "-n", "1")
    assert proc.returncode == 0, proc.stderr
    combined = proc.stdout + proc.stderr
    # Routing regression guard.
    assert "No such command" not in combined
    # `async def`-never-awaited regression guard.
    assert "was never awaited" not in combined
    assert "cannot be called from a running event loop" not in combined


def test_search_help_lists_artifacts_subcommand():
    """`search --help` exits 0 and advertises the `artifacts` subcommand."""
    proc = _run_cli("search", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "artifacts" in proc.stdout
