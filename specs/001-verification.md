# SPEC-001 — Verification evidence and remaining gates

**Evidence date:** 2026-11-07. CI run #41 and Pre-commit run #21 were inspected on pre-fix SHA `398895823a194f4e2ba4238637b1116abd2939ea`: tox passed; codespell failed on 37 diagnostics for valid German words. The targeted dictionary adjustment passes the full local pre-commit suite and retains English spellchecking (an intentionally misspelled English token is still rejected). On code/config fix SHA `68eb8c4171ae4c9b299fd3a8b34c9708270cacb2`, GitHub CI, Validation, Pre-commit, Autolabeler, and PR lint are `action_required` with zero jobs; no remote verification ran. The earlier Ruff failure on `c9a8c63` was also fixed and verified locally. Human review remains pending. No production services were accessed.

**Documentation-only follow-up (2026-11-07):** this follow-up adds a PR #11/PR #12 baseline comparison and provenance mapping, a dated static Home Assistant release-compatibility audit, a permanent SDD-Light review policy in `AGENTS.md` section 5.1, a short contributor pointer in `CONTRIBUTING.md`, and ranked feature proposals (not implemented) below. The earlier GitHub Actions snapshots are on audited parent SHA `1b32ce5b7383f395f99a8e6ab86de0619ebcd94c` and documentation commit `cdb2dc95609ae5c6ba724503ade0d6d31d383984`; the latter is recorded below. The latest observed checks are on SHA `1c91bdc8841a5ca54fce3ee2693d26b24f348cbb`. No production service or secret was accessed; the upstream audit consulted public GitHub sources. SPEC-001 remains Draft; T007 remains partial and T009 human review and manual merge remain open.

**Earlier observed GitHub checks (2026-11-07), SHA `cdb2dc95609ae5c6ba724503ade0d6d31d383984`:** each listed Actions run completed as `action_required`; each jobs API response had `total_count=0`. There are no step logs or test results, and the API disclosed no reason. `action_required` is not a pass; no specific approval cause is confirmed, and these results do not establish that tests ran.

| Workflow / event | Run |
|---|---|
| CI | [42373449062](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373449062) |
| Validation `pull_request` / `push` | [42373449080](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373449080) / [42373444056](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373444056) |
| Pre-commit | [42373449057](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373449057) |
| Autolabeler `pull_request` / `pull_request_target` | [42373449077](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373449077) / [42373446341](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373446341) |
| Lint PR | [42373446332](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373446332) |

These runs are historical evidence for `cdb2dc95609ae5c6ba724503ade0d6d31d383984`, not the latest observed checks. No local test, build, lint, or format result is claimed for `cdb2dc9`.

**Latest observed GitHub checks (2026-11-07), SHA `1c91bdc8841a5ca54fce3ee2693d26b24f348cbb`:** each listed Actions run completed with conclusion `action_required`; each equivalent jobs lookup returned zero jobs. No reason or test output is available. These are not passes and do not establish that tests ran.

| Workflow / event | Run |
|---|---|
| CI | [42373844976](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373844976) |
| Validation `pull_request` / `push` | [42373844998](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373844998) / [42373841520](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373841520) |
| Pre-commit | [42373844981](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373844981) |
| Autolabeler `pull_request` / `pull_request_target` | [42373844982](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373844982) / [42373843510](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373843510) |
| Lint PR | [42373843486](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42373843486) |

SHA `1c91bdc8841a5ca54fce3ee2693d26b24f348cbb` is the latest observed head; the next documentation-only evidence commit will have a newer SHA, and checks for that newer commit are not yet observed. No local test, build, lint, or format result is claimed for this SHA.

## SDD phase and review gates

| Phase | Artifact or evidence | Status / gate |
|---|---|---|
| Specify | `specs/001-test-environment.md` requirements and acceptance criteria | Draft; human review required |
| Clarify | PR #12 review comments and CI investigation | Requirements reconciled; old CI root cause remains unknown because retrieved logs contained no tox output |
| Plan | `specs/001-test-environment.md` design and plan sections | Draft; no architecture or acceptance criteria were self-approved |
| Tasks | `specs/001-test-environment.md` task checklist | CI #33 evidence is for `b48bdee`; GitHub checks on code/config fix SHA `68eb8c4` are action-required with zero jobs; T007 remains partial and human review remains |
| Analyze | Workflow, tox, test, fixture, configuration, and documentation-impact inventory below | Complete for this scope |
| Implement | PR #12 changes and imported PR #11 baseline | Complete locally; no production changes |
| Verify | Commands, documentation-impact review, and results below | Full local tox passed on `e5911cd`; targeted tests passed on `d41cf3a`; local pre-commit passes with the German-word allowlist; GitHub tox passed but pre-fix codespell failed on `3988958`; post-fix GitHub checks are action-required |

