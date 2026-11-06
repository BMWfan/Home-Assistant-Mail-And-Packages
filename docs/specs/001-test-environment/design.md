# SPEC-001: Test environment design

## Environment

GitHub Actions uses Python 3.14 and tox to create separate environments for
pytest, Ruff, and mypy. The pytest dependency list pins Home Assistant to
2026.11.0; the integration's production manifest and runtime dependencies are
unchanged. The existing validation workflow separately runs HACS and hassfest
checks. The available Home Assistant pytest helper release pins HA 2026.10.4,
so tox installs that pinned helper without dependencies; its test-time
dependencies are declared alongside the HA pin. The test command imports HA
before pytest plugin discovery so HA's HTTP client compatibility layer is
initialized before the helper imports HTTP client libraries. It also supplies
the logger cleanup callback removed in HA 2026.11 for the older helper release.

## Deterministic and isolated tests

Tests use the checked-in `.eml` samples under `tests/test_emails/`, fake config
entries, and fixtures that replace the integration's IMAP clients. The
multi-entry regression test sets up two entries with different fake hosts, then
reloads one and verifies both sets of sensors and runtime data remain intact.
Test setup does not require credentials, a production Home Assistant instance,
or a real mail server.

## Compatibility, migration, and rollback

This change updates only the test and development environment. It does not
change the integration's config-entry schema, production dependencies, or
stored user data, so no user migration is required. Python 3.14 and Home
Assistant 2026.11.0 are the CI compatibility target for this spec; they do not
by themselves change the integration's declared support policy.

To roll back, revert the test environment, test-fixture, and documentation
changes. No production data or Home Assistant instance needs restoration.
