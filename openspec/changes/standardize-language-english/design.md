## Context

The repository currently has its primary `README.md` written entirely in Portuguese, and the SQL migration file (`001_initial.sql`) contains Portuguese section-header comments. All source code (Python, JavaScript) and other documentation files are already in English. The change is purely textual — no logic, schema, or API modifications are needed.

## Goals / Non-Goals

**Goals:**
- Translate `README.md` to English, preserving all content and structure
- Translate Portuguese comments in `001_initial.sql` to English
- Confirm `docs/authorization.md`, `client/README.md`, `client/CLAUDE.md` are already in English (or translate if not)
- Establish a written convention: project-level text is English; database content is user-language-agnostic

**Non-Goals:**
- Translating or modifying content already persisted in the database
- Adding language detection or enforcement logic to the MCP server
- Changing any API contracts, tool signatures, or database schema
- Translating planning artifacts inside `openspec/changes/` (they are development artifacts, not shipped docs)

## Decisions

**Decision: Translate in-place, keep the same file structure**
Both `README.md` and the SQL migration file keep their paths unchanged. Renaming or restructuring would break external links and Docker/CI references unnecessarily.
*Alternative considered*: Keep a Portuguese version alongside an English one. Rejected — maintaining two copies of docs diverges quickly.

**Decision: No runtime enforcement**
Language policy is a developer convention documented in `CLAUDE.md` and the new spec, not a gate in the MCP server. Adding a language-detection layer would add latency, require a language model or library dependency, and would incorrectly reject multilingual or code-mixed content.
*Alternative considered*: Lint check in CI that scans new commits for non-ASCII characters in `.py`/`.js` files. Rejected — overly broad (would reject user-provided strings, log messages, etc.).

**Decision: Scope limited to files with confirmed Portuguese content**
Only `README.md` and `001_initial.sql` have confirmed Portuguese text. All other files (`docs/`, `client/`) are already in English and require only verification, not translation.

## Risks / Trade-offs

- [Risk] README translation loses nuance or technical accuracy → Mitigation: keep original structure section-by-section, review terminology against the codebase
- [Risk] Future contributors write Portuguese docs again (convention drift) → Mitigation: document the rule in `CLAUDE.md` and the new `project-language-standard` spec

## Migration Plan

1. Translate `README.md` in-place (no redirects needed — no published URL to preserve)
2. Update SQL comments in `001_initial.sql` (comments only, schema unchanged)
3. Verify `docs/` and `client/` docs are English
4. Append language convention note to `CLAUDE.md`
5. No deployment or database migration required

## Open Questions

- None — scope is bounded to documentation and comments only
