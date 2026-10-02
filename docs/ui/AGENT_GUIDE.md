# OpenSddRag Web UI — Guide for AI Agents

This file teaches an AI coding agent (Claude Code, Cursor, Copilot, etc.) how to understand, run, extend, and implement the OpenSddRag web prototype (`OpenSddRag.dc.html`) in production.

---

## 1. What this is

A clickable prototype of a web dashboard for **OpenSddRag**, an MCP server that gives AI agents persistent memory and a Spec-Driven Development (SDD) workflow.

The prototype has two parts:
- **Landing page**: the product pitch.
- **Internal app**: project registry, SDD pipeline, artifacts (proposal, specs, design, tasks), harness rules, and semantic search.

Every screen reads from mock data held in memory. Nothing is saved when the page reloads.

## 2. Files

| File | Purpose |
|---|---|
| `OpenSddRag.dc.html` | The whole prototype: template, logic, and mock data. |
| `support.js` | Runtime that renders the `.dc.html` file. Do not edit it. |
| `AGENT_GUIDE.md` | This document. |

Open `OpenSddRag.dc.html` in a browser from a local static server (for example `npx serve .`). It will not run from `file://` because `support.js` must load.

## 3. File anatomy

`OpenSddRag.dc.html` has two blocks:

1. **Template** (the markup inside `<x-dc>`)
   - HTML with inline styles only.
   - `{{ path }}` holes do dotted lookups only. They cannot contain expressions.
   - Control flow uses `<sc-if value="{{ bool }}">` and `<sc-for list="{{ arr }}" as="item">`.
   - Hover styles use `style-hover="..."`.
2. **Logic** (the `<script data-dc-script>` block)
   - `class Component extends DCLogic`, which works like a React class component without `render()`.
   - `renderVals()` returns every value and handler the template uses.
   - The mock data lives in `seedProjects()`, and the SDD phases live in `PHASES`.

**Rule:** put every computation (ternaries, maps, colors that depend on state) in `renderVals()` and give the result a name. Never put logic in `{{ }}`.

## 4. Domain model

This matches the OpenSddRag server concepts:

```
Project
 ├─ id, name, slug, language, desc
 ├─ change            // active change name, e.g. "add-stripe-billing"
 ├─ phaseIndex        // 0..7 → PHASES
 ├─ proposal { problem, whatChanges[], affected[], outOfScope[] }
 ├─ specs[] { capability, status, requirements[] { text, scenarios[] { when, then } } }
 ├─ design { decisions[] { title, choice, rationale }, tradeoffs[], risks[] { risk, mitigation } }
 ├─ tasks[] { group, items[] { text, done } }
 ├─ rules[] { name, trigger, category, severity, instruction, enabled }   // harness
 ├─ traces[] { tool, summary, time }        // episodic memory
 └─ session { activeArtifacts[], note }     // working context
```

**SDD phases, in order:**
`propose → spec → design → tasks → apply → verify → sync → archive`

- Each phase maps to a tab. See `PHASES[i].tab`.
- A phase is `done` when `i < phaseIndex`, `active` when `i === phaseIndex`, and `pending` otherwise.

**Harness rule fields:**
- `trigger`: `always` | `on_spec` | `on_apply` | `on_verify`
- `severity`: `error` | `warning` | `info`
- `category`: `architecture` | `naming` | `forbidden` | `verification`

## 5. Screens and state

| State (`this.state`) | Effect |
|---|---|
| `view: 'landing' \| 'app' \| 'docs'` | Switches between the landing page, the app, and the Docs & Design System page (`goDocs`). |
| `activeProjectId: null \| id` | `null` shows the dashboard. An id shows that project's detail page. |
| `tab` | `overview` \| `proposal` \| `specs` \| `design` \| `tasks` \| `harness` |
| `searchOpen`, `searchQuery` | ⌘K semantic search overlay. |
| `createOpen`, `draft` | "New project" modal. |
| `expandedSpecs{}` | Which spec cards are expanded. |

**Handlers:**

