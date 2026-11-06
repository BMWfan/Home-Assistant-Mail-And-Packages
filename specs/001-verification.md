# SPEC-001 — Verification evidence and remaining gates

**Evidence date:** 2026-11-06. **Status:** Local pip-audit gate and full tox pass on code SHA `500a926`; current-SHA GitHub validation is `action_required` with zero jobs. Human review remains pending. No production services were accessed.

## SDD phase and review gates

| Phase | Artifact or evidence | Status / gate |
|---|---|---|
| Specify | `specs/001-test-environment.md` requirements and acceptance criteria | Draft; human review required |
| Clarify | PR #12 review comments and CI investigation | Requirements reconciled; old CI root cause remains unknown because retrieved logs contained no tox output |
| Plan | `specs/001-test-environment.md` design and plan sections | Draft; no architecture or acceptance criteria were self-approved |
| Tasks | `specs/001-test-environment.md` task checklist | Local audit gate and tox completed; current-SHA GitHub verification and review remain |
| Analyze | Workflow, tox, test, fixture, configuration, and documentation-impact inventory below | Complete for this scope |
| Implement | PR #12 changes and imported PR #11 baseline | Complete locally; no production changes |
| Verify | Commands, documentation-impact review, and results below | Local audit gate and tox recorded for `500a926`; current PR SHA checks remain gated and human review is pending |

## Documentation impact review

| Documentation | Impact and decision |
|---|---|
| `README.md` | No documentation change needed: no user-visible integration behavior or configuration changed. README already links to `CONTRIBUTING.md`; another test-command link would duplicate contributor guidance. |
| `CONTRIBUTING.md` | Updated to explain that tox performs a strict pip-audit of installed test-environment distributions before pytest; local commands remain unchanged. |
| `AGENTS.md` and `DEVCONTAINER.md` | No documentation change needed: the test-only reload assertion does not change the developer container or supported runtime. The existing Python guidance includes 3.14. |
| Example configuration (`config/configuration.yaml`) | No change needed: no configuration or runtime behavior changed. The isolated test safety review remains recorded below. |
| Changelog/release notes | No change needed: this is internal test/verification work, not an unreleased user-facing feature or release. No `CHANGELOG.md` exists in the repository. |
| `specs/001-*.md` | Updated verification evidence and this impact review are recorded in the existing Draft SPEC-001 artifacts; requirements and acceptance criteria were not changed. |

No additional README or user-facing documentation change is warranted. This review covers the multi-entry test assertion and the SPEC-001 testing/CI documentation; no product configuration, compatibility promise, migration, or user-facing feature changed in the follow-up commits.

## Isolated environment and safety

- Python 3.14.10 and Home Assistant 2026.11.0 were used for local tox verification.
- Tests run with `--disable-socket --allow-hosts=127.0.0.1,::1,localhost`; IMAP is mocked by test fixtures.
- `config/configuration.yaml` was inspected and contains no `remote_homeassistant`, secrets, or `!secret` references. No Home Assistant instance or production service was started.
- Tests cover two config entries and independently reloading one entry. The follow-up assertion checks the second entry's registered sensor identities and state/attributes before and after the first entry reload.
- Existing producer-side entity attribute tests are available in `tests/test_sensor.py`. No companion-card source or browser test tooling is present in this repository, so consumer/browser tests were not run; this is a documented scope limitation, not a passed check.

## Test status matrix

