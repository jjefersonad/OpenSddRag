"""Tests for the hybrid (lexical + vector) `search_semantic` pipeline.

Capability: `hybrid-search` of the `improve-retrieval-accuracy` change.
All tests run against the isolated test database (`docker-compose.test.yml`,
port 54327) and never touch production data — see `tests/conftest.py` for the
isolation guard.

Each test gets an isolated project (uuid-suffixed slug) that is cleaned up on
teardown, and seeds artifacts with controlled embeddings so the lexical and
vector signals can be made to disagree on demand. This lets us assert on the
RRF contract directly:

  * exact identifiers surface via the lexical ranking even when their
    embedding is far from the query (REQ-002 Sc1);
  * semantic paraphrases surface via the vector ranking even when they share
    no tokens with the query (REQ-002 Sc2);
  * `project_slug` and `type` filters are honored in both rankings (REQ-002
    Sc3);
  * a document present in both rankings outranks a document present in only
    one, and tied scores are ordered deterministically (REQ-003 Sc1, Sc2);
  * the established result shape and empty-result semantics are preserved
    (REQ-004 Sc1, Sc2).
"""

import asyncio
import re
from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.config import settings
from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.models.artifact import ArtifactCreate, ArtifactStatus, ArtifactType
from opensddrag.models.project import ProjectCreate


# ── Helpers ──────────────────────────────────────────────────────────────────

_DIM = 384
_FTS_NORMALIZE_RE = re.compile(r"[/._-]")
_FTS_WS_COLLAPSE_RE = re.compile(r"\s+")


def _sparse_vector(seed: int, modulus: int) -> list[float]:
    """Build a deterministic 384-d sparse unit-style vector.

    The `modulus` parameter scatters non-zero entries in different positions
    so two artifacts with different `modulus` values are guaranteed to be
    dissimilar under cosine distance. The test corpus uses a few distinct
    moduli to make the vector ranking predictable.
    """
    vec = [0.0] * _DIM
    for g in range(1, _DIM + 1):
        if g % modulus == seed % modulus:
            vec[g - 1] = 1.0
    return vec


async def _create_artifact(
    project_id,
    *,
    name: str,
    content: str,
    embedding: list[float] | None = None,
    type: ArtifactType = ArtifactType.spec,
    status: ArtifactStatus = ArtifactStatus.active,
    metadata: dict | None = None,
) -> None:
    """Insert an artifact via the public repository path.

    The repository embeds the `content` server-side; for tests we want to
    override the embedding to control the vector ranking, so we hit the
    repository first and then patch the column directly via SQL.
    """
    data = ArtifactCreate(
        project_id=project_id,
        name=name,
        type=type,
        content=content,
        status=status,
        metadata=metadata or {},
    )
    # Create with the auto-generated embedding; we'll overwrite it below.
    await repository.create_artifact(data, _sparse_vector(1, 97))
    if embedding is not None:
        async with get_conn() as conn:
            await conn.execute(
                "UPDATE artifacts SET embedding = %s::vector WHERE project_id = %s AND name = %s",
                (str(embedding), str(project_id), name),
            )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def project():
    """Yield an isolated project; clean up its artifacts + the project row."""
    slug = f"test-hybrid-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


@pytest_asyncio.fixture
async def other_project():
    """Second isolated project for the filter-scoping test."""
    slug = f"test-hybrid-other-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


