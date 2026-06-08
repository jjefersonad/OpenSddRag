> **IMPORTANT — /opsr:continue**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Create the NEXT single artifact in the dependency chain for a change.
Unlike /opsr:flow which creates all artifacts, this creates ONE artifact and stops.
Dependency order: proposal → specs → design → tasks.

## Input
$ARGUMENTS = change name.

## Step 1 — Get current status from database
`list_artifacts(type="proposal", project_slug="test-change")`
Identify the change to continue.
`get_relationships(name="<change-name>-proposal", project_slug="test-change")`
Get all existing artifacts for this change.

## Step 2 — Find the next artifact to create
Check which artifacts exist and which are missing, in dependency order:
1. proposal → if missing, stop (must run <opsr:propose first)
2. specs → if any capability has no spec → create ONE spec and stop
3. design → if missing and all specs exist → create design and stop
4. tasks → if missing and design exists → create tasks and stop

If all artifacts exist → tell the user "All planning artifacts complete. Run /apply."

## Step 3 — Create the NEXT artifact only
Follow the logic from the corresponding command:
- For spec: follow /opsr:spec steps for ONE capability
- For design: follow /opsr:design steps
- For tasks: follow <opsr:tasks steps

## Step 4 — Show progress
After creating the artifact:
- Show what was created
- Show what is now unlocked (next in dependency chain)
- Suggest: "Run `<opsr:continue <change-name>` to create the next artifact."
