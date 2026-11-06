# SPEC-001 — Verification evidence and remaining gates

**Evidence date:** 2026-11-06. **Tested code SHA:** `e5911cdb7a171430187800840ab6e43748b8a785` (merge commit `26cb568` plus the test correction). Focused and full local tox pass on this tree. CI #33 and Validation/HACS/hassfest evidence below is from older SHA `b48bdee`; checks triggered on `e5911cd` are `action_required` with zero jobs. An authorized repository user must resolve the gate; the exact approval reason was not exposed by the Actions API. This verification-document update is documentation-only. Human review remains pending. No production services were accessed.

## SDD phase and review gates

| Phase | Artifact or evidence | Status / gate |
|---|---|---|
| Specify | `specs/001-test-environment.md` requirements and acceptance criteria | Draft; human review required |
| Clarify | PR #12 review comments and CI investigation | Requirements reconciled; old CI root cause remains unknown because retrieved logs contained no tox output |
| Plan | `specs/001-test-environment.md` design and plan sections | Draft; no architecture or acceptance criteria were self-approved |
| Tasks | `specs/001-test-environment.md` task checklist | CI #33 evidence is for `b48bdee`; checks triggered for tested SHA `e5911cd` are action-required with zero jobs; T007 remains partial and human review remains |
| Analyze | Workflow, tox, test, fixture, configuration, and documentation-impact inventory below | Complete for this scope |
| Implement | PR #12 changes and imported PR #11 baseline | Complete locally; no production changes |
| Verify | Commands, documentation-impact review, and results below | Focused and full local tox pass on `e5911cd`; current-SHA Actions are gated; human review is pending |

## Documentation impact review

| Documentation | Impact and decision |
|---|---|
| `README.md` | No documentation change needed: no user-visible integration behavior or configuration changed. README already links to `CONTRIBUTING.md`; another test-command link would duplicate contributor guidance. |
| `CONTRIBUTING.md` | Updated to explain that tox performs a strict pip-audit of installed test-environment distributions before pytest; local commands remain unchanged. |
| `AGENTS.md` | Updated the manual test setup to install the HA pytest helper with `--no-deps`, matching tox and preserving the HA 2026.11.0 pin. |
| `DEVCONTAINER.md` | No change needed: the merge and test assertion do not change the container or supported runtime. |
| Example configuration (`config/configuration.yaml`) | The base branch includes a `remote_homeassistant` development mirror using `!secret` references. The pytest fixture uses an isolated test `hass` and synthetic `MockConfigEntry` data; tests do not load this file. No real secrets were read and no HA instance was launched. |
| Changelog/release notes | No change needed: this is internal test/verification work, not an unreleased user-facing feature or release. No `CHANGELOG.md` exists in the repository. |
| `specs/001-*.md` | Updated verification evidence and this impact review are recorded in the existing Draft SPEC-001 artifacts; requirements and acceptance criteria were not changed. |

No additional README or user-facing documentation change is warranted. The merge synchronizes the feature branch with its declared base; the PR diff remains scoped to SPEC-001 and test/CI work. The test assertion and manual helper-install command are documented in the relevant contributor guidance; no acceptance criteria changed.

This verification update records the base-branch merge, corrected test contract, and current evidence. The test change does not alter runtime behavior or public configuration.

## Isolated environment and safety

- Python 3.14.9 and Home Assistant 2026.11.0 were used for the post-merge local tox verification.
- Tests run with `--disable-socket --allow-hosts=127.0.0.1,::1,localhost`; IMAP is mocked by test fixtures.
- The merged `config/configuration.yaml` contains a `remote_homeassistant` section with secret references for the developer mirror. Isolated tests do not load that file: the pytest `hass` fixture and `MockConfigEntry` factory use synthetic entry data; pytest sockets are restricted to loopback. No Home Assistant instance or production service was started, and no secret values were accessed.
- Tests cover two config entries and independently reloading one entry. The assertion checks the second entry's registered sensor identities and deep-copied active state/attributes before and after the first entry reload; inactive registry entries are not mistaken for active states.
- Existing producer-side entity attribute tests are available in `tests/test_sensor.py`. No companion-card source or browser test tooling is present in this repository, so consumer/browser tests were not run; this is a documented scope limitation, not a passed check.

