"""Benchmark helpers for the SDD workflow (not collected by pytest).

Modules here are plain libraries — no `test_` prefix — so they carry no DB or
network dependency and can run standalone (`python -m tests.benchmarks.<name>`)
as a rollout gate, independent of the suite's database fixtures.
"""
