## Context

The OpenSddRag MCP server is now hosted and managed via Portainer. End users (developers on other projects) only need to install the Node.js client locally and run `opensddrag init` to connect their project. The current documentation is oriented toward contributors running the full stack locally, making it hard for end users to find the relevant steps.

The client CLI (`client/bin/opensddrag.js`) already accepts `--server` and `--project` flags, already checks server health, and already writes all required config files. The core functionality is complete — what's missing is documentation and a slightly more informative success output.

## Goals / Non-Goals

**Goals:**
- Add a "Quick Install" section to root `README.md` with exact copy-pasteable commands for connecting to the hosted server.
- Improve the `opensddrag init` success output to show the server URL, project slug, and a clear "what to do next" step.
- Add a `client/README.md` that documents the end-user setup flow standalone (no server setup required).
- Handle the case where `--project` is not supplied: the CLI already defaults to the directory name, but the success message should confirm the slug used.

**Non-Goals:**
- Changing the install mechanism (it stays as `npm install` + `node bin/opensddrag.js`).
- Publishing the client to npm (out of scope).
- Adding authentication/token management flows.
- Changing any server-side code.

## Decisions

### 1. Where to add Quick Install in README.md
Add a new top-level section `## Início Rápido — Conectando ao Servidor Hospedado` (matching the existing Portuguese language used in the README) immediately after the "Pré-requisitos" section. It will contain three steps: clone the repo (or just the client folder), `npm install` inside `client/`, and `node bin/opensddrag.js init --server <URL> --project <slug>`.

**Alternative considered:** A separate `QUICKSTART.md` file. Rejected because users land on README.md first; a separate file adds indirection.

### 2. CLI success output improvement
Update the final "Done" block in `client/src/commands/init.js` to print:
- The configured server URL
- The project slug registered
- A numbered "next steps" list: (1) open the project in Claude Code or OpenCode, (2) run `/opsr:status` to verify the connection

The change is additive: just replace the two `console.log` lines at the end with richer output. No flags, no new options, no behavior change.

### 3. client/README.md
Create `client/README.md` with: overview (one paragraph), prerequisites (Node.js 18+), installation, usage (`init` and `status` commands with flag reference), and a troubleshooting section for the most common error (server unreachable).

## Risks / Trade-offs

- [Risk] README.md section may go stale if the server URL changes → Mitigation: use a placeholder `<URL_DO_SERVIDOR>` in the docs and note that the actual URL is provided by the project maintainer.
- [Risk] More verbose CLI output could scroll past on slow terminals → Mitigation: the extra lines are minimal (4-5 lines total, no spinners or heavy formatting).

## Migration Plan

1. Edit `client/src/commands/init.js` — update the success block (last ~4 lines of the action).
2. Create `client/README.md`.
3. Edit root `README.md` — insert the new Quick Install section.

No migrations, no rollback needed — all changes are documentation and cosmetic CLI output.

## Open Questions

- What is the actual hosted server URL? The tasks will use a placeholder `<URL_DO_SERVIDOR>`; the user should substitute it with the real Portainer URL when writing the README.