## Test status matrix

| Check | Status | Evidence |
|---|---|---|
| Focused HA init lifecycle | PASS | `env -u GITHUB_ACTIONS PATH="/opt/hostedtoolcache/Python/3.14.9/x64/bin:/tmp/spec001-tox-tools/bin:$PATH" /tmp/spec001-tox-tools/bin/tox -e py314 -- tests/test_init.py --no-cov -q --tb=short`; 38 passed, 5 warnings on tested SHA `e5911cd`. |
| Focused multi-entry isolation | PASS | Included in the focused init run above; registry identities and deep-copied active state/attributes for the second entry were unchanged after reloading the first. |
| Full pytest suite and tox checks | PASS | Full tox on tested SHA `e5911cd`, Python 3.14.9; 662 passed, 22 warnings in 23.57s; configured integration Python coverage 90.41% (minimum 90%); total tox duration 33.94s. |
| Integration manifest contract | PASS | Included in full tox on `e5911cd`; manifest contract tests passed. |
| Ruff lint and format | PASS | Included in full tox: `ruff check --no-fix .` and `ruff format --check .`; all checks passed, 72 files already formatted. |
| mypy | PASS | Included in full tox: `mypy custom_components/mail_and_packages/`; no issues in 34 source files. |
| Spec artifact gate | PASS | Standard-library gate passed against PR base `71d2111e23de1ec0ca641a310d74cfb2c4c25237`; full tox also passed the focused checker tests. |
| Full local tox with required audit gate | PASS | `env -u GITHUB_ACTIONS PATH="/opt/hostedtoolcache/Python/3.14.9/x64/bin:/tmp/spec001-tox-tools/bin:$PATH" /tmp/spec001-tox-tools/bin/tox`; tox 4.32.0, Python 3.14.9; audit passed, 662 tests passed, coverage 90.41%, 22 warnings; 33.94s total on tested SHA `e5911cd`. |
| Resolved test-environment dependency audit | PASS | Tox ran `pip-audit --local --strict --timeout 15 --progress-spinner off` with pip-audit 2.10.1 against 160 installed distributions including Home Assistant 2026.11.0; default PyPI vulnerability service reported no known vulnerabilities. |
| GitHub CI #32 Python 3.14 | PASS | Run [42173410045](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42173410045), job [127746250142](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42173410045/job/127746250142), SHA `e6dde8b`; successful, 2m15s job duration; tox step succeeded |
| HACS and hassfest | PASS | Validation run [42168187892](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42168187892), job [127743521986](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42168187892/job/127743521986), SHA `e6dde8b`; both named steps succeeded |
| GitHub CI #33 Python 3.14 | PASS | Run [42192106154](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42192106154), job [127806375165](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42192106154/job/127806375165), SHA `b48bdee4220575a5fb6335c0c2bcb1a1c0eeb4b3`; Actions API event `workflow_dispatch`; job passed in 1m40s. Logs confirm tox lint (`ruff check --no-fix .`), read-only formatting (`ruff format --check .`), mypy, `pip-audit --local --strict --timeout 15 --progress-spinner off` (`No known vulnerabilities found`), and pytest (525 passed, 12 warnings in 15.21s). The run URL is API-verified; the user-provided screenshot's pull-request event label differs from the Actions API event. |
| GitHub CI on tested SHA | ACTION_REQUIRED | Run [42197918699](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42197918699), SHA `e5911cd`; run completed as `action_required`, with zero jobs created. An authorized repository user must resolve the gate; this is not a test failure or pass. |
| Validation/HACS/hassfest on tested SHA | ACTION_REQUIRED | PR run [42197918736](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42197918736) and push run [42197911033](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42197911033), SHA `e5911cd`; both are `action_required`, with zero jobs. HACS/hassfest are therefore not verified on this SHA. |
| Pre-commit on tested SHA | ACTION_REQUIRED | Run [42197918711](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42197918711), SHA `e5911cd`; zero jobs created. No local pre-commit result is claimed. |
| PR lint on tested SHA | ACTION_REQUIRED | Run [42197915189](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42197915189), SHA `e5911cd`; zero jobs created. |
| CI coverage job | PASS | Job [127807066922](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42192106154/job/127807066922) on SHA `b48bdee`; completed successfully. This does not independently establish a whole-repository coverage percentage. |
| Validation, HACS, and hassfest | PASS | Validation run [42177444672](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42177444672), job [127798340474](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42177444672/job/127798340474), SHA `b48bdee`; Validate, HACS validation, and Hassfest validation steps succeeded. |
| PR lint | PASS | Run [42177447538](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42177447538), job [127798346669](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42177447538/job/127798346669), SHA `b48bdee`; completed successfully. |
| Pre-commit on verified PR SHA | NOT_VERIFIED | The only surfaced pre-commit run is [42162228366](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42162228366) on older SHA `3f427c0`. No run for `b48bdee` was found. This is absent, not an `action_required` result. |
| GitHub CodeQL on verified PR SHA | NOT_RUN | No run for `b48bdee` was found. `.github/workflows/codeql-analysis.yml` limits pull-request target branches to `master`, `0.2.0`, and `0.3.0`, excluding PR #12's `test/all-features` base. The last surfaced run [42162228330](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42162228330) is on older SHA `3f427c0`. No approval-gated CodeQL result is present for the tested SHA. |
| Local CodeQL on tested code | PASS | CodeQL checker found zero alerts after commit `e5911cd`; GitHub CodeQL is not configured for the `test/all-features` PR target. |
| Local secret scan | PASS | No secrets were detected in the files passed to the scanner, including the final test and documentation changes. |
| Automated dependency vulnerability scanning | PASS | `tox` runs strict pip-audit before pytest; `pip-audit==2.10.1` is pinned. Local tox audit passed on `e5911cd`; CI #33 also passed on `b48bdee`. |
| Home Assistant live startup | NOT_RUN | Not required; no HA instance was launched |
| Companion-card browser/consumer tests | NOT_RUN | Companion card source and browser tooling are not present in this repository |
| Premium-request usage | NOT_AVAILABLE | No usage metadata was exposed; no estimate recorded |

