# SPEC-001: Test environment and CI requirements

## Goal

Provide a repeatable, isolated validation environment for the Mail and Packages
integration against Home Assistant 2026.11 without accessing a production Home
Assistant instance or real mail accounts.

## Requirements

- Run the test suite on Python 3.14 with Home Assistant pinned to 2026.11.0.
- Run pytest, Ruff lint/format checks, mypy, HACS validation, and hassfest in CI.
- Keep Python checks in tox-managed virtual environments.
- Use deterministic email fixtures and mocked IMAP connections in tests.
- Cover startup of multiple config entries and reloading one without affecting
  the other.
- Document local commands and compatibility/rollback implications.

## Acceptance criteria

- CI identifies its Python and Home Assistant versions explicitly and runs the
  existing test, lint, type-check, and integration-validation commands.
- The multi-entry regression test completes without accessing a real mail
  server or Home Assistant instance.
- A contributor can run the Python checks locally using the documented steps.
