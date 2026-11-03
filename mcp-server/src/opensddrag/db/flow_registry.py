"""Flow registry persistence — flows / artifact_kinds (flow-registry REQ-002).

Gateway between the domain-level `FlowManifest` (REQ-001) and the registry
tables created by migration 008. All write paths live here so the CLI
(`init`, `register-flow`) and future adapters share one idempotent,
partial-row-free implementation.

Guarantees (REQ-002):
  * `ensure_sdd_flow` seeds `flows['sdd']` + the five SDD kinds — safe to
    call any number of times (ON CONFLICT DO NOTHING).
  * `register_flow` upserts by canonical manifest identity: a manifest
    whose canonical JSON equals the stored one — and whose kind list
    matches — is left untouched ("unchanged"); a differing manifest is
    re-embedded and that flow's kind rows are replaced ("replaced"). A
    manifest failing REQ-001 validation raises before any write (no
    partial rows).
"""

from __future__ import annotations

import json
from typing import Any

from opensddrag.core.domain.flow_manifest import FlowManifest, validate_manifest
from opensddrag.db.connection import get_conn

_SDD_FLOW = "sdd"
_SDD_KINDS = ("proposal", "spec", "task", "design", "test")


async def ensure_sdd_flow() -> None:
    """Idempotently seed the built-in `sdd` flow and its five kinds.

    Called by `init` — mirrors migration 008's plain-SQL seed so both
    paths converge on identical rows even if only one of them runs.
    """
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO flows (flow, manifest)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (flow) DO NOTHING
            """,
            (_SDD_FLOW, json.dumps({"flow": _SDD_FLOW})),
        )
        for kind in _SDD_KINDS:
            await conn.execute(
                """
                INSERT INTO artifact_kinds (flow, kind, rules)
                VALUES (%s, %s, '{}'::jsonb)
                ON CONFLICT (flow, kind) DO NOTHING
                """,
                (_SDD_FLOW, kind),
            )


async def register_flow(manifest_payload: dict) -> dict[str, Any]:
    """Upsert one flow from its raw manifest payload (flow-registry REQ-002).

    Validates first (a malformed manifest raises before any DB write —
    no partial rows). Then, atomically:
      * new manifest     → insert flow + kinds,       status "registered"
      * unchanged        → no rows touched,           status "unchanged"
      * changed manifest → update manifest JSON and   status "replaced"
                           replace that flow's kind
                           rows (other flows untouched)
    """
    manifest: FlowManifest = validate_manifest(manifest_payload)

    flow_slug = manifest.flow
    canonical = canonical_json(manifest_payload)
    kinds = [k.kind for k in manifest.kinds]
    rules_by_kind = {
        k.kind: {
            "required_headings": k.required_headings,
            "required_metadata_keys": k.required_metadata_keys,
        }
        for k in manifest.kinds
    }

    async with get_conn() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT manifest::text FROM flows WHERE flow = %s",
                    (flow_slug,),
                )
                row = await cur.fetchone()
                if row is not None:
                    stored = canonical_json(json.loads(row[0]))
                    if stored == canonical and await _kinds_match(cur, flow_slug, kinds):
                        return {
                            "flow": flow_slug,
                            "status": "unchanged",
                            "kinds": len(kinds),
                        }
                    written = await _upsert_flow_and_kinds(
                        cur, flow_slug, canonical, kinds, rules_by_kind
                    )
                    return {
                        "flow": flow_slug,
                        "status": "replaced",
                        "kinds": written,
                    }

                await _upsert_flow_and_kinds(
                    cur, flow_slug, canonical, kinds, rules_by_kind
                )
                return {
                    "flow": flow_slug,
                    "status": "registered",
                    "kinds": len(kinds),
                }


async def registered_flows() -> list[str]:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT flow FROM flows ORDER BY flow")
            return [r[0] for r in await cur.fetchall()]


async def registered_kinds(flow: str) -> list[dict[str, Any]]:
    """Kinds of a registered flow with their declarative rules."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT kind, rules::text FROM artifact_kinds WHERE flow = %s ORDER BY kind",
                (flow,),
            )
            return [{"kind": r[0], "rules": json.loads(r[1])} for r in await cur.fetchall()]


def canonical_json(payload: dict) -> str:
    """Key-order-independent serialization used for change detection."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


async def _kinds_match(cur, flow: str, kinds: list[str]) -> bool:
    await cur.execute(
        "SELECT kind FROM artifact_kinds WHERE flow = %s ORDER BY kind",
        (flow,),
    )
    return [r[0] for r in await cur.fetchall()] == sorted(kinds)


async def _upsert_flow_and_kinds(
    cur, flow: str, manifest_json: str, kinds: list[str], rules_by_kind: dict
) -> int:
    """Insert/replace the flow row and exactly its declared kind rows."""
    await cur.execute(
        """
        INSERT INTO flows (flow, manifest)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (flow) DO UPDATE
            SET manifest = EXCLUDED.manifest, registered_at = NOW()
        """,
        (flow, manifest_json),
    )
    await cur.execute("DELETE FROM artifact_kinds WHERE flow = %s", (flow,))
    for kind in kinds:
        await cur.execute(
            """
            INSERT INTO artifact_kinds (flow, kind, rules)
            VALUES (%s, %s, %s::jsonb)
            """,
            (flow, kind, json.dumps(rules_by_kind[kind])),
        )
    return len(kinds)