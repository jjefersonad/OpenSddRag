# Test Change

---

## OpenSddRag — SDD + Harness

This project uses **OpenSddRag** for Spec-Driven Development with persistent semantic memory.

- **MCP server:** http://localhost:8000
- **Project slug:** `test-change`
- **Skills:** `.claude/skills/opensddrag-*/SKILL.md`
- **Commands:** `.claude/commands/opsr/`

### Before implementing any feature

Always search for existing specs first:

```
search_semantic(query="<topic>", project_slug="test-change")
```

### SDD Commands

| Command | When to use |
|---------|-------------|
| `/opsr:propose` | Start here — capture intent and scope before any code |
| `/opsr:spec` | Formalize requirements (Purpose / SHALL / Scenarios) |
| `/opsr:design` | Document technical decisions and trade-offs |
| `/opsr:tasks` | Decompose spec into atomic tasks (< 4h each) |
| `/opsr:apply` | Implement the next pending task against spec criteria |
| `/opsr:flow` | Run the full flow end-to-end for a feature |
| `/opsr:search` | Semantic search over specs and past work |
| `/opsr:status` | Show what's in progress and what's done |
| `/opsr:archive` | Mark a completed feature as archived |

### SDD Flow

```
/opsr:propose → /opsr:spec → /opsr:design → /opsr:tasks → /opsr:apply → /opsr:archive
```
