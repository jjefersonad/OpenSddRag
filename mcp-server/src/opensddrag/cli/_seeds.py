"""
Global SDD skills — semantic index for suggest_skill().
Each entry describes WHEN to use a command so the AI can find it by natural language objective.
Detailed step-by-step instructions live in .claude/skills/opensddrag-*/SKILL.md (created by npm client).

This module also seeds global harness rules (per-project). Rules are persisted
per-project (the `project_rules` schema requires a `project_id`); for that
reason the seed function iterates over every existing project and upserts the
rule idempotently. `opensddrag-server init` invokes this function so that
fresh databases get the `tdd-first` rule for every project already registered
— re-running `init` is a no-op thanks to the `ON CONFLICT (project_id, name)
DO UPDATE` clause in `rule_repository.upsert`.
"""

from opensddrag.db import project_repository, rule_repository, skill_repository
from opensddrag.embedding.service import embed
from opensddrag.models.rule import RuleCreate
from opensddrag.models.skill import SkillCreate, SkillStep


# Harness rule seeded into every project by `opensddrag-server init`.
# Implements REQ-001 of the `tdd-red-green-refactor` capability from the
# `embed-tdd-in-sdd-workflow` change: the agent MUST NOT write production code
# for a unit before a failing test exists. The exemption path (tasks with
# `metadata.test_exempt=true` plus a stated reason) comes from the MODIFIED
# REQ-005 of `sdd-workflow-lifecycle` in the same change.
#
# `project_id` is injected per-project in `seed_global_harness_rules` because
# the `RuleCreate` model requires it (the `project_rules` schema does not
# support a global `project_id = NULL`).
_TDD_FIRST_RULE_TEMPLATE: dict = {
    "name": "tdd-first",
    "trigger": "on_apply",
    "category": "verification",
    "severity": "error",
    "instruction": (
        "Apply is test-first (RED → GREEN → REFACTOR) per testable unit. "
        "MUST NOT write production code for a unit before a failing unit test "
        "exists covering the intended behavior; the unit MUST have a linked "
        "`test` artifact (`type=\"test\"`, `level=\"unit\"`) progressing "
        "`test_status` from `pending` → `failing` → `passing`. Stack-agnostic: "
        "applies equally to pytest, vitest, jest, and go test. "
        "EXCEPTION: tasks carrying `metadata.test_exempt=true` with a stated "
        "reason in their content (e.g. prompt templates, SQL migrations with "
        "no independently testable behavior) are not subject to this gate — "
        "see sdd-workflow-lifecycle REQ-005 (MODIFIED). Do not write "
        "trivially-passing tests solely to satisfy this rule."
    ),
    "enabled": True,
    "metadata": {
        "origin_change": "embed-tdd-in-sdd-workflow",
        "capability": "tdd-red-green-refactor",
        "applies_to_capability": "sdd-workflow-lifecycle",
        "modified_requirement": "REQ-005",
    },
}

