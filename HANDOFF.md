# Handoff — Mail and Packages (Docker Compose dev setup)

Branch: `feature/docker-devcontainer`. This document is for continuing
development in a plain Docker container (official HA image via
`docker-compose`, **no HAOS/Supervisor**) instead of the existing VS Code
devcontainer (`.devcontainer.json`/`DEVCONTAINER.md`, which pip-installs HA
core directly) or the live production instance this integration was
previously tested against.

For the detailed history of *why* the code looks the way it does (the IMAP
timeout saga, the 17track carrier-collision fixes, the DHL auth chain
reverse-engineering, etc.), see `HANDOFF_HISTORY.md` — this file stays
focused on "how do I get a working dev environment and what will bite me."

## 1. What this integration does

Connects to one IMAP mailbox (Outlook/Office365, Gmail, or generic IMAP)
and scans **today's** emails for shipping/delivery notifications from ~25
supported carriers (DHL, UPS, USPS, FedEx, GLS, Evri/Hermes, Amazon, and
more), producing:

- Per-carrier sensors: packages in transit, delivered today, exceptions.
- A "universal" tracking sensor (`universal_packages`) that extracts raw
  tracking numbers from any email via regex, independent of carrier-specific
  sender/subject parsing — the fallback path for carriers/templates the
  per-carrier logic doesn't cover.
