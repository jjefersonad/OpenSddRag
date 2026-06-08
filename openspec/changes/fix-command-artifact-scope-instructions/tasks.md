## 1. Refactor header functions

- [x] 1.1 Rename the existing `header(name)` function to `artifactHeader(name)` in `client/src/templates/commands/index.js`
- [x] 1.2 Add a new `implementHeader(name)` function that allows local file I/O (Edit/Write/Bash) while still including the MCP server URL, project slug, and a note that SDD artifact reads/trace records go through MCP
- [x] 1.3 Add JSDoc comments to both functions documenting which commands use each and why

## 2. Assign correct headers to each command

- [x] 2.1 Update `propose`, `spec`, `design`, `tasks`, `archive`, `explore`, `continue`, `status`, `search`, and `sync` commands to call `artifactHeader(name)`
- [x] 2.2 Update `apply` command to call `implementHeader(name)`
- [x] 2.3 Update `verify` command to call `implementHeader(name)`
- [x] 2.4 Update `flow` command to use `artifactHeader(name)` and add an inline note in the implementation section clarifying that code writes are local

## 3. Verify and test

- [x] 3.1 Inspect the rendered output of each command to confirm no command has both "DO NOT create local files" and an instruction to implement code changes
- [x] 3.2 Run `node bin/opensddrag.js init` in a test project and verify the generated `.claude/commands/opsr/apply.md` contains the new implementation-aware header
- [x] 3.3 Verify the generated `.claude/commands/opsr/propose.md` still contains the artifact-only restriction
