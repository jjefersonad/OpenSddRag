"""Measurement gate for `reduce-token-consumption` (tier1-2).

Asserts the read-strategy benchmark is deterministic and that Tier 1 reduces the
`apply`-phase read cost versus the pre-change baseline. The benchmark model
(`tests.benchmarks.read_strategy`) is pure Python — no DB, no network — so these
checks gate the rollout without touching the database.
"""

from tests.benchmarks.read_strategy import (
    PHASES,
    VARIANTS,
    format_table,
    make_fixture_change,
    phase_chars,
    report,
)


def test_report_is_deterministic():
    # Same fixture, two runs → byte-identical report (no randomness, no clock).
    assert report(make_fixture_change()) == report(make_fixture_change())


def test_tier1_and_tier2_reduce_apply_phase_chars(capsys):
    change = make_fixture_change()
    baseline = phase_chars(change, "apply", "baseline")
    tier1 = phase_chars(change, "apply", "tier1")
    tier2 = phase_chars(change, "apply", "tier2")

    # Tier 1 drops the per-task proposal read and reads one spec instead of all.
    assert tier1 < baseline
    # Tier 2 uses cross-task caching, yielding even lower reads than Tier 1.
    assert tier2 < tier1

    # Visibility: print the full per-phase table so the gate is auditable in -s.
    print("\n" + format_table(report(change), VARIANTS))


def test_holistic_phases_unchanged_in_tier1_and_tier2():
    # Tier 1 & 2 only trim apply; verify/archive must be identical across variants.
    change = make_fixture_change()
    for phase in ("verify", "archive"):
        assert (
            phase_chars(change, phase, "baseline")
            == phase_chars(change, phase, "tier1")
            == phase_chars(change, phase, "tier2")
        )


def test_tier3_reduces_holistic_phases_vs_baseline():
    # Tier 3 adopts read_change_bundle in verify/archive: full proposal+design+
    # specs, but tasks summarized to name+status — so each holistic phase reads
    # strictly fewer chars than the baseline point-read pass.
    change = make_fixture_change()
    for phase in ("verify", "archive"):
        assert phase_chars(change, phase, "tier3") < phase_chars(
            change, phase, "baseline"
        )
    # Apply is deliberately untouched by Tier 3 — identical to Tier 2.
    assert phase_chars(change, "apply", "tier3") == phase_chars(
        change, "apply", "tier2"
    )


def test_total_chars_reduced_overall():
    change = make_fixture_change()
    rep = report(change)
    assert rep["total"]["tier1"] < rep["total"]["baseline"]
    assert rep["total"]["tier2"] < rep["total"]["tier1"]
    # Tier 3 cuts the holistic phases, so the running total drops again.
    assert rep["total"]["tier3"] < rep["total"]["tier2"]


def test_every_phase_and_variant_is_covered():
    rep = report(make_fixture_change())
    for phase in PHASES:
        for variant in VARIANTS:
            assert rep[phase][variant] > 0