## Documentation impact review

| Documentation | Impact and decision |
|---|---|
| `README.md` | No documentation change needed: no user-visible integration behavior or configuration changed. README already links to `CONTRIBUTING.md`; another test-command link would duplicate contributor guidance. |
| `CONTRIBUTING.md` | Updated to explain that tox performs a strict pip-audit of installed test-environment distributions before pytest; local commands remain unchanged. The codespell adjustment changes no commands or security requirements, so no additional contributor-documentation change is needed. This 2026-11-07 follow-up adds a short pointer to the new permanent SDD-Light review policy in `AGENTS.md` section 5.1; no commands changed. |
| `AGENTS.md` | Updated the manual test setup to install the HA pytest helper with `--no-deps`, matching tox and preserving the HA 2026.11.0 pin. This 2026-11-07 follow-up adds a new, permanent section 5.1 ("SDD-Light review policy") requiring HA-release/upstream/fork-contract review evidence for substantial changes, with a lightweight checklist option for small fixes; scheduled upstream monitoring is documented as proposed and disabled, not implemented. |
| `DEVCONTAINER.md` | No change needed: the merge and test assertion do not change the container or supported runtime. |
| Example configuration (`config/configuration.yaml`) | The base branch includes a `remote_homeassistant` development mirror using `!secret` references. The pytest fixture uses an isolated test `hass` and synthetic `MockConfigEntry` data; tests do not load this file. No real secrets were read and no HA instance was launched. |
| Changelog/release notes | No change needed: this is internal test/verification work, not an unreleased user-facing feature or release. No `CHANGELOG.md` exists in the repository. |
| `specs/001-*.md` | Updated verification evidence and this impact review are recorded in the existing Draft SPEC-001 artifacts; requirements and acceptance criteria were not changed. This 2026-11-07 follow-up adds the PR #11/PR #12 provenance comparison, the dated HA compatibility audit, and ranked feature proposals below, and updates `specs/001-test-environment.md` task T007 evidence only; no acceptance criterion, Draft status, or T009 review requirement was changed. |

