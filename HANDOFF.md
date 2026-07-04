# Handoff – Mail and Packages (branch `test/all-features`)

Stand: 2026-07-04 (aktualisiert)  
Aktuelles Release: **v0.5.5-test52** (prerelease auf GitHub)

> Abschnitte 2–3 unten dokumentieren die **historische** IMAP-Timeout-Saga (test11–17).
> Das Problem ist seit **test16 (Reconnect)** + **test21 (Batch-Fetch)** gelöst – siehe Abschnitt 0.
> Für den aktuellen Stand und den Deploy-Workflow **zuerst Abschnitt 0 lesen.**

---

## 0. Aktueller Stand (2026-07-03) — HIER ANFANGEN

### Gelöste Großbaustellen
- **IMAP-Scan-Timeout: gelöst.** Reconnect bei Stall (test16) + gebündelter Universal-Fetch
  (`FETCH_BATCH_SIZE = 25`, test21). Scan läuft jetzt live in ~6–15 s durch. `custom_days`
  auf **10** gesetzt (30 löste den Timeout erneut aus). Universal-Scanner-Fehltreffer
  (186 → 0) über `ORDERED_PATTERNS` in `shippers/universal.py` bereinigt.
- **DHL Briefankündigung (OAuth2 PKCE): eingerichtet und live bestätigt** (test24–28).
  - Auth-URL nutzt `/login/authorize` (nicht `/oauth2/v2.0/authorize` → 403).
  - App-User-Agent `DHLPaket_PROD/...` nötig (Akamai-Bot-Schutz).
  - `client_id` NICHT im Token-Body senden (Basic-Auth-Header reicht; sonst HTTP 400
    "cannot specify authorization in multiple ways").
  - `config_flow.py` behält DHL-Tokens über Reconfigure (liest Live-Tokens, nicht den
    Wizard-Start-Snapshot). Tokens/`id_token` in `diagnostics.py` redigiert.
  - Vollständige Details in `shippers/dhl_briefankundigung.py`.

### Diese Session (test29–test34) — DHL-Letter-Kosmetik + amazon.de-Erkennung