The post-merge full tox run on `e5911cd` measured 90.41% coverage for the configured integration Python files (`custom_components/mail_and_packages/`), exceeding the configured 90% threshold; this is not whole-repository coverage or proof of every behavior. It completed with 22 warnings and no failures. Earlier code at SHA `500a926` had a separate 100% result; that number does not describe the merged base. No live HA instance was started.

The security audit used the locally installed distributions after resolving `requirements_test.txt` with Python 3.14.9 and adding the same `pytest-homeassistant-custom-component==0.13.375` package with `--no-deps`, as configured by tox. The resulting environment had 160 installed distributions (including pinned HA 2026.11.0, audit tool 2.10.1, and its own dependencies); pip-audit's local installed-package scan against its default PyPI vulnerability service reported no known vulnerabilities. The repository does not lock the complete transitive dependency graph, so versions other than explicitly pinned requirements can vary across fresh resolutions; this result applies to this resolved inventory, not all future installs.

`pip check` exits nonzero after tox's intentional `--no-deps` install of `pytest-homeassistant-custom-component==0.13.375`. That helper declares exact requirements for HA 2026.10.4, coverage 7.16.2, numpy 2.3.2, pytest 9.0.3 and pytest-asyncio 1.4.0, conflicting with this environment's pinned HA 2026.11.0 and newer resolved test packages; it also declares helper packages (including `aiohasupervisor`, `mock-open`, `pipdeptree`, `pydantic`, `PyGithub`, `pytest-freezer`, `pytest-picked`, `pytest-unordered`, `tqdm`, and `unidiff`) which are not installed. Tox uses `--no-deps` to avoid downgrading the supported HA target; the suite and audit pass with that established setup. The audit scans distributions actually installed and cannot report on packages omitted by this no-deps install. This is a known test-helper resolution limitation, not an audit suppression. No dependency auto-fixes were used.

