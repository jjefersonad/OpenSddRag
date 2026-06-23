import json
import re
from typing import Literal
from uuid import UUID

import psycopg.rows

from opensddrag.config import settings
from opensddrag.db.connection import get_conn
from opensddrag.models.artifact import (
    Artifact,
    ArtifactCreate,
    ArtifactRelationship,
    ArtifactStatus,
    ArtifactType,
    ArtifactUpdate,
)

# Query-side pre-normalization for hybrid search. Mirrors the expression
# that builds the `content_tsv` generated column in migration
# `004_hybrid_search.sql`: replace `/`, `.`, `_`, `-` with a single space,
# collapse runs of whitespace, then trim. Required so that the query side of
# `websearch_to_tsquery('simple', ...)` recovers the same identifier parts
# (`db`, `repository`, `py`) that the indexed column exposes. See
# `docs/spikes/fts-tokenization-spike.md` for the spike that established the
# contract.
_FTS_NORMALIZE_RE = re.compile(r"[/._-]")
_FTS_WS_COLLAPSE_RE = re.compile(r"\s+")



def _row_to_artifact(row: dict) -> Artifact:
    return Artifact(**{k: v for k, v in row.items() if k != "embedding"})


async def create_artifact(data: ArtifactCreate, embedding: list[float]) -> Artifact:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO artifacts (project_id, name, type, status, content, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                RETURNING id, project_id, name, type, status, content, metadata, created_at, updated_at
                """,
                (
                    str(data.project_id),
                    data.name,
                    data.type.value,
                    data.status.value,
                    data.content,
                    json.dumps(data.metadata),
                    str(embedding),
                ),
            )
            row = await cur.fetchone()
            return _row_to_artifact(row)


async def get_artifact(project_id: UUID, name: str) -> Artifact | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts WHERE project_id = %s AND name = %s
                """,
                (str(project_id), name),
            )
            row = await cur.fetchone()
            return _row_to_artifact(row) if row else None


