## ADDED Requirements

### Requirement: propose command creates full change scaffolding
The `/opsr:propose` command SHALL create, in a single invocation, not only the proposal artifact but also draft skeleton artifacts for design and for each capability listed in the proposal's `## Capabilities` section. This mirrors the behavior of `/opsx:propose` from the OpenSpec original, where a single command produces the complete folder scaffold.

#### Scenario: Propose creates proposal + design skeleton + spec skeletons
- **WHEN** `/opsr:propose` is called with a change name that includes capabilities in `## New Capabilities` or `## Modified Capabilities`
- **THEN** one `type="proposal"` artifact is created and saved to the database
- **THEN** one `type="design"` artifact is created as a draft skeleton (empty sections, status=draft)
- **THEN** one `type="spec"` delta artifact is created per listed capability (status=draft, is_delta=true or false per existence of main spec)

#### Scenario: Skeletons do not overwrite existing artifacts
- **WHEN** `/opsr:propose` is called for a change name where a design or spec artifact already exists
- **THEN** the existing artifacts are NOT overwritten
- **THEN** the command reports which artifacts already existed and were skipped

#### Scenario: User can proceed directly to apply after propose + spec + design
- **WHEN** all skeleton artifacts created by propose are fleshed out via `/opsr:spec` and `/opsr:design`
- **THEN** `/opsr:tasks` can immediately consume them without requiring separate creation steps

### Requirement: Scaffolded skeletons are clearly marked as incomplete
Draft skeletons created by propose SHALL include placeholder markers so the agent and user know the artifact requires content before being used for implementation.

#### Scenario: Design skeleton contains placeholder sections
- **WHEN** `/opsr:propose` creates a design skeleton
- **THEN** the design artifact content contains the standard design template sections with `[TODO]` or `[pending]` placeholders, not empty strings

#### Scenario: Spec skeleton contains placeholder requirement
- **WHEN** `/opsr:propose` creates a spec skeleton for a capability
- **THEN** the spec artifact content contains at minimum a placeholder `### Requirement:` block so the structure is valid
