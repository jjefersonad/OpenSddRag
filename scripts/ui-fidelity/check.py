#!/usr/bin/env python3
"""UI fidelity check for the OpenSddRag web dashboard (REQ-019, design D12).

Opens the design prototype (docs/ui/OpenSddRag.dc.html) and the running app
(real API), captures 1440x900 screenshots per screen into a scratch directory
and measures structural fidelity items (fonts, link styling, grid columns,
card width, presence of header/strip/tabs/panels) via page.evaluate. Prints a
per-screen pass/fail checklist and exits non-zero when any APP item fails.

Prototype-side items are PASS/FAIL too, but screens the single-file prototype
cannot reach by simple navigation degrade to SKIP (annotated) instead of
failing the run — the gate on the real app is strict either way.

Prerequisites: pip install playwright && playwright install chromium.
Run: python3 scripts/ui-fidelity/check.py [--app-url ...] [--serve-prototype]
See docs/ui/FIDELITY_CHECKLIST.md for the full procedure.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
VIEWPORT = {"width": 1440, "height": 900}
TOKEN_KEY = "opensddrag.management_token"

# ---------------------------------------------------------------------------
# CLI + infrastructure helpers


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prototype-vs-app UI fidelity checklist.")
    parser.add_argument("--app-url", default=os.environ.get("APP_URL", "http://localhost:3001"))
    parser.add_argument(
        "--prototype-url", default=os.environ.get("PROTOTYPE_URL", "http://localhost:4100/OpenSddRag.dc.html")
    )
    parser.add_argument(
        "--serve-prototype",
        action="store_true",
        help="serve <repo>/docs/ui/ on the prototype-url host/port with a stdlib http server",
    )
    parser.add_argument(
        "--slug", default=os.environ.get("OPENSDDRAG_SLUG", ""), help="project slug for detail screens (default: first dashboard card)"
    )
    parser.add_argument("--token", default=os.environ.get("OPENSDDRAG_TOKEN", ""), help="management API token")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / ".scratch" / "ui-fidelity"))
    return parser.parse_args(argv)


def serve_prototype(url: str):
    """Serve <repo>/docs/ui/ on the host/port of `url` (daemon thread)."""
    parsed = urlparse(url)
    directory = str(REPO_ROOT / "docs" / "ui")

    handler = http.server.SimpleHTTPRequestHandler
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    class _Handler(handler):  # type: ignore[type-arg,misc]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, *args):  # silence request logging
            pass

    server = socketserver.ThreadingTCPServer((parsed.hostname or "localhost", parsed.port or 4100), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class PageSession:
    """A playwright page plus out_dir — delegates native page calls (evaluate,
    wait_for_timeout, ...) and adds the check's helpers (goto with wait
    selector, screenshot naming, token injection)."""

    def __init__(self, page, out_dir: Path):
        self._page = page
        self._out_dir = out_dir

    def __getattr__(self, name):
        return getattr(self._page, name)

    def goto(self, url: str, wait_for: str, timeout: int = 15000) -> None:
        self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            self._page.wait_for_selector(wait_for, state="attached", timeout=timeout)
        except Exception:
            pass  # the metric probes report what they find

    def shot(self, name: str) -> str:
        path = str(self._out_dir / f"{name}.png")
        self._page.screenshot(path=path)
        return path

    def set_token(self, token: str, app_url: str) -> None:
        self._page.goto(f"{app_url.rstrip('/')}/login")
        self._page.evaluate("([key, token]) => localStorage.setItem(key, token)", [TOKEN_KEY, token])


class Browser:
    """Lazy-playwright host so --help does not require playwright; hands out
    isolated 1440x900 PageSessions from ONE browser/loop (nested sync
    playwright loops are not allowed in a thread)."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self._pw = None
        self._browser = None

    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            sys.exit("playwright is not installed. Run: pip install playwright && playwright install chromium")
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        return False

    def new_page(self) -> PageSession:
        context = self._browser.new_context(viewport=VIEWPORT)
        return PageSession(context.new_page(), self.out_dir)


# ---------------------------------------------------------------------------
# Fidelity probes


def check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def skip(name: str, detail: str) -> dict:
    return {"name": name, "status": "SKIP", "detail": detail}


def mono_font(font_family: str) -> bool:
    return "IB Plex Mono" in font_family or "IBM Plex Mono" in font_family


def sans_font(font_family: str) -> bool:
    return "IBM Plex Sans" in font_family


def anchor_underlines(page) -> int:
    return page.evaluate(
        "() => [...document.querySelectorAll('a')].filter((a) => {"
        "  const s = getComputedStyle(a);"
        "  return (s.textDecorationLine || '').includes('underline');"
        "}).length"
    )


