## MODIFIED Requirements

### Requirement: Scaffolded skeletons are clearly marked as incomplete
Draft skeletons created by propose SHALL include placeholder markers so the agent and user know the artifact requires content before being used for implementation. The agent executing `/opsr:propose` SHALL copy these markers verbatim and MUST NOT replace them with generated domain-specific content (such as authentication rules, database schemas, or technology-specific requirements) that was not explicitly provided by the user in the change description.

#### Scenario: Design skeleton contains placeholder sections
- **WHEN** `/opsr:propose` creates a design skeleton
- **THEN** the design artifact content contains the standard design template sections with `[TODO]` or `[pending]` placeholders, not empty strings
- **THEN** the design artifact does not contain generated technical decisions, architecture choices, or risk assessments that the user did not specify

#### Scenario: Spec skeleton contains placeholder requirement
- **WHEN** `/opsr:propose` creates a spec skeleton for a capability
- **THEN** the spec artifact content contains at minimum a placeholder `### Requirement:` block so the structure is valid
- **THEN** the `[TODO]` markers inside the requirement block are preserved as literal text, not replaced with inferred requirements

#### Scenario: Agent receives explicit prohibition in command template
- **WHEN** the agent reads Steps 5 and 6 of the `/opsr:propose` command template
- **THEN** a clearly highlighted instruction (bold or WARNING block) prohibiting placeholder replacement is visible immediately before each `create_artifact` call
- **THEN** the instruction uses imperative language (e.g., "MUST NOT", "DO NOT replace", "copy VERBATIM")
