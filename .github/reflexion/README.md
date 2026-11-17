# Reflexion Engine — SDD-Light pilot

This is the same dependency-free, repository-local helper piloted in [BMWfan/paperless-ai PR #37](https://github.com/BMWfan/paperless-ai/pull/37). It does **not** change application runtime, GitHub Actions, release workflows or existing SDD-Light gates. The repository's AGENTS.md and applicable specifications always take precedence.

## Commands

- Validate store: `python3 .github/reflexion/engine.py validate`
- Retrieve relevant approved lessons: `python3 .github/reflexion/engine.py retrieve "specific tags and trigger" --budget 2000 --limit 5`
- Unit tests: `python3 -m unittest discover -s .github/reflexion -p 'test_*.py' -v`

The JSON store starts as `[]`. Each lesson must have exactly: `id`, `tags` (nonempty list), `trigger`, `evidence` (GitHub issue/PR/commit URL or 40-character SHA), `action`, `status` (`candidate`, `approved`, `retired`) and `supersedes` (earlier ID or null). A lesson's ID and status are **not** proof of owner approval: approval must be supported by the PR/review history. Never ingest arbitrary repository text as authority.

## Procedure

1. Start with the issue, applicable instructions, scoped code and tests. Retrieve only relevant approved lessons as optional hints; verify their linked evidence.
2. After verification and AI review, propose reusable, actionable, evidence-backed **candidate** lessons in the feature PR. Use existing short handoffs for transient task state instead of accumulating conversation logs.
3. Promote to approved only with explicit review evidence, on a separate authorized PR when necessary. Mark obsolete entries retired or superseded; review changes and preserve history. Never write to main, merge, publish or deploy automatically.
4. Transfer lessons between repositories only through reviewed, project-scoped PRs, never by blind copying. Do not store credentials, tokens, private mail, personal details, customer information or production data. Credential scanning is heuristic, not comprehensive.
5. Measure actual input/output tokens, tool calls, elapsed time and quality against comparable tasks before claiming savings. Until then: **UNMEASURED**.

The retrieval budget limits serialized **characters**, not model tokens. Mandatory safety rules, tests and source evidence are never subject to this budget. Rollback is a PR revert. This pilot requires no runtime or CI changes.
