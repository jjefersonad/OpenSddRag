## Why

The MCP server is now hosted and available remotely (via Portainer), but there is no clear, user-facing quick-start guide for developers who only need to install and configure the local client to connect to the hosted server. Users currently have to read through the full README (written for contributors running everything locally) to find the relevant steps, which creates friction for adoption.

## What Changes

- Add a **Quick Install** section to `README.md` with a single-command flow for users who just want to connect to the hosted server.
- Improve the `client/` CLI so that `opensddrag init` accepts the server URL and project slug as flags (already supported) and provides clear, actionable output so users know the setup succeeded.
- Document the required environment and the exact commands: `npm install`, `node bin/opensddrag.js init --server <url> --project <slug>`.
- Add a `client/README.md` (or expand the existing one) focused on end-user client setup.

## Capabilities

### New Capabilities

- `client-install-flow`: End-user documentation and CLI UX for installing and configuring the local client against a remote hosted MCP server.

### Modified Capabilities

- _(none)_

## Impact

- `README.md` — new Quick Install / Client Setup section added.
- `client/` package — minor CLI output improvements (confirmation messages, next-steps hints).
- No breaking changes, no new dependencies, no server-side changes.