def measure_landing(bp, ap) -> list[dict]:  # prototype page, app page
    items: list[dict] = []
    for label, page, tag in (("prototype", bp, "proto"), ("app", ap, "app")):
        # body has no font-family in the prototype markup — measure a text element
        body_font = page.evaluate(
            "() => {"
            "  const el = document.querySelector('h1') || document.querySelector('p, span');"
            "  return el ? getComputedStyle(el).fontFamily : getComputedStyle(document.body).fontFamily;"
            "}"
        ) or ""
        underlined = anchor_underlines(page)
        items.append(check(f"{tag}: body font is IBM Plex Sans", sans_font(body_font), body_font.split(",")[0]))
        cta = page.evaluate(
            "() => {"
            "  const btn = [...document.querySelectorAll('a,button')].find((el) => {"
            "    if (!/launch app|sign in/i.test(el.textContent || '')) return false;"
            "    return getComputedStyle(el).backgroundColor !== 'rgba(0, 0, 0, 0)';"
            "  });"
            "  return btn ? getComputedStyle(btn).backgroundColor : null;"
            "}"
        )
        items.append(check(f"{tag}: Launch CTA filled with accent #10b981", bool(cta) and "rgb(16, 185, 129)" in str(cta), str(cta)))
        if label == "app":  # prototype keeps guide links underlined-free too, but only the app gates
            items.append(check("app: no link renders with an underline", underlined == 0, f"{underlined} underlined anchors"))
    return items


def measure_dashboard(page, tag: str) -> list[dict]:
    items: list[dict] = []
    grid_cols = page.evaluate(
        "() => {"
        "  const grid = document.querySelector('.dashboard-grid');"
        "  return grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0;"
        "}"
    )
    items.append(check(f"{tag}: dashboard grid has 2 columns at 1440px", grid_cols == 2, f"resolved columns={grid_cols}"))
    card_width = page.evaluate(
        "() => {"
        "  const card = document.querySelector('.dashboard-grid > li > a');"
        "  return card ? Math.round(card.getBoundingClientRect().width) : 0;"
        "}"
    )
    items.append(check(f"{tag}: first card wider than 400px", (card_width or 0) > 400, f"width={card_width}px"))
    if tag == "app":
        subtitle = page.evaluate(
            "() => ([...document.querySelectorAll('p')].find((p) => /registered/i.test(p.textContent || '')) || {}).textContent || ''"
        )
        items.append(
            check(
                "app: subtitle '<N> registered · multi-tenant artifact memory'",
                "registered · multi-tenant artifact memory" in (subtitle or "").replace("\n", " ").strip(),
                (subtitle or "")[:80],
            )
        )
    return items


def measure_detail_overview(page, tag: str) -> list[dict]:
    items: list[dict] = []
    strip = page.evaluate("() => document.querySelector('[data-testid^=phase-strip-]') !== null")
    overview_cols = page.evaluate(
        "() => {"
        "  const grid = document.querySelector('.overview-grid');"
        "  return grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0;"
        "}"
    )
    items.append(check(f"{tag}: overview-grid resolves to 2 tracks at 1440px", overview_cols == 2, f"resolved tracks={overview_cols}"))
    panels = page.evaluate(
        "() => ({"
        "  context: document.querySelector('[data-testid=working-context-panel]') !== null,"
        "  traces: document.querySelector('[data-testid=traces-panel]') !== null,"
        "})"
    )
    items.append(check(f"{tag}: Working context + Execution trace panels present", panels["context"] and panels["traces"], json.dumps(panels)))
    if tag == "app":
        h1 = page.evaluate("() => document.querySelector('[data-testid=app-h1]') !== null")
        tabs_count = page.evaluate("() => document.querySelectorAll('[role=tab]').length")
        items.append(check("app: header (app-h1) present", h1, f"tabs={tabs_count}"))
        items.append(check("app: tab bar has ≥3 tabs (Overview + kinds + rest)", tabs_count >= 3, f"tabs={tabs_count}"))
    items.append(check(f"{tag}: horizontal phase strip present", strip, "phase-strip-*" if strip else "absent"))
    return items


