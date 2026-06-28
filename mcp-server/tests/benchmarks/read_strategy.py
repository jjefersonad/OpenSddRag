"""Deterministic read-cost benchmark for the SDD workflow read strategies.

This is the *measurement gate* for the `reduce-token-consumption` change. It
quantifies the relative cost of each phase's read strategy by summing the number
of artifact **content characters** a phase pulls from the read tools
(`read_artifact`, and later `read_change_bundle`).

Why characters, and why a model instead of live tool calls:
- Character count is a deterministic proxy for tokens. It is only meaningful for
  before/after comparison within this benchmark — never as an absolute token
  figure (design decision: open question resolved in favour of raw chars over a
  chars/4 estimate).
- Driving the real tools would require Postgres plus the sentence-transformers
  embedding model (a network download) and would be non-deterministic. The task
  mandates a fixed fixture with no network, so the change's artifact sizes and
  per-phase read sets are modelled explicitly here.

Each tier of the rollout adds a `variant` and must show a net reduction over the
previous baseline. Tier 1 (this task) trims the `apply` phase only; `verify` and
`archive` are unchanged and therefore identical across the two variants.
"""

from __future__ import annotations

from dataclasses import dataclass

# Variants in rollout order: baseline → tier1 (apply read-trimming) → tier2
# (working-context cache) → tier3 (read_change_bundle for verify/archive).
VARIANTS: tuple[str, ...] = ("baseline", "tier1", "tier2", "tier3")
PHASES: tuple[str, ...] = ("apply", "verify", "archive")


@dataclass(frozen=True)
class Artifact:
    name: str
    kind: str  # "proposal" | "design" | "spec" | "task"
    content: str

    @property
    def chars(self) -> int:
        return len(self.content)

    @property
    def summary_chars(self) -> int:
        """Cost of a name+status summary (as a bundle returns for tasks)."""
        return len(self.name) + len("archived")


@dataclass(frozen=True)
class Change:
    proposal: Artifact
    design: Artifact
    specs: tuple[Artifact, ...]
    tasks: tuple[Artifact, ...]


def make_fixture_change(n_specs: int = 2, n_tasks: int = 6) -> Change:
    """A representative change with fixed, deterministic artifact sizes.

    Sizes are illustrative of a typical change (a longer design than proposal,
    mid-size specs, small tasks). Content is filler of an exact length so the
    benchmark is byte-stable across runs and machines.
    """
    proposal = Artifact("c-proposal", "proposal", "P" * 2000)
    design = Artifact("c-design", "design", "D" * 3000)
    specs = tuple(Artifact(f"c-spec-{i}", "spec", "S" * 1500) for i in range(n_specs))
    tasks = tuple(Artifact(f"c-task-{i}", "task", "T" * 600) for i in range(n_tasks))
    return Change(proposal, design, specs, tasks)


def _apply_reads(change: Change, variant: str) -> list[Artifact]:
    """`/opsr:apply` runs once per task — each invocation is its own session.

    baseline: re-reads proposal + design + ALL specs on every task.
    tier1:    reads design + only the one implementing spec; no proposal.
    tier2:    reads design + spec once (first task), then uses cache; task is read every time.
    tier3:    apply is deliberately untouched by tier3 — identical to tier2.
    """
    reads: list[Artifact] = []
    if variant == "baseline":
        for task in change.tasks:
            reads += [change.proposal, change.design, *change.specs, task]
    elif variant == "tier1":
        for task in change.tasks:
            impl_spec = change.specs[0]  # each task implements one spec
            reads += [change.design, impl_spec, task]
    elif variant in ("tier2", "tier3"):
        # First task reads design + impl_spec + task
        # Subsequent tasks read only task (design and impl_spec are cache hits).
        # tier3 leaves apply unchanged, so it shares tier2's behavior.
        impl_spec = change.specs[0]
        reads += [change.design, impl_spec]
        for task in change.tasks:
            reads += [task]
    return reads


def _holistic_chars(change: Change, variant: str) -> int:
    """`/opsr:verify` and `/opsr:archive` — a single holistic pass.

    baseline/tier1/tier2: N point reads — full proposal + design + every spec +
    every full task body.
    tier3: one `read_change_bundle` call — full proposal + design + specs, but
    tasks are summarized to name+status (not full content), so the task cost
    collapses to a few bytes each.
    """
    full = [change.proposal, change.design, *change.specs]
    if variant == "tier3":
        return sum(a.chars for a in full) + sum(t.summary_chars for t in change.tasks)
    return sum(a.chars for a in full) + sum(t.chars for t in change.tasks)


def phase_chars(change: Change, phase: str, variant: str) -> int:
    """Total content characters read during `phase` under `variant`."""
    if phase == "apply":
        return sum(a.chars for a in _apply_reads(change, variant))
    return _holistic_chars(change, variant)


def report(
    change: Change, variants: tuple[str, ...] = VARIANTS
) -> dict[str, dict[str, int]]:
    """{phase: {variant: chars}} plus a synthetic 'total' row."""
    rep = {
        phase: {v: phase_chars(change, phase, v) for v in variants} for phase in PHASES
    }
    rep["total"] = {v: sum(rep[phase][v] for phase in PHASES) for v in variants}
    return rep


def format_table(rep: dict[str, dict[str, int]], variants: tuple[str, ...]) -> str:
    """Render the report as a fixed-width before/after table with deltas."""
    header = f"{'phase':<10}" + "".join(f"{v:>12}" for v in variants) + f"{'Δ%':>8}"
    lines = [header, "-" * len(header)]
    for phase, cols in rep.items():
        base = cols[variants[0]]
        last = cols[variants[-1]]
        delta = 0.0 if base == 0 else (last - base) / base * 100
        row = f"{phase:<10}" + "".join(f"{cols[v]:>12,}" for v in variants)
        lines.append(row + f"{delta:>7.1f}%")
    return "\n".join(lines)


if (
    __name__ == "__main__"
):  # standalone gate: `python -m tests.benchmarks.read_strategy`
    change = make_fixture_change()
    rep = report(change)
    print("Read-cost benchmark — content chars per phase (token proxy)\n")
    print(format_table(rep, VARIANTS))
