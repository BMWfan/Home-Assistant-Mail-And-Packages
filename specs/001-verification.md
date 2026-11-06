# SPEC-001 — Verification evidence and remaining gates

**Evidence date:** 2026-11-06. **Status:** CI and HACS/hassfest passed on reviewed SHA `e6dde8b`; verification of the follow-up test change and human review remain pending. No production services were accessed.

## SDD phase and review gates

| Phase | Artifact or evidence | Status / gate |
|---|---|---|
| Specify | `specs/001-test-environment.md` requirements and acceptance criteria | Draft; human review required |
| Clarify | PR #12 review comments and CI investigation | Requirements reconciled; old CI root cause remains unknown because retrieved logs contained no tox output |
| Plan | `specs/001-test-environment.md` design and plan sections | Draft; no architecture or acceptance criteria were self-approved |
| Tasks | `specs/001-test-environment.md` task checklist | Local implementation tasks completed; final-SHA verification and review remain |
| Analyze | Workflow, tox, test, fixture, and configuration inventory below | Complete for this scope |
| Implement | PR #12 changes and imported PR #11 baseline | Complete locally; no production changes |
| Verify | Commands and results below | CI and HACS/hassfest evidence recorded for `e6dde8b`; final follow-up SHA and review remain |

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
| Full local tox | PASS | `env -u GITHUB_ACTIONS PATH="$(dirname "$(/tmp/spec001-venv/bin/uv python find 3.14)"):$PATH" /tmp/spec001-venv/bin/tox`; 525 passed; 17.06s total |
| GitHub CI #32 Python 3.14 | PASS | Run [42173410045](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42173410045), job [127746250142](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42173410045/job/127746250142), SHA `e6dde8b`; successful, 2m15s job duration; tox step succeeded |
| HACS and hassfest | PASS | Validation run [42168187892](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42168187892), job [127743521986](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42168187892/job/127743521986), SHA `e6dde8b`; both named steps succeeded |
| Pre-commit on reviewed SHA | NOT_VERIFIED | No run for `e6dde8b` was found; an earlier successful pre-commit run was for SHA `3f427c0` and is not evidence for the reviewed SHA |
| GitHub CodeQL on reviewed SHA | NOT_RUN | No CodeQL workflow run for `e6dde8b` was found; the local CodeQL tool result is separately recorded below |
| Local CodeQL on changed Python | PASS | CodeQL checker found zero alerts after commit `4e39b95` |
| Local secret scan | PASS | Secret scanner found no secrets in the three changed files; the final verification-document edit was also scanned before commit |
| Automated dependency vulnerability scanning | NOT_IMPLEMENTED | `.github/dependabot.yml` schedules pip version updates but is not a vulnerability scan. No dependency audit workflow/tool is configured. Repository alert APIs returned 403; only selected tox packages were checked against the advisory database, which is not a project-wide scan. |
| Home Assistant live startup | NOT_RUN | Not required; no HA instance was launched |
| Companion-card browser/consumer tests | NOT_RUN | Companion card source and browser tooling are not present in this repository |
| GitHub CI on follow-up SHA | NOT_RUN | No CI run exists for `4e39b95`; CI #32 passed on prior SHA `e6dde8b` only |
| Validation/HACS/hassfest on follow-up SHA | ACTION_REQUIRED | Validation run [42174653628](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42174653628) is `action_required` for `4e39b95` and has zero jobs |
| PR lint on follow-up SHA | ACTION_REQUIRED | Lint PR run [42174656579](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42174656579) is `action_required` for `4e39b95` and has zero jobs |
| Pre-commit on follow-up SHA | NOT_VERIFIED | No run exists for `4e39b95`; the available run is for older SHA `3f427c0` |
| GitHub CodeQL on follow-up SHA | NOT_VERIFIED | No run exists for `4e39b95`; the available run is for older SHA `3f427c0` |
| Premium-request usage | NOT_AVAILABLE | No usage metadata was exposed; no estimate recorded |

Full tox measured 100% coverage for the configured integration Python files (`custom_components/mail_and_packages/`), not for every behavior or the whole repository. It completed with 12 existing pytest/deprecation/runtime warnings and no failures. No live HA instance was started. An initial full tox attempt used the sandbox's Python 3.12 Actions context and could not resolve HA 2026.11; it passed when rerun with Python 3.14.10 and the sandbox-only `GITHUB_ACTIONS` variable unset.

The previously reported CI job `127711456311` (run `42162228288`, attempt 2) failed after the `Run tox` step ran for 37m38s. Job-log retrieval returned step-security runner teardown output but no tox output, so the cause is still unconfirmed. The local pass does not establish a cause for that remote run.

## Tooling and cost notes

- tox 4.32.0 and tox-gh-actions 3.5.0 were used and pinned in CI; both support the Python 3.14 configuration. The tox-gh-actions 3.5.0 compatibility table supports tox 4.x.
- Removed the obsolete `pip>=21,<22.1` cap, which did not match the Python 3.14 target. Tox now uses its Python-compatible environment pip.
- Home Assistant, Ruff, the HA pytest helper, and selected test tooling are pinned or constrained. The full transitive dependency closure is not locked; adding and maintaining a platform-specific full lock was not included in this minimal CI fix.
- Dependency-vulnerability scanning remains an acceptance-criterion gap. Dependabot is configured for pip version updates only; no full audit is claimed. A new audit gate was not added because the available GitHub vulnerability-alert API is inaccessible in this session and the scope/triage policy for adding another security tool needs human review. Keep this as a blocker rather than treating the selected tox advisory lookup as project-wide coverage.
- CI runs lint and type checking before pytest, caches uv dependencies, cancels superseded runs for the same ref, and bounds the test job at 20 minutes.
- No extra path-filtered test suite was added: the repository has one relevant integration suite, and skipping it for broad source changes would weaken coverage. No LLM calls, agent-trigger loop, privileged token, auto-approval, or auto-merge were added. No two-repair-attempt cap is enforced because self-healing is not configured.
- CI #32's Python 3.14 job took 2m15s on `e6dde8b`; the tox step itself took 1m56s. The measured 17.06s is a cached local tox duration. The earlier failed tox step ran 37m38s on a different SHA, with no tox output in retrieved logs; its cause remains unknown. No premium-request usage was available.

## Compatibility, rollback, and remaining scope

- These changes affect test tooling and tests only; they do not alter integration runtime dependencies, config-entry schemas, entity IDs, or stored data. No user-data migration is required.
- Rollback is a source-control revert of the CI/test/spec changes; no production HA instance or data restoration is involved.
- The companion-card requirement is limited to producer-side entity contract checks because the consumer project/tooling is absent. Browser/consumer validation remains not run.
- No self-healing automation is implemented; the two-attempt cap is consequently not enforced. Human review and manual merge remain required.

## Next actions

- Request repository approval to run CI, Validation/HACS/hassfest, pre-commit, and GitHub CodeQL on the follow-up SHA; the current Validation and PR-lint runs are gated with zero jobs. Local tests, CodeQL, secret scan, and the changed-spec gate have been verified.
- Resolve whether dependency vulnerability scanning should be introduced and what sources/exception policy it should use; this acceptance criterion remains incomplete.
- Inspect the resulting current-SHA CI logs; do not infer a cause for the earlier 404 job.
- Obtain human review of the still-Draft specification and implementation. Merge remains manual.
