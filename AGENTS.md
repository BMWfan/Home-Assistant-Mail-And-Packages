# Projektkontext und Regeln für GitHub Copilot

# Infrastructure & Environment

This section describes the *dev environment*, not the code -- read this
before touching anything, especially in a fresh session with no memory of
prior work here.

## What this is

Two things exist for this project, do not confuse them:

- **Production**: a real Home Assistant instance at
  `homeassistant.mack-cloud.de` (behind Cloudflare, mTLS client
  certificate required -- browser needs that cert or an
  AutoSelectCertificateForUrls policy entry for the domain, or it just
  hangs on "Unable to connect"). Real mailbox, real home automation
  alongside it. Installed via HACS from tagged GitHub releases
  (`vX.Y.Z-testNN`), not from source.
- **Dev**: a disposable plain-Docker HA instance (no HAOS/Supervisor,
  `ghcr.io/home-assistant/home-assistant:stable` via `docker compose`,
  container `mail_and_packages_dev`) with this repo's
  `custom_components/mail_and_packages/` bind-mounted live -- code
  changes take effect on container restart, no HACS/release/tag cycle
  needed. See `docker-compose.yml` + `HANDOFF.md` for the full setup,
  including the optional companion-card mount.

**Never assume a finding on one applies to the other** -- different entity
IDs, different `.storage/`, different auth path (dev commonly uses simple
IMAP password auth; prod's config entry uses Office365 OAuth, which can
expire and needs a Repairs-UI reauth -- that already happened once this
project's life, see `HANDOFF_HISTORY.md`).

## Starting the dev container

```bash
cp .env.example .env    # fill in HA_OWNER_USERNAME/PASSWORD to skip onboarding
docker compose up -d
docker compose ps        # confirm "healthy", not just "running"
```

`bootstrap-owner` creates the HA owner account non-interactively if
`HA_OWNER_*` are set; otherwise onboard manually in the browser once. If HA
flags "country not configured" afterward: `pip install websockets && python3
scripts/set-core-config.py`.

## Known pitfalls specific to this setup

- IMAP `SEARCH` does not descend into subfolders -- a mail rule filing
  carrier mail into e.g. `INBOX/Online-Shops/Amazon` makes it invisible to
  a scan configured for `INBOX` alone, and it looks exactly like broken
  carrier detection. This already caused one false "detection is broken"
  report; check the configured folder(s) before touching detection code.
- The dev container's `bootstrap-owner` only handles HA's own onboarding.
  The `mail_and_packages` config flow itself (IMAP credentials, 17track
  key) is separate and always manual.
- A `docker compose up` that changes any volume/mount on the
  `homeassistant` service forces a recreate, not just a restart -- brief
  downtime, harmless here, but don't be surprised by it.


Dieses Dokument definiert globale Regeln, die der Copilot Coding Agent und alle Custom Agents projektspezifisch beachten sollen.

## Build und Test

- Für dieses Projekt (Home Assistant Custom Integration, kein Build-Schritt):
  - Syntax-/Build-Check: `python -m py_compile <geänderte .py-Dateien>`
  - Tests: `uv run pytest` (bzw. `python -m pytest tests/ -q`; unter Windows nur via WSL/Linux lauffähig, da Home Assistant `fcntl` benötigt)
  - Linting: `ruff check .` und `ruff format --check .`
  - Type-Check: `mypy custom_components/mail_and_packages/`
- Jede signifikante Änderung muss:
  - ohne Build-Fehler abschließen.
  - alle existierenden Tests erfüllen.
  - keine neuen Lint-Errors einführen.

## Scope und Änderungen

- Architekturänderungen:
  - Keine Änderungen an der Gesamtstruktur (z.B. neue Module, Package-Umbenennungen, große Datei-Umzüge) ohne explizite Anweisung von CLAUDE.md (Planer).
  - Executor darf nur lokale Änderungen im jeweils übergebenen Scope machen.

- Shared/Basismodule:
  - Vermeide Änderungen an den Kernmodulen `custom_components/mail_and_packages/__init__.py`, `const.py`, `coordinator.py`, `utils/` und `shippers/base.py` ohne explizite Erlaubnis.
  - Bei Änderungen an Shared-Basismodulen:
    - Tests müssen alle durchlaufen.
    - Keine Breaking Changes in öffentlichen Schnittstellen ohne explizite Sign-off.

- Existing Code:
  - Keine Refactorings oder Aufräumaktivitäten im laufenden Code, die nicht im Handoff-Prompt explizit gefordert sind.
  - Änderungen nur in den im Prompt definierten Verzeichnissen und Dateien.

## Graphify

- Codebase-orientierte Fragen:
  - Nutze `graphify query "<question>"`, wenn `graphify-out/graph.json` existiert.
  - Für Beziehungen: `graphify path "<A>" "<B>"`.
  - Für fokussierte Themen: `graphify explain "<concept>"`.

- Nach Änderungen:
  - `graphify update .` um den Graph aktuell zu halten.

## Qualitätsstandards

- Jede Änderung muss:
  - semantisch sinnvolle Message im Commit haben (Conventional Commits, z.B. `fix(imap): ...`).
  - keine Debugging- oder provisorischen Werte einbringen.
  - nach der Änderung lokal konsistent sein (Build, Tests).

## Besondere Hinweise für Executor

- Der Executor darf:
  - neue Dateien im erlaubten Scope erstellen.
  - bestehende Dateien im erlaubten Scope ändern.
  - Tests im erlaubten Scope hinzufügen/ändern.
- Der Executor darf NICHT:
  - Architekturänderungen durchführen.
  - breaking changes in öffentlichen Schnittstellen einführen.
  - Änderungen außerhalb des gegebenen Scope machen.
  - ungefragte Refactorings oder Aufräumaktionen im gesamten Repo durchführen.

---

# Projektüberblick und Repository-Standards

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

### IMAP Integration & Compatibility Guidelines
- **IMAP RFC Compliance**: All IMAP query keys and arguments used in search commands (e.g. `search()`) must strictly conform to the IMAP RFC specifications (e.g., RFC 3501). Do not use FETCH-specific section/body specifiers (like `BODY[TEXT]`) inside `SEARCH` commands; instead, use standard search keys such as `BODY` or `TEXT` to prevent setup/login timeouts or parse errors on strictly compliant IMAP servers.
- **Test Fidelity**: Keep mock IMAP structures and test assertions aligned with standard RFC query formatting so invalid query structures are not masked by test mocks.

## 2. Python Environment & Dependency Management

- **Target Python Version**: **3.13 / 3.14**
- **Environment Tooling**: **`uv`** is the standard tool for environment creation and dependency management.
- To install test dependencies:
  ```bash
  uv pip install -r requirements_test.txt
  uv pip install --no-deps pytest-homeassistant-custom-component==0.13.375
  ```
  The pytest helper is installed separately without dependencies to preserve the
  pinned Home Assistant 2026.11.0 test environment.

## 3. Code Style, Linting & Type Checking

- **Linter & Formatter**: **Ruff** (ersetzt `black`, `flake8`, `isort`, `pydocstyle`, `pylint`); Konfiguration in `pyproject.toml`.
- **Type Checker**: **mypy**; Konfiguration in `setup.cfg`.
- Auto-Format + Fixes: `ruff check --fix . && ruff format .`

## 4. Git Hooks (`pre-commit`)

- Hook-Definitionen: `.pre-commit-config.yaml`.
- Manuell ausführen: `pre-commit run --all-files`

## 5. CI/CD & Security Hardening Guidelines

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

## 5.1 SDD-Light review policy (permanent)

Any substantial change to integration behavior, configuration schema,
persistence/storage, or release packaging must record, before merge, in the
relevant legacy `specs/NNN-*.md` + `specs/NNN-verification.md` pair or new
`specs/NNN-slug/` bundle (see section 6), or
the existing SPEC-001 artifacts / the PR description (small fixes):

- **(a) Latest stable Home Assistant release.** The exact HA version used
  for testing, any breaking API/quality-scale guidance that applies, with
  official source links (release blog/changelog, `developers.home-assistant`
  docs, `contributors.home-assistant.io` quality-scale docs) and the SHA/tag
  of the source actually consulted.
- **(b) Canonical upstream changes.** What changed in the canonical upstream
  project since the exact last-reviewed SHA, and an explicit adopt / adapt /
  defer / reject decision for each relevant change, with commit references.
- **(c) Fork-specific contracts.** Confirmation that fork-specific entity
  IDs, config-entry/options state, storage schema, companion-card contracts,
  and auth flows are covered by isolated tests (no production HA, no real
  secrets, no external network).

For **small, narrowly scoped fixes**, a lightweight proportional checklist in
the PR description is sufficient instead of a full SPEC pair: record the
exact HA version tested, the upstream/fork commit SHAs reviewed, official
links consulted, the adopt/adapt/defer/reject decision, which tests were run,
and known limitations.

For **larger or more substantive work**, follow the S/M/L artifact rules in
section 6. Preserve active legacy SPEC-001 through SPEC-008 files and references;
new specifications use `specs/NNN-slug/`. The changed-artifact check accepts both
formats. Do not self-approve acceptance criteria or implementation status —
human review and manual merge remain required.

Scheduled/automated monitoring of upstream HA releases or the canonical
upstream repository is a **proposal only**: it is not implemented, and
remains disabled pending explicit human approval. No auto-merge, autonomous
repair loop, or automated documentation edit based on such monitoring is
authorized by this policy.

## 6. Specification-Driven Development

Use lightweight, risk-proportionate specifications rather than a full document suite for every change. Follow the [NetClaw `specs/NNN-slug/` example](https://github.com/automateyournetwork/netclaw/blob/main/specs/072-hud-2-org-chart/spec.md), adapted as follows:

- **S — small fix:** issue, focused pull request, regression test, and human review. No standalone SPEC for a trivial fix, documentation edit, CI rerun, or review comment.
- **M — bounded feature:** one `spec.md` with the problem, scope and non-goals, requirements, acceptance criteria, dependencies, compatibility risks, documentation impact, rollback, and approval gate. Add a task checklist.
- **L — architecture, security, or data migration:** `spec.md`, `plan.md`, and `tasks.md`, plus explicit verification and migration/rollback evidence. Split implementation into small pull requests where useful. `verification.md` is required for L; research notes and interface contracts are optional when there is real uncertainty or a cross-project interface.

Create new feature specifications at `specs/NNN-short-slug/`, with the number assigned once. A SPEC describes one coherent, independently reviewable change and may be implemented by multiple focused PRs; each PR links the SPEC and relevant task IDs. Keep existing SPEC-001 through SPEC-008 issue links, artifact paths, verification evidence, and in-flight work intact. Do not renumber or move active artifacts to adopt the new layout; any migration requires a separately reviewed plan and reference updates. The changed-spec checker supports both formats: legacy pairs retain their section checks; new folders require `spec.md` and `tasks.md`. If either `plan.md` or `verification.md` is present, both are required. S/M/L classification and acceptance quality still require human review. Do not create a separate project constitution.

Use the gates **Specify → Clarify → Plan → Tasks → Analyze → Implement → Verify**. Get human approval of significant scope before implementation. During Analyze and Verify, explicitly review test, security, and documentation impact; update affected docs or record why none are affected. Preserve stable entity and unique IDs, stored tracking history, and existing user data. No production Home Assistant testing, live credentials, autonomous repair loops, or automatic merges.

### Compatibility and verification

- For every behavior or API change, identify the latest applicable **stable Home Assistant Core release** and its supported Python version; review its release notes, API changes, and deprecations before implementation and again during verification. Do not rely on dev-only APIs. Record the release/version reviewed and the compatibility result in the SPEC or PR.
- Check the current Actions runs for the PR and report the actual coverage. The current CI workflow has a Python **3.14-only** matrix and runs `tox` (`lint`, `mypy`, `py314`) with read-only Ruff checks and a dependency audit before pytest, then coverage upload; the Validation workflow runs HACS and Hassfest checks. Do not imply that Actions tests multiple Python or Core versions unless the workflow matrix does. Update the documented matrix when CI changes.
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

## 7. Pull Request & Contribution Guidelines

### A. Pre-submission Checklist
1. **Formatting & Linting**: `ruff check --fix . && ruff format .`
2. **Type Safety**: `mypy custom_components/mail_and_packages/`
3. **Unit Tests**: `uv run pytest`
4. **Pre-commit Hooks**: `pre-commit run --all-files`

### B. Pull Request Scope & Structure
* **Keep PRs Atomic**: Avoid combining unrelated refactoring, styling fixes, or multiple feature requests into a single PR. Keep changes focused and small where possible.
* **PR Templates**: Pull requests must use the repository's PR template, leaving nothing out unless the template explicitly states that it is optional or can be skipped.
* **Commit Messages**: Write descriptive commit messages. Ensure the PR title matches the Conventional Commits specification (e.g., `fix(imap): handle body search syntax error`).