A preliminary, discarded setup experiment installed the HA test helper with its dependencies instead of tox's `--no-deps`; it downgraded HA to 2026.10.4 and Pillow to 12.3.0, producing 39 Pillow advisory records (fix version reported as 13.0.0). A repeat audit of that disposable, non-target environment exited 1, confirming that findings fail the gate; it is not counted as the target baseline. The advisory output described issues including memory-safety, resource-exhaustion and potential code-execution classes, but did not return severity ratings; the supplemental advisory lookup also supplied no severity scores. The correctly resolved target environment uses Pillow 13.0.0 and reports no known vulnerabilities. If a valid HA 2026.11 scan later resolves Pillow below 13.0.0, a narrow `Pillow>=13.0.0` lower-bound review in the test requirements is preferable to broad upgrades; no dependency upgrade was made based on the invalid setup.

The previously reported CI job `127711456311` (run `42162228288`, attempt 2) failed after the `Run tox` step ran for 37m38s. Job-log retrieval returned step-security runner teardown output but no tox output, so the cause is still unconfirmed. The local pass does not establish a cause for that remote run.

## Tooling and cost notes

- tox 4.32.0 and tox-gh-actions 3.5.0 were used and pinned in CI; both support the Python 3.14 configuration. The tox-gh-actions 3.5.0 compatibility table supports tox 4.x.
- Removed the obsolete `pip>=21,<22.1` cap, which did not match the Python 3.14 target. Tox now uses its Python-compatible environment pip.
- Home Assistant, Ruff, the HA pytest helper, pip-audit, and selected test tooling are pinned or constrained. The full transitive dependency closure is not locked; the audit records the actually resolved installed inventory on each run.
- Dependabot remains configured for pip version updates, not vulnerability auditing. The pip-audit tox gate scans all installed distributions in the Python 3.14 test environment with strict dependency collection and a 15-second per-request timeout. It fails the Python test environment when known advisories or dependency-collection errors are found; the CI job has a 20-minute overall timeout. No blanket ignore list or automatic remediation is configured.
- CI runs lint and type checking before pytest, caches uv dependencies, cancels superseded runs for the same ref, and bounds the test job at 20 minutes.
- No extra path-filtered test suite was added: the repository has one relevant integration suite, and skipping it for broad source changes would weaken coverage. No LLM calls, agent-trigger loop, privileged token, auto-approval, or auto-merge were added. No two-repair-attempt cap is enforced because self-healing is not configured.
- CI #33's Python 3.14 job took 1m40s on `b48bdee`; its tox log confirms 525 passing tests, a clean pip-audit result, and successful lint, format, and mypy stages. Earlier CI #32 took 2m15s on `e6dde8b`; the previously failed tox step ran 37m38s on a different SHA, with no tox output in retrieved logs, so its cause remains unknown. No premium-request usage was available.

## Compatibility, rollback, and remaining scope

- These changes affect test tooling and tests only; they do not alter integration runtime dependencies, config-entry schemas, entity IDs, or stored data. No user-data migration is required.
- The new audit package is test-only and does not change `manifest.json` or runtime dependencies. Rollback is a source-control revert of the requirements, tox, contribution-guidance, and SPEC changes; no production HA instance or data restoration is involved.
- The companion-card requirement is limited to producer-side entity contract checks because the consumer project/tooling is absent. Browser/consumer validation remains not run.
- No self-healing automation is implemented; the two-attempt cap is consequently not enforced. Human review and manual merge remain required.

## Next actions

- Ask an authorized repository user to resolve the `action_required` runs for CI, Validation/HACS/hassfest, Pre-commit, and PR lint on `e5911cd`; the API reports zero jobs and does not expose a more specific approval reason. CodeQL is not configured for PRs targeting `test/all-features`; changing its trigger scope requires maintainer review.
- CI #33 already verifies the pip-audit gate and tox on `b48bdee`; retain its no-suppressions policy and revisit the helper's intentional no-deps compatibility gap separately if desired.
- The retrieved CI #33 logs explicitly show the audit and pytest results. Do not infer a cause for the earlier 404 job.
- Obtain human review of the Draft specification and implementation. GitHub currently reports PR #12 as open but not Draft; no PR state change was made. Merge remains manual.
