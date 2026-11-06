# SPEC-001 — Reproducible testing, security gates and AI-cost baseline

**Status:** Draft — inventory completed from repository files; execution evidence pending.
**Parent:** https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/2
**Tracking:** https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/3
**Baseline branch:** `test/all-features`; work only on `feature/ha-2026-11-spec-driven`.

## Goal

Establish reliable, repeatable checks for the existing Home Assistant integration and its companion card, without altering production Home Assistant or changing public entity IDs, tracking data, or storage schemas.

## Confirmed existing capabilities

- `AGENTS.md` documents a disposable Docker Home Assistant instance, existing tests and operational constraints.
- `pyproject.toml` configures Ruff; existing agent guidance also calls for mypy and pytest.
- `.github/workflows/ci.yml` runs Python 3.14 via tox, uploads coverage, uses pinned GitHub Actions and step-security/harden-runner in audit mode.
- Existing CodeQL is referenced in project documentation; actual workflow and enforcement still need verification.

**Do not install duplicate linters, recreate the test environment, or replace working CI without measuring a concrete gap.**

## Acceptance criteria

1. Inventory all existing workflows, tox/pytest coverage, dev-container configuration and security scanners. Record versions, limitations and exact commands.
2. Establish a repeatable baseline: lint, types, unit tests, Home Assistant startup/config-entry reload and multi-entry behavior. Mark each check PASS, FAIL, BLOCKED or NOT_RUN; never infer success from configuration alone.
3. Exercise only isolated Home Assistant and synthetic mailbox/17TRACK fixtures; no production secrets or endpoints.
4. Add missing high-value security gates selectively: secret detection, dependency vulnerability checks and applicable static analysis. Avoid overlapping tools unless findings justify them.
5. Check compatibility with Home Assistant 2026.11 and Python 3.14 without silently altering stable unique IDs or user data.
6. Define companion-card browser tests only after checking its existing test tooling.
7. Produce `verification.md` with actual commands, CI links, failure evidence, coverage gaps and rollback notes.
8. Measure AI work where usage metadata is available: model, token usage, number of repair loops, wall time and resolved findings. Keep CI CPU/minutes separate from AI tokens. Do not invent token counts.
9. Require review before merging architecture, persistence or migration changes.

## Proposed order of work

- [ ] T001 Read-only inventory of workflows, tox, tests, Docker and companion-card tests.
- [ ] T002 Run existing checks unchanged and capture baseline.
- [ ] T003 Add only missing deterministic checks with regression tests.
- [ ] T004 Validate isolated Home Assistant startup, reload and multi-entry scenarios.
- [ ] T005 Add targeted security checks and verify actionable findings.
- [ ] T006 Document outcomes and incremental AI/CI cost; open a focused draft PR.

## Scope boundaries

This phase must not touch production HA, change credentials, publish releases, modify tracking persistence, merge PRs or create eight new implementation branches. Existing Amazon fix PR stays separate. No automatic unbounded agent repair loop; stop after two attempts and report the blocker.

## Decision rule

Prefer a check when its expected defect-detection or regression-prevention benefit exceeds its maintenance, CI and AI-triage cost. Reuse existing infrastructure first. Require evidence before making any quality gate mandatory.