| Check | Status | Evidence |
|---|---|---|
| Focused HA init lifecycle | PASS | `tox -e py314 -- tests/test_init.py --no-cov`; 37 passed on earlier implementation |
| Focused multi-entry isolation | PASS | `tox -e py314 -- tests/test_init.py::test_multiple_entries_setup_and_reload --no-cov -q --tb=short --log-level=WARNING`; 1 passed |
| Full pytest suite | PASS | Full tox run on Python 3.14.10; 525 passed, configured integration Python coverage 100%; pytest runtime 10.83s |
| Integration manifest contract | PASS | `tests/test_manifest.py`; manifest metadata and required fields pass |
| Ruff lint and format | PASS | `ruff check --no-fix .` and `ruff format --check .`; read-only; 53 files formatted |
| mypy | PASS | `mypy custom_components/mail_and_packages/`; no issues in 24 source files |
| Spec artifact gate | PASS | 3 standard-library unit tests pass; changed spec artifacts pass against PR base `71d2111e23de1ec0ca641a310d74cfb2c4c25237` |
| Full local tox with required audit gate | PASS | `env -u GITHUB_ACTIONS PATH="/opt/hostedtoolcache/Python/3.14.9/x64/bin:/tmp/spec001-tox-tools/bin:$PATH" /tmp/spec001-tox-tools/bin/tox`; Python 3.14.9; audit passed in 0.72s, 525 tests passed, integration Python coverage 100%, 12 existing warnings; 25.82s total, code SHA `500a926`. |
| Resolved test-environment dependency audit | PASS | `pip-audit --local --strict --timeout 15 --progress-spinner off`; pip-audit 2.10.1, Python 3.14.9, 160 installed distributions including Home Assistant 2026.11.0 and Pillow 13.0.0; default PyPI vulnerability service; no known vulnerabilities; exit 0. |
| GitHub CI #32 Python 3.14 | PASS | Run [42173410045](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42173410045), job [127746250142](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42173410045/job/127746250142), SHA `e6dde8b`; successful, 2m15s job duration; tox step succeeded |
| HACS and hassfest | PASS | Validation run [42168187892](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42168187892), job [127743521986](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42168187892/job/127743521986), SHA `e6dde8b`; both named steps succeeded |
| Pre-commit on reviewed SHA | NOT_VERIFIED | No run for `e6dde8b` was found; an earlier successful pre-commit run was for SHA `3f427c0` and is not evidence for the reviewed SHA |
| GitHub CodeQL on reviewed SHA | NOT_RUN | No CodeQL workflow run for `e6dde8b` was found; the local CodeQL tool result is separately recorded below |
| Local CodeQL on changed Python | PASS (earlier code SHA) | CodeQL checker found zero alerts after test commit `4e39b95`; the latest audit changes are requirements/tox/docs, for which the checker reported no CodeQL-analyzable code and performed no analysis |
| Local secret scan | PASS | Secret scanner found no secrets in the three changed files; the final verification-document edit was also scanned before commit |
| Automated dependency vulnerability scanning | PASS (local baseline) | `tox` now runs the strict pip-audit command above before pytest; `pip-audit==2.10.1` is pinned. Same-SHA GitHub CI remains pending. |
| Home Assistant live startup | NOT_RUN | Not required; no HA instance was launched |
| Companion-card browser/consumer tests | NOT_RUN | Companion card source and browser tooling are not present in this repository |
| GitHub CI on latest code SHA | NOT_RUN | No CI run exists for `500a926`; CI #32 passed on prior SHA `e6dde8b` only |
| Validation/HACS/hassfest on latest code SHA | ACTION_REQUIRED | Validation run [42177190824](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42177190824) is `action_required` for `500a926` and has zero jobs |
| PR lint on latest code SHA | ACTION_REQUIRED | Lint PR run [42177194498](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42177194498) is `action_required` for `500a926` |
| Pre-commit on latest code SHA | NOT_VERIFIED | No run exists for `500a926`; the available run is for older SHA `3f427c0` |
| GitHub CodeQL on latest code SHA | NOT_VERIFIED | No run exists for `500a926`; the available run is for older SHA `3f427c0` |
| Premium-request usage | NOT_AVAILABLE | No usage metadata was exposed; no estimate recorded |

Full tox measured 100% coverage for the configured integration Python files (`custom_components/mail_and_packages/`), not for every behavior or the whole repository. It completed with 12 existing pytest/deprecation/runtime warnings and no failures. No live HA instance was started. An initial full tox attempt used the sandbox's Python 3.12 Actions context and could not resolve HA 2026.11; it passed when rerun with Python 3.14.10 and the sandbox-only `GITHUB_ACTIONS` variable unset.

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
- CI #32's Python 3.14 job took 2m15s on `e6dde8b`; the tox step itself took 1m56s. The current local full tox run including the audit took 25.82s. The earlier failed tox step ran 37m38s on a different SHA, with no tox output in retrieved logs; its cause remains unknown. No premium-request usage was available.

## Compatibility, rollback, and remaining scope

- These changes affect test tooling and tests only; they do not alter integration runtime dependencies, config-entry schemas, entity IDs, or stored data. No user-data migration is required.
- The new audit package is test-only and does not change `manifest.json` or runtime dependencies. Rollback is a source-control revert of the requirements, tox, contribution-guidance, and SPEC changes; no production HA instance or data restoration is involved.
- The companion-card requirement is limited to producer-side entity contract checks because the consumer project/tooling is absent. Browser/consumer validation remains not run.
- No self-healing automation is implemented; the two-attempt cap is consequently not enforced. Human review and manual merge remain required.

## Next actions

- Request repository approval to run CI, Validation/HACS/hassfest, pre-commit, and GitHub CodeQL on the latest PR revision; Validation run `42177190824` is gated with zero jobs on `500a926`. Local tox/audit, secret scan, and the changed-spec gate passed.
- Verify the pip-audit gate in the current-SHA CI run after repository approval; retain its no-suppressions policy and revisit the helper's intentional no-deps compatibility gap separately if desired.
- Inspect the resulting current-SHA CI logs; do not infer a cause for the earlier 404 job.
- Obtain human review of the still-Draft specification and implementation. Merge remains manual.