- Optional [17track.net](https://17track.net) API integration: once a
  tracking number is known, 17track supplies authoritative status, ETA, and
  full event history (independent of what the source email said) — this is
  what backs the companion Lovelace card's shipment timeline.
- USPS Informed Delivery mail-piece images (rotating GIF).
- DHL "Briefankündigung" (letter preview) images, via a separate
  undocumented DHL app API (PKCE OAuth, not part of the main IMAP flow).
- Amazon order tracking (arrival-today / delivered-today / delayed),
  camera entity for the delivery driver photo, OTP delivery codes.
- A persistent "delivered history" store (survives restarts, independent of the
  today-only per-scan counters) — see `packages_history` sensor.
- Manual shipment tracking (`mail_and_packages.add_tracking` /
  `remove_tracking` services) for orders no email ever mentions — added
  2026-07-26, gated behind a 17track API key since that's what actually
  fetches status for a manually-entered number.

Companion Lovelace card (separate repo, `mail-packages-card`,
`feat/shipment-list-redesign` branch) renders all of the above; not part of
this repo, but the sensor *attribute shapes* (`tracking_details`,
`history` per shipment, `packages_history_details`, etc.) are effectively a
contract between the two — changing a key name here breaks the card
silently (no schema validation anywhere).

## 2. Current state — what works / what's untested here

Everything below was live-verified against the **production** HA instance
(`homeassistant.mackcloud.de`) via HACS prereleases, over many iterations —
see `HANDOFF_HISTORY.md` and `git log` for the blow-by-blow. As of the last
commit on `test/all-features` before this branch:

**Working (live-verified on production):**
- Core IMAP scan (multi-folder, batched fetch, reconnect-on-timeout).
- Universal tracking number extraction + 17track enrichment (status, ETA,
  full event history, carrier auto-correction via 17track's own resolution).
- DHL Briefankündigung image fetch (full PKCE + grantToken→AccessToken
  exchange, see pitfalls below).
- Amazon order/delivery detection (German subjects, `amazon.de` sender).
- Manual add/remove tracking (`add_tracking`/`remove_tracking` services),
  including carrier auto-detection from the number's own format and history
  purge on removal (incl. Amazon `order`-keyed history records).
- Repairs UI entries for auth failures (DHL, Office365 OAuth, 17track).

**Verified in Docker since (2026-08-06):**
- Fresh `docker compose up` starts cleanly, zero errors, integration loads.
  Dependencies are complete: an AST cross-check of every external import
  against `manifest.json` found no gaps beyond the `anyio` one already
  fixed here, so the "there may be others" worry is settled.
- **`pytest` runs.** Full suite: **657 passed in ~77s**. Recipe (the HA
  image has no test deps, so use a throwaway container):
  ```
  docker compose run --rm --no-deps -v $PWD:/repo -w /repo --entrypoint sh homeassistant -c "
    pip install -q pytest pytest-asyncio pytest-aiohttp \
      pytest-homeassistant-custom-component freezegun aioresponses
    python -m pytest tests/ --no-cov"
  ```
  `--no-cov` matters: the 90% fail-under threshold aborts any partial run.
- A fresh config entry used to crash setup with `KeyError: 'resources'`
  (fixed + covered here). Only new installs were affected; migrated
  entries carry the legacy key, which is also why no test caught it.

**Still NOT verified in a fresh/Docker environment:**
- OAuth flows (Microsoft/Google) — never tested outside the production
  instance's stable public URL; a throwaway Docker container without a
  reachable callback URL likely can't complete them. Use Password auth
  (IMAP app password) for Docker dev.
- Whether the `debugpy:` block in `config/configuration.yaml` actually
  works through Docker (port 5678 is published in `docker-compose.yml`,
  untested).

**Known-open items** (not blocking, just not done):
- No automated test coverage for the manual-tracking feature's interaction
  with `_process_manual_tracking`'s 17track enrichment path (unit tests
  exist for the simpler pieces; the full add→enrich→deliver→history
  transition isn't covered).
- `pytest` could not be run in the original Windows dev environment. This is
  resolved — see the Docker recipe in §2; ignore the `~/.venvs/mnp` trail in
  `HANDOFF_HISTORY.md`.
- The subfolder test covers the sequential select+search fallback only; the
  ESEARCH path (servers advertising MULTISEARCH) is still uncovered.
- The card contract test pins the attribute keys on the *producing* side
  only — nothing verifies the card actually reads them under those names.
- **Unresolved suspicion:** the IMAP search cache hangs off the connection
  object (`account._search_cache`) and is documented as "per-scan". With the
  long-lived, reconnect-on-timeout connections this integration uses, it may
  outlive a scan and keep serving a stale empty result. It was *not* the
  cause of the Amazon miss (that was folder scope, see §6), but nobody has
  confirmed the cache is actually reset between scans.

## 3. Entity IDs — how they're built

Entity IDs are **not static** — they're derived from the mailbox host you
configure, at setup time, via HA's normal slugify-the-friendly-name
mechanism. Pattern observed throughout testing (host `outlook.office365.com`):

```
sensor.<host_with_dots_as_underscores>_mail_<sensor_type>
```

e.g. `sensor.outlook_office365_com_mail_universal_packages`,
`sensor.outlook_office365_com_mail_amazon_packages`,
`sensor.outlook_office365_com_mail_packages_history`. Other platforms follow
the same host-prefixed pattern: `camera.<host>_<carrier>_camera`,
`button.<host>_scan_now`, `calendar.<host>_...`. **A different mailbox host
in Docker will produce different entity IDs than whatever you're comparing
against from production** — don't assume entity IDs are portable between
environments; look them up fresh (`ha_search`/Developer Tools > States, or
just check `sensor.py`'s `unique_id`/`type` construction) rather than
hardcoding the ones from prior sessions.

`config_flow.py` is entirely UI-driven (`config_flow: true`) — there is no
YAML platform config, so there's no static entity-id-to-config mapping to
grep for either; it only exists after you complete the wizard once.

## 4. External dependencies — does this even run without them?

**The integration loads and the config flow works with zero external
dependencies** — HA will show "Add Integration" and the wizard regardless.
But it does nothing useful without:

- **An IMAP mailbox** (real one, reachable from wherever Docker runs) —
  this is not mockable/fakeable within the integration itself; there's no
  offline/demo mode. Use a real account (Outlook/Gmail/other IMAP) with app
  password auth. See `config/secrets.yaml.example` for the checklist.
- **17track API key** (optional, free tier) — without it, status comes only
  from parsing email text (works, but no ETA/history/carrier
  auto-correction, and the manual add/remove feature refuses to enrich
  numbers at all — logs a warning and does nothing).
- **DHL Briefankündigung** — only relevant if you enable it; needs a live
  browser-based PKCE login against `login.dhl.de` from the config flow, not
  pre-seedable. Skip unless you're specifically touching that code path.
- **Network egress from the container** to whichever IMAP host, 17track,
  and (if enabled) DHL/Microsoft/Google endpoints — nothing is proxied or
  configurable beyond the mailbox's own host/port.

Given all of that, **realistic Docker dev testing needs a real test mailbox
you're willing to point at**, ideally one that actually receives some
shipping-adjacent mail (or one you can forward test emails into) — there is
no synthetic/replay fixture for the IMAP layer in this repo. `tests/` uses
mocked IMAP responses for unit tests, but there's no equivalent for manual
end-to-end poking.

## 5. How this was tested before (context, not a Docker recipe)

Every fix throughout this project's history was verified against the
**live production instance**, not a local dev environment:

1. Edit code, `python -m py_compile <file>` (no `ruff`/`black` available in
   the Windows shell used) as a syntax gate.
2. Commit + push to `test/all-features`.
3. `gh api repos/BMWfan/Home-Assistant-Mail-And-Packages/releases -f
   tag_name=vX.Y.Z-testN ...` (see pitfall below — `gh release create`
   resolves to the wrong repo on this machine).
4. Install via HA's HACS MCP tool
   (`ha_manage_hacs(action="download", version="vX.Y.Z-testN")`), which
   needs ~60-90s after tag creation before HACS's release cache picks it up.
5. `ha_restart`, wait 1-5 min, trigger a scan
   (`button.<host>_scan_now`), inspect sensor attributes directly via HA's
   API.

This is slow (minutes per iteration) and — as literally happened during
this session — the live instance became briefly unreachable under
DEBUG-level IMAP logging load. **That's the whole motivation for this
Docker branch**: fast, disposable, isolated iteration instead of testing
against the one production HA instance the user actually depends on.

## 6. Non-obvious pitfalls (the valuable part)

- **`anyio` was an undeclared dependency** (see §2) — always cross-check
  `grep -rhoE "^\s*(import|from) [a-zA-Z_][a-zA-Z0-9_]*"` across
  `custom_components/mail_and_packages` against `manifest.json`'s
  `requirements` after adding any new import; nothing catches this
  automatically, and it silently works if your dev Python env happens to
  already have the package from something else.
- **IMAP SEARCH does not descend into subfolders.** If a mail rule files
  carrier mail into e.g. `INBOX/Online-Shops/Amazon`, a scan configured for
  `INBOX` finds nothing — and it looks *exactly* like broken carrier
  detection. This is what actually caused the "Amazon mails are ignored"
  report (2026-08-06): subject, sender, language filter, domain config and
  the generated IMAP query were all verified correct; the mail simply sat
  outside the searched folder. **Check the configured folder(s) against the
  mailbox's rules before touching detection code.** `CONF_FOLDER` accepts a
  list (the config flow renders a multi-select and stores a string for one
  folder, a list for several), so the fix is to select every relevant folder
  rather than moving mail or narrowing the scan.
- **`amazon_packages` / `amazon_delivered` are TODAY-ONLY counters, reset
  each scan against the current date** — an Amazon order that shipped a few
  days ago and hasn't had a *fresh* email today will correctly show `0`.
  This looks exactly like a detection bug (and was reported as one during
  this session) but is the integration's actual by-design scope (see the
  README: "creates sensors tracking mail and packages scheduled for
  delivery **today**"). Before chasing an "Amazon not detected" report,
  check the actual email dates first — `packages_history` (the persistent
  delivered-history store) is the only place that survives past today.
- **`gh release create --target <branch>` resolves to the wrong repo** on
  this dev machine (picks the upstream fork parent, not `origin`) even
  after granting the `workflow` OAuth scope — misleading "workflow scope
  may be required" error. Workaround: `gh api
  repos/<owner>/<repo>/releases -f tag_name=... -f
  target_commitish=<branch> ...` directly, every time.
- **HACS's release-list cache needs ~60-90s** after a GitHub release is
  created before `ha_manage_hacs(action="download", version=...)` will
  accept the new tag — the first attempt right after creating a release
  reliably 404s.
- **17track's own carrier resolution overrides text-based guessing, and
  should** — a bare 14-digit tracking number is ambiguous between DPD (DE)
  and Hermes/Evri (DE) from email text alone; 17track's own carrier
  database match (`track_info.tracking.providers[0].provider.key`) is
  authoritative and can disagree with (and correct) the regex-based first
  guess. See `seventeen_track.py`'s `_RESOLVED_CARRIER_NAMES` /
  `universal.py`'s `_enrich_with_17track`.
- **DHL Briefankündigung needs TWO separate auth tokens**, not one: the
  advices API uses a `dhli` login cookie (OAuth/PKCE against
  `login.dhl.de`), but image *downloads* need a completely different
  `AccessToken` cookie obtained by exchanging a short-lived `grantToken`
  (from the advices response) via `POST
  briefankuendigung.enplify.dhl.de/pdapp-web/access-tokens` with body
  `{"grant_token": ...}` (snake_case; camelCase 400s) — the real token
  comes back in a `Set-Cookie` header on a `204` response, not the body.
  Reusing the `dhli` cookie for images just 401s forever.
- **German dates (`DD.MM.YYYY`) get silently misread as US `MM.DD.YYYY`**
  by naive `new Date(...)`/`datetime.date.fromisoformat()` calls — this bit
  three separate places independently (Python `calendar.py`, the JS card's
  letter-date rendering) before being fixed with explicit day/month
  parsing. If you see a delivery date that's off by a transposed
  day/month, this is almost certainly why — check for a raw `Date(...)`
  call on a `DD.MM.YYYY` string first.
- **A single aggregate DEBUG log line can look like a bug that isn't one**
  — an early investigation this session misdiagnosed a "multi-folder IMAP
  scan only checks one folder" bug from log evidence; the coordinator was
  actually scanning all folders correctly, it just logged the *query* once
  per cycle rather than once per folder, making the log read like
  single-folder behavior. Verify against actual returned tracking-number
  content, not just log line counts, before assuming an architecture bug.
- **HA's `logger.set_level` debug logging on this integration is
  extremely verbose** (dumps full raw IMAP `FETCH` responses, i.e. entire
  email bodies, into the log) — a single scan cycle can produce 800KB+ of
  log text. Fine for a quick targeted check, but querying that log back
  through a tool with a response-size limit will blow through it; grep/jq
  the raw log file instead of asking a tool to return it whole, and turn
  debug back off (`logger.set_level: warning`) once done — it also visibly
  slowed the live HA instance down during this session.
- **`CalendarEntity` mixing all-day (`date`) and timed (`datetime`) events
  breaks HA core's internal comparisons** with a silent `TypeError` inside
  HA core (not raised to the integration's own logs in an obvious way) —
  manifests as a calendar that's permanently empty despite `_build_events()`
  clearly producing events. Fix is a normalizer that promotes bare `date`
  to local-midnight `datetime` before any `>`/`<` comparison. Any future
  calendar work here needs to keep doing this.

## 7. Credentials / secrets

See `config/secrets.yaml.example` — copy to `config/secrets.yaml` (already
git-ignored) and fill in before starting the wizard. **This integration's
config flow is 100% UI-driven**; it does not read `secrets.yaml` itself —
the example file is a checklist to have values ready, not a file this code
consumes directly.

## 8. Quick start (Docker Compose)

```bash
cp config/secrets.yaml.example config/secrets.yaml   # fill in real values
docker compose up
# open http://localhost:8123, complete HA's own onboarding,
# then Settings > Devices & Services > Add Integration > Mail and Packages
```

`docker-compose.yml` bind-mounts `custom_components/mail_and_packages/`
(single source of truth, same code the tests and the non-Docker devcontainer
use) into `/config/custom_components/mail_and_packages` inside the official
`ghcr.io/home-assistant/home-assistant:stable` image — no code duplication,
no symlinks, no HAOS/Supervisor involved.

### Companion card (separate repo)

The Lovelace card that renders this integration's sensors
(`Home-Assistant-Mail-And-Packages-Custom-Card`, branch
`feat/shipment-list-redesign`, own `feature/docker-devcontainer` branch
there too) is a **different git repository**, not a subfolder here. Clone
it as a sibling directory (default assumed name: `mail-packages-card`;
override via `.env` — copy `.env.example` and set `CARD_DIST_PATH` if you
cloned it under its full GitHub name or elsewhere). `docker-compose.yml`
mounts its `dist/` read-only into `/config/www/mail-packages-card`.

`docker compose up` will **fail to start** if that path doesn't exist
(bind-mount sources must exist) — either clone the card repo first, or
comment out that volume line in `docker-compose.yml` if you only need the
integration/backend side (sensors, services) and not the card UI.

Once HA is up, the card still needs registering as a dashboard resource
once (HA doesn't auto-discover files under `www/`): Settings > Dashboards
> (⋮) > Resources > Add Resource >
`/local/mail-packages-card/Home-Assistant-Mail-And-Packages-Custom-Card.js`,
type **JavaScript Module** — then add the card itself via
`type: custom:mail-and-packages-card` on any dashboard.
