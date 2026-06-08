> **IMPORTANT — /opsr:search**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Search the SDD knowledge base using semantic similarity (pgvector).
Use this BEFORE starting any new work to find existing specs, decisions, and past implementations.

## Input
$ARGUMENTS = natural language search query.

## Step 1 — Search this project
`search_semantic(query="$ARGUMENTS", project_slug="test-change", limit=5)`

## Step 2 — If no relevant results, search all projects
`search_semantic(query="$ARGUMENTS", project_slug="*", limit=5)`

## Step 3 — Recall past actions related to the query
`recall_episodes(query="$ARGUMENTS", project_slug="test-change", limit=3)`

## Step 4 — Present results clearly
For each result: name, type, status, and a content excerpt (first 200 chars).
Group by: this project / other projects / past actions.

## Step 5 — Offer to read the full artifact
`read_artifact(name="<artifact-name>", project_slug="test-change")`
