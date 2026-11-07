# SPEC-001 — Reproducible testing, security gates and AI-cost baseline

**Status:** Draft — implementation evidence is being recorded; human review is required before merge.
**Parent:** https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/2
**Tracking:** https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/3
**Baseline branch:** `test/all-features`.

## Goal

Establish reliable, repeatable checks for the existing Home Assistant integration and its companion card, without altering production Home Assistant or changing public entity IDs, tracking data, or storage schemas.

## Requirements

- Run tests against Python 3.14 and Home Assistant 2026.11.0, with isolated tox environments and deterministic fixtures.
- Validate startup and independent reload of multiple config entries without production Home Assistant, real secrets, external IMAP, or external network access.
- Check the integration manifest and existing frontend-facing entity attributes with deterministic contract tests; run companion-card browser tests only if its source and tooling are available.
- Keep formatting checks read-only; pin compatible tox tooling, use dependency caching and a bounded CI timeout, and cancel superseded runs safely.
- Add a deterministic standard-library spec artifact check for changed specs only. Keep requirements, design, plan, and tasks in the existing `specs/NNN-*.md` specification, with verification in `specs/NNN-verification.md`; do not gate untouched legacy specs.
- Run no LLM/API calls in CI. Do not add an autonomous repair loop, privileged token, auto-approval, or auto-merge. Human review and manual merge remain required.
- Document local commands, compatibility, migration, and rollback implications.

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

## Design

The existing tox and GitHub Actions validation are retained. The Python CI job remains a single supported Home Assistant 2026.11/Python 3.14 target, with exact tox tooling, a bounded runtime, dependency caching, and concurrency cancellation. Formatting remains a read-only check. Test sockets are restricted to loopback, and integration tests use existing synthetic fixtures and mocked IMAP clients.

The spec checker uses Python's standard library and runs only for pull requests. It inspects changed files under `specs/` against the repository's existing two-file layout; requirements, design, plan, and tasks are headings in the spec document, while verification evidence is kept in its companion file. Existing unchanged specifications are grandfathered. No companion card implementation is present in this repository; existing producer-side attribute contract tests remain the available check.

## Plan

Follow the required gates in order: Specify → Clarify → Plan → Tasks → Analyze → Implement → Verify. The specification remains Draft until human review; no implementation status or acceptance criterion is self-approved. The CI/tooling changes are limited to the testing scope above. Self-healing remains opt-in and unimplemented because no bounded, approved repair mechanism is configured.

## Tasks

- [x] T001 Read-only inventory of workflows, tox, tests, devcontainer, and available card contract checks.
- [x] T002 Clarify the legacy tox/pip constraints and establish that the previously reported CI job's root cause is unknown (retrieved logs contained no tox output).
- [x] T003 Implement and test changed-spec artifact validation in the existing `specs/` layout.
- [x] T004 Verify the manifest, isolated startup, reload, and multi-entry scenarios against HA 2026.11/Python 3.14.
- [x] T005 Verify local lint, format, type, CodeQL, and secret checks on the final implementation.
- [x] T006 Record measured local duration and actual premium-request usage if available; report unavailable metrics without estimating.
- [ ] T007 (partial) CI #33 (tox), Validation/HACS/hassfest, and PR lint passed on older SHA `b48bdee`. On latest inspected head `f44cb2a`, CI, Validation, Pre-commit, Autolabeler, and PR lint are `action_required` with zero jobs; an authorized repository user must resolve the gate, whose exact reason is not exposed by the API. HACS/hassfest and successful full CI are not verified on this SHA. GitHub CodeQL is not configured for PRs targeting `test/all-features`; keep these gaps explicit.
- [x] T008 Add pinned `pip-audit==2.10.1` to the Python 3.14 tox environment and scan installed dependencies before pytest. Local post-merge tox/audit passed on tested head `e5911cd`; CI #33 also passed on older SHA `b48bdee`. The scanned inventory and helper `--no-deps` limitation are documented in the verification artifact. Human review remains T009.
- [ ] T009 Obtain human review and retain manual merge.

## Scope boundaries

This phase must not touch production HA, change credentials, publish releases, modify tracking persistence, merge PRs or create eight new implementation branches. Existing Amazon fix PR stays separate. No automatic repair loop is configured; therefore a two-attempt limit is not enforced by CI. Repairs remain opt-in and require human approval.

## Decision rule

Prefer a check when its expected defect-detection or regression-prevention benefit exceeds its maintenance, CI and AI-triage cost. Reuse existing infrastructure first. Require evidence before making any quality gate mandatory.
