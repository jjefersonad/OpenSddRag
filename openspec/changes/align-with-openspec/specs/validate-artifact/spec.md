## ADDED Requirements

### Requirement: validate_artifact checks structural sections for task artifacts
The `validate_artifact` MCP tool SHALL verify that artifacts of `type="task"` contain the required structural sections `## Goal` and `## Acceptance Criteria`. Content that lacks these sections SHALL produce validation errors, not pass silently.

#### Scenario: Valid task passes validation
- **WHEN** `validate_artifact` is called on a task artifact whose content contains `## Goal` and `## Acceptance Criteria`
- **THEN** the response is `{"valid": true, "issues": []}`

#### Scenario: Task missing Goal section fails validation
- **WHEN** `validate_artifact` is called on a task artifact whose content does not contain `## Goal`
- **THEN** the response contains `{"valid": false, "issues": ["Task must have a '## Goal' section."]}``

#### Scenario: Task missing Acceptance Criteria fails validation
- **WHEN** `validate_artifact` is called on a task artifact whose content does not contain `## Acceptance Criteria`
- **THEN** the response contains `{"valid": false, "issues": ["Task must have an '## Acceptance Criteria' section."]}``

#### Scenario: Empty task content fails validation
- **WHEN** `validate_artifact` is called on a task artifact with empty or whitespace-only content
- **THEN** the response contains at least one issue about content being too short

### Requirement: validate_artifact spec check remains unchanged
The existing validation rules for `type="spec"` (must contain `Purpose` and `Requirements` sections) SHALL continue to work as before. This change is additive only.

#### Scenario: Valid spec still passes
- **WHEN** `validate_artifact` is called on a spec artifact with `Purpose` and `Requirements` sections
- **THEN** the response is `{"valid": true, "issues": []}`
