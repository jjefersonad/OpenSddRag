"""Page a derived change list. Newest `updated_at` first; missing dates last.

Changes are grouped in memory from artifacts, so the page is cut after that
derivation. The API returns one page plus `total` — the client does not slice.
"""

from __future__ import annotations

from typing import Any


def order_newest_first(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Most recently updated change first. Missing dates stay at the end, by name."""
    dated = sorted(
        (item for item in changes if item.get("updated_at")),
        key=lambda item: item.get("change") or "",
    )
    dated.sort(key=lambda item: item["updated_at"], reverse=True)
    undated = sorted(
        (item for item in changes if not item.get("updated_at")),
        key=lambda item: item.get("change") or "",
    )
    return dated + undated


def paginate(changes: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    """`{items, total, page, page_size}` over `changes`, ordered newest first."""
    ordered = order_newest_first(changes)
    start = (page - 1) * page_size
    return {
        "items": ordered[start : start + page_size],
        "total": len(ordered),
        "page": page,
        "page_size": page_size,
    }
