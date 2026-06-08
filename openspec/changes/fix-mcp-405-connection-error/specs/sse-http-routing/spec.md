## ADDED Requirements

### Requirement: GET /api/projects returns project list
The server SHALL respond to `GET /api/projects` with a JSON array of existing projects.

#### Scenario: List projects successfully
- **WHEN** a client sends `GET /api/projects`
- **THEN** the server SHALL return HTTP 200 with a JSON array of project objects (`id`, `slug`, `name`, `description`)

### Requirement: POST /api/projects creates or returns a project
The server SHALL respond to `POST /api/projects` with the created or already-existing project.

#### Scenario: Create a new project
- **WHEN** a client sends `POST /api/projects` with a valid JSON body containing `slug` and `name`
- **THEN** the server SHALL return HTTP 201 with the project object and `already_existed: false`

#### Scenario: Return existing project on duplicate slug
- **WHEN** a client sends `POST /api/projects` with a `slug` that already exists
- **THEN** the server SHALL return HTTP 200 with the existing project object and `already_existed: true`

#### Scenario: Reject missing required fields
- **WHEN** a client sends `POST /api/projects` without `slug` or `name`
- **THEN** the server SHALL return HTTP 422

### Requirement: Same path handles multiple HTTP methods without 405
The server SHALL NOT return 405 Method Not Allowed for `GET` or `POST` requests to `/api/projects` due to routing conflicts.

#### Scenario: POST does not receive 405 from GET-only route
- **WHEN** a client sends `POST /api/projects` with a valid body
- **THEN** the server SHALL NOT return HTTP 405

#### Scenario: GET does not receive 405 from POST-only route
- **WHEN** a client sends `GET /api/projects`
- **THEN** the server SHALL NOT return HTTP 405
