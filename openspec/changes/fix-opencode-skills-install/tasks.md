## 1. Add helper functions for OpenCode skill format

- [x] 1.1 Add `extractDescription(skillContent)` function in `init.js` to parse first paragraph after skill title for description (1-1024 chars)
- [x] 1.2 Add `addOpencodeFrontmatter(skill)` function in `init.js` that wraps skill content with YAML frontmatter (name, description, compatibility: opencode)
- [x] 1.3 Test that `extractDescription` correctly identifies skill purpose from existing skill templates

## 2. Modify init.js skill installation logic

- [x] 2.1 Read `client/src/commands/init.js` lines 147-169 to understand current skill installation flow
- [x] 2.2 Add condition check for `configuringOpenCode` to trigger OpenCode skill installation
- [x] 2.3 Create `.opencode/skills/` directory structure when OpenCode is selected
- [x] 2.4 Install all 13 SDD skills to `.opencode/skills/<skill-name>/SKILL.md` with identical content
- [x] 2.5 Add log messages to `configured` array for OpenCode skill installation confirmation

## 3. Verify skills have identical content

- [x] 3.1 Test that all 13 skill files are created in `.opencode/skills/`
- [x] 3.2 Verify each SKILL.md file has identical content to Claude Code (no YAML frontmatter)
- [x] 3.3 Verify skills use same format for both platforms
- [x] 3.4 Verify skills are also installed to `.claude/skills/` and `.agents/skills/` (dual installation)

## 4. Integration test

- [ ] 4.1 Run `opensddrag init` with OpenCode selected in a test project
- [ ] 4.2 Confirm `opencode.json` MCP config is correct
- [ ] 4.3 Confirm 13 skills installed to `.opencode/skills/`
- [ ] 4.4 Confirm skills have identical content to Claude Code format
- [ ] 4.5 Restart OpenCode and verify skills appear in the skill tool

## 3. Verify implementation against specs

- [ ] 3.1 Test that all 13 skill files are created in `.opencode/skills/`
- [ ] 3.2 Verify each SKILL.md file has valid YAML frontmatter with name, description, compatibility: opencode
- [ ] 3.3 Verify descriptions are between 1-1024 characters
- [ ] 3.4 Verify skills are also installed to `.claude/skills/` and `.agents/skills/` (dual installation)

## 4. Integration test

- [ ] 4.1 Run `opensddrag init` with OpenCode selected in a test project
- [ ] 4.2 Confirm `opencode.json` MCP config is correct
- [ ] 4.3 Confirm 13 skills installed to `.opencode/skills/`
- [ ] 4.4 Confirm output shows skill installation summary
- [ ] 4.5 Restart OpenCode and verify skills appear in the skill tool