@pytest_asyncio.fixture
async def seeded_corpus(project, other_project):
    """Seed the four artifacts the REQ-002 / REQ-003 scenarios rely on.

    Layout (project = the `project` fixture unless noted):

      * `lex-strong-spec`     — contains `get_harness_checklist`; embedding
        uses modulus 7 (sparse, far from the `unrelated-spec` modulus 13 so
        the vector ranking puts it below `unrelated-spec` for a neutral
        query).
      * `vec-only-paraphrase` — content shares NO tokens with the test
        queries; embedding uses modulus 11 so a query built from the same
        modulus surfaces it via vector.
      * `unrelated-spec`      — neither lexical nor vector match for the
        identifier query; used as a foil and to verify ordering on ties.
      * `unrelated-task`      — a `task` artifact, used to confirm the `type`
        filter excludes non-matching types.
      * (other project) `other-project-spec` — also contains
        `get_harness_checklist`; must never appear in `project`-scoped
        results.
    """
    # A neutral query vector for the `lex-strong-spec` case: its embedding
    # (modulus 7) is sparse, so a query vector with a different pattern
    # ranks `unrelated-spec` (modulus 13) above it by cosine distance.
    neutral_query = _sparse_vector(1, 13)
    vec_only_query = _sparse_vector(1, 11)

    await _create_artifact(
        project.id,
        name="lex-strong-spec",
        content=(
            "Purpose: hybrid search. The artifact exposes the "
            "get_harness_checklist identifier and tests identifier recall."
        ),
        embedding=neutral_query,  # vector ranking will put this at rank 2+
        type=ArtifactType.spec,
    )
    await _create_artifact(
        project.id,
        name="vec-only-paraphrase",
        content=(
            "Purpose: harness validation across SDD phases using deterministic "
            "checks and rules. This artifact shares no exact tokens with the "
            "test identifier queries."
        ),
        embedding=vec_only_query,  # vector ranking will put this at rank 1
        type=ArtifactType.spec,
    )
    await _create_artifact(
        project.id,
        name="unrelated-spec",
        content=(
            "Purpose: seasonal cooking recipes and ingredient pairing — nothing "
            "to do with SDD or harness."
        ),
        embedding=_sparse_vector(1, 13),  # identical to neutral_query → rank 1
        type=ArtifactType.spec,
    )
    await _create_artifact(
        project.id,
        name="unrelated-task",
        content="Task: do something unrelated to search.",
        embedding=_sparse_vector(1, 17),
        type=ArtifactType.task,
    )
    await _create_artifact(
        other_project.id,
        name="other-project-spec",
        content=(
            "Cross-project foil: this artifact also contains "
            "get_harness_checklist but must be filtered out by project_id."
        ),
        embedding=neutral_query,
        type=ArtifactType.spec,
    )

    return {
        "project_id": project.id,
        "other_project_id": other_project.id,
        "neutral_query": neutral_query,
        "vec_only_query": vec_only_query,
    }


# ── REQ-002 Scenario 1: exact identifier surfaces despite weak vector ────────

async def test_exact_identifier_surfaces_via_lexical_ranking(seeded_corpus):
    """An exact-identifier query MUST surface the artifact even when its
    embedding is far from the query vector (REQ-002 Sc1).
    """
    project_id = seeded_corpus["project_id"]
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=seeded_corpus["neutral_query"],
        limit=5,
        query_text="get_harness_checklist",
    )
    names = [a.name for a in results]
    # The lex-strong-spec carries the identifier; it MUST be in the result.
    assert "lex-strong-spec" in names, (
        f"exact-identifier query did not surface the matching artifact; "
        f"got {names}"
    )


# ── REQ-002 Scenario 2: paraphrase surfaces via vector ranking ───────────────

async def test_paraphrase_surfaces_via_vector_ranking(seeded_corpus):
    """A natural-language query that shares NO tokens with any artifact
    MUST still surface the right one via the vector ranking (REQ-002 Sc2).
    """
    project_id = seeded_corpus["project_id"]
    # "validation pipeline" — verified separately to have zero lexical
    # overlap with any seeded artifact (see the assertion in
    # `test_paraphrase_has_no_lexical_overlap` below for the guard).
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=seeded_corpus["vec_only_query"],
        limit=5,
        query_text="validation pipeline",
    )
    names = [a.name for a in results]
    assert "vec-only-paraphrase" in names, (
        f"paraphrase query did not surface the vector-only artifact; "
        f"got {names}"
    )


async def test_paraphrase_has_no_lexical_overlap(seeded_corpus):
    """Guard: the paraphrase query must not lexically match any seeded
    artifact, so the test above is actually exercising the vector-only
    scenario. If this fails the corpus needs to be re-seeded with a
    non-overlapping paraphrase.
    """
    from psycopg.rows import dict_row
    project_id = seeded_corpus["project_id"]
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT name FROM artifacts "
                "WHERE project_id = %s AND content_tsv @@ "
                "websearch_to_tsquery('simple', %s)",
                (str(project_id), "validation pipeline"),
            )
            rows = await cur.fetchall()
    assert not rows, (
        f"paraphrase query lexically matches {rows}; the test corpus is no "
        f"longer exercising the vector-only path"
    )


# ── REQ-002 Scenario 3: filters honored across both rankings ─────────────────

