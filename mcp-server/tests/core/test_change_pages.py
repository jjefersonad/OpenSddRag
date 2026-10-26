"""Ordering and paging of the changes list (newest first, no client-side cut)."""

from opensddrag.core.domain.change_pages import paginate


def _change(name: str, updated_at: str | None) -> dict:
    return {"change": name, "updated_at": updated_at}


def test_paginate_orders_newest_first_and_returns_only_the_requested_page() -> None:
    changes = [
        _change("older", "2026-10-01T00:00:00Z"),
        _change("newest", "2026-10-08T00:00:00Z"),
        _change("middle", "2026-10-04T00:00:00Z"),
        _change("undated", None),
    ]
    first = paginate(changes, page=1, page_size=2)
    assert first["total"] == 4
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert [item["change"] for item in first["items"]] == ["newest", "middle"]

    second = paginate(changes, page=2, page_size=2)
    assert [item["change"] for item in second["items"]] == ["older", "undated"]

    past = paginate(changes, page=3, page_size=2)
    assert past["items"] == []
    assert past["total"] == 4
