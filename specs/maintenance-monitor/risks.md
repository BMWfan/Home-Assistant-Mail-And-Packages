# Risks

Public API/feed failures halt state advancement. Bounded source windows can miss older history; report is not a full security inventory. State artifacts expire and config/ref changes rebaseline. Findings are conservative observations needing human assessment. Scheduled runs and artifact storage use GitHub Actions account allowance. Private shared-action access policy may require owner configuration; never add broad credentials silently.
