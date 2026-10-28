# UI Fidelity Checklist (web-ui-prototype-fidelity, REQ-019 / design D12)

Measured checklist comparing the design prototype (`docs/ui/OpenSddRag.dc.html`)
against the running app (real API data) at **1440×900**, one screenshot pair per
screen, produced by `scripts/ui-fidelity/check.py`. Screenshots land in
`.scratch/ui-fidelity/` (git-ignored scratch).

## Prerequisites

- Python 3.10+ and Playwright for Python:
  ```bash
  pip install playwright
  playwright install chromium
  ```
- The full stack running with real data:
  ```bash
  docker compose up -d        # database + MCP server (SSE :8000) + dashboard
  ```
- A management API token (`OPENSDDRAG_TOKEN` env or `--token`). The dashboard
  stores it under the localStorage key `opensddrag.management_token`.
- The dashboard URL (`APP_URL` env or `--app-url`, default `http://localhost:3001`).
  `mcp-server` CORS allows **exactly one** origin (`WEB_ORIGIN`, default
  `http://localhost:3001` — `mcp-server/src/opensddrag/config.py`). The API sends
  no `Access-Control-Allow-Origin` for Vite's default port (5173). Either:
  - run Vite on the allowed origin: `npm run dev -- --port 3001` (from `web/`), or
  - for local check runs only, launch a Chrome instance with web security disabled
    (`playwright` chromium launch arg `--disable-web-security`).
  Prefer the first. Do not disable web security outside local verification.
- The prototype is served automatically with `--serve-prototype` (stdlib static
  server over `docs/ui/` on the prototype URL host/port, default
  `http://localhost:4100`), or bring your own static server and pass `--prototype-url`.

## How to run

```bash
python3 scripts/ui-fidelity/check.py \
  --app-url http://localhost:3001 \
  --serve-prototype \
  --token "$OPENSDDRAG_TOKEN"
# detail screens use the first dashboard card's slug; override with --slug <slug>
```

Exit code `0` only when every APP checklist item passes. FAIL items are listed
at the end of the output; SKIP items (documented below) do not fail the run.

## Checklist items

### Landing (public)

| Item | Measured by |
|---|---|
| body font resolves to IBM Plex Sans | computed `font-family` of `body` |
| no anchor renders with an underline (app) | computed `text-decoration-line` of every `<a>` |
| Launch CTA is a filled accent button `#10b981` | computed `background-color` of the "Launch app" control |
| prototype: same font + CTA measurements (screenshots are the visual reference) | same probes on the prototype page |

### Dashboard

| Item | Measured by |
|---|---|
| `.dashboard-grid` resolves 2 columns at 1440px | computed `grid-template-columns` |
| first card wider than 400px | `getBoundingClientRect().width` |
| subtitle `<N> registered · multi-tenant artifact memory` | app text probe |
| prototype: screenshots only — the single-file mock drives its views through an internal state machine (no queryable classes), so dashboard structure **degrades to SKIP** on the prototype side and the screenshot pair (`proto-dashboard.png` / `impl-dashboard.png`) is the visual reference | capture after clicking the prototype's Launch control |

### Detail — Overview (`/p/<slug>`)

| Item | Measured by |
|---|---|
| header `app-h1` present; tab bar has ≥3 tabs | presence probes |
| horizontal phase strip present | `[data-testid^=phase-strip-]` (omitted when the flow has no lifecycle → item reports "absent" and fails only if the project's flow declares one) |
| `.overview-grid` resolves 2 tracks at 1440px | computed `grid-template-columns` |
| Working context + Execution trace panels present | test ids `working-context-panel` / `traces-panel` |

### Detail — Specs tab

| Item | Measured by |
|---|---|
| at least one spec card (`<article>`) renders | DOM count |
| card shows `<n> requirements` count | text probe matching `/requirements/` |
| WHEN scenarios render amber `rgb(251,191,36)` | computed color of `[data-testid=scenario-when]` after expanding a card |

### Detail — Tasks / Hierarchy / Harness tabs

| Item | Measured by |
|---|---|
| the tab's panel renders content (rows or empty state) | panel text length probe |

### Docs (`/docs`)

| Item | Measured by |
|---|---|
| TOC lists every getting-started + reference section (≥15) | link count inside `docs-toc`; labels include Server setup, CLI client, Claude Code, OpenCode, Pipelines |
| Color section has a swatch for every token (≥15) | `[data-testid^=docs-swatch-]` / `[data-hex]` count |
| Quickstart commands in mono code blocks (≥2 `pre`/`code`) | count + font-family probe |

## Screenshots

| Screen | Prototype | App |
|---|---|---|
| landing | `proto-landing.png` | `impl-landing.png` |
| dashboard | `proto-dashboard.png` (best effort) | `impl-dashboard.png` |
| detail overview | — (single-view mock) | `impl-detail-overview.png` |
| Specs / Tasks / Hierarchy / Harness tabs | — | `impl-detail-specs.png`, `impl-detail-tasks.png`, `impl-detail-hierarchy.png`, `impl-detail-harness.png` |
| docs | `proto-docs-reference.png` | `impl-docs.png` |

## Notes

- The prototype is a single-file mock; only its landing view is reliably
  reachable by external navigation, so its extra screens degrade to **SKIP**
  (annotated in the output) rather than failing the gate. The **app** side is
  strict: every FAIL makes the exit code non-zero.
- Run `/opsr:verify` for the change, record this checklist's output there.