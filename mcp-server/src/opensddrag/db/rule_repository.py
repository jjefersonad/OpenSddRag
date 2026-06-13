import json
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.rule import Rule, RuleCreate, RuleSummary


def _row_to_rule(row: dict) -> Rule:
    return Rule(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        trigger=row["trigger"],
        category=row["category"],
        severity=row["severity"],
        instruction=row["instruction"],
        enabled=row["enabled"],
        metadata=row["metadata"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_rule_summary(row: dict) -> RuleSummary:
    return RuleSummary(
        name=row["name"],
        category=row["category"],
        severity=row["severity"],
        instruction=row["instruction"],
    )


async def upsert(data: RuleCreate) -> Rule:
    """Insert a project rule, or update it in place if (project_id, name) exists.

    This is the soft-delete mechanism: passing ``enabled=False`` on an
    existing rule flips the ``enabled`` flag to FALSE rather than removing
    the row, preserving the rule's history and metadata.
    """
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO project_rules
                    (project_id, name, trigger, category, severity, instruction, enabled, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (project_id, name) DO UPDATE
                  SET trigger     = EXCLUDED.trigger,
                      category    = EXCLUDED.category,
                      severity    = EXCLUDED.severity,
                      instruction = EXCLUDED.instruction,
                      enabled     = EXCLUDED.enabled,
                      metadata    = EXCLUDED.metadata,
                      updated_at  = NOW()
                RETURNING id, project_id, name, trigger, category, severity,
                          instruction, enabled, metadata, created_at, updated_at
                """,
                (
                    str(data.project_id),
                    data.name,
                    data.trigger,
                    data.category,
                    data.severity,
                    data.instruction,
                    data.enabled,
                    json.dumps(data.metadata),
                ),
            )
            row = await cur.fetchone()
            return _row_to_rule(row)


async def list_all(
    project_id: UUID,
    trigger: str | None = None,
    category: str | None = None,
    enabled_only: bool = True,
) -> list[Rule]:
    """List all project rules for a project, with optional filters.

    Filters:
      * ``trigger``     — exact match on the trigger column.
      * ``category``    — exact match on the category column.
      * ``enabled_only`` — when True (default), exclude rules with
        ``enabled = FALSE`` (i.e. soft-deleted rules).
    """
    clauses: list[str] = ["project_id = %s"]
    params: list = [str(project_id)]

    if trigger is not None:
        clauses.append("trigger = %s")
        params.append(trigger)
    if category is not None:
        clauses.append("category = %s")
        params.append(category)
    if enabled_only:
        clauses.append("enabled = TRUE")

    where_sql = " AND ".join(clauses)
    sql = f"""
        SELECT id, project_id, name, trigger, category, severity,
               instruction, enabled, metadata, created_at, updated_at
        FROM project_rules
        WHERE {where_sql}
        ORDER BY created_at, name
    """

    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(sql, tuple(params))
            rows = await cur.fetchall()
            return [_row_to_rule(r) for r in rows]


async def list_by_trigger(
    project_id: UUID,
    trigger: str,
    enabled_only: bool = True,
) -> list[RuleSummary]:
    """List lightweight rule summaries for a given trigger, ordered by severity.

    Severity ordering puts the most critical rules first so harness tooling
    can short-circuit on the first error-level match. Unknown severities
    are sorted last to keep custom severities from interleaving with the
    built-in ones.
    """
    clauses: list[str] = ["project_id = %s", "trigger = %s"]
    params: list = [str(project_id), trigger]

    if enabled_only:
        clauses.append("enabled = TRUE")

    where_sql = " AND ".join(clauses)
    sql = f"""
        SELECT name, category, severity, instruction
        FROM project_rules
        WHERE {where_sql}
        ORDER BY CASE severity
                     WHEN 'error'   THEN 0
                     WHEN 'warning' THEN 1
                     WHEN 'info'    THEN 2
                     ELSE 3
                 END,
                 name
    """

    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(sql, tuple(params))
            rows = await cur.fetchall()
            return [_row_to_rule_summary(r) for r in rows]