def measure_specs_tab(page, tag: str) -> list[dict]:
    page.evaluate(
        "() => {"
        "  const tab = [...document.querySelectorAll('[role=tab]')].find((t) => /specs/i.test(t.textContent || ''));"
        "  if (tab) tab.click();"
        "}"
    )
    page.wait_for_timeout(600)
    try:  # spec cards come from an async fetch
        page.wait_for_selector("[role=tabpanel] article", state="attached", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(300)
    items: list[dict] = []
    spec_cards = page.evaluate("() => document.querySelectorAll('[role=tabpanel] article').length")
    count_label = page.evaluate(
        "() => {"
        "  const lbl = [...document.querySelectorAll('[role=tabpanel] span')]"
        "    .find((s) => /requirements/.test(s.textContent || ''));"
        "  return lbl ? lbl.textContent.trim() : null;"
        "}"
    )
    items.append(check(f"{tag}: at least one spec card renders", spec_cards > 0, f"cards={spec_cards}"))
    if spec_cards == 0:
        items.append(check(f"{tag}: spec card shows '<n> requirements'", False, "no cards"))
        return items
    items.append(check(f"{tag}: spec card shows '<n> requirements' count", bool(count_label), str(count_label)))
    page.evaluate(
        "() => {"
        "  const card = document.querySelector('[role=tabpanel] article');"
        "  const btn = card && card.querySelector('button[aria-expanded]');"
        "  if (btn && btn.getAttribute('aria-expanded') === 'false') btn.click();"
        "}"
    )
    page.wait_for_timeout(300)

    def when_color():
        return page.evaluate(
            "() => {"
            "  const card = document.querySelector('[role=tabpanel] article');"
            "  const when = card && card.querySelector('[data-testid=scenario-when]');"
            "  if (when) return getComputedStyle(when).color;"
            "  const scenario_btn = card && [...card.querySelectorAll('button[aria-expanded=false]')][0];"
            "  if (scenario_btn) { scenario_btn.click(); return 'clicked'; }"
            "  return null;"
            "}"
        )

    color = when_color()
    if color == "clicked":  # scenarios start collapsed — one click reveals WHEN
        page.wait_for_timeout(250)
        color = when_color()
    items.append(check(f"{tag}: WHEN scenarios render in amber rgb(251,191,36)", color is not None and "251, 191, 36" in str(color), str(color)))
    return items


def measure_simple_tab(page, tag: str, tab_label: str, probe: str) -> list[dict]:
    page.evaluate(
        "label => {"
        "  const tab = [...document.querySelectorAll('[role=tab]')].find((t) => new RegExp(label, 'i').test(t.textContent || ''));"
        "  if (tab) tab.click();"
        "}",
        tab_label,
    )
    page.wait_for_timeout(600)
    try:  # tab content comes from an async fetch
        page.wait_for_selector("[role=tabpanel] article, [role=tabpanel] li, [role=tabpanel] p", state="attached", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(300)
    non_empty = page.evaluate(
        "() => {"
        "  const panel = document.querySelector('[role=tabpanel]');"
        "  return panel ? (panel.textContent || '').trim().length > 20 : false;"
        "}"
    )
    return [check(f"{tag}: {probe}", bool(non_empty), "panel renders content" if non_empty else "panel empty")]


def measure_docs(page, tag: str) -> list[dict]:
    items: list[dict] = []
    toc_labels = page.evaluate(
        "() => [...document.querySelectorAll('[data-testid=docs-toc] a')].map((a) => (a.textContent || '').trim())"
    )
    required = ["Overview", "Quickstart", "Server setup", "CLI client", "Claude Code", "OpenCode", "Pipelines", "Color"]
    missing = [name for name in required if name not in toc_labels]
    items.append(
        check(
            f"{tag}: docs TOC lists getting-started and reference sections",
            len(toc_labels) >= 15 and not missing,
            f"links={len(toc_labels)} missing={missing}",
        )
    )
    swatches = page.evaluate(
        "() => document.querySelectorAll('[data-testid=docs-section-color] [data-hex], [data-testid=docs-section-color] [data-testid^=docs-swatch-]').length"
    )
    items.append(check(f"{tag}: color section has a swatch for each token (>=15)", swatches >= 15, f"swatches={swatches}"))
    code_blocks = page.evaluate(
        "() => {"
        "  const section = document.querySelector('[data-testid=docs-section-quickstart]');"
        "  if (!section) return {count: 0, mono: 0};"
        "  const blocks = [...section.querySelectorAll('pre, code')].filter((el) => {"
        "    const s = getComputedStyle(el);"
        "    return (s.fontFamily || '').includes('Plex Mono') || (el.style.fontFamily || '').includes('--font-mono');"
        "  });"
        "  return {count: [...section.querySelectorAll('pre, code')].length, mono: blocks.length,};"
        "}"
    )
    items.append(check(f"{tag}: quickstart commands in mono code blocks", code_blocks["count"] >= 2 and code_blocks["mono"] >= 2, json.dumps(code_blocks)))
    return items


# ---------------------------------------------------------------------------
# Screens


def run(prototype_url: str, app_url: str, out_dir: Path, slug: str, token: str, serve_proto: bool) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    server = serve_prototype(prototype_url) if serve_proto else None
    items: list[dict] = []
    try:
        with Browser(out_dir) as b:
            proto = b.new_page()
            app = b.new_page()

            # -- landing (public; prototype first view) ------------------------
            proto.goto(prototype_url, "body")
            proto.wait_for_timeout(500)
            proto.shot("proto-landing")
            app.goto(app_url, "body")
            app.wait_for_timeout(500)
            app.shot("impl-landing")
            items += measure_landing(proto, app)

            # -- authenticated screens (app only, strict) ----------------------
            if not token:
                return fail(items, app_url, "OPENSDDRAG_TOKEN/--token required for authenticated screens")

            app.set_token(token, app_url)
            app.goto(f"{app_url.rstrip('/')}/projects", ".dashboard-grid", timeout=20000)
            app.wait_for_timeout(1500)
            try:  # async list — cards may land slightly after the grid mounts
                app.wait_for_selector(".dashboard-grid li", state="attached", timeout=15000)
            except Exception:
                pass
            app.wait_for_timeout(400)
            app.shot("impl-dashboard")
            items += measure_dashboard(app, "app")

            if not slug:
                slug = app.evaluate(
                    "() => {"
                    "  const link = document.querySelector('.dashboard-grid li a');"
                    "  return link ? (link.getAttribute('href') || '').split('/').pop() : '';"
                    "}"
                )
            if not slug:
                items.append(skip("dashboard slug discovery", "no project cards — create a project before running the check"))
                return fail(items, app_url, "no slug; pass --slug")

            detail = f"{app_url.rstrip('/')}/p/{slug}"
            app.goto(detail, "[data-testid=app-h1]", timeout=20000)
            app.wait_for_timeout(700)
            app.shot("impl-detail-overview")
            items += measure_detail_overview(app, "app")

            items += measure_specs_tab(app, "app")
            app.shot("impl-detail-specs")

            for label, name, probe in (
                ("Tasks", "impl-detail-tasks", "tasks rows or empty state render"),
                ("Hierarchy", "impl-detail-hierarchy", "hierarchy content renders"),
                ("Harness", "impl-detail-harness", "harness rules render"),
            ):
                items += measure_simple_tab(app, "app", label, probe)
                app.shot(name)

            # -- prototype best-effort: dashboard screenshot only ---------------
            # The single-file mock drives its views through an internal state
            # machine (no queryable classes), so measurement degrades to SKIP
            # — the screenshot pair is the visual reference (see FIDELITY_CHECKLIST).
            proto.goto(prototype_url, "body")
            proto.wait_for_timeout(500)
            proto.evaluate(
                "() => {"
                "  const btn = [...document.querySelectorAll('a,button')].find((el) => /launch app/i.test(el.textContent || ''));"
                "  if (btn) btn.click();"
                "}"
            )
            proto.wait_for_timeout(700)
            proto.shot("proto-dashboard")
            items.append(skip("prototype dashboard structure", "skipped (mock's internal navigation is not queryable; screenshot captured)"))

            # -- docs (public) --------------------------------------------------
            app.goto(f"{app_url.rstrip('/')}/docs", "[data-testid=docs-toc]", timeout=20000)
            app.wait_for_timeout(500)
            app.shot("impl-docs")
            items += measure_docs(app, "app")
            proto.goto(prototype_url, "body")  # back to first view for the final screenshot set
            proto.wait_for_timeout(300)
            proto.shot("proto-docs-reference")
    finally:
        if server:
            server.shutdown()

    failed = [i for i in items if i["status"] == "FAIL"]
    skipped = [i for i in items if i["status"] == "SKIP"]
    passed = [i for i in items if i["status"] == "PASS"]

    print("\n=== UI FIDELITY CHECKLIST ===")
    for item in items:
        print(f"[{item['status']:>4}] {item['name']:<58} {item['detail']}")
    print(f"\nSCREEN SUMMARY: pass={len(passed)} fail={len(failed)} skip={len(skipped)}")
    if failed:
        print("FAILURES:")
        for item in failed:
            print(f"  - {item['name']}: {item['detail']}")
    print(f"RESULT: {'FAIL' if failed else 'PASS'} — screenshots in {out_dir}")
    return 1 if failed else 0


def fail(items: list[dict], _app_url: str, reason: str) -> int:
    items.append(check("run completed", False, reason))
    for item in items:
        print(f"[{item['status']:>4}] {item['name']:<58} {item['detail']}")
    print(f"RESULT: FAIL — {reason}")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        prototype_url=args.prototype_url,
        app_url=args.app_url,
        out_dir=Path(args.out_dir),
        slug=args.slug,
        token=args.token,
        serve_proto=args.serve_prototype,
    )


if __name__ == "__main__":
    sys.exit(main())