| Release | Änderung | Dateien | Live-verifiziert |
|---|---|---|---|
| test29 | Redundanten DATE-Sensor „DHL Letter Next Delivery" (`dhl_brief_naechster`) **entfernt** (zeigte „Unbekannt", kein Mehrwert; USPS-Vorbild hat auch kein Datum). Datum bleibt als Attribut pro Brief in `dhl_brief_letters`. | `const.py`, `coordinator.py`, `sensor.py` | ✅ Sensor weg, Zähler läuft |
| test30/31 | DHL-Letter-**Kamera zeigt „No Mail"-Platzhalter** (`mail_none.gif`) statt Leerlauf, wenn keine Briefe. (test30 nutzte fälschlich `image-no-mailpieces700.jpg` → test31 korrigiert.) | `camera.py` (`DhlBriefCamera.async_camera_image`) | ✅ Bild bestätigt |
| **test32** | **amazon.de-Erkennung gefixt (Kern-Bug).** (1) Absender-Sprachfilter entfernt → `order-update@amazon.de` (tatsächlicher Absender) wird nicht mehr verworfen. (2) Deutsche Betreffe „Versendet:"/„In Zustellung:" ergänzt. | `utils/amazon.py` (`amazon_email_addresses`, `DOMAIN_LANG_MAP`), `const.py` (`AMAZON_SHIPMENT_SUBJECT`) | ✅ `amazon_delivered` 0→1 |
| test33 | Amazon-**Fahrer-Foto**: starre 2-Host-Liste → Muster `*-prod-temp.s3.*.amazonaws.com` (alle Regionen). | `utils/amazon.py` (`_is_amazon_delivery_image_host`, `get_amazon_image_urls`) | ⚠️ kein aktuelles Foto zum Test (2023er nutzte `gb-prod-temp`, schon abgedeckt) |
| test34 | Deutsche **Amazon-Verzögerungs-Mails** (`amazon_exception`): Betreff „Lieferungsaktualisierung:", Text „verspätet"/„Verzögerung" (case-insensitive). | `const.py` (`AMAZON_EXCEPTION_SUBJECTS`/`_BODIES`), `shippers/amazon.py` (`_amazon_exception`) | ✅ lädt sauber, Delivered bleibt 1 (Sensor 0 bis Verzögerungs-Mail **von heute**) |
| test35 | Universal-Scanner: (a) **FedEx-Fehltreffer gefixt** — FedEx verlangt jetzt den Markennamen „fedex" nahe der Nummer (wie GLS), killt Unsinns-Nummern wie `869999999999997`. (b) **Zugestellte (17track-Code 40) fallen sofort** aus Universal-Zähler + `tracking_details`-Anzeige, werden aber weiter an den Coordinator gemeldet (In-Transit-Cleanup). | `shippers/universal.py` (`_BRAND_CONTEXT_RE`, `process_batch`) | ✅ Universal 4→1 (FedEx+2×DHL raus) |
| test36 | **Temporärer Diagnose-Build** (in test37 wieder entfernt): loggte pro gefundener Universal-Nummer Absender+Betreff der Quell-Mail (WARNING). Ergebnis: Phantom-DPD-Nummer `58303696535936` stammt aus einer **BANDWERK-Werbemail** („Neu: Signal Edition…") — bestätigter Fehltreffer. | `shippers/universal.py` | ✅ Quelle identifiziert |
| test37 | (a) Diagnose-Logging aus test36 wieder **entfernt**. (b) **DPD-Markenkontext**: 14-stellige DPD-Nummer zählt nur noch mit „dpd"/dpd.de-Link nahebei → killt das BANDWERK-Phantom. | `shippers/universal.py` (`_BRAND_CONTEXT_RE`) | ✅ Universal 1→0, In Transit 0 |
| test38 | **17track-Rejected-Filter**: Nummern mit `status_code -1` (17track verwirft = keinem Carrier zuordenbar) fallen komplett raus (keine Liste, keine Weiterleitung). `NotFound (0)` bleibt bewusst drin (frisch verschickte Pakete). Prinzipieller Fehltreffer-Filter zusätzlich zum Markenkontext. | `shippers/universal.py` (`process_batch`) | ✅ Universal bleibt 0, sauberer Scan |
| test39 | **Wizard-Übersetzungen (DE)**: `amazon_enabled`, `seventeen_track_api_key`, `dhl_brief_enabled`, `custom_days` fehlten in `de.json` → zeigten Englisch. Jetzt deutsche, stilkonsistente Labels + 17track-Hinweistext (`data_description`), in config_2 **und** reconfig_2. `amazon_fwds`-Label vom Satz zum Label angeglichen. **Amazon-Detailseite war bereits korrekt an den Haken gekoppelt** (config_flow.py:969) — keine Codeänderung nötig. | `translations/de.json` | ✅ JSON valide, Integration lädt sauber (Labels im Wizard) |
| test40 | **Alle übrigen 19 Sprachen nachgezogen** (Konsistenz): dieselben 3 Labels + `custom_days` + 17track-`data_description` in config_2 & reconfig_2 für ca/cs/es/es_419/fi/fr/hu/it/ko/nl/no/pl/pt/pt_BR/ru/sk/sl/sv/zh_Hant_HK; englischer Hinweistext auch in `en.json` + `strings.json`. Per Skript (`scratchpad/fill_translations.py`), nur echte Lücken gefüllt. | `translations/*.json`, `strings.json` | ✅ 22 JSON valide, 0 verbleibende Lücken |
| test41 | **DHL-Token-Rotation-Bug gefixt (Kern-Ursache für schnelles Ablaufen).** DHL (Azure B2C) rotiert den Refresh-Token bei jeder Erneuerung. `_fetch_dhl_brief` speicherte den erneuerten Token aber erst NACH dem `if not letters: return` — d. h. am Normaltag (keine Briefe) wurde der rotierte Token nie persistiert → nächster Scan nutzt den toten Token → HTTP 400, Feature stirbt binnen Stunden. Persistierung jetzt in `_persist_dhl_tokens()` ausgelagert und **direkt nach `fetch_letters()`** (vor dem Early-Return) aufgerufen. **Password-Grant/ROPC ist bei DHL nicht verfügbar** — war aber auch nicht die Ursache. Live-Log zeigte `Token-Refresh 400` + `advices 500`. | `coordinator.py` (`_fetch_dhl_brief`, `_persist_dhl_tokens`) | ✅ deployed; **einmalige Neu-Anmeldung noch offen** (alter Token tot) |
| test43 | **Repairs-Plattform: Auth-Fehler erscheinen unter Einstellungen → Reparaturen** (wie VW We Connect), mit geführter Neu-Anmeldung — für **alle drei** Auth-Quellen. **(a) DHL Briefankündigung:** Client meldet `auth_failed` (Refresh 400 / advices 401/403); Coordinator `ir.async_create_issue("dhl_brief_auth_failed")`; neue `repairs.py` mit Reauth-Fixflow (Login-URL + Code). **(b) Office365-OAuth:** Token-Refresh wirft jetzt `ConfigEntryAuthFailed` (statt UpdateFailed); zusätzlich `except ConfigEntryAuthFailed: raise` VOR dem generischen `except Exception` (das hat den bestehenden IMAP-Auth-Fehler bisher zu UpdateFailed verschluckt) → HAs eingebaute Reauth-Reparatur. **(c) 17track:** Client-`auth_failed` bei HTTP 401/403 oder Auth-Code; über `universal.process_batch` (`_17track_auth_failed`) an Coordinator → `ir.async_create_issue("seventeen_track_auth_failed")`; Fixflow zum Neu-Eintragen des API-Keys. Alle Issues werden bei Erfolg automatisch gelöscht. Übersetzungen (Issue-Titel + Fixflow) in strings/en/de; **andere 18 Sprachen noch offen** (fallen auf EN zurück). | `repairs.py` (neu), `coordinator.py`, `shippers/dhl_briefankundigung.py`, `tracking/seventeen_track.py`, `shippers/universal.py`, `strings.json`, `translations/{en,de}.json` | ✅ **live verifiziert**: „DHL Briefankündigung: Anmeldung abgelaufen" erscheint unter Reparaturen (neben VW), Fixflow zeigt Login-Link + Code-Feld korrekt |
| test44 | (Unvollständiger Fix) Fixflow-Politur-Versuch: Guard `is not None`→Truthiness. **Hat NICHT gereicht** — HA übergibt die Issue-`data` (`{"entry_id":…}`, nicht-leeres Dict) als initialen `user_input` an `async_step_init`. | `repairs.py` | ❌ Fehler blieb |
| **test52** | **Wizard Schritt 2: drei Felder in Section-Boxen gruppiert (Option B).** Amazon-Sensoren, DHL Briefankündigung und Sendungsstatus-Quelle stehen jetzt je in einer eigenen HA-`section()`-Box (Titel + Rahmen), in config_2 **und** reconfig_2. Import `from homeassistant.data_entry_flow import section`; Felder je in `vol.Schema` pro Section, `{"collapsed": False}`. Neuer Helper `_flatten_step_2_sections()` zieht die verschachtelten Section-Keys (`sec_amazon`/`sec_dhl`/`sec_source`) vor der Validierung wieder auf Top-Level (beide Handler). Übersetzungen: Feld-Labels + Section-Titel unter `config.step.{config_2,reconfig_2}.sections.<sec>.{name,data,data_description}` (strings/en/de), Top-Level-Labels der 3 Felder entfernt. **Manifest 0.5.4 → 0.5.5** — Kern-Fix: Version stand seit vielen Deploys still → Frontend cachte Übersetzungen → Roh-Keys („tracking_source"/„mail"/…). „Leer lassen…"-Hinweis beim 17track-Schlüssel entfernt. | `config_flow.py`, `manifest.json`, `strings.json`, `translations/{en,de}.json` | ✅ kompiliert, Integration lädt sauber als **v0.5.5**; Wizard-Sicht wegen OAuth nicht automatisiert prüfbar → **User-Sichttest offen** |
| test51 | **Alle Boolean-Felder von Checkbox → Toggle-Schalter.** HA rendert `cv.boolean` als altmodische Checkbox; `selector.BooleanSelector()` rendert als modernen Toggle. Alle 14 `cv.boolean` im Config-Flow umgestellt (Amazon/DHL aktivieren, mp4, Bildraster, diverse „eigenes Bild", weitergeleitete Mails, `dhl_brief_reauth` …). Rein optisch, gleicher Wert; Labels unverändert. Design vorab per Mockup (visualize) abgestimmt: „gemischt" (Schalter für Ein/Aus, Radio für Quellenwahl) gewählt. | `config_flow.py` | ✅ kompiliert, Integration lädt sauber (Wizard-Sicht wegen OAuth-Schritt nicht automatisiert prüfbar) |
| test50 | **Toggle → Zwei-Optionen-Auswahl** (User wollte „Switch" mit benannten Optionen, keinen An/Aus-Toggle). Boolean `use_seventeen_track` ersetzt durch `SelectSelector` `tracking_source` (mode=LIST, Optionen `mail` / `seventeen_track`, `translation_key`); Default = `seventeen_track` wenn Key vorhanden, sonst `mail`. Flow-Logik: `tracking_source == "seventeen_track"` → Key-Schritt, sonst Key löschen. Übersetzungen: Feld-Label + `data_description` + `selector.tracking_source.options` in strings/en/de (`use_seventeen_track`-Texte entfernt). | `config_flow.py`, `strings.json`, `translations/{en,de}.json` | ⏳ Deploy läuft |
| test49 | **17track-Schlüssel ist jetzt Pflicht, wenn der Schalter an ist.** Feld im 17track-Schritt `vol.Optional`→`vol.Required`; zusätzlich Server-Validierung: leer/whitespace → Fehler `seventeen_track_required` (config.error), Schritt wird erneut gezeigt. Key wird getrimmt gespeichert. In beiden Flows (setup + reconfigure). Fehlermeldung in strings/en/de. | `config_flow.py`, `strings.json`, `translations/{en,de}.json` | ✅ kompiliert, Integration lädt sauber |
| test48 | **Wizard: expliziter Schalter „17track als Statusquelle" statt nacktem Key-Feld.** In Schritt 2 (config_2 & reconfig_2) ersetzt ein Boolean `use_seventeen_track` (Default = ob Key vorhanden) das API-Feld. **An → neuer Folgeschritt** `seventeen_track`/`reconfig_seventeen_track` mit dem Key-Feld; **aus → Key wird gelöscht** (zurück zu Mail-Tracking). Verzweigung nach Schritt 2 in `_route_after_config_2()`/`_route_after_reconfig_2()` extrahiert; Flag ist transient (gepoppt, nie gespeichert). Übersetzungen (Schalter-Label + `data_description` + neuer Schritt) in strings/en/de; **andere 19 Sprachen noch offen** (fallen auf EN zurück). | `config_flow.py`, `strings.json`, `translations/{en,de}.json` | ✅ kompiliert, Integration lädt sauber (Reconfigure-UI nicht automatisiert prüfbar wegen OAuth-Schritt) |
| test47 | **Reparatur-Übersetzungen in alle 19 übrigen Sprachen nachgezogen** (Konsistenz-Lücke aus test43 geschlossen): beide Issues (`dhl_brief_auth_failed`, `seventeen_track_auth_failed`) mit Titel + Fixflow-Schritt `reauth` (Titel/Beschreibung/Feld) + `error.invalid_auth` für ca/cs/es/es_419/fi/fr/hu/it/ko/nl/no/pl/pt/pt_BR/ru/sk/sl/sv/zh_Hant_HK. Skript: `scratchpad/fill_repair_i18n.py`, Audit „ALL LOCALES COMPLETE". | `translations/*.json` | ✅ JSON valide, Integration lädt sauber |
| test46 | **HA-Plattform-Bausteine nachgerüstet (5 auf einmal).** (1) **Button** „Scan Now" (`button.py`) → `coordinator.async_request_refresh()` (endlich manueller Scan ohne Reload). (2) **`state_class=MEASUREMENT`** auf allen Paket/Stück-Zählern (Loop nach `SENSOR_TYPES` via `dataclasses.replace`) → HA-Langzeitstatistik + Verlaufsgraphen. (3) **System Health** (`system_health.py`) → Panel: Konten, letzter Scan ok?, letzter Scan-Zeitpunkt. (4) **Event-Entity** (`event.py`) feuert `package_delivered`/`new_package_in_transit` bei Anstieg von `zpackages_delivered`/`_transit`. (5) **Kalender** (`calendar.py`) mit DHL-Brief-Terminen + „Amazon-Pakete heute". `PLATFORMS` += button/calendar/event. system_health-Übersetzungen in strings/en/de. | `const.py`, `button.py`, `event.py`, `calendar.py`, `system_health.py`, `strings.json`, `translations/{en,de}.json` | ✅ live: button/calendar/event-Entities da, `state_class=measurement` aktiv, Button-Druck löst Scan aus, keine Setup-Fehler |
| test45 | **Echter Fix:** Kanonischer **Zwei-Schritt-Repair-Flow** (`async_step_init` → `async_step_reauth`). init leitet nur weiter (ignoriert die Issue-data), der Formular-Schritt validiert nur echte Eingaben. Step-Key `init`→`reauth` in strings/en/de umbenannt. | `repairs.py`, `strings.json`, `translations/{en,de}.json` | ✅ **live verifiziert**: Fixflow öffnet ohne Vorab-Fehler, Login-Link + Code-Feld sauber |
| test42 | **Optionaler „DHL neu anmelden"-Haken im Reconfigure.** Nach Ersteinrichtung überspringt der Flow die DHL-Anmeldung (test28, um Token nicht zu clobbern) → es gab keinen Weg, einen widerrufenen/abgelaufenen Login zu erneuern. Neuer optionaler Haken `dhl_brief_reauth` im `reconfig_storage`-Schritt, **nur sichtbar wenn DHL aktiv + Token vorhanden**. Aus = bestehender Login bleibt; an = führt in den DHL-Code-Schritt. Flag ist transient (nie gespeichert). Label+Beschreibung in `strings.json` + allen 20 Sprachdateien. | `config_flow.py` (`_get_schema_step_storage`, `async_step_reconfig_storage`, `_show_reconfig_storage`), `strings.json`, `translations/*.json` | ⏳ Deploy läuft |

### Wie die amazon.de-Erkennung funktioniert (für Folge-Arbeit)
- Absender werden aus `AMAZON_EMAIL` + `AMAZON_SHIPMENT_TRACKING` × Domain gebaut und
  **nicht mehr** sprachgefiltert (nur Betreffe werden per `filter_amazon_strings` +
  `DOMAIN_LANG_MAP` je Domain gefiltert).
- `amazon_packages` = Pakete, deren Ankunftsdatum im Mail-Text = **heute** ist (minus
  bereits zugestellte). `amazon_delivered` = heutige „Zugestellt:"/„Geliefert:"-Mails.
- Verifiziert per Live-Blick in die echte Mailbox (Chrome-MCP/Outlook Web,
  `daniel@bmw-dm.de`): alle Amazon-Zustell-/Versand-/Verzögerungs-Mails kommen von
  `order-update@amazon.de` mit deutschen Betreffen.

### Deploy-Workflow (AKTUELL — so wird ausgeliefert)
Der Build läuft unter **Windows/PowerShell**; `ruff` ist in dieser Umgebung **nicht**
installiert → Syntax stattdessen mit `python -m py_compile` prüfen. Zip-Dateien müssen im
**Root** liegen (nicht unter `custom_components/mail_and_packages/`), siehe Abschnitt 3c.

1. Code in `custom_components/mail_and_packages/` ändern.
2. `python -m py_compile <geänderte Dateien>` (+ ggf. Standalone-Sanity-Skript).
3. Zip bauen (PowerShell):
   ```powershell
   $src = "custom_components\mail_and_packages"; $zip = "mail_and_packages.zip"
   Get-ChildItem $src -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
   if (Test-Path $zip) { Remove-Item $zip -Force }
   Add-Type -AssemblyName System.IO.Compression.FileSystem
   [System.IO.Compression.ZipFile]::CreateFromDirectory($src, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false)
   ```
4. `git add -A && git commit && git push origin test/all-features`
5. `git tag v0.5.4-testN && git push origin v0.5.4-testN`
6. `gh release create v0.5.4-testN mail_and_packages.zip --target test/all-features --title "v0.5.4-testN" --notes "..."`
7. HACS-Install per HA-MCP: `ha_manage_hacs(action="download", repository_id="BMWfan/Home-Assistant-Mail-And-Packages", version="v0.5.4-testN")`
8. `ha_restart(confirm=true)` → ~180 s warten → `ha_get_state(...)` zur Verifikation.

### Umgebung / IDs (für Live-Verifikation per HA-MCP)
- HA-Instanz: `homeassistant.mackcloud.de` (HA 2026.4.3, Container, aarch64).
- Config-Entry-ID: `01KVNWJJBRTHRCW43KA383KS6K`.
- Mailbox: `daniel@bmw-dm.de` über `outlook.office365.com` (IMAP SSL, OAuth2 Microsoft).
- Konfig: `amazon_domain=amazon.de`, `amazon_enabled=true`, `amazon_days=3`,
  `custom_days=10`, `dhl_brief_enabled=true`, `resources=["universal_packages"]`,
  14 Ordner inkl. `INBOX/Online-Shops/Amazon`.
- Reload ohne Neustart: `ha_call_service("homeassistant","reload_config_entry", data={"entry_id": "..."})`.

### Offene Punkte / mögliche nächste Schritte
- **test34 nach Neustart verifizieren** (keine Regression: `amazon_delivered` bleibt 1,
  Integration lädt sauber). Non-Null-Beweis für `amazon_exception` erst bei einer
  Verzögerungs-Mail von heute möglich.
- Fahrer-Foto-Host live gegenprüfen, sobald eine echte Foto-Zustellung („an sicherem Ort
  abgegeben" **mit** Bild) reinkommt.
- Optional weitere Sprachen für Exception-Betreffe/Bodies (aktuell EN + DE).

### Architektur-Notizen & aufgeschobene Ideen (bewusst NICHT umgesetzt)

Der User will vorerst **konsolidieren statt erweitern** (Branch stabilisieren/mergen,
Testsuite reparieren). Diese Ideen sind dokumentiert für „vielleicht später":

**A) DHL-Paketverfolgung / Fahrer-Ort (aufgeschoben).**
- Wir sind für die Briefankündigung bereits per OAuth an deinem **DHL-Konto** eingeloggt
  und sprechen das **App-Backend** an (`dhl.de`, `id_token`-Cookie). Dieselbe Session
  könnte auch DHLs **Paket**-Endpunkte erreichen — technisch „dasselbe" wie die
  Briefankündigung, kein neues Amazon-artiges Reverse-Engineering.
- Endpunkt ist praktisch bekannt: der **ioBroker.parcel-Adapter** (Quelle unserer
  DHL-Login-Details) trackt auch DHL-Pakete.
- **Aber:** (1) nur **konto-verknüpfte** Pakete sichtbar (nicht jede in Mails gefundene
  Sendung); (2) liefert vermutlich **Status + Zustellfenster + „N Stopps"**, **kein**
  Live-GPS des Fahrers; (3) neue fragile Carrier-API-Abhängigkeit + verletzt „kein
  direkter Carrier-API-Aufruf außer 17track" (bräuchte explizite Freigabe wie die
  Briefankündigung).
- **Entscheidung:** vorerst **weggelassen** (fragil, unklarer Nutzen). Falls doch:
  zuerst Endpunkt mit vorhandenem Token anprobieren und schauen, welche Orts-/Zustelldaten
  real zurückkommen, bevor ein „DHL Paket"-Sensor gebaut wird.

**B) Redundanz 17track- vs. Mail-Status (Konsolidierungs-Chance).**
- Status-Führung ist bei gesetztem 17track-Key **bereits** 17track-exklusiv:
  [coordinator.py:203-214](custom_components/mail_and_packages/coordinator.py:203) verwirft
  dann die mail-basierten `_tracking_details` und nutzt nur `_17track_details`.
- **Verbleibende Redundanz:** Der Scanner führt trotzdem **jeden Scan** die
  Per-Carrier-Mail-Suchen (`*_delivered`/`*_delivering`-Betreffe) aus, parallel zu 17track.
  `*_delivering`/`*_packages` werden von 17track überschrieben, `*_delivered` kommt aber
  weiter aus Mails. Das ist die „gemixte" Wahrnehmung im Wizard/den Sensoren.
- **Saubere Zielarchitektur:** „Entdeckung" (Nummern in Mails finden) von „Status"
  (gehört 17track) trennen; bei aktivem 17track die redundanten Per-Carrier-**Status**-Mail-
  Suchen abschalten (Amazon bleibt separat, ohne 17track).
- **Caveats gegen blindes Entfernen:** Deckungslücke (Sendungen ohne parsebare Nummer →
  Mail ist einziges Signal), 17track-Monats-Quota (Mail ist gratis), Verhalten der
  Per-Carrier-Sensoren ändert sich. → echter Refactor, nicht trivial.
- **Wizard-UX:** macht die Datenflüsse (Mail-Entdeckung vs. 17track-Status vs.
  Amazon-separat) nicht klar — Kandidat für bessere Gruppierung/Erklärtexte.

---

## 1. Was auf diesem Branch ist

25 Commits über `master`. Die wichtigsten Features:

| Feature | Commit(s) | Status |
|---|---|---|
| DPD France / DPD UK / GLS France Shipper | `e889e03` | fertig, ungetestet live |
| Universal Email Scanner (Tracking-Nummern aus beliebigen Mails) | `1d020ae` | fertig |
| Persistenz: In-Transit-State überlebt HA-Neustart | `09154c2` | fertig |
| 17track.net API-Integration als autoritäre Statusquelle | `ee54fb4`, `4642972` | fertig |
| Universal-Findings → Carrier-Sensoren routen | `14d1d11` | fertig |
| Auto-Discover aller Sensoren (keine Checkbox-Auswahl mehr) | `4f8dfd3` | fertig |
| DHL Briefankündigung (Letter Preview) | `0f9c018` | fertig |
| DHL-Labels englisch (`DHL Letter Preview`, `DHL Letter Next Delivery`) | `01bbb9d` | fertig |
| Fehlende `en.json`-Übersetzungsschlüssel ergänzt | `0f4458d` | fertig |
| `manifest.json` Version `0.5.4` (HACS-Update-Erkennung) | `4b358bd` | fertig |
| IMAP Search-Cache (Deduplizierung innerhalb eines Scans) | `0d11194` | fertig |
| **Batch IMAP Pre-Fetch** (Kern-Fix für Timeout) | `dbd0ac6` | in Test |
| Timing-Diagnostik im Pre-Fetch | `54e3e74` | in Test |
| **LOGOUT-Cleanup mit eigenem Kurz-Timeout** (behebt 120s-statt-60s-Doppel-Timeout) | `ae2c695` | in Test (test13) |

---

## 2. Das aktuelle Hauptproblem: IMAP-Timeout

### Symptom
Integration bricht nach 120 s mit Timeout ab beim Scan. Betroffener User hat:
- 13 konfigurierte IMAP-Ordner
- INBOX mit ~20 000 Nachrichten
- ~30 aktive Sensor-Typen

### Ursache
Ursprünglicher Code: pro Sensor × pro Ordner 1 `SELECT` + 1 `SEARCH`.  
Bei 30 Sensoren × 13 Ordnern = **390 SELECT-Kommandos** à ~250 ms = ~97 s.

### Fix (test11, test12)
**Inverted-Loop Pre-Fetch** in `_prefetch_imap_searches`:
1. `collect_queries()` auf jedem Shipper sammelt alle IMAP-Query-Strings ohne IMAP-Zugriff.
2. `batch_search_folders()` führt pro Ordner **einmalig SELECT** durch, dann alle Queries sequenziell.
3. Anschließend treffen alle `email_search()`-Calls auf Cache-Hits → 0 weitere IMAP-Ops.

Resultat: **13 SELECTs** statt 390.

### Stand nach test12
Der Fehler im Log (`CancelledError`, 99 s) war **kein Timeout** – HA wurde während des ersten Scans gestoppt (log-Zeile: "Home Assistant is stopping"). Die 99 s sind die Laufzeit bis zum externen Abbruch.

### Live-Diagnose per HA-MCP (2026-07-01, beantwortet die alte "was noch unklar ist"-Frage)

Direkt aus der laufenden Instanz (`homeassistant.mackcloud.de`) ausgelesen:

- **N = 93 unique Queries über 14 Ordner** – deutlich unter den befürchteten 520. Das Query-Volumen selbst ist **nicht** das Problem.
- In **keinem** von 36 beobachteten Scan-Versuchen erschien je die Zeile `Batch pre-fetch: folder %s — %d queries in %.1fs` ([utils/imap.py:533](custom_components/mail_and_packages/utils/imap.py:533)) oder `Pre-fetch complete`. Der Pre-Fetch hängt sich also **beim allerersten Ordner** auf.
- Jeder Scan brach nach exakt **120,0 s** ab, obwohl `imap_timeout` = **60 s** konfiguriert war – identisch bei allen 35 aufgezeichneten Vorkommen. Kein Zufall, sondern ein deterministischer Doppel-Timeout.
- Der Config-Entry (`01KVNWJJBRTHRCW43KA383KS6K`) hing deswegen dauerhaft in `setup_in_progress` fest (HA-Bootstrap-Log zeigte 2361 s Wartezeit beim Neustart).

### Root Cause gefunden (nicht mehr spekulativ)

1. [utils/imap.py:127-130](custom_components/mail_and_packages/utils/imap.py:127) setzt den **aioimaplib-Client-Timeout** (`account.timeout`) auf denselben Wert wie das ganze Scan-Budget (`self.timeout`, i.d.R. 60 s). Jeder einzelne IMAP-Befehl (SELECT, SEARCH, LOGOUT) darf also bis zu 60 s hängen, bevor sein eigener interner Timeout greift.
2. Hängt eine `uid_search()`-Query im ersten Ordner des Pre-Fetch-Loops, wird sie erst nach ~60 s vom äußeren `asyncio.timeout(self.timeout)` in [coordinator.py:120](custom_components/mail_and_packages/coordinator.py:120) gecancelt.
3. Der `finally`-Block in [coordinator.py:214-215](custom_components/mail_and_packages/coordinator.py:214) ruft **immer** `await logout(account)` auf – auch bei Cancellation. `logout()` machte bis test13 selbst wieder einen ungebremsten Netzwerk-Roundtrip auf derselben (vermutlich toten) Verbindung, mit demselben 60s-Timeout → **zwei serielle 60s-Timeouts = 120 s**, exakt wie beobachtet.

**Fix (test13, Commit `ae2c695`):** `logout()` in [utils/imap.py](custom_components/mail_and_packages/utils/imap.py) kappt den LOGOUT-Roundtrip jetzt mit einem eigenen, unabhängigen `LOGOUT_TIMEOUT` (5 s) statt das volle Scan-Budget zu erben. Cleanup nach einem bereits fehlgeschlagenen Scan kann das Budget dadurch nicht mehr ein zweites Mal verbrennen.

**Wichtig:** Das behebt die *Verdopplung*, nicht die *Ursache* des ersten Hängers (warum ein einzelner IMAP-Befehl gegen `outlook.office365.com` überhaupt >60 s braucht). Option C aus Abschnitt 3b (Timeout erhöhen) macht mit dem Fix jetzt tatsächlich das, was sie verspricht – vorher hätte ein auf 180 s erhöhter Timeout real bis zu 360 s gedauert.

### ✅ Live bestätigt (2026-07-01, 20:24:59, nach test13-Install + Neustart)

```
Mail and Packages scan exceeded its 60s time budget (elapsed 65.0s).
```

**65,0 s statt 120,0 s** – der Doppel-Timeout ist weg, bestätigt auf der echten Instanz direkt nach dem Update. Die verbleibenden ~5 s über dem 60s-Budget sind der (jetzt gebremste) LOGOUT-Cleanup, nicht mehr ein zweiter voller Timeout. Der Scan schlägt weiterhin fehl (`setup_retry`), weil der **ursprüngliche** Hänger im ersten Ordner/erster Query weiterhin besteht – das ist die in Abschnitt 3b beschriebene, noch offene Ursache. Nächster Schritt: welcher Ordner/welche Query genau hängt, per zusätzlichem Logging oder Option D (ESEARCH IN) eingrenzen.

### ✅ Genauer Hänger gefunden (test14, per-Query-Logging, 2026-07-01 21:12–21:17)

Drei unabhängige Scan-Versuche (eigene TCP-Verbindung/Login pro Versuch, ~2,5 Min Abstand) hängen **exakt an derselben Stelle**: Ordner `INBOX`, Query **40 von 93**:

```
FROM "noreply@service.dpd.de" OR SUBJECT "Bald ist ihr DPD Paket da" SUBJECT "kommt Ihr DPD Paket" SINCE 28-Jun-2026
```

Query 39 wird in allen drei Läufen noch geloggt, Query 41 nie – der `uid_search()`-Call für #40 bekommt nie eine Antwort (`utils/imap.py:492`). Die Query selbst ist unauffällig (kurz, keine Sonderzeichen), was gegen ein Problem mit dem Query-*Inhalt* spricht.

**Wahrscheinlichste Ursache:** Microsoft/Exchange-Online drosselt IMAP-Verbindungen, die sehr viele Befehle in kurzer Zeit hintereinander schicken (hier: ~40 SEARCHes in <1 s auf derselben Connection, siehe Timestamps – alle Queries 1–39 werden in Sekundenbruchteilen durchgereicht). Das würde erklären, warum immer dieselbe *Positions-Nummer* hängt, unabhängig vom konkreten Query-Inhalt – ein bekanntes, undokumentiertes Throttling-Verhalten von Exchange-Online-IMAP.

**Auswirkung auf Abschnitt 3b:**
- Option A (parallele Queries) würde das Problem vermutlich verschlimmern (mehr Befehle, noch schneller).
- Option D (ESEARCH IN) reduziert Ordner-Roundtrips, aber nicht die Gesamtzahl an Befehlen (~93) –träfe vermutlich denselben Trigger.
- **Option B (ein SEARCH `ALL SINCE` pro Ordner + client-seitiges Filtern)** ist jetzt die aussichtsreichste Option: senkt die Befehlsanzahl auf ~14 (ein Befehl pro Ordner) statt 93 – das würde eine vermutete Drossel-Schwelle um Faktor ~7 unterschreiten.
- Nicht implementiert (noch keine Freigabe): Das ist ein echter Design-Wechsel der Suchstrategie (mehr Rohdaten client-seitig verarbeiten), keine kleine Bugfix-Änderung mehr.

### ❌ Pacing-Fix getestet (test15) – Zeit-/Burst-Theorie widerlegt (2026-07-01 21:34–21:35)

`IMAP_COMMAND_PACING = 0.1` (100ms Pause vor jedem `uid_search`) live installiert und neu gestartet. Ergebnis: **exakt derselbe Hänger** – Ordner INBOX, Query 40/93, Elapsed **65,0s**, identisch zu test13/test14 ohne Pacing. Die Query-Abstände zwischen den Log-Zeilen zeigen die Pause aktiv (~113ms statt vorher <20ms), trotzdem hängt es an derselben Position.

**Das widerlegt die Zeit-/Burst-Theorie:** Wäre es ein Rate-Limit (Befehle pro Sekunde), hätte das Pacing die Hänge-Position nach hinten verschieben oder das Problem ganz vermeiden müssen. Stattdessen identisch bei #40 – das spricht für ein **festes Befehls-Limit pro IMAP-Verbindung** (Count-basiert, nicht zeitbasiert): Nach ca. 40 Befehlen (SELECT + ~39 SEARCHes) reagiert diese Exchange-Online-Verbindung schlicht nicht mehr, unabhängig vom Tempo.

**Neue Konsequenz:** Auch Option C (Timeout erhöhen) hilft NICHT – das ist kein "langsamer" Befehl, der irgendwann doch antwortet, sondern ein endgültiges Verstummen der Verbindung. Ein höheres Budget würde nur länger auf denselben permanenten Hänger warten.

**Nächster Kandidat: periodischer Reconnect.** Alle ~30 Befehle (oder bei einem kurzen Command-Timeout, z. B. 10s) die IMAP-Verbindung schließen und neu aufbauen (frisches Login), dann mit der nächsten Query weitermachen. Das würde die exakte Such-Semantik unangetastet lassen (kein Risiko wie bei Option B), erfordert aber eine invasivere Änderung: `batch_search_folders`/`_batch_search_one_folder` müssten die (ggf. neue) Connection zurückgeben, und `coordinator.py` müsste sie durch `_prefetch_imap_searches` → `_update_shippers` → `process_emails` (inkl. des finalen `logout()` im `finally`-Block) durchreichen, damit der Rest des Scans nicht mit einer toten Connection weiterläuft. Nicht implementiert – das ist ein echter Architektur-Eingriff über zwei Dateien hinweg, noch keine Freigabe.

### ✅ Reconnect-Fix umgesetzt und live bestätigt (test16, Commit `33eda65`, 2026-07-02 01:09–01:14)

`IMAP_COMMAND_TIMEOUT = 10` in [utils/imap.py](custom_components/mail_and_packages/utils/imap.py): jeder SELECT/SEARCH wird einzeln mit 10s begrenzt. Bei Stall: Verbindung schließen, neu einloggen (Login-Parameter werden beim initialen Login auf dem `account`-Objekt gespeichert), aktuellen Ordner neu selecten, dieselbe Query einmal erneut versuchen. Da sich das Connection-Objekt dabei ändern kann, geben `batch_search_folders`/`_prefetch_imap_searches` es jetzt zurück, und `coordinator.py` (`_update_shippers`, `process_emails`, inkl. `EmailCache` und finalem `logout()`) reicht es durch.

**Live-Verifikation nach Neustart:** In derselben Sitzung feuerten **7 Reconnects** (`Batch pre-fetch: IMAP connection stalled past 10s, reconnecting`), und der Scan kam dadurch erstmals **über Ordner INBOX hinaus** – bis in einen Unterordner (`INBOX/Online-Shops/ABOUT YOU`). Vorher war bei JEDEM Versuch bei Query 40 im ALLERERSTEN Ordner endgültig Schluss. Der Reconnect-Mechanismus funktioniert also nachweislich.

**Aber:** Jeder einzelne Scan-Versuch bricht weiterhin bei exakt **65,0s** ab (`scan exceeded its 60s time budget`) – nicht mehr wegen eines permanenten Hängers, sondern weil die **Gesamtmenge an Arbeit** (bis zu 93 Queries × 14 Ordner = 1.302 Befehle, plus ein Reconnect-Zyklus alle ~40 Befehle à ca. 10-15s inkl. Stall-Erkennung) schlicht länger dauert als 60s. Grobe Hochrechnung aus den beobachteten Reconnect-Intervallen: ein kompletter Scan bräuchte bei diesem Tempo geschätzt **~7-8 Minuten**.

**Konsequenz:** Der Hänger-Bug ist behoben (kein permanentes Einfrieren mehr), aber `imap_timeout` muss jetzt zwingend deutlich höher gesetzt werden (z. B. 480-600s), damit ein Scan überhaupt durchlaufen kann – das lässt sich nicht automatisiert setzen (kein Options-Flow, nur mehrstufiger Reconfigure-Dialog mit Zugangsdaten, siehe unten). Alternativ bleibt Option B (Befehlsvolumen fundamental senken statt nur den Hänger zu umschiffen) weiterhin die Option mit dem größten Hebel auf die tatsächliche Scan-Dauer.

### ✅ Option B umgesetzt (test17, Commit `d7a7340`, 2026-07-02)

Statt einer echten `SEARCH`-Anfrage pro Query (bis zu 93 pro Ordner) macht `batch_search_folders` pro Ordner jetzt nur noch:
1. **Eine breite** `SEARCH SINCE <frühestes benötigtes Datum>` über alle anstehenden Queries dieses Ordners.
2. **Ein paar gebündelte** `UID FETCH ... (INTERNALDATE BODY[HEADER.FIELDS (FROM SUBJECT ...)])` für die gefundenen UIDs (in Chunks von 200 als reine Sicherheitsgrenze, kein Skalierungshebel).
3. **Client-seitiges Klassifizieren** jeder Nachricht gegen die Kriterien jeder einzelnen Query (From/Subject/Header-Substring-Matches wie `build_search()`, SINCE mit Tagesgranularität über `INTERNALDATE` – nicht über den fälschungsanfälligen `Date:`-Header).

**Wichtige Design-Entscheidung:** `GenericShipper.collect_queries()` gibt jetzt `QuerySpec`-Objekte zurück (Adressen, Betreffs, since_date, Forwarding-Header) statt fertiger Query-Strings. Das `query`-Feld jedes `QuerySpec` enthält aber weiterhin exakt den String, den `build_search()` produzieren würde – das ist der Cache-Key, den der normale Pro-Sensor-Suchpfad (`email_search()`) unverändert selbst baut und nachschlägt. Dadurch bleiben Cache-Hits nach dem Pre-Fetch erhalten, ohne den bestehenden Suchpfad anfassen zu müssen.

**Jede Query behält ihr eigenes `since_date`**, auch wenn die breite Suche das früheste Datum über alle Queries hinweg nutzt – eine Nachricht, die inhaltlich zu einer Query passt, aber vor deren `since_date` liegt, wird beim Klassifizieren korrekt ausgeschlossen (per Test abgesichert, siehe unten).

**Verifiziert per Standalone-Skript** (reale Testsuite weiterhin kaputt, siehe Abschnitt 5): simulierte, realistische Mehrfach-Nachrichten-FETCH-Antworten von aioimaplib (inkl. MIME-kodierter Betreffs), Klassifizierung korrekt, nur 1 SEARCH + 1 FETCH für 2 Queries (statt 2 SEARCHes), Reconnect-Schutz (test16) funktioniert unverändert auch um die neue breite Suche/FETCH herum. Auch als echte Tests in `tests/utils/test_imap_email.py` committet.

**Noch zu verifizieren:** Live-Test nach Installation – reduziert das die Scan-Zeit tatsächlich auf wenige Sekunden pro Ordner (Ziel: alle 14 Ordner deutlich unter 60s)?

---

## 3. Nächste Schritte

### 3a. Diagnose mit test12 auswerten — ✅ erledigt (siehe Abschnitt 2)

N = 93 unique Queries über 14 Ordner. Die Gesamtzeit `XX.X` ließ sich nicht ermitteln, weil der Pre-Fetch nie eine einzige `Batch pre-fetch: folder ...`-Zeile loggte – er hing im ersten Ordner fest, bis der (verdoppelte) Timeout griff. Root Cause siehe Abschnitt 2.

**Nach test13 erneut prüfen:** Mit dem LOGOUT-Fix sollte entweder (a) der Scan durchlaufen, oder (b) bei echtem Hänger jetzt eine saubere `Batch pre-fetch: folder ...`-Zeile für mindestens den ersten Ordner erscheinen, bevor der Timeout greift – das würde bestätigen, welcher Ordner/welche Query tatsächlich hängt.

### 3b. Falls Pre-Fetch immer noch zu lang

**Option A: Queries parallel innerhalb eines Ordners**

Pro Ordner ein `SELECT`, dann alle Queries via `asyncio.gather()` parallel schicken. IMAP ist verbindungsseitig seriell (eine Verbindung), aber aioimaplib kann Befehle pipelinen. Riskant: manche Exchange-Server verhalten sich bei parallelen Commands unzuverlässig.

```python
# statt sequenziell:
for query in pending:
    res = await account.uid_search(query, charset=None)

# parallel:
tasks = [account.uid_search(q, charset=None) for q in pending]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Option B: SINCE-Datum als Vorfilter, dann client-seitig filtern**

Einen einzigen SEARCH `ALL SINCE since_date` pro Ordner, alle Nachrichten-Header laden, dann alles client-seitig filtern. Besonders effizient wenn der Ordner wenige Einträge im Zeitfenster hat. Für INBOX mit 20 K Nachrichten aber riskant (viele Header).

**Option C: Timeout erhöhen**

Kurzfristige Lösung: User erhöht den `imap_timeout`-Wert in den Optionen. Standard ist 120 s; 180–240 s würde für die meisten Cases reichen.

**Option D: ESEARCH IN nutzen**

Der Code hat bereits einen ESEARCH-Pfad (`_execute_single_search` → Zeile ~391). Wenn der Exchange-Server `ESEARCH IN ("folder1" "folder2")` unterstützt, läuft alles in einer einzigen Anfrage pro Query. Testen, ob `outlook.office365.com` das unterstützt.

### 3c. Test-Release erstellen

**⚠️ Zip-Struktur-Bug (gefunden und gefixt bei test13):** `hacs.json` setzt `"zip_release": true, "filename": "mail_and_packages.zip"` — HACS lädt bei dieser Konfiguration **genau dieses Release-Asset** herunter und entpackt es so, dass der Inhalt direkt im Zip-Root liegen muss (`manifest.json`, `__init__.py`, … auf oberster Ebene), NICHT unter `custom_components/mail_and_packages/`. Die alte Build-Anleitung unten (und der committete Zip bis einschließlich test13-Erstversion) hatte die Dateien fälschlich unter dem vollen Pfad `custom_components/mail_and_packages/...` – das führte dazu, dass ein HACS-`download` zwar "erfolgreich" meldete, HA danach aber `Setup failed for 'mail_and_packages': Integration not found.` loggte, weil kein `manifest.json` im erwarteten Wurzelverzeichnis lag. Vermutlich war dieser Bug schon in test1–test12 vorhanden, ist aber nie aufgefallen, weil HACS dort nie tatsächlich per `download`-Aktion gegen den zip-Release lief.

Korrigierter Build-Befehl (Dateien relativ zu `custom_components/mail_and_packages/`, nicht mit vollem Pfad):

```bash
# Code ändern
ruff check . && ruff format .
python3 -c "
import zipfile, os
base = 'custom_components/mail_and_packages'
with zipfile.ZipFile('mail_and_packages.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.pyc'):
                continue
            full = os.path.join(root, file)
            zf.write(full, os.path.relpath(full, base))
"
git add custom_components/mail_and_packages/ mail_and_packages.zip
git commit -m "..."
git push origin test/all-features
git tag v0.5.4-testN && git push origin v0.5.4-testN
gh release create v0.5.4-testN mail_and_packages.zip --repo BMWfan/Home-Assistant-Mail-And-Packages --prerelease --notes "..."
```

**test13 Status:** ✅ erstellt (Fix-Commit `ae2c695`, Tag `v0.5.4-test13`, Prerelease auf GitHub). Enthält den LOGOUT-Timeout-Fix aus Abschnitt 2. Der Zip-Struktur-Bug wurde direkt in derselben Session entdeckt (HACS-Install brach danach mit "Integration not found" ab) und mit einem korrigierten, neu hochgeladenen Zip behoben — siehe Warnung oben.

---

## 4. Schlüsseldateien

| Datei | Was wurde geändert |
|---|---|
| `utils/imap.py` | `batch_search_folders`, `_batch_search_one_folder`, `_batch_search_single_folder`, `_get_search_cache`; Search-Cache in `_execute_single_search` und `email_search`; Per-Folder-Timing |
| `shippers/generic.py` | `collect_queries()` auf `GenericShipper` |
| `coordinator.py` | `_prefetch_imap_searches()`, Timing-Log, Aufruf in `_update_shippers()` |
| `translations/en.json` | Fehlende Felder `dhl_brief_enabled`, `amazon_enabled`, `seventeen_track_api_key`, beide DHL-Auth-Steps |
| `strings.json` | Dieselben Felder (HA-Vorlage) |
| `const.py` | `"DHL Letter Preview"`, `"DHL Letter Next Delivery"` (statt Deutsch) |
| `camera.py` | `"DHL Letter Preview"` (Kamera-Entitätsname) |
| `manifest.json` | `"version": "0.5.4"` (war `"0.0.0-dev"`, blockierte HACS-Updates) |
| `shippers/dhl_briefankundigung.py` | Neuer Shipper für DHL Briefankündigung |
| `utils/imap.py` | `logout()` kappt LOGOUT jetzt mit eigenem `LOGOUT_TIMEOUT` (5s) statt dem vollen Scan-Budget zu erben (test13, siehe Abschnitt 2) |
| `utils/imap.py` | `IMAP_COMMAND_PACING`, `IMAP_COMMAND_TIMEOUT`, `_reconnect()`, `_select_with_reconnect()`; `_batch_search_one_folder`/`batch_search_folders` geben jetzt die (ggf. neue) Connection zurück (test15/test16, siehe Abschnitt 2) |
| `coordinator.py` | `_get_imap_connection` speichert `_login_kwargs`/`_hass` auf dem `account`-Objekt; `_prefetch_imap_searches`/`_update_shippers`/`process_emails` reichen die (ggf. neue) Connection durch bis zum finalen `logout()` (test16) |
| `utils/imap.py` | `QuerySpec`, `_parse_fetch_records`, `_query_matches_record`, `_fetch_and_classify`; `batch_search_folders`/`_batch_search_one_folder`/`_batch_search_single_folder` machen jetzt 1 breite SEARCH + gebündelte FETCHes statt 1 SEARCH pro Query (test17, Option B, siehe Abschnitt 2) |
| `shippers/generic.py` | `collect_queries()` gibt `list[QuerySpec]` statt `list[str]` zurück (test17) |

---

## 5. Bekannte offene Punkte / Risiken

- **Test-Environment ist strukturell kaputt, nicht nur ein Python-Versions-Mismatch:**
  - `conftest.py` erzwingt global `pytest_plugins = "pytest_homeassistant_custom_component"`. Dessen letzte PyPI-Version (0.9.17) pinnt zwingend `homeassistant==2022.6.7` + `pytest==7.1.1`.
  - Der Code selbst (z. B. `utils/imap.py` Zeile ~254) nutzt verschachtelte f-String-Quotes (PEP 701) → **erfordert Python ≥3.12** zum Parsen.
  - `homeassistant` 2022.x pinnt wiederum `ciso8601==2.2.0`, das **keine Windows-Wheels** hat und ohne MSVC Build Tools nicht kompiliert.
  - Auf Python 3.13/3.14 crasht stattdessen `pytest`s eigener Assertion-Rewriter (`TypeError: required field "lineno" missing from alias`) beim Laden des `pytest_homeassistant_custom_component`-Plugins – ein bekanntes Kompatibilitätsproblem alter pytest-Internals mit neueren Python-AST-Validierungen.
  - **Kurz:** Es gibt aktuell keine Python-Version, unter der `uv run pytest` in diesem Repo durchläuft, ohne entweder MSVC Build Tools zu installieren oder `pytest-homeassistant-custom-component` durch etwas Aktuelles zu ersetzen. Das ist unabhängig von unseren Änderungen und eine eigene, größere Aufgabe.
  - Der test13-LOGOUT-Fix wurde deshalb per Stand-alone-Skript verifiziert (Homeassistant-Module gestubbt, `utils/imap.py` direkt per `importlib` geladen) statt über die Testsuite.
- `uv.lock` hatte unstaged Changes durch Venv-Experimente – zurückgesetzt, nicht committet.
- **`collect_queries` deckt nicht 100 % der Shipper ab**: Nur `GenericShipper` implementiert `collect_queries`. Shipper ohne diese Methode (z. B. `DHLBriefankundigungShipper`) fallen durch in den normalen Per-Sensor-IMAP-Flow. Das ist korrekt – sie nutzen einfach keinen Pre-Fetch.
- **Ob Pre-Fetch nach dem LOGOUT-Fix schnell genug ist**, ist weiterhin offen – siehe "Nach test13 erneut prüfen" in Abschnitt 3a.

---

## 6. Entscheidungen aus früheren Sessions

- Kein direkter Carrier-API-Aufruf außer 17track (explizit genehmigt).
- Kein LLM/Ollama/OpenAI.
- Kein Amazon-Cookie-Scraping.
- Credentials/Tokens nur im HA ConfigEntry, nirgendwo sonst.
