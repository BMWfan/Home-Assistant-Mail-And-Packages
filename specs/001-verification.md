# SPEC-001 — Read-only inventory and verification baseline

**Evidence date:** 2026-11-06. **Status:** Repository inspection complete for selected files; no tests executed. All findings below describe configuration or historical notes, not fresh PASS results.

## Files inspected

- `AGENTS.md`: existing Docker dev workflow, pytest, Ruff, mypy and production isolation instructions.
- `docker-compose.yml`: HA image `ghcr.io/home-assistant/home-assistant:stable`, port 8123, debug port 5678, live source bind mount, companion card dist bind mount, health check.
- `tox.ini`: `envlist = py314, lint, format, mypy`.
- `.github/workflows/ci.yml`: Python 3.14, `tox`, coverage upload, SHA-pinned actions, harden-runner in egress audit mode.
- `requirements_test.txt`: HA custom component pytest plugin with lower bound; Home Assistant and other dependencies unpinned.
- `tests/conftest.py`: HA fixture, mocked IMAP, config-entry factory.
- `HANDOFF.md`: historical Docker test report (657 passed in August 2026), known integration gaps. **Historical result is not a current test pass.**
- `.env.example`: optional HA onboarding credentials and companion card path.

## Actionable findings, ordered by impact

1. **High — CI includes a mutating formatting environment.** `tox.ini` declares `format` in default `envlist` and `[testenv:format]` runs `ruff check --fix .` and `ruff format .`. CI must check formatting without silently editing the checkout. Keep an explicit opt-in formatting command for developers; do not make it part of required CI.
2. **High — CI may hide skipped environments.** `skip_missing_interpreters = True` can allow missing interpreters to be skipped. Verify expected Python 3.14 and check whether all mandatory environments actually execute.
3. **Medium — non-reproducible Home Assistant version.** `docker-compose.yml` uses `:stable`; `requirements_test.txt` has unpinned HA and plugin versions. For 2026.11 compatibility, record exact image digest and resolved dependencies; consider a pinned CI test target while retaining a separate latest-stable compatibility job.
4. **Medium — Docker host exposure.** Ports `8123:8123` and `5678:5678` are published on all interfaces by default. Prefer `127.0.0.1:8123:8123` and avoid exposing debugpy unless explicitly enabled. Evaluate existing remote development use before changing mappings.
5. **Medium — card integration gap.** `HANDOFF.md` states the producer-side attribute contract is tested, but not the consumer card. Verify current companion-card repository tests before adding contract/browser checks.
6. **Medium — historical test gaps.** `HANDOFF.md` identifies manual tracking add→enrich→deliver→history, IMAP ESEARCH and search-cache lifetime as unverified. Check whether subsequent tests already cover them before writing new ones.
7. **Unknown — CodeQL configuration.** README references CodeQL, but the guessed workflow path `.github/workflows/codeql.yml` was not found. This does not establish CodeQL is absent; inspect all workflow filenames before drawing a conclusion.
8. **Unknown — existing secret/dependency scanning.** No conclusion until workflows and GitHub settings have been inventoried.

## Test status matrix

| Check | Current status | Evidence needed |
|---|---|---|
| pytest on Python 3.14 | NOT_RUN | Actual command, count and exit code |
| Ruff lint | NOT_RUN | Actual command and exit code |
| Ruff formatting check | NOT_RUN | Actual command and exit code |
| mypy | NOT_RUN | Actual command and exit code |
| HA 2026.11 startup | NOT_RUN | Image version/digest and health log |
| HA reload and multiple config entries | NOT_RUN | Integration test and state assertions |
| Manual tracking and 17TRACK | NOT_RUN | Synthetic end-to-end fixtures |
| Card consumer contract | NOT_RUN | Companion repo tests |
| CodeQL/secret/dependency checks | NOT_VERIFIED | Actual workflow and settings inventory |

## AI and CI cost reporting

For each future implementation task, record the model/provider and reported input/output tokens *only if exposed by the runner*, CI duration, number of repair iterations, observed findings and false positives. Never estimate missing usage as measured data. Compare maintenance burden and defect detection before requiring an additional gate.

## Next actions

- Confirm all workflow names and current CI status.
- Replace mutating default `format` gate with read-only checks after validating tox behavior.
- Establish an exact-version test environment, without touching production.
- Run existing checks and attach actual evidence.