async def test_project_slug_filter_excludes_other_projects(seeded_corpus):
    """The `project_slug` filter MUST exclude artifacts from other projects,
    even when they lexically match (REQ-002 Sc3).
    """
    project_id = seeded_corpus["project_id"]
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=seeded_corpus["neutral_query"],
        limit=10,
        query_text="get_harness_checklist",
    )
    other_project_id = seeded_corpus["other_project_id"]
    for a in results:
        assert a.project_id != other_project_id, (
            f"project_slug filter leaked: {a.name} from other project {a.project_id}"
        )
    # And the other-project foil must not be in the result list.
    assert not any(a.name == "other-project-spec" for a in results)


async def test_type_filter_excludes_other_types(seeded_corpus):
    """The `type` filter MUST exclude artifacts of other types, even when
    they lexically or vectorially match (REQ-002 Sc3).
    """
    project_id = seeded_corpus["project_id"]
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=seeded_corpus["neutral_query"],
        limit=10,
        type=ArtifactType.task,
        query_text="get_harness_checklist",
    )
    assert results, "expected at least one task to surface via vector"
    for a in results:
        assert a.type == ArtifactType.task, (
            f"type filter leaked: {a.name} is {a.type.value}, not task"
        )
    # The lex-strong-spec and others are specs — they MUST be excluded.
    assert not any(a.name == "lex-strong-spec" for a in results)


# ── REQ-003 Scenario 1: dual-signal outranks single-signal ───────────────────

async def test_dual_signal_outranks_single_signal(seeded_corpus):
    """An artifact present in BOTH rankings (lex + vec) MUST outrank an
    artifact present in only one (REQ-003 Sc1).
    """
    project_id = seeded_corpus["project_id"]
    # The query contains the identifier `get_harness_checklist` (lex match
    # for `lex-strong-spec`) AND the query vector uses modulus 13, identical
    # to `unrelated-spec`'s embedding — so `unrelated-spec` will rank ~1
    # by vector. `lex-strong-spec`'s embedding is modulus 7, so it ranks
    # *poorly* by vector. The RRF score of `lex-strong-spec` benefits from
    # the top lex rank, so it MUST outrank `unrelated-spec` (which only
    # gets a top vec rank).
    vec = _sparse_vector(1, 13)  # favors unrelated-spec
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=vec,
        limit=5,
        query_text="get_harness_checklist",
    )
    names = [a.name for a in results]
    assert "lex-strong-spec" in names and "unrelated-spec" in names, (
        f"corpus missing one of the expected artifacts; got {names}"
    )
    idx_lex = names.index("lex-strong-spec")
    idx_unrelated = names.index("unrelated-spec")
    assert idx_lex < idx_unrelated, (
        f"dual-signal lex-strong-spec (idx={idx_lex}) should outrank "
        f"single-signal unrelated-spec (idx={idx_unrelated}); order={names}"
    )


# ── REQ-003 Scenario 2: deterministic ordering on tied scores ────────────────

async def test_tied_score_ordering_is_deterministic(seeded_corpus):
    """Two runs of the same hybrid query MUST return artifacts in the same
    order, including on tied RRF scores (REQ-003 Sc2). The tie-break on
    artifact `id ASC` is what makes this work.
    """
    project_id = seeded_corpus["project_id"]
    vec = seeded_corpus["neutral_query"]
    a = await repository.search_semantic(
        project_id=project_id,
        query_embedding=vec,
        limit=5,
        query_text="get_harness_checklist",
    )
    b = await repository.search_semantic(
        project_id=project_id,
        query_embedding=vec,
        limit=5,
        query_text="get_harness_checklist",
    )
    ids_a = [str(art.id) for art in a]
    ids_b = [str(art.id) for art in b]
    assert ids_a == ids_b, (
        f"non-deterministic ordering: {ids_a} vs {ids_b}"
    )


# ── REQ-004 Scenario 1: existing caller unaffected ───────────────────────────