async def get_artifact_by_id(artifact_id: UUID) -> Artifact | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts WHERE id = %s
                """,
                (str(artifact_id),),
            )
            row = await cur.fetchone()
            return _row_to_artifact(row) if row else None


async def list_artifacts(
    project_id: UUID,
    type: ArtifactType | None = None,
    status: ArtifactStatus | None = None,
) -> list[Artifact]:
    conditions = ["project_id = %s"]
    params: list = [str(project_id)]
    if type:
        conditions.append("type = %s")
        params.append(type.value)
    if status:
        conditions.append("status = %s")
        params.append(status.value)
    where = " AND ".join(conditions)
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"""
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts WHERE {where} ORDER BY updated_at DESC
                """,
                params,
            )
            rows = await cur.fetchall()
            return [_row_to_artifact(r) for r in rows]


async def update_artifact(
    project_id: UUID,
    name: str,
    data: ArtifactUpdate,
    embedding: list[float] | None = None,
) -> Artifact | None:
    sets = ["updated_at = NOW()"]
    params: list = []
    if data.content is not None:
        sets.append("content = %s")
        params.append(data.content)
    if data.status is not None:
        sets.append("status = %s")
        params.append(data.status.value)
    if data.metadata is not None:
        sets.append("metadata = jsonb_strip_nulls(metadata || %s::jsonb)")
        params.append(json.dumps(data.metadata))
    if embedding is not None:
        sets.append("embedding = %s::vector")
        params.append(str(embedding))
    params.extend([str(project_id), name])
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"""
                UPDATE artifacts SET {', '.join(sets)}
                WHERE project_id = %s AND name = %s
                RETURNING id, project_id, name, type, status, content, metadata, created_at, updated_at
                """,
                params,
            )
            row = await cur.fetchone()
            return _row_to_artifact(row) if row else None


async def search_semantic(
    project_id: UUID | Literal["*"],
    query_embedding: list[float],
    limit: int = 5,
    type: ArtifactType | None = None,
    query_text: str = "",
) -> list[Artifact]:
    """Hybrid (lexical + vector) semantic search over `artifacts`.

    When `settings.hybrid_search_enabled` is true and `query_text` is non-empty,
    fuses a lexical ranking (`ts_rank` over `websearch_to_tsquery('simple', ...)`)
    and a vector ranking (`embedding <=> $vec`) via Reciprocal Rank Fusion
    (RRF), each limited to `settings.search_candidate_depth`, then truncates to
    `limit`. Otherwise falls back to the pure-vector query (preserves the
    pre-hybrid behavior exactly).

    The query text is pre-normalized with the same `[/._-]` → space + whitespace
    collapse + trim expression used to build the `content_tsv` generated
    column (migration 004), so path-style identifiers match on the lexical
    side. See `docs/spikes/fts-tokenization-spike.md` and the design decision
    "Pre-normalize the input to the generated column" for the rationale.
    """
    # Build the filter clause shared by both the fallback and the hybrid
    # queries, so the two paths can never disagree on what `project_id` /
    # `type` mean. `base_where` is the AND-joined condition list **without**
    # a leading `WHERE`, so the caller can prepend it (or compose it with
    # additional conditions, as the hybrid `lex` CTE does for `@@`).
    base_conditions: list[str] = []
    filter_params: list = []
    if project_id != "*":
        base_conditions.append("project_id = %s")
        filter_params.append(str(project_id))
    if type:
        base_conditions.append("type = %s")
        filter_params.append(type.value)
    base_where = " AND ".join(base_conditions)

    use_hybrid = settings.hybrid_search_enabled and bool(query_text and query_text.strip())
    if not use_hybrid:
        # Pre-normalization is a no-op for the vector path; the fallback is
        # the original pure-vector query exactly as it was before this
        # change, with the same parameter order.
        vec = str(query_embedding)
        where = ("WHERE " + base_where) if base_where else ""
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    f"""
                    SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                    FROM artifacts
                    {where}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    filter_params + [vec, limit],
                )
                rows = await cur.fetchall()
                return [_row_to_artifact(r) for r in rows]

    # Hybrid path: a single SQL query that computes the lexical and vector
    # candidate rankings in two CTEs, FULL OUTER JOINs them on id, and scores
    # each row with RRF (`score = 1/(k+lex.rank) + 1/(k+vec.rank)`). Filters
    # are applied inside both CTEs so they cannot be bypassed by which side
    # surfaced a row. Ties break on `id ASC` for determinism (REQ-003).
    #
    # Query-side pre-normalization (contract with migration 004 — see
    # `004_hybrid_search.sql`): the same `[/._-]` → space + whitespace
    # collapse + trim expression that builds the `content_tsv` generated
    # column must be applied to the query before
    # `websearch_to_tsquery('simple', ...)`, otherwise path-style identifiers
    # (`repository.py` etc.) are tokenized as a single lexeme and the lexical
    # match is lost.
    normalized_query = _FTS_WS_COLLAPSE_RE.sub(
        " ", _FTS_NORMALIZE_RE.sub(" ", query_text)
    ).strip()
    if not normalized_query:
        # Empty after normalization (e.g. query was only `___.---`). Nothing
        # can match lexically; fall back to the pure-vector path.
        vec = str(query_embedding)
        where = ("WHERE " + base_where) if base_where else ""
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    f"""
                    SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                    FROM artifacts
                    {where}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    filter_params + [vec, limit],
                )
                rows = await cur.fetchall()
                return [_row_to_artifact(r) for r in rows]

    vec = str(query_embedding)
    depth = int(settings.search_candidate_depth)
    rrf_k = int(settings.rrf_k)
    # `vec_where` filters by project/type only. `lex_where` filters by
    # project/type **and** the `@@` FTS operator (so the GIN index can be
    # used) — the `@@` is composed into the same `WHERE` to avoid emitting
    # two `WHERE` clauses (which is a SQL syntax error).
    vec_where = ("WHERE " + base_where) if base_where else ""
    if base_where:
        lex_where = f"WHERE {base_where} AND content_tsv @@ websearch_to_tsquery('simple', %s)"
        # `lex_where` ends with one extra `%s` placeholder that must be bound
        # alongside the existing `filter_params` in order. We bind
        # `normalized_query` twice (once here, once for the `ts_rank` ORDER
        # BY above) and split filter params accordingly.
        lex_filter_params = [*filter_params, normalized_query]
    else:
        lex_where = "WHERE content_tsv @@ websearch_to_tsquery('simple', %s)"
        lex_filter_params = [normalized_query]
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"""
                WITH lex AS (
                    SELECT id, row_number() OVER (
                        ORDER BY ts_rank(content_tsv, websearch_to_tsquery('simple', %s)) DESC,
                                 id ASC
                    ) AS rank
                    FROM artifacts
                    {lex_where}
                    LIMIT %s
                ),
                vec AS (
                    SELECT id, row_number() OVER (
                        ORDER BY embedding <=> %s::vector ASC, id ASC
                    ) AS rank
                    FROM artifacts
                    {vec_where}
                    LIMIT %s
                ),
                fused AS (
                    SELECT coalesce(lex.id, vec.id) AS id,
                           coalesce(1.0 / (%s + lex.rank), 0)
                           + coalesce(1.0 / (%s + vec.rank), 0) AS score
                    FROM lex
                    FULL OUTER JOIN vec ON vec.id = lex.id
                )
                SELECT a.id, a.project_id, a.name, a.type, a.status, a.content, a.metadata,
                       a.created_at, a.updated_at
                FROM artifacts a
                JOIN fused ON fused.id = a.id
                ORDER BY fused.score DESC, a.id ASC
                LIMIT %s
                """,
                # Parameter order (must match `%s` placeholders left-to-right
                # in the rewritten SQL above):
                #   1. normalized_query   (lex CTE: ts_rank ORDER BY arg)
                #   2. lex_filter_params   (lex CTE: WHERE filters + @@ query)
                #   3. depth               (lex CTE LIMIT)
                #   4. vec                 (vec CTE: distance arg)
                #   5. filter_params       (vec CTE: WHERE filters)
                #   6. depth               (vec CTE LIMIT)
                #   7. rrf_k               (fused: lex divisor)
                #   8. rrf_k               (fused: vec divisor)
                #   9. limit               (outer LIMIT)
                [
                    normalized_query,
                    *lex_filter_params,
                    depth,
                    vec,
                    *filter_params,
                    depth,
                    rrf_k,
                    rrf_k,
                    limit,
                ],
            )
            rows = await cur.fetchall()
            return [_row_to_artifact(r) for r in rows]


async def link_artifacts(source_id: UUID, target_id: UUID, relationship_type: str) -> ArtifactRelationship:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO artifact_relationships (source_id, target_id, relationship_type)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING *
                """,
                (str(source_id), str(target_id), relationship_type),
            )
            row = await cur.fetchone()
            # If ON CONFLICT DO NOTHING didn't return a row, fetch existing
            if row is None:
                await cur.execute(
                    """
                    SELECT * FROM artifact_relationships
                    WHERE source_id = %s AND target_id = %s AND relationship_type = %s
                    """,
                    (str(source_id), str(target_id), relationship_type),
                )
                row = await cur.fetchone()
            return ArtifactRelationship(**row)


async def get_relationships(artifact_id: UUID) -> list[dict]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT r.relationship_type, r.created_at,
                       a.id, a.name, a.type, a.status, a.project_id
                FROM artifact_relationships r
                JOIN artifacts a ON (a.id = r.target_id OR a.id = r.source_id)
                WHERE (r.source_id = %s OR r.target_id = %s) AND a.id != %s
                """,
                (str(artifact_id), str(artifact_id), str(artifact_id)),
            )
            return await cur.fetchall()
