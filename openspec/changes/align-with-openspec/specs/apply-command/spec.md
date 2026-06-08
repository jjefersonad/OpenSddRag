## ADDED Requirements

### Requirement: apply command finds tasks in both draft and active status
The `/opsr:apply` command SHALL query for pending tasks using `status IN ('draft', 'active')`, not only `status='draft'`. This prevents tasks that were set to `active` in a previous session from being permanently orphaned and invisible to subsequent apply invocations.

#### Scenario: Resuming work after session interruption finds the active task
- **WHEN** a task was set to `status="active"` in session A (step 4 of apply)
- **AND** session A was interrupted before the task was completed
- **WHEN** `/opsr:apply` is called in session B
- **THEN** the active task appears in the list of pending tasks
- **THEN** the agent resumes from that task rather than picking a different one or reporting no tasks pending

#### Scenario: Active task is prioritized over draft tasks
- **WHEN** there is one task with `status="active"` and two with `status="draft"`
- **WHEN** `/opsr:apply` is called
- **THEN** the active task is selected first (it was already in progress)

#### Scenario: No orphaned tasks after full apply cycle
- **WHEN** all tasks for a change are completed (set to `status="archived"`)
- **WHEN** `/opsr:apply` is called again
- **THEN** the command reports no pending tasks and suggests running `/opsr:verify`

### Requirement: apply command filters tasks by change name
When called with a specific change name, `/opsr:apply` SHALL only consider tasks whose `metadata.change_name` matches the given change. It MUST NOT pick up tasks from other changes that happen to be in `draft` or `active` status.

#### Scenario: Multiple changes in progress are isolated
- **WHEN** two changes each have tasks in `status="draft"` in the database
- **WHEN** `/opsr:apply change-a` is called
- **THEN** only tasks with `metadata.change_name="change-a"` are considered
- **THEN** tasks from change-b are not touched