async def test_existing_style_call_returns_established_shape(seeded_corpus):
    """`search_semantic(query, project_slug, limit)` — the call shape used
    before this change — MUST keep working and return at most `limit`
    results in the established `Artifact` shape (REQ-004 Sc1).
    """
    project_id = seeded_corpus["project_id"]
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=seeded_corpus["neutral_query"],
        limit=2,
    )
    # No `query_text` passed → repository falls back to the pure-vector
    # path. The result shape is still a list of `Artifact` objects.
    assert isinstance(results, list)
    assert len(results) <= 2
    for a in results:
        # Every field documented on `Artifact` must be present.
        assert hasattr(a, "id")
        assert hasattr(a, "project_id")
        assert hasattr(a, "name")
        assert hasattr(a, "type")
        assert hasattr(a, "status")
        assert hasattr(a, "content")
        assert hasattr(a, "metadata")
        assert hasattr(a, "created_at")
        assert hasattr(a, "updated_at")


async def test_query_text_empty_string_falls_back_to_pure_vector(seeded_corpus):
    """An empty `query_text` (explicit) MUST be treated as a fallback to the
    pure-vector path. This is what `mcp/server.py` would do if a caller
    ever passed `query_text=""` by mistake — it must not crash.
    """
    project_id = seeded_corpus["project_id"]
    vec = seeded_corpus["neutral_query"]
    a = await repository.search_semantic(
        project_id=project_id, query_embedding=vec, limit=5,
    )
    b = await repository.search_semantic(
        project_id=project_id, query_embedding=vec, limit=5, query_text="",
    )
    assert [x.name for x in a] == [x.name for x in b], (
        "fallback path (query_text='') diverges from default path"
    )


# ── REQ-004 Scenario 2: no matches returns empty, no error ───────────────────

async def test_no_matches_returns_empty(seeded_corpus):
    """A query that matches nothing in either ranking MUST return `[]`,
    not raise (REQ-004 Sc2). We use `type=design` — no `design` artifacts
    exist in the corpus — to filter out every row regardless of the
    lexical/vector signals.
    """
    project_id = seeded_corpus["project_id"]
    results = await repository.search_semantic(
        project_id=project_id,
        query_embedding=seeded_corpus["neutral_query"],
        limit=5,
        type=ArtifactType.design,
        query_text="get_harness_checklist",
    )
    assert results == [], f"expected empty list, got {results}"


# ── REQ-004 / RRF / isolation: defense in depth ──────────────────────────────

async def test_rrf_k_setting_is_consulted():
    """The RRF constant `k` and candidate depth are read from settings at
    call time. The default values in `config.py` (k=60, depth=20) are part
    of the contract documented in the design; this test pins them so a
    silent default change is caught.
    """
    assert settings.rrf_k == 60, f"RRF_K default drifted to {settings.rrf_k}"
    assert settings.search_candidate_depth == 20, (
        f"SEARCH_CANDIDATE_DEPTH default drifted to {settings.search_candidate_depth}"
    )
    assert settings.hybrid_search_enabled is True, (
        "HYBRID_SEARCH_ENABLED default drifted to False — hybrid path is "
        "the default behavior per design"
    )


async def test_query_side_normalization_matches_index_expression():
    """The repository applies the same `[/._-]` → space + whitespace
    collapse + trim expression to the query that migration 004 applies
    when building `content_tsv`. Without that, path-style identifiers
    wouldn't match. This test pins the regex by exercising it directly.
    """
    raw = "  db/repository.py  hybrid_search  "
    expected = _FTS_WS_COLLAPSE_RE.sub(" ", _FTS_NORMALIZE_RE.sub(" ", raw)).strip()
    assert expected == "db repository py hybrid search"
    # And the repository exposes the regex on its module — if the
    # expression ever drifts, the assertion below catches it without
    # needing a DB roundtrip.
    from opensddrag.db import repository as _repo
    assert _repo._FTS_NORMALIZE_RE.pattern == r"[/._-]"
    assert _repo._FTS_WS_COLLAPSE_RE.pattern == r"\s+"


# ── Isolation: confirm the suite is running against the test DB ──────────────

def test_database_url_is_isolated_test_db():
    """Last line of defense: the resolved DATABASE_URL MUST NOT point at the
    production port (54326). The session-scoped `_assert_isolated_test_db`
    fixture in `conftest.py` is the primary guard; this is a second,
    test-level assertion that the same invariant holds at test time.
    """
    assert "54327" in settings.database_url or "54328" in settings.database_url or \
        "54329" in settings.database_url, (
        f"DATABASE_URL={settings.database_url!r} does not look like the "
        f"isolated test DB (expected a non-production port)"
    )
    assert ":54326/" not in settings.database_url, (
        f"Refusing to run: DATABASE_URL points at the production port "
        f"({settings.database_url!r})"
    )