No additional README or user-facing documentation change is warranted. The PR diff includes SPEC-001, test/CI work, and the SDD-Light documentation in `AGENTS.md` and `CONTRIBUTING.md`; no runtime behavior or acceptance criteria changed. The test assertion and manual helper-install command are documented in the relevant contributor guidance.

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
| CI on codespell-fix SHA | ACTION_REQUIRED | [Run 42371893495](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371893495), SHA `68eb8c4`; completed `action_required`, zero jobs. No CI steps ran on the corrected SHA. |
| Pre-commit on codespell-fix SHA | ACTION_REQUIRED | [Run 42371893208](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371893208), SHA `68eb8c4`; completed `action_required`, zero jobs. The GitHub codespell hook has not run on the corrected SHA. |
| Validation on codespell-fix SHA | ACTION_REQUIRED | [PR run 42371893268](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371893268) and [push run 42371889456](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371889456), SHA `68eb8c4`; both completed `action_required`, zero jobs. HACS/hassfest are not verified on this SHA. |
| Autolabeler and PR lint on codespell-fix SHA | ACTION_REQUIRED | Autolabeler [runs 42371893345](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371893345) and [42371892074](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371892074), plus PR lint [run 42371892031](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42371892031), SHA `68eb8c4`; each completed `action_required`, zero jobs. |
| Post-fix Actions gate diagnosis | NOT_DETERMINED | The Actions API reports no jobs and exposes no specific approval/permission cause for the runs above. An authorized repository user must inspect/resolve the gate; it was not bypassed. |
| CI on pre-codespell-fix SHA | PASS | [Run 42370999117](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370999117), Python 3.14 job [128399641895](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370999117/job/128399641895), SHA `3988958`, attempt 2; job passed in 1m48s. Tox/pytest reported 663 passed, 22 warnings in 21.61s. |
| Pre-commit on pre-fix SHA | FAIL (codespell only) | [Run 42370999151](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370999151), job [128399585817](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370999151/job/128399585817), SHA `3988958`, attempt 2. YAML, whitespace, Ruff, and Ruff format passed; codespell exited 65 with 37 diagnostics, all for German-language words: `als`, `lokal`, `unter`, `Dokument`, `alle`, `lokale`, `oder`, `explizit`, `Manuell`, `Juli`, `Alle`, `Ende`, `offen`, `vor`, `Modell`, `finde`, `Probleme`, and `sie`. The occurrences are in mixed-language `AGENTS.md`/`CLAUDE.md`, scripts, the German test fixture, and agent guidance; no source text was changed. |
| Local pre-commit after allowlist adjustment | PASS | `pre-commit==4.5.0` in a temporary Python 3.12.3 environment; `pre-commit run --all-files` passed YAML, end-of-file, whitespace, debug-statements, Ruff, Ruff format, and codespell. The codespell hook remains pinned at `v2.4.1`. |
| English spellcheck negative probe | PASS (expected rejection) | The configured codespell ignore list rejected a temporary English misspelling with the expected correction (exit 65); the probe file was kept in `/tmp` and removed. |
| Earlier SHA CI | ACTION_REQUIRED | [Run 42370904163](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370904163), SHA `3e65b9d`; completed `action_required`, zero jobs. This predates the later CI success on `3988958`. |
| Earlier SHA Validation | ACTION_REQUIRED | [PR run 42370903982](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370903982) and [push run 42370898146](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370898146), SHA `3e65b9d`; both completed `action_required`, zero jobs. HACS/hassfest were not verified on that SHA. |
| Earlier SHA Pre-commit | ACTION_REQUIRED | [Run 42370903941](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370903941), SHA `3e65b9d`; completed `action_required`, zero jobs. |
| Earlier SHA Autolabeler | ACTION_REQUIRED | [PR run 42370904008](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370904008) and [pull_request_target run 42370901276](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370901276), SHA `3e65b9d`; both completed `action_required`, zero jobs. |
| Earlier SHA PR lint | ACTION_REQUIRED | [Run 42370901252](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42370901252), SHA `3e65b9d`; completed `action_required`, zero jobs. |
| Earlier SHA status diagnosis | NOT_DETERMINED | The Actions API reported no jobs for the runs above and did not expose a specific approval/permission cause. The combined commit-status API returned zero statuses. A repository maintainer must inspect/resolve the gate; it was not bypassed. |
| CI run that exposed the current failure | FAIL (diagnosed) | [Run 42198668574](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198668574), job [128382480615](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198668574/job/128382480615), SHA `c9a8c63`; Python 3.14.10; step `Run tox`; job duration 1m42s. Exact lint output: `FLY002 Consider f-string instead of string join` at `tests/test_spec_artifacts.py:62:17`, followed by `Found 1 error.` The overall tox result was `lint: FAIL code 1`; `mypy: OK`, `py314: OK`, and `evaluation failed :( (85.19 seconds)`, causing exit 255. |
| CI tests/audit within the failing run | PASS (not overall CI) | Same job: pip-audit printed `No known vulnerabilities found`; pytest printed `663 passed, 22 warnings in 18.23s`, and coverage was 90.41%. These passing stages do not change the overall CI failure. |
| Local fix verification | PASS | On `d41cf3a`, Ruff 0.15.0 `ruff check --no-fix tests/test_spec_artifacts.py` and `ruff format --check tests/test_spec_artifacts.py` passed after replacing the flagged tuple join with a newline literal. `python -m unittest tests.test_spec_artifacts -v`: 4 passed; `python -m py_compile check_spec_artifacts.py tests/test_spec_artifacts.py` and `git diff --check` passed. Full tox was not rerun locally for this literal-only test-data change. |
| Validation on failure SHA | ACTION_REQUIRED | [Run 42198659735](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198659735), SHA `c9a8c63`; completed `action_required`. |
| Pre-commit on failure SHA | ACTION_REQUIRED | [Run 42198668282](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198668282), SHA `c9a8c63`; completed `action_required`. |
| Autolabeler on failure SHA | ACTION_REQUIRED | [Run 42198668741](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198668741) (`pull_request`) and [run 42198665336](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198665336) (`pull_request_target`), SHA `c9a8c63`; both completed `action_required`. |
| PR lint on failure SHA | ACTION_REQUIRED | [Run 42198665100](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42198665100), SHA `c9a8c63`; completed `action_required`. |
| Actions gate diagnosis on failure SHA | NOT_DETERMINED | The run snapshots for Validation, Pre-commit, both Autolabeler runs, and PR lint show `action_required`; the API exposes no jobs and no specific approval or permission reason. A repository maintainer must inspect/resolve the repository-side gate; no gate was bypassed. |
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
| GitHub CodeQL on PR #12 base | NOT_CONFIGURED | `.github/workflows/codeql-analysis.yml` limits pull-request target branches to `master`, `0.2.0`, and `0.3.0`, excluding PR #12's `test/all-features` base. The last surfaced run [42162228330](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/actions/runs/42162228330) is on older SHA `3f427c0`; no GitHub CodeQL result is established for `b48bdee` or `cdb2dc9`. |
| Local CodeQL on tested code | PASS (historical) | CodeQL checker found zero alerts after commit `e5911cd`. This is local evidence for that tested SHA only, not a GitHub CodeQL result or evidence for `cdb2dc9`. |
| Local secret scan | PASS | No secrets were detected in the files passed to the scanner, including the final test and documentation changes. |
| Automated dependency vulnerability scanning | PASS | `tox` runs strict pip-audit before pytest; `pip-audit==2.10.1` is pinned. Local tox audit passed on `e5911cd`; CI #33 also passed on `b48bdee`. |
| Home Assistant live startup | NOT_RUN | Not required; no HA instance was launched |
| Companion-card browser/consumer tests | NOT_RUN | Companion card source and browser tooling are not present in this repository |
| Premium-request usage | NOT_AVAILABLE | No usage metadata was exposed; no estimate recorded |

