## 1. Create OpenCode command templates module

- [x] 1.1 Create `client/src/templates/commands/opencode.js` file
- [x] 1.2 Implement `getOpenCodeCommands(slug, serverUrl)` function with all 13 commands
- [x] 1.3 Add YAML frontmatter generation (description, agent, model)
- [x] 1.4 Convert each command content from Claude Code format to OpenCode format (remove `/opsr:` prefix references)

## 2. Add content conversion helper

- [x] 2.1 Create `convertToOpenCodeFormat(content, commandName)` helper function
- [x] 2.2 Test conversion: `/opsr:propose` → `/propose`
- [x] 2.3 Test conversion: `$ARGUMENTS = /opsr:<command>` → `$ARGUMENTS = /<command>`

## 3. Modify init.js for OpenCode command installation

- [x] 3.1 Read `client/src/commands/init.js` to understand current command installation flow (lines 229-240)
- [x] 3.2 Import `getOpenCodeCommands` from templates
- [x] 3.3 Add OpenCode command installation loop after skill installation
- [x] 3.4 Create `.opencode/commands/` directory when OpenCode is selected
- [x] 3.5 Write each command file with YAML frontmatter
- [x] 3.6 Add log messages to `configured` array for OpenCode command installation

## 4. Update preview output

- [x] 4.1 Modify preview section to show OpenCode commands will be installed
- [x] 4.2 Add line: `.opencode/commands/                      — slash commands (/propose, /apply...)`

## 5. Integration test

- [ ] 5.1 Run `opensddrag init` with OpenCode selected in a test project
- [ ] 5.2 Verify 13 command files are created in `.opencode/commands/opsr/`
- [ ] 5.3 Verify each command file has identical content to Claude Code
- [ ] 5.4 Verify folder structure: `.opencode/commands/opsr/<name>.md`
- [ ] 5.5 Verify output shows command installation summary
- [ ] 5.6 Restart OpenCode and verify commands appear in command list

## 6. Claude Code and OpenCode now have identical command format

- [x] 6.1 Claude Code commands in `.claude/commands/opsr/<name>.md`
- [x] 6.2 OpenCode commands in `.opencode/commands/opsr/<name>.md`
- [x] 6.3 Both platforms use identical command content and structure