| Handler | What it does |
|---|---|
| `launch` | Opens the app. |
| `goHome` | Returns to the landing page. |
| `goProjects` | Shows the dashboard. |
| `openProject(id)` | Opens a project's detail page. |
| `setTab(t)` | Switches the active tab. |
| `openSearch` / `closeSearch` | Opens or closes search. |
| `openCreate` / `submitCreate` | Opens the modal / registers the project. |
| `toggleTask(pid, gi, ti)` | Checks or unchecks a task. |
| `toggleSpec(id)` | Expands or collapses a spec card. |
| `toggleRule(pid, ri)` | Turns a harness rule on or off. |

**Keyboard:** `⌘K` / `Ctrl+K` opens search. `Esc` closes any overlay.

## 6. Common tasks (recipes)

### 6.1 Add a mock project
Add an object to the array in `seedProjects()` that follows the model in §4. The dashboard, sidebar, and search index pick it up automatically.

### 6.2 Add a new tab (e.g. "Traces")
1. In `renderVals()`, add `mkTab('traces','Traces',ap.traces.length)` to `tabs`.
2. Return `tabTraces: st.tab==='traces'`.
3. In the template, add `<sc-if value="{{ tabTraces }}">…</sc-if>` next to the other tabs. Reuse the card style: `background:#131619; border:1px solid rgba(255,255,255,0.08); border-radius:12px`.

### 6.3 Advance a project to the next phase
Add a handler:
```js
advance=(pid)=>{ const p=this.state.projects.find(x=>x.id===pid); if(p&&p.phaseIndex<7){ p.phaseIndex++; this.forceUpdate(); } };
```
Expose it in `renderVals()` and bind it to a button.

### 6.4 Change the search
Search builds `idxRows` in `renderVals()` and filters them with a substring match. The `score` shown is fake. To use real search, see §7.

## 7. Moving to production (connect the real server)

The OpenSddRag MCP server has the real data. Keep the UI and replace the mock data layer.

1. **Create a small REST/HTTP layer** in front of the server, or call the MCP tools directly. Suggested endpoints:
   - `GET  /projects` → list of projects
   - `POST /projects` → register a project `{name, slug, description, language}`
   - `GET  /projects/:slug/artifacts?type=proposal|spec|design|tasks`
   - `PATCH /projects/:slug/tasks/:id` → `{done}`
   - `GET  /projects/:slug/rules`, `PATCH /projects/:slug/rules/:id` → `{enabled}`
   - `GET  /projects/:slug/traces`
   - `GET  /search?q=...` → semantic search over artifacts and traces (embeddings + cosine similarity)
2. **In `componentDidMount`**, replace `seedProjects()` with `fetch('/projects')` and call `setState`.
3. **Make mutations optimistic:** update local state first, send the PATCH, and roll back if it fails.
4. **For search**, debounce `onSearchInput` (about 200 ms), call `/search`, and map the results to `{type,title,snippet,project,score,pid,tab}`.
5. **Auth:** send the project API key in the `Authorization: Bearer <key>` header.

Keep the shapes in §4 so the template needs no changes.

## 8. Visual rules (keep the layout consistent)

- **Fonts:** `IBM Plex Sans` for UI text. `IBM Plex Mono` for code, slugs, labels, and metadata.
- **Backgrounds:** `#0a0c0d` for the page, `#0c0e10` for the sidebar, `#131619` for cards, `#0e1113` for insets and terminals.
- **Borders:** `rgba(255,255,255,0.08)`.
- **Text:** `#e8ebed` primary, `#8a9298` secondary, `#5b6469` tertiary.
- **Accent:** `#10b981` (hover and bright shade `#34d399`). Text on accent backgrounds is `#04140d`.
- **Semantic colors:** amber `#fbbf24` (WHEN / warning / proposal), blue `#60a5fa` (SHALL / info / spec), violet `#a78bfa` (design), red `#f87171` (error / risk).
- **Section labels:** mono, 11px, uppercase, letter-spacing 0.08em.
- **Styles are always inline.** Do not use CSS classes. Keep keyframes in `<helmet><style>`.
- **Avoid entry animations that use `animation-fill-mode: both` with `opacity: 0`.** They caused a bug where content stayed invisible.

## 9. Checklist before you finish a change

- [ ] No `{{ }}` hole contains an expression.
- [ ] Every new value is returned from `renderVals()`.
- [ ] Every `<sc-for>` and `<sc-if>` has a `hint-*` attribute.
- [ ] No console errors.
- [ ] You tested: landing → Launch → project → every tab → ⌘K → New project.
