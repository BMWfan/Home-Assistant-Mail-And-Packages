# Guidelines for AI Coding Assistants (AGENTS.md)

Welcome! This file provides a repository overview, architecture guidelines, developer environment setup, and styling/workflow standards for AI assistants contributing to this repository.

---

## 1. Project Overview & Architecture

This repository is a **Home Assistant Custom Integration** that connects to an IMAP email server, parses email notifications from various shipping carriers (USPS, FedEx, UPS, DHL, Amazon, Evri/Hermes, etc.), and exposes sensors and cameras to track mail and package deliveries in real-time.

### Core Directory Structure
- `custom_components/mail_and_packages/`: Contains the integration code.
  - `__init__.py`: Component setup, setup entries, unloading, and coordinator.
  - `const.py`: Shared constants, domains, config keys, and sensor descriptions.
  - `config_flow.py`: Setup flows and options flow handlers.
  - `sensor.py`: Home Assistant sensor entities representing delivery counts/status.
  - `camera.py`: Home Assistant camera entities that show mail scans or shipper status images.
  - `shippers/`: Specific parsers matching individual carrier email formats.
  - `utils/`: IMAP connection and query utilities.
  - `manifest.json`: Home Assistant custom component metadata.
- `tests/`: Pytest suite.
  - `conftest.py`: Shared testing fixtures and mock IMAP client overrides.
  - `test_init.py`, `test_config_flow.py`, etc.: Integration and unit tests.

---

## 2. Python Environment & Dependency Management

- **Target Python Version**: **3.13 / 3.14**
- **Environment Tooling**: **`uv`** is the standard tool for environment creation and dependency management.

### Setup and Testing
- Virtual environments are handled using `uv`.
- To install test dependencies:
  ```bash
  uv pip install -r requirements_test.txt
  ```

---

## 3. Code Style, Linting & Type Checking

This codebase uses modern, fast Rust-based tooling for formatting and static analysis:
- **Linter & Formatter**: **Ruff** replaces `black`, `flake8`, `isort`, `pydocstyle`, and `pylint`.
- **Type Checker**: **mypy**.

### Configuration Locations
- Ruff configuration: Configured in `pyproject.toml`.
- Mypy configuration: Configured in `setup.cfg`.

### Local Execution Commands
- To run lint checks:
  ```bash
  ruff check .
  ```
- To run formatting checks:
  ```bash
  ruff format --check .
  ```
- To auto-format and fix autofixable lint errors:
  ```bash
  ruff check --fix . && ruff format .
  ```
- To run type checks:
  ```bash
  mypy custom_components/mail_and_packages/
  ```

---

## 4. Git Hooks (`pre-commit`)