The post-merge full tox run on `e5911cd` measured 90.41% coverage for the configured integration Python files (`custom_components/mail_and_packages/`), exceeding the configured 90% threshold; this is not whole-repository coverage or proof of every behavior. It completed with 22 warnings and no failures. Earlier code at SHA `500a926` had a separate 100% result; that number does not describe the merged base. No live HA instance was started.

The security audit used the locally installed distributions after resolving `requirements_test.txt` with Python 3.14.9 and adding the same `pytest-homeassistant-custom-component==0.13.375` package with `--no-deps`, as configured by tox. The resulting environment had 160 installed distributions (including pinned HA 2026.11.0, audit tool 2.10.1, and its own dependencies); pip-audit's local installed-package scan against its default PyPI vulnerability service reported no known vulnerabilities. The repository does not lock the complete transitive dependency graph, so versions other than explicitly pinned requirements can vary across fresh resolutions; this result applies to this resolved inventory, not all future installs.

`pip check` exits nonzero after tox's intentional `--no-deps` install of `pytest-homeassistant-custom-component==0.13.375`. That helper declares exact requirements for HA 2026.10.4, coverage 7.16.2, numpy 2.3.2, pytest 9.0.3 and pytest-asyncio 1.4.0, conflicting with this environment's pinned HA 2026.11.0 and newer resolved test packages; it also declares helper packages (including `aiohasupervisor`, `mock-open`, `pipdeptree`, `pydantic`, `PyGithub`, `pytest-freezer`, `pytest-picked`, `pytest-unordered`, `tqdm`, and `unidiff`) which are not installed. Tox uses `--no-deps` to avoid downgrading the supported HA target; the suite and audit pass with that established setup. The audit scans distributions actually installed and cannot report on packages omitted by this no-deps install. This is a known test-helper resolution limitation, not an audit suppression. No dependency auto-fixes were used.

A preliminary, discarded setup experiment installed the HA test helper with its dependencies instead of tox's `--no-deps`; it downgraded HA to 2026.10.4 and Pillow to 12.3.0, producing 39 Pillow advisory records (fix version reported as 13.0.0). A repeat audit of that disposable, non-target environment exited 1, confirming that findings fail the gate; it is not counted as the target baseline. The advisory output described issues including memory-safety, resource-exhaustion and potential code-execution classes, but did not return severity ratings; the supplemental advisory lookup also supplied no severity scores. The correctly resolved target environment uses Pillow 13.0.0 and reports no known vulnerabilities. If a valid HA 2026.11 scan later resolves Pillow below 13.0.0, a narrow `Pillow>=13.0.0` lower-bound review in the test requirements is preferable to broad upgrades; no dependency upgrade was made based on the invalid setup.

