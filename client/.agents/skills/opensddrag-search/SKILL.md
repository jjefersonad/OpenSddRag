# OpenSddRag — Search
> Server: http://localhost:8000 | project_slug: `test-change`

Semantic search over the SDD knowledge base using pgvector similarity.
Always run this BEFORE starting new work to find existing specs and decisions.

Searches: this project first, then all projects if no results.
Also recalls past agent actions (episodic memory).

**Run:** `/opsr:search <natural language query>`
