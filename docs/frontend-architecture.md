# Frontend Architecture

Technical reference for the dashboard in `web/` — a Vite + React SPA that talks to the management REST API (`/api/v1`), not to MCP.

Live getting-started and design tokens: [http://localhost:3001/docs](http://localhost:3001/docs). For ports, env and CORS, see [`CLAUDE.md`](../CLAUDE.md) and [`mcp-server/.env.example`](../mcp-server/.env.example).

---

## Stack

| Technology | Role |
|---|---|
| React 19 | UI |
| Vite 7 | Dev server and production build |
| TypeScript | Static typing (`tsc --noEmit` in `npm run build`) |
| React Router 7 | SPA routes |
| CSS variables | Design tokens in `web/src/styles/tokens.css` (inline styles in components) |
| Vitest + Testing Library | Unit / component tests |
| nginx (Compose `web` image) | Serves `dist/` on port 3001 |

There is no Tailwind, Axios, Zustand, or Socket.io in this app. Fetch goes through `web/src/api/client.ts`.

---

## Directory structure

```
web/src/
├── api/              # /api/v1 client (Bearer management token) + resource modules
├── features/         # Screens by domain (landing, docs, auth, projects, keys, …)
├── components/       # Shared chrome (PublicNav, ProtectedRoute, ui/)
├── hooks/            # Data hooks over api/
├── lib/              # Path helpers
├── styles/           # tokens.css
├── routes.tsx        # Route table
└── App.tsx           # Authenticated shell
```

**Dependency rule:** `features/` render; `hooks/` fetch; `api/` is the only HTTP layer. Pages do not call `fetch` directly.

---

## Auth and API

- Login stores `MANAGEMENT_API_TOKEN` in `localStorage` (`opensddrag.management_token`).
- Every `/api/v1` call sends `Authorization: Bearer <token>`. HTTP 401 clears the token and routes to `/login`.
- `VITE_API_URL` defaults to `http://localhost:8000/api/v1`. Compose `WEB_ORIGIN` must match the dashboard origin (`http://localhost:3001`) or the browser is blocked by CORS.
- MCP API keys (`/keys`) are a different secret from the dashboard token. The dashboard is not an MCP client.

---

## Public vs protected routes

| Path | Auth |
|---|---|
| `/`, `/docs`, `/login` | Public |
| `/projects`, `/p/:slug`, `/p/:slug/c/:change`, `/keys` | Protected |

Pipelines (flows) drive the phase strip from `GET /api/v1/flows` — a new registered flow renders without UI changes.

---

## Local run

```bash
# Full stack (recommended)
docker compose up -d          # dashboard http://localhost:3001

# Vite only (CORS: WEB_ORIGIN must allow this origin, or use --port 3001)
cd web && npm install && npm run dev
```