_SKILLS = [
    SkillCreate(
        name="sdd:propose",
        description=(
            "Start here when beginning something new. Captures intent, motivation, scope and approach "
            "before any code or spec is written. Creates a named change with Why/What/Capabilities/Impact. "
            "Use when: starting a feature, planning a change, something new needs to be built."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:propose <change-name>", artifact_type="proposal")],
    ),
    SkillCreate(
        name="sdd:spec",
        description=(
            "Formalizes a proposal into structured requirements using SHALL/MUST language with WHEN/THEN scenarios. "
            "New capabilities get full specs. Modified capabilities get delta specs (ADDED/MODIFIED/REMOVED/RENAMED). "
            "Use when: a proposal exists and needs formal requirements."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:spec <change-name>", artifact_type="spec")],
    ),
    SkillCreate(
        name="sdd:design",
        description=(
            "Documents technical decisions with alternatives considered, architecture, risks, trade-offs and migration plan. "
            "Must read proposal and all specs as context. "
            "Use when: specs exist and a technical plan is needed before implementation."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:design <change-name>", artifact_type="design")],
    ),
    SkillCreate(
        name="sdd:tasks",
        description=(
            "Decomposes specs and design into atomic task artifacts, each completable in under 4 hours. "
            "Each task references REQ-NNN acceptance criteria from the specs. "
            "Use when: specs and design are ready and implementation needs to be planned."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:tasks <change-name>", artifact_type="task")],
    ),
    SkillCreate(
        name="sdd:apply",
        description=(
            "Implements pending tasks one by one, reading all planning artifacts as context. "
            "Validates each task against spec acceptance criteria before marking done. "
            "Use when: tasks exist and implementation should begin or continue."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:apply <change-name>")],
    ),
    SkillCreate(
        name="sdd:verify",
        description=(
            "Read-only validation: checks completeness (tasks done, REQ-NNN implemented), "
            "correctness (scenarios covered), and coherence (design decisions followed). "
            "Produces CRITICAL/WARNING/SUGGESTION report. "
            "Use when: all tasks are done and implementation needs validation before archiving."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:verify <change-name>")],
    ),
    SkillCreate(
        name="sdd:sync",
        description=(
            "Merges delta specs (ADDED/MODIFIED/REMOVED/RENAMED) into main specs in the database. "
            "Applies partial updates intelligently — does not wholesale replace existing content. "
            "Use when: a change has delta specs that need to be reflected in the main spec."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:sync <change-name>")],
    ),
    SkillCreate(
        name="sdd:archive",
        description=(
            "Finalizes a completed change: validates completion, syncs delta specs, archives all artifacts. "
            "Use when: all tasks are implemented and verified, ready to close out the change."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:archive <change-name>")],
    ),
    SkillCreate(
        name="sdd:explore",
        description=(
            "Thinking and investigation mode — explores ideas without writing any code. "
            "Reads existing specs and codebase, surfaces options and trade-offs. "
            "Use when: investigating feasibility, comparing approaches, thinking before proposing."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:explore <topic>")],
    ),
    SkillCreate(
        name="sdd:continue",
        description=(
            "Creates the next single artifact in the dependency chain (proposal → spec → design → tasks) and stops. "
            "Use when: stepping through the flow one artifact at a time instead of all at once."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:continue <change-name>")],
    ),
    SkillCreate(
        name="sdd:status",
        description=(
            "Shows current state of all in-progress changes: artifact completion, task progress, recent activity. "
            "Use when: starting a session to understand what needs to be done next."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:status")],
    ),
    SkillCreate(
        name="sdd:flow",
        description=(
            "Runs the complete SDD flow end-to-end in one session: propose → spec → design → tasks → apply → archive. "
            "All artifacts saved to database, no local files. "
            "Use when: implementing a feature from scratch in a single session."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:flow <feature description>")],
    ),
    SkillCreate(
        name="sdd:search",
        description=(
            "Semantic search over the SDD knowledge base using pgvector similarity. "
            "Searches specs, designs, proposals, tasks. Also recalls past agent actions. "
            "Use BEFORE starting any new work to find existing specs and prior decisions."
        ),
        workflow_steps=[SkillStep(step=1, instruction="Run /opsr:search <query>")],
    ),
]


async def seed_sdd_skills() -> None:
    for skill_data in _SKILLS:
        embedding = embed(f"{skill_data.name} {skill_data.description}")
        await skill_repository.create_skill(skill_data, embedding)
        print(f"  ✓ Seeded skill: {skill_data.name}")


async def seed_global_harness_rules() -> None:
    """Seed the global harness rules into every existing project.

    Rules are persisted per-project (`project_rules.project_id` is `NOT NULL`),
    so a single rule must be upserted once per project. The seed is idempotent:
    `rule_repository.upsert` resolves `(project_id, name)` collisions with
    `ON CONFLICT DO UPDATE`, so re-running `opensddrag-server init` does not
    create duplicates or change behavior for projects that already have the
    rule installed.

    On a clean database with no projects yet, this function is a no-op for
    the rule itself — the rule will be seeded automatically the next time
    `init` runs after projects are created, or when individual projects are
    re-seeded by a follow-up workflow.
    """
    projects = await project_repository.list_projects()
    if not projects:
        print("  • No projects registered; skipping global harness rule seed.")
        return
    for project in projects:
        data = RuleCreate(project_id=project.id, **_TDD_FIRST_RULE_TEMPLATE)
        await rule_repository.upsert(data)
        print(f"  ✓ Seeded harness rule 'tdd-first' for project '{project.slug}'")
