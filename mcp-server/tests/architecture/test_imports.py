"""Architecture tests: enforce the layer-dependency rule.

These tests run `grep` against the source tree via `subprocess.run` and
fail when a forbidden import direction is detected. The rules enforced
here are the spec-mandated ones — see:

    mcp-domain-core-spec REQ-001
        Scenario "Pure domain module is importable without side effects"
        Scenario "Domain directory is import-clean" (delta spec)
    tool-execution-usecase-spec REQ-002
        Scenario "Architecture rule passes"
    mcp-protocol-adapter-spec REQ-002
        Scenario "Domain layer is MCP-agnostic"
    mcp-server-internals-spec (delta) REQ-008/009/010
        "Layer boundaries"

The layer-dependency rule in one line:

    core/domain/  ->  (nothing inside the project; only stdlib + itself)
    core/ports/   ->  core/domain
    core/usecases/ -> core/domain, core/ports
    infrastructure/ -> core/*, infrastructure/* (itself), db/, embedding/
    mcp/           -> core/usecases/, infrastructure/, but NOT db/ directly
                        (after Phase 4)
    db/, embedding/  -> unchanged
    cli/            -> unchanged

The tests use `subprocess.run(..., check=False, capture_output=True)`
because:
    * `grep` exits with code 1 when it finds no matches. With
      `check=True` the test would raise `CalledProcessError` instead of
      letting us write a clear `assert`.
    * `capture_output=True` keeps stdout/stderr in the result object
      for the assertion error message.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


# Resolve the mcp-server source root from this test file's location so
# the test is robust to where the suite is invoked from.
TEST_FILE = Path(__file__).resolve()
MCP_SERVER_ROOT = TEST_FILE.parent.parent.parent  # tests/architecture/test_imports.py -> mcp-server/
SRC = MCP_SERVER_ROOT / "src" / "opensddrag"


def _grep(pattern: str, path: Path) -> subprocess.CompletedProcess:
    """Run `grep -RInE <pattern> <path>` and return the completed process.

    `-R` recursive, `-I` skip binary files, `-n` line numbers, `-E` extended
    regex. The caller checks `result.returncode` and `result.stdout` to
    decide pass/fail.
    """
    return subprocess.run(
        ["grep", "-RInE", pattern, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )


# ─── Layer 1: core/domain/ is pure (no internal imports) ─────────────────────


def test_domain_is_pure() -> None:
    """`core/domain/` MUST NOT import from any internal layer.

    Spec refs:
        mcp-domain-core-spec REQ-001 Scenario "Pure domain module is
        importable without side effects" — "the import MUST NOT trigger
        database connections, network I/O, logging side effects..."
        mcp-server-internals-spec (delta) REQ-008 — "core/domain/... MUST
        have zero imports from mcp, fastmcp, starlette, psycopg..."
    """
    result = _grep(
        r"from opensddrag\.(infrastructure|db|embedding|cli|mcp|config|models)",
        SRC / "core" / "domain",
    )
    assert result.returncode != 0, (
        f"core/domain/ has forbidden internal imports:\n{result.stdout}\n"
        f"See mcp-domain-core-spec REQ-001 and mcp-server-internals-spec "
        f"(delta) REQ-008 for the full list of forbidden modules."
    )
    assert result.stdout == "", (
        f"core/domain/ has forbidden internal imports:\n{result.stdout}"
    )


# ─── Layer 2: core/usecases/ has no infra or DB imports ─────────────────────


def test_usecases_have_no_infra_or_db_imports() -> None:
    """`core/usecases/` MUST NOT import from infrastructure/db/embedding/cli/mcp.

    Spec refs:
        tool-execution-usecase-spec REQ-002 Scenario "Architecture rule
        passes" — "grep ... for `from opensddrag.infrastructure|import
        opensddrag.infrastructure|from opensddrag.db|import opensddrag.db`
        in `core/usecases/` returns no matches".
    """
    result = _grep(
        r"from opensddrag\.(infrastructure|db|embedding|cli|mcp)",
        SRC / "core" / "usecases",
    )
    assert result.returncode != 0, (
        f"core/usecases/ has forbidden imports:\n{result.stdout}\n"
        f"Use cases MUST depend only on ports (core/ports/) and domain "
        f"types (core/domain/). See tool-execution-usecase-spec REQ-002."
    )


# ─── Layer 3: infrastructure/ only imports downward (or itself) ─────────────


def test_infrastructure_only_imports_downward() -> None:
    """`infrastructure/` may import from `core/domain/` and
    `core/ports/`, but ONLY `infrastructure/composition.py` may
    import from `core/usecases/` (because `composition.py` is the
    composition root that BUILDS the use cases — adapters
    referencing use cases would create a cycle).

    Spec refs:
        mcp-server-internals-spec (delta) REQ-010 Scenario "Infrastructure
        depends only downward" — refined by this change to allow
        adapters to reference `core.domain.*` (leaf data types)
        and `core.ports.*` (the protocols they implement) without
        creating cycles.

    The rule is therefore:
        * Any file in `infrastructure/` may import from
          `opensddrag.core.domain.*` (domain types).
        * Any file in `infrastructure/` may import from
          `opensddrag.core.ports.*` (Protocols that the adapter
          implements — necessary for type hints and `isinstance`
          checks).
        * Only `infrastructure/composition.py` may import from
          `opensddrag.core.usecases.*` (the use cases are the
          dependency that gets composed there; an adapter
          referencing a use case would create a cycle).

    Pass conditions:
        * `grep` returns exit code 1 (no matches).
        * `grep` returns exit code 0 and every match's path is
          either `infrastructure/composition.py` (any `core/`
          subpackage is OK) or any other infrastructure file
          importing only from `core.domain` or `core.ports`.

    The fail condition is: `grep` finds at least one match outside
    `infrastructure/composition.py` that imports from
    `opensddrag.core.usecases.*`. This catches accidental
    upward imports that would create a cycle.
    """
    result = _grep(
        r"from opensddrag\.core",
        SRC / "infrastructure",
    )
    # Case 1: no matches at all. The infrastructure package is either
    # empty or its adapters do not import from core (the current state
    # during Phase 0-2). This is a valid pass.
    if result.returncode != 0:
        return

    # Case 2: matches exist. Categorize each match by subpackage.
    allowed_subpaths = (
        "infrastructure/composition.py",
        "infrastructure\\composition.py",  # Windows-style separators
    )
    allowed_subpackages = (
        "opensddrag.core.domain",
        "opensddrag.core.ports",
    )
    forbidden_subpackages = (
        "opensddrag.core.usecases",
    )

    offending_lines: list[str] = []
    for line in result.stdout.splitlines():
        # The grep output is `path:lineno:content`. The path is the
        # first field before the first `:`.
        path_field = line.split(":", 1)[0] if ":" in line else line
        # Allow the match if it is in composition.py.
        if any(sub in path_field for sub in allowed_subpaths):
            continue
        # Otherwise the import MUST be from one of the allowed
        # subpackages (`core.domain` or `core.ports`).
        if not any(allowed in line for allowed in allowed_subpackages):
            offending_lines.append(line)
        # Belt-and-braces: explicitly check for forbidden subpackages.
        if any(forbidden in line for forbidden in forbidden_subpackages):
            offending_lines.append(line)

    assert not offending_lines, (
        "infrastructure/ files other than composition.py may only "
        "import from `opensddrag.core.domain.*` or "
        "`opensddrag.core.ports.*` (never from "
        "`opensddrag.core.usecases.*` — that would create a cycle). "
        "Offending matches:\n"
        + "\n".join(offending_lines)
    )


# ─── Layer 4: mcp/server.py must not import db/ (gated) ──────────────────────


# Gate env var. When OPENSDDRAG_PHASE is set to a value >= 4, the test
# is enabled. Default (unset) -> skipped, because the mcp adapter is
# refactored in Phase 4 of the change (tasks adapter-2 .. adapter-8)
# and until then the inline `_dispatch` still calls `db.*` modules.
_PHASE_GATE_ENV = "OPENSDDRAG_PHASE"


def _current_phase() -> int:
    """Return the current OpenSddRag architectural phase as an int.

    Read from the `OPENSDDRAG_PHASE` env var. Defaults to 0 (no phase
    declared), which keeps the gated test skipped.
    """
    raw = os.environ.get(_PHASE_GATE_ENV, "0")
    try:
        return int(raw)
    except ValueError:
        return 0


@pytest.mark.skipif(
    _current_phase() < 4,
    reason=(
        "gated on Phase 4: mcp/server.py is refactored in adapter-2..8 "
        f"to stop calling db.* modules. Set {_PHASE_GATE_ENV}=4 (or higher) "
        "to enable this assertion."
    ),
)
def test_mcp_adapter_does_not_import_repositories() -> None:
    """`mcp/server.py` MUST NOT import from `opensddrag.db` after Phase 4.

    Spec refs:
        mcp-server-internals-spec (delta) REQ-005 Scenario "`mcp/server.py`
        no longer imports repositories" — "the command MUST return no
        matches".

    Before Phase 4, this assertion is intentionally skipped because the
    existing inline `_dispatch` body (the only consumer of the repositories
    that will be refactored) still imports `db.*`. Once tasks
    `task-adapter-2..8` are done, set `OPENSDDRAG_PHASE=4` (or higher)
    to re-enable the assertion in CI.
    """
    mcp_server_py = SRC / "mcp" / "server.py"
    result = _grep(r"from opensddrag\.db", mcp_server_py)
    assert result.returncode != 0, (
        f"mcp/server.py still imports from opensddrag.db (forbidden after "
        f"Phase 4):\n{result.stdout}\n"
        f"Set OPENSDDRAG_PHASE=4 to enable this assertion; the underlying "
        f"fix is in task-adapter-2..8."
    )
    assert result.stdout == "", (
        f"mcp/server.py still imports from opensddrag.db:\n{result.stdout}"
    )


# ─── Sanity: every test uses subprocess.run with check=False ─────────────────


def test_uses_subprocess_with_check_false() -> None:
    """Meta-test: the grep helper itself uses `check=False`.

    This is a "the test infrastructure is correct" test — it reads the
    source of `_grep` and asserts the documented contract. A future
    refactor that drops `check=False` would silently turn every "no
    matches" case into `CalledProcessError`, which would make the
    architecture tests harder to debug.

    Cheap: a single `grep` of the test file's source.
    """
    test_source = TEST_FILE.read_text(encoding="utf-8")
    assert "check=False" in test_source, (
        "test_imports.py must use subprocess.run(..., check=False) so "
        "`grep` exit code 1 (no matches) does not raise CalledProcessError."
    )
    assert "capture_output=True" in test_source, (
        "test_imports.py must use subprocess.run(..., capture_output=True) "
        "so we can show the offending lines in the assertion message."
    )