This project uses **`pre-commit`** to run git hooks automatically on commit.
- Hook definitions: [`.pre-commit-config.yaml`](file:///.pre-commit-config.yaml).
- Run all checks manually:
  ```bash
  pre-commit run --all-files
  ```

---

## 5. Test Suite

Unit and integration tests are written with `pytest` and can be orchestrated using `tox` or run directly with `uv`.
- Running tests locally:
  ```bash
  uv run pytest
  ```
- Running tests in isolated environments via tox:
  ```bash
  tox
  ```

---

## 6. Specification-Driven Development

Use lightweight, risk-proportionate specifications rather than a full document suite for every change. Follow the [NetClaw `specs/NNN-slug/` example](https://github.com/automateyournetwork/netclaw/blob/main/specs/072-hud-2-org-chart/spec.md), adapted as follows:

- **S — small fix:** issue, focused pull request, regression test, and human review. No standalone SPEC for a trivial fix, documentation edit, CI rerun, or review comment.
- **M — bounded feature:** one `spec.md` with the problem, scope and non-goals, requirements, acceptance criteria, dependencies, compatibility risks, documentation impact, rollback, and approval gate. Add a task checklist.
- **L — architecture, security, or data migration:** `spec.md`, `plan.md`, and `tasks.md`, plus explicit verification and migration/rollback evidence. Split implementation into small pull requests where useful. `verification.md` is required for L; research notes and interface contracts are optional when there is real uncertainty or a cross-project interface.

Create new feature specifications at `specs/NNN-short-slug/`, with the number assigned once. A SPEC describes one coherent, independently reviewable change and may be implemented by multiple focused PRs; each PR links the SPEC and relevant task IDs. Keep existing SPEC-001 through SPEC-008 issue links, artifact paths, verification evidence, and in-flight work intact. Do not renumber or move active artifacts to adopt the new layout; any migration requires a separately reviewed plan and reference updates. Do not create a separate project constitution.

Use the gates **Specify → Clarify → Plan → Tasks → Analyze → Implement → Verify**. Get human approval of significant scope before implementation. During Analyze and Verify, explicitly review test, security, and documentation impact; update affected docs or record why none are affected. Preserve stable entity and unique IDs, stored tracking history, and existing user data. No production Home Assistant testing, live credentials, autonomous repair loops, or automatic merges.

### Compatibility and verification

- For every behavior or API change, identify the latest applicable **stable Home Assistant Core release** and its supported Python version; review its release notes, API changes, and deprecations before implementation and again during verification. Do not rely on dev-only APIs. Record the release/version reviewed and the compatibility result in the SPEC or PR.
- Check the current Actions runs for the PR and report the actual coverage. The current CI workflow has a Python **3.14-only** matrix and runs `tox` (`py314`, lint, format, mypy), then coverage upload; the Validation workflow runs HACS and Hassfest checks. Do not imply that Actions tests multiple Python or Core versions unless the workflow matrix does. Update the documented matrix when CI changes.
- Keep HA tests isolated and deterministic; use fixtures, never production instances or live accounts. Verify focused tests and relevant Actions jobs, and distinguish automated evidence from manual or not-run checks.
- For every SPEC and substantive integration PR, review the [companion card repository](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages-Custom-Card) contract and link relevant card issues/PRs. Check entity registry auto-discovery, entity IDs/platforms, sensor attributes, universal and 17TRACK shipment structures, OTP/Hub pickup-code mapping, delivery photos, DHL letter previews and image URLs, scan button/service, and status/last-updated data. Preserve backwards compatibility or coordinate an explicitly versioned change across both repositories. Use the disposable HA development environment with both repositories when feasible; add fixture/contract and browser/E2E checks proportionate to risk. State which checks actually ran.

### Roadmap links and workflow

The roadmap is [issue #2](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/2). Existing feature issues remain the references for their respective SPECs:

- [SPEC-001 — Test environment and CI (#3)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/3) — implementation remains in [PR #12](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/pull/12).
- [SPEC-002 — Coordinator and lifecycle (#4)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/4)
- [SPEC-003 — Tracking persistence and migration (#5)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/5)
- [SPEC-004 — Tracking and 17TRACK (#6)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/6)
- [SPEC-005 — Entities and device registry (#7)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/7)
- [SPEC-006 — Config flow and repairs (#8)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/8)
- [SPEC-007 — Custom Card and automation events (#9)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/9)
- [SPEC-008 — Release quality and distribution (#10)](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/issues/10)

Use the GitHub Copilot Coding Agent for assigned work in this repository. Open a draft PR against the roadmap's `test/all-features` branch, keep unrelated work and PR #12 separate, wait for Actions and an independent review, and merge only after owner approval. Do not start a separate Codex session, change production, or make releases without owner approval. The card-side counterpart to SPEC-007 is [companion issue #17](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages-Custom-Card/issues/17).

---

## 7. CI/CD & Security Hardening Guidelines

When modifying or introducing new GitHub Actions workflows, adhere to the following rules:

### A. Pin Actions to Commit SHAs
Do **NOT** use version tags (e.g., `@v4`, `@master`, `@main`) for Actions. Pin them to full-length 40-character commit SHAs. Use comment tags to document human-readable versions:
```yaml
uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v4.4.4
```

### B. Use Step-Security Harden-Runner
Add `step-security/harden-runner` as the **first step** in every job running on hosted runners to monitor outbound traffic:
```yaml
- name: Harden Runner
  uses: step-security/harden-runner@5c7944e73c4c2a096b17a9cb74d65b6c2bbafbde # v2.9.1
  with:
    egress-policy: audit
```

### C. Restrict GITHUB_TOKEN Permissions
Specify minimal default permissions at the top level of each workflow:
```yaml
permissions:
  contents: read
```

### D. Conventional Commit PR Titles
All pull request titles must follow the Conventional Commits specification (e.g., `feat: ...`, `fix: ...`, `ci: ...`).
- Workflow checks: Managed via the `Semantic PR Check` action in `.github/workflows/semantic-pr.yaml`.
- Auto-labeling: Handled automatically by the built-in autolabeler in `.github/release-drafter.yml`.