The previously reported CI job `127711456311` (run `42162228288`, attempt 2) failed after the `Run tox` step ran for 37m38s. Job-log retrieval returned step-security runner teardown output but no tox output, so the cause is still unconfirmed. This is separate from the current `c9a8c63` failure, whose root cause is confirmed above as Ruff FLY002 in the deletion-only regression test.

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

## PR #11 / PR #12 baseline comparison and provenance (2026-11-07)

Upstream PR #11 (`BMWfan/Home-Assistant-Mail-And-Packages#11`) head at audit
time is `6a31eebe0c3b0250c52c3e1c843e8555c5385718`, with seven commits: six
baseline follow-up commits plus a later tox fix. This PR (#12), head
`1b32ce5b7383f395f99a8e6ab86de0619ebcd94c` on base `test/all-features`
`71d2111e23de1ec0ca641a310d74cfb2c4c25237`, contains the corresponding
changes in its history and current diff. Provenance mapping by commit
subject/hash, as far as the retrievable record allows:

| PR #11 commit | Subject (as retrieved) | Corresponding PR #12 state |
|---|---|---|
| `a6e2e53` | Define evidence-first testing/security baseline | Present: the corresponding SPEC/verification requirements (evidence-first testing and security baseline) are recorded in `specs/001-test-environment.md` and `specs/001-verification.md`. |
| `666c716` | Record evidence-based test/hardening inventory | Present: the read-only inventory of workflows, tox, tests, and hardening is recorded in `specs/001-test-environment.md` (T001) and `specs/001-verification.md`. |
| `db7e095` | Keep auto-formatting opt-in | Present: `tox -l`/`tox.ini` default envlist excludes the mutating `format` env; `format` remains read-only (`ruff format --check`), run only when explicitly selected. |
| `ec39c71` | Allow HA YAML tags | Present: the `check-yaml` pre-commit hook is configured with `--unsafe` so HA-specific YAML tags (e.g. `!include`, `!secret`) do not fail the hook. |
| `26512cd` | Remove `HANDOFF_HISTORY.md` whitespace | Present: no trailing-whitespace diagnostics remain in `HANDOFF_HISTORY.md` under the current pre-commit whitespace hook. |
| `c562c08` | Scope codespell / preserve DHL vocabulary | Present and further extended: codespell has scoped skip/ignore exceptions preserving DHL-related vocabulary; PR #12 additionally adds a German-word allowlist in its own commit `68eb8c4` (see below), which is not itself one of the seven PR #11 commits. |
| `6a31eeb` | Later tox mapping / mutating-formatter fix (PR #11 head) | Present: corresponds to this repository's existing tox envlist/format-mapping configuration; no separate regression was found. |

PR #12 keeps the existing `specs/001-*.md` two-file SPEC artifact layout only;
no duplicate or alternate spec layout was introduced.

**Caveat:** this mapping was verified via the GitHub PR #11/PR #12 file and
commit APIs (commit subjects and the files each commit touches), matched
against PR #12's corresponding files/sections (SPEC/verification documents,
`tox.ini` read-only format env, `check-yaml --unsafe`, `HANDOFF_HISTORY.md`
whitespace, and codespell skip/ignore plus the German allowlist). It is
**not** a byte-for-byte comparison of the two PRs' entire trees. No required
PR #11 item was found to be absent from PR #12.

## Home Assistant release compatibility audit (static, dated 2026-11-07)

| Source | Finding |
|---|---|
| HA Core latest-stable release API | Version `2026.11.0`, published 2026-11-04, tag commit `74cf5a49c63ed8d4d87717844bf14f79c28c9cea`. Release API/tag metadata was verified. The official release-notes **source markdown** was read via the GitHub API at `home-assistant/home-assistant.io`, file `source/_posts/2026-11-04-release-202611.markdown`, latest file-affecting commit `9ec83f84c9d11169bd6824ee0a54800033822a24` (https://github.com/home-assistant/home-assistant.io/blob/9ec83f84c9d11169bd6824ee0a54800033822a24/source/_posts/2026-11-04-release-202611.markdown). Direct retrieval of the **rendered** page (`https://www.home-assistant.io/blog/2026/11/04/release-202611/`) and `https://www.home-assistant.io/changelogs/core-2026.11` via `web_fetch` was blocked in this environment; the raw source markdown review is limited in scope and is not a claim of an exhaustive review of the full changelog. |
| HA Core tagged source for `2026.11.0` | `REQUIRED_PYTHON_VER = (3, 14, 2)`. |
| This verification's test pairing | Python 3.14.9 and HA 2026.11.0, as recorded throughout this document (e.g. the full tox run on `e5911cd`). This is the pinned CI/local test pairing actually exercised, not a declaration of the full HA/Python support matrix. |
| `home-assistant/developers.home-assistant` (docs source) | Current `master` commit `50b518898989b67bb76b69827f227aa6f0acd32a`. Documents config-entry setup/unload/reconfigure/options, coordinator polling, manifest requirements, entity patterns, and diagnostics. |
| `home-assistant/contributors.home-assistant.io` (quality-scale docs) | Current `main` commit `ed61b5a5553f3d92e94f80375b87a59eab02a5da`; quality-scale rules under `src/content/docs/core/quality-scale/` cover `runtime_data`, reauth/reconfigure flows, diagnostics, config flow, entity metadata, and tests. |

No release-specific breaking API change was found against the sources
actually consulted above. This is **not** a claim of an exhaustive review of
the HA Core changelog or of all 5,827 changes between the versions involved;
it is limited to the release/tag metadata, the developer-docs source, and the
quality-scale docs source listed, at the commit/tag SHAs recorded above.

### Additional verified findings against official sources (2026-11-07)

These findings come from reading HA Core's tagged `2026.11.0` source and
official HA blog posts; they are static-source review only, not an
exhaustive changelog sweep, and no code was changed based on them.

| Finding | Evidence | Status |
|---|---|---|
| (a) Forward deprecation of `CONN_CLASS_CLOUD_POLL` | HA Core `2026.11.0` tag's `homeassistant/config_entries.py` still defines `CONN_CLASS_CLOUD_POLL` as a `DeprecatedConstant`, with removal version `2027.5.0` ([source](https://github.com/home-assistant/core/blob/74cf5a49c63ed8d4d87717844bf14f79c28c9cea/homeassistant/config_entries.py)). This fork's `custom_components/mail_and_packages/config_flow.py:915` still assigns `CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL`. Upstream HA's own `dev` branch has already removed the constant's use in commit `d9cd889` (home-assistant/core#1546). | Works today on `2026.11.0`; this is an explicit **forward deprecation**, not a current failure. Follow-up needed before `2027.5.0`. No code was changed here. |
| (b) Coordinator `config_entry` assignment order | HA `2026.11.0`'s `DataUpdateCoordinator.__init__` assigns `self.config_entry` from the current config-entry context unless an explicit `config_entry` kwarg is passed to `super().__init__()`. This fork's `custom_components/mail_and_packages/coordinator.py` sets `self.config_entry = config_entry` at line 103 and then calls `super().__init__(hass, _LOGGER, name=self.name, update_interval=self.interval)` at line 117 without passing `config_entry=...`; existing tests manually reset `coordinator.config_entry` afterward. | **Latent source-level fragility, not a confirmed runtime defect.** No normal setup failure was established and no live HA instance was started to reproduce one; this is flagged for a small, separately reviewed fix/regression test, not treated as confirmed broken. |
| (c) `DeviceInfo` plain-dict usage | The plain-`dict` `DeviceInfo` shim remains supported in `2026.11.0` and is marked "To be deprecated" with **no removal date set** (per https://www.home-assistant.io/blog/2026/10/13/device-info-class/). All six of this integration's platforms currently use the plain-dict form. | Supported today; no forced migration date exists yet. Tracked as a future, undated proposal only. |
| (d) Repair-issue refresh APIs and manifest categories | `2026.11` adds repair-issue `config_entry_id`/refresh APIs (https://www.home-assistant.io/blog/2026/10/28/issue-registry-refresh/) and optional manifest `categories` (https://www.home-assistant.io/blog/2026/10/20/integration-categories/); this integration's package-tracking purpose matches the `productivity_information` category, but `manifest.json` does not yet set any `categories` value. | Optional, additive manifest metadata; not required for current operation. |
| (e) Flow-result step IDs and setup/unload return types | All of this integration's flow results already use explicit step IDs, consistent with https://www.home-assistant.io/blog/2026/10/23/flow-results-require-step-id/. Custom-integration `async_setup_entry`/`async_unload_entry` boolean returns remain supported per https://www.home-assistant.io/blog/2026/10/23/config-entry-methods-return-none/. | No action needed; current code already matches current guidance on both points. |
| (f) `hacs.json` minimum HA version | `hacs.json` declares a minimum HA version of `2025.5.0`. CI only exercises `2026.11.0`; the stated `2025.5.0` floor is **not verified** by this or any other check in this repository. | Unverified compatibility floor; not addressed by this documentation-only update. |

### Static code review against current quality-scale guidance

Code inspection (no live HA instance) found:

- `manifest.json` declares `config_flow: true`, required dependencies,
  `integration_type: service`, and `iot_class: cloud_polling`.
- The integration uses a typed `ConfigEntry.runtime_data`, a coordinator with
  a first-refresh/lifecycle pattern and `ConfigEntryNotReady` /
  `ConfigEntryAuthFailed` handling, a config flow with reconfigure and reauth
  steps (`async_step_reconfigure`, `async_step_reauth`/
  `async_step_reauth_confirm`), diagnostics, and repair flows. There is **no**
  separate `OptionsFlow` handler in `config_flow.py`.
- Coordinator-backed platforms include calendar and event entities in
  addition to sensor/camera.
- Sensor and camera entities use entry-scoped unique IDs; producer-side
  attribute tests exist (`tests/test_sensor.py` and related).
- PR #12 adds manifest contract tests and an independent two-entry
  reload/state-preservation test (see "Isolated environment and safety"
  above).

These findings match patterns documented by the current quality-scale docs
(`ConfigEntry.runtime_data`, options/reconfigure, diagnostics redaction,
tests, entity metadata) cited above, but do **not** assert any
release-specific deprecation unless it is explicitly documented in a source
listed above. This is code-inspection and isolated-test evidence only: there
is no live HA startup test here, and no companion-card source or browser
test tooling is available in this repository (consistent with the existing
"Isolated environment and safety" and test-status-matrix entries above).

### Test and runtime limitations (recap)

- No live HA startup test was run (`NOT_RUN` in the test status matrix).
- No companion-card source or browser/consumer test tooling is present in
  this repository (`NOT_RUN`).
- `web_fetch` to the rendered `home-assistant.io` pages was blocked in this
  environment; the release-announcement **source markdown** was instead read
  via the GitHub API at commit `9ec83f84c9d11169bd6824ee0a54800033822a24`
  (see table above), while the rendered blog page and the separate
  changelog page were cited by URL only, not read, and this remains a
  limited, non-exhaustive review.
- This audit distinguishes three evidence classes used throughout this
  document: **static review** (source/docs inspection without execution),
  **local tests** (tox/pytest/pre-commit run in this environment), and
  **remote gated checks** (GitHub Actions runs that returned
  `action_required` with zero jobs, which are neither pass nor fail).

### Ranked, qualified feature-opportunity proposals (not implemented)

The following are **proposals only**, requiring a separate SDD cycle
(`specs/NNN-*.md` + `specs/NNN-verification.md`) before any implementation;
none of this work was started as part of this documentation update.

1. **Adopt `ConfigEntry.runtime_data` consistently where not yet used** (if
   any remaining module still stores runtime state outside it). Official
   basis: `contributors.home-assistant.io` quality-scale docs (`main`
   `ed61b5a`) and `developers.home-assistant` config-entry docs (`master`
   `50b5188`). Estimated risk: low (if already fully adopted, this is a
   no-op); effort: low; compatibility: no entity/storage schema change
   expected. Needs confirmation of current coverage before scoping.
2. **Expand reauth/reconfigure flow test coverage** for any auth paths not
   yet covered by isolated tests, per the same quality-scale reauth/
   reconfigure rule. Risk: low; effort: low-to-medium; compatibility: test-only,
   no runtime change.
3. **Review diagnostics redaction completeness** against the quality-scale
   diagnostics rule, to confirm no sensitive IMAP/17track field is
   unredacted. Risk: medium (requires careful review to avoid both
   under- and over-redaction); effort: low; compatibility: diagnostics-only,
   no entity/storage change.
4. **Migrate `config_flow.py:915` off `CONN_CLASS_CLOUD_POLL`** before its
   `2027.5.0` removal (finding (a) above). Official basis: HA Core
   `2026.11.0` tagged `homeassistant/config_entries.py` and upstream HA's own
   `dev`-branch removal (commit `d9cd889`, home-assistant/core#1546). Risk:
   low (constant is deprecated, not yet removed); effort: low; compatibility:
   no entity/storage/behavior change expected, config-flow metadata only.
   Not urgent for `2026.11.0`, but should not slip past `2027.5.0`.
5. **Add an explicit `config_entry=` kwarg to the coordinator's
   `super().__init__()` call** (finding (b) above), to remove the
   assign-then-override pattern in `coordinator.py` and its matching test
   workaround. Risk: low-to-medium (touches coordinator initialization, a
   shared/base module requiring explicit sign-off per `AGENTS.md`); effort:
   low; compatibility: no entity/storage change expected, but requires full
   regression-test coverage before merge because it is a shared-module
   change. This is a proposed fix for a latent fragility, not a confirmed
   defect.
6. **Set a `categories` value (e.g. `productivity_information`) in
   `manifest.json`** (finding (d) above). Official basis:
   https://www.home-assistant.io/blog/2026/10/20/integration-categories/.
   Risk: very low (additive, optional manifest metadata); effort: low;
   compatibility: no runtime behavior change.

These rankings are qualified by the static-review-only nature of this audit;
each proposal requires its own requirements/design/plan/tasks cycle and
explicit human review before any code change, per the SDD-Light policy in
`AGENTS.md` section 5.1.

## Upstream audit pointer (assessment/planning only, 2026-11-07)

The detailed prioritized canonical-upstream audit was posted in the
[PR #12 response thread](https://github.com/BMWfan/Home-Assistant-Mail-And-Packages/pull/12#issuecomment-6707075190);
issue #13 remains the tracking issue. It is assessment/planning only, not an
exhaustive 178-commit review or full card/attribute diff. The verified source
and history facts are recorded here as a concise pointer:

- The canonical public non-fork repository identified in GitHub metadata is
  `moralmunky/Home-Assistant-Mail-And-Packages`.
- Upstream default branch `master` is at `f2a8ecfedb5627a8e7a1871ce7948e50c77e1142`;
  the active development branch `dev` is at
  `0eec4af19924a21607761e0bb1d6a741a66e2733`.
- Upstream's latest stable release is `0.6.9` at
  `b2d33107a8b5de79bfca5ef985f2e8c3fa6875cd`; latest beta is `0.6.10-b0` at
  `57d218d0413237d2cc878d5252f8f2b66c575a03`.
- This fork's relevant base `test/all-features` is at
  `71d2111e23de1ec0ca641a310d74cfb2c4c25237`; this PR (#12) head at audit
  start was `1b32ce5b7383f395f99a8e6ab86de0619ebcd94c`.
- Against upstream `dev`, merge-base is
  `115b21305cb1a99748b5d3e41be1dfee5a62656f`; full-history
  `git rev-list --left-right --count fork...dev` is `178 156`. Against
  upstream `master`, merge-base is
  `1867b7322878c72e31f2ff7db8ae9e9cb55a7dc8` and the counts are `461 5`.
- This is prioritized assessment/planning, not an exhaustive review of all
  178 commits or a full companion-card/entity attribute diff. **No upstream
  code has been imported**, and no integration work on upstream changes will
  start until SPEC-001 is accepted by human review. No production Home
  Assistant, mailbox, or secrets were accessed.

## Next actions

- An authorized repository user must resolve/inspect the Actions gate for corrected code/config SHA `68eb8c4`: CI, Validation, Pre-commit, Autolabeler, and PR lint all returned `action_required` with zero jobs and no API-exposed cause. CodeQL is not configured for PRs targeting `test/all-features`; changing its trigger scope requires maintainer review.
- CI #33 already verifies the pip-audit gate and tox on `b48bdee`; retain its no-suppressions policy and revisit the helper's intentional no-deps compatibility gap separately if desired.
- The retrieved CI #33 logs explicitly show the audit and pytest results. Do not infer a cause for the earlier 404 job.
- Obtain human review of the Draft specification and implementation. GitHub currently reports PR #12 as open but not Draft; no PR state change was made. Merge remains manual.
- The detailed upstream audit is posted in the PR #12 response thread; issue #13 remains the tracking issue (see "Upstream audit pointer" above). SPEC-001 must be accepted by human review before any upstream change is implemented.
