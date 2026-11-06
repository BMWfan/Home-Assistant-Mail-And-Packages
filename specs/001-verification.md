# SPEC-001 — Verification evidence and remaining gates

**Evidence date:** 2026-11-06. **Status:** Local checks pass; current PR GitHub validation and human review remain pending. No production services were accessed.

## SDD phase and review gates

| Phase | Artifact or evidence | Status / gate |
|---|---|---|
| Specify | `specs/001-test-environment.md` requirements and acceptance criteria | Draft; human review required |
| Clarify | PR #12 review comments and CI investigation | Requirements reconciled; old CI root cause remains unknown because retrieved logs contained no tox output |
| Plan | `specs/001-test-environment.md` design and plan sections | Draft; no architecture or acceptance criteria were self-approved |
| Tasks | `specs/001-test-environment.md` task checklist | Local implementation tasks completed; remote validation and review remain |
| Analyze | Workflow, tox, test, fixture, and configuration inventory below | Complete for this scope |
| Implement | PR #12 changes and imported PR #11 baseline | Complete locally; no production changes |
| Verify | Commands and results below | Local results recorded; updated PR SHA checks pending |

## Isolated environment and safety

- Python 3.14.10 and Home Assistant 2026.11.0 were used for local tox verification.
- Tests run with `--disable-socket --allow-hosts=127.0.0.1,::1,localhost`; IMAP is mocked by test fixtures.
- `config/configuration.yaml` was inspected and contains no `remote_homeassistant`, secrets, or `!secret` references. No Home Assistant instance or production service was started.
- Tests cover two config entries and independently reloading one entry.
- Existing producer-side card attribute tests are available in `tests/test_sensor.py`; the companion card source and browser test suite are not in this repository, so consumer/browser validation remains out of scope.

## Test status matrix

| Check | Status | Evidence |
|---|---|---|
| Focused HA init lifecycle | PASS | `tox -e py314 -- tests/test_init.py --no-cov`; 37 passed; cold environment setup and run took 47.90s |
| Full pytest suite | PASS | Full tox run on Python 3.14.10; 525 passed, coverage 100%; pytest runtime 13.50s |
| Integration manifest contract | PASS | `tests/test_manifest.py`; manifest metadata and required fields pass |
| Ruff lint and format | PASS | `ruff check --no-fix .` and `ruff format --check .`; read-only; 53 files formatted |
| mypy | PASS | `mypy custom_components/mail_and_packages/`; no issues in 24 source files |
| Spec artifact gate | PASS | 3 standard-library unit tests pass; changed spec artifacts pass against PR base `71d2111e23de1ec0ca641a310d74cfb2c4c25237` |
| Full local tox | PASS | `env -u GITHUB_ACTIONS PATH="$(dirname "$(/tmp/spec001-venv/bin/uv python find 3.14)"):$PATH" /tmp/spec001-venv/bin/tox`; 525 passed; 16.07s cached total |
| HACS and hassfest on current PR SHA | ACTION_REQUIRED | Validation run `42167716397` is gated; no current-SHA results are available |
| CodeQL on current changes | PENDING | Re-run after the manifest contract test is committed |
| Secret scanning on current changes | PENDING | Scan the final changed files before commit |
| Home Assistant live startup | NOT_RUN | Not required; no HA instance was launched |
| Companion-card browser/consumer tests | NOT_RUN | Companion card source is not present in this repository |
| CI run duration on updated PR SHA | NOT_AVAILABLE | No updated-SHA CI run is available yet |
| Premium-request usage | NOT_AVAILABLE | No usage metadata was exposed; no estimate recorded |

The full tox run completed with 12 existing pytest/deprecation/runtime warnings; there were no test failures. An initial full tox attempt used the sandbox's Python 3.12 Actions context and could not resolve HA 2026.11. It was rerun with Python 3.14.10 and the sandbox-only `GITHUB_ACTIONS` variable unset; the complete suite then passed.

The previously reported CI job `127711456311` (run `42162228288`, attempt 2) failed after the `Run tox` step ran for 37m38s. Job-log retrieval returned step-security runner teardown output but no tox output, so the cause is still unconfirmed. The local pass does not establish a cause for that remote run.

## Tooling and cost notes

- tox 4.32.0 and tox-gh-actions 3.5.0 were used and pinned in CI; both support the Python 3.14 configuration. The tox-gh-actions 3.5.0 compatibility table supports tox 4.x.
- Removed the obsolete `pip>=21,<22.1` cap, which did not match the Python 3.14 target. Tox now uses its Python-compatible environment pip.
- Home Assistant, Ruff, the HA pytest helper, and selected test tooling are pinned or constrained. The full transitive dependency closure is not locked; adding and maintaining a platform-specific full lock was not included in this minimal CI fix.
- CI runs lint and type checking before pytest, caches uv dependencies, cancels superseded runs for the same ref, and bounds the test job at 20 minutes.
- No extra path-filtered test suite was added: the repository has one relevant integration suite, and skipping it for broad source changes would weaken coverage. No LLM calls, agent-trigger loop, privileged token, auto-approval, or auto-merge were added. No two-repair-attempt cap is enforced because self-healing is not configured.
- The measured 16.07s is a cached local tox duration, not a GitHub CI duration. The 37m38s measurement is the previous failed remote tox step, not the updated PR SHA. No premium-request usage was available.

## Next actions

- Verify HACS, hassfest, pre-commit, and GitHub CodeQL on the updated PR SHA after repository approval allows the checks to run.
- Inspect the resulting current-SHA CI logs; do not infer a cause for the earlier 404 job.
- Obtain human review of the still-Draft specification and implementation. Merge remains manual.
