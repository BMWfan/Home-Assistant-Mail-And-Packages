# Handoff – Mail and Packages (branch `test/all-features`)

Stand: 2026-07-01 (aktualisiert)  
Aktuelles Release: **v0.5.4-test13** (prerelease auf GitHub)

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
