# Testing

How to run the automated checks in this repository. There is no Playwright Page Object e2e suite for a separate `frontend/` app — the dashboard lives in `web/` and is covered by Vitest plus a visual fidelity script.

---

## Layers

| Package | Runner | What it covers |
|---|---|---|
| `web/` | Vitest (`npm test`) | Routes, docs, landing, keys, dashboard components |
| `mcp-server/` | pytest | Domain, repositories, MCP tools, management API |
| `client/` | Node test (`npm test`) | CLI init, flow registration, templates |
| `scripts/ui-fidelity/check.py` | Playwright for Python | Pixel/layout checklist vs `docs/ui/OpenSddRag.dc.html` |

---

## Dashboard (Vitest)

```bash
cd web
npm test
# one file
npx vitest run src/features/docs/DocsPage.test.tsx
```

The app under test is public `/docs` and `/` without a token; protected routes stub `fetch`.

---

## MCP server (pytest)

```bash
cd mcp-server
pytest
pytest tests/test_foo.py
pytest -k "test_name"
```

Needs PostgreSQL/pgvector reachable (`DATABASE_URL`, Compose maps host port `54326`).

---

## CLI client

```bash
cd client
npm test
```

---

## UI fidelity (visual)

Measured checklist at 1440×900 against the prototype. Details: [`docs/ui/FIDELITY_CHECKLIST.md`](ui/FIDELITY_CHECKLIST.md).

```bash
docker compose up -d
pip install playwright && playwright install chromium
python3 scripts/ui-fidelity/check.py \
  --app-url http://localhost:3001 \
  --serve-prototype \
  --token "$OPENSDDRAG_TOKEN"
```

`OPENSDDRAG_TOKEN` is `MANAGEMENT_API_TOKEN` (Compose default `123456`), not an MCP API key. Default dashboard origin is `http://localhost:3001`; Vite on `:5173` is blocked by CORS unless `WEB_ORIGIN` matches.
