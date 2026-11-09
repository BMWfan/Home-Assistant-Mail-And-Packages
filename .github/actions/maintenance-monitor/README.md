# Shared SDD-Light maintenance monitor, phase 1

This action is report-only. It performs GET requests to public GitHub APIs and
explicit official feeds, writes reports and stores a successful comparison state
as an Actions artifact. It never creates issues, starts agents, merges, releases
or contacts production Home Assistant. No Copilot subscription is needed.

Independent projects do not need a fork or upstream remote. Configure `release`,
`feed`, `advisory` sources; `upstream` is optional and requires an explicit repo
and ref. Public sources only; redirect following is disabled before credentials
can reach another host. HTTP errors, oversized responses, invalid XML/JSON and
restore failures fail the job. Rate-limits/5xx retry at most three attempts with
bounded backoff; retry-after over 30 seconds reports a failure for a later run.
No error body or token is included in reports. TLS verification remains enabled.

## Adoption

Use the project config `.github/maintenance-monitor.yml` and a workflow containing
checkout, then this action pinned to its full reviewed SHA:

```yaml
permissions:
  contents: read
  actions: read
# within a job, after checkout (harden-runner first on hosted runners):
# - uses: BMWfan/Home-Assistant-Mail-And-Packages/.github/actions/maintenance-monitor@<reviewed-40-character-SHA>
#   with:
#     config: .github/maintenance-monitor.yml
#     token: ${{ github.token }}
```

A minimal YAML config (no upstream assumption):

```yaml
version: 1
project: example-card
mode: report
create_issues: false
delegate: false
sources:
  - id: ha-core
    kind: release
    repository: home-assistant/core
    relevance: Integration APIs and compatibility tests
```

The provided workflows use workflow_dispatch and a weekly schedule. Source and
adoption development branches also run read-only reports on push to validate the
new workflow before merge; schedules run only once merged into the default branch.
For private cross-repo use, allow this action in source repository Actions access
settings if needed. Do not add a broad PAT; prefer approved repository access or
an organization-owned shared action repository. A policy block must be reported.
GitHub-hosted Actions minutes and artifact storage can incur account charges.

## Report and persistence

`report.json` records exact source versions/SHAs, citations, timestamps, relevance,
priority, decision and uncertainty. `report.md` is attached and shown in the run
summary. New advisory observations are high priority; they are **unconfirmed**
package matches, not claims about the installed version. All decisions start as
`defer` pending human review; risk/effort remain explicitly unknown. This monitor
reports opportunities for compatibility/regression work and does not infer that
a title or feed item proves a breaking change affects this integration.

Latest stable release adapters inspect up to 20 recent releases, ignoring draft
and prerelease flags. Feed/advisory adapters inspect up to 20 items. This is a
bounded maintenance signal, not an exhaustive historical security audit or a
semantic code-diff analyzer. No installed-version, Docker digest, or automatic
GitHub Actions upgrade is inferred. Configure release/advisory sources for the
specific dependencies/toolchain; production inventory stays out of the monitor.
The official HA developer blog currently lives at
`https://contributors.home-assistant.io/blog/rss.xml`.

State is namespaced by repository, ref and exact config bytes. It is restored
only from the matching non-expired artifact; none means a clearly documented
baseline. A config/ref change deliberately starts a new baseline. Identical
snapshots generate no new observations; up to 2,000 fingerprints/source are
retained. State advances only after **all** sources succeed. Restore failures
are fatal instead of silently resetting history. State expires after 90 days;
reports after 30 days; expired state means a fresh baseline, never an assumed
review. Snapshot persistence means *observed*, not *human-approved*; manual
acceptance is independent. Fork upstream SHA observations are only collected
when explicitly configured; current run SHA is in the Actions run metadata.

Download `maintenance-report` from a successful run; inspect source links and
uncertainty before choosing adopt/adapt/defer/reject in your normal SDD process.
Disable by disabling the workflow in Actions, or remove schedule/push triggers.
Delete stored artifacts to intentionally rebaseline. Roll back by restoring the
previous pinned action SHA/config. Issue creation and agent delegation are
unsupported here; enabling those config flags fails before any request.

## Tests

```sh
python -m pip install PyYAML==6.0.3 defusedxml==0.7.1
python -m unittest discover -s tests_maintenance -v
python .github/actions/maintenance-monitor/monitor.py --config .github/maintenance-monitor.yml
```

The mocked suite covers fork/non-fork, stable filtering, deduplication, config
identity, source/restore failures, partial failure without state advancement,
rate-limit behavior, advisory uncertainty, citation validation and redirect safety.
