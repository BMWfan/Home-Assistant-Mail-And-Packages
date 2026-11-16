# Token-efficient SDD-Light — integration (#21)

This is supplementary guidance. AGENTS.md and existing SDD-Light specifications, security, CI, compatibility and explicit owner merge/release approvals take precedence. Never expose real IMAP credentials, private email contents, Home Assistant tokens or production data.

## Scoped Codex execution
1. Start with the approved issue, affected paths, applicable AGENTS instructions, nearest tests and existing spec. Locate filenames/symbols before reading whole files; expand whenever correctness or security requires it.
2. Prefer bounded searches, relevant source spans, changed-file diffs and failing test output over repository-wide dumps. Never hide or truncate an error and call a test passing.
3. Size proportionately: S is a focused issue/PR with evidence; M retains existing spec/checklist; L retains architecture, risk, verification and rollback artifacts required by the repository. No missing documentation to save tokens.
4. Handoff using [the compact template](spec-templates/handoff.md), normally at most 200 words, linking original issue, SHA, exact checks and blockers. Revalidate the revision and primary evidence when resuming.
5. Batch independent reads safely and avoid repeated identical retrieval. Do not introduce embeddings, memory services, new subscriptions or additional paid model runs just for token reduction.
6. Run scoped tests first and broaden on cross-repository, Home Assistant, HACS or security impact. Preserve IMAP parser coverage, synthetic fixtures, integration compatibility and workflow security requirements.
7. Measure actual input/output tokens, cached-input subset, calls, duration, tests, review defects and rework only when telemetry is available. Otherwise report **UNMEASURED**. Never infer savings from word counts or a single unpaired task.

No autonomous production deployment, prerelease, merge, stable release or credential-backed testing. Documentation-only work still requires CI, review and explicit owner merge approval.
