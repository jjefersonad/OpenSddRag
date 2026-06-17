-- 004_hybrid_search.sql — Hybrid (lexical + vector) retrieval for `artifacts`.
--
-- Context: capability `hybrid-search` of the `improve-retrieval-accuracy` change.
-- Adds an additive, pre-normalized `tsvector` generated column and a GIN index
-- to support Reciprocal Rank Fusion (RRF) with the existing `vector(384)`
-- ranking. No change to the `embedding` column or its HNSW index (REQ-005).
--
-- Design reference:
--   docs/spikes/fts-tokenization-spike.md — option A (pre-normalize `/._-` → space)
--   improves-retrieval-accuracy-design.md  — Decision: `tsvector` as a STORED
--   generated column; Decision: `simple` text-search configuration; Decision:
--   pre-normalize the input to the generated column.
--
-- Immutability: every function used here is IMMUTABLE, so the expression is
-- valid for a STORED generated column.
--   to_tsvector(regconfig, text)       — IMMUTABLE
--   regexp_replace(text, text, text, text) — IMMUTABLE
--   btrim(text)                          — IMMUTABLE
--   coalesce(text, text)                 — IMMUTABLE
--   (text || text)                       — IMMUTABLE

-- 1. Add the pre-normalized `content_tsv` column.
--
-- Pre-normalization: replace `/`, `.`, `_`, `-` with a single space, collapse
-- runs of whitespace, then trim. This recovers identifier parts (so
-- `db/repository.py` indexes `{db, repository, py}` and a query `repository.py`
-- matches lexically — see spike §2) and avoids the default parser's
-- `asciihword`+`uint` re-classification that strips numeric suffixes from
-- kebab slugs (spike §4). The composed-lexeme form is sacrificed; the vector
-- ranking still covers phrase/semantic matching.
--
-- `metadata::text` is included so capability slugs (`hybrid-search`) and
-- change names (`improve-retrieval-accuracy`) feed the index — these are the
-- same identifier patterns we just pre-normalized for, and the spike's open
-- question §"Should `metadata` JSONB also feed `content_tsv`?" recommends yes.
--
-- `simple` configuration: no stemming, no stopwords. DB content is
-- language-agnostic (per project convention) and identifiers must be preserved
-- verbatim.
ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector(
            'simple',
            btrim(
                regexp_replace(
                    regexp_replace(
                        coalesce(name, '')
                            || ' '
                            || coalesce(content, '')
                            || ' '
                            || coalesce(metadata::text, ''),
                        '[/._-]', ' ', 'g'
                    ),
                    '\s+', ' ', 'g'
                )
            )
        )
    ) STORED;

-- Idempotency: if a previous run of 004 already created the column under an
-- earlier expression (e.g. an option-B spike), the GENERATED ALWAYS clause
-- would normally conflict. The expression above is the **final** expression
-- (per the spike's option A), so this migration is the one true source. Re-
-- running 004 against a DB that already has the column is a no-op.

-- 2. GIN index for the lexical ranking. GIN is the right structure for
-- `tsvector` lookups (`@@` / `ts_rank`).
CREATE INDEX IF NOT EXISTS idx_artifacts_content_tsv
    ON artifacts USING GIN (content_tsv);

-- Query-side contract (consumed by `db/repository.py` in task-3): the
-- repository MUST pre-normalize the user query with the same
-- `[/._-]` → space + whitespace-collapse + trim expression before calling
-- `websearch_to_tsquery('simple', $q_normalized)`. Otherwise `websearch_to_tsquery`
-- tokenizes `repository.py` as a single lexeme and the path-style identifier
-- the pre-normalization was designed to recover is lost on the query side.
-- Keeping the expression out of a stored function here means the contract is
-- duplicated as SQL in exactly two places (this migration and the repository
-- query); an additional SQL function is not warranted at current scale.
