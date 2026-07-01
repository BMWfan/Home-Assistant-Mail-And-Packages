# Handoff – Mail and Packages (branch `test/all-features`)

Stand: 2026-07-01  
Aktuelles Release: **v0.5.4-test12** (prerelease auf GitHub)

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

**Was noch unklar ist:**  
Wie viele unique Queries gibt es tatsächlich? Wenn z. B. 40 unique Queries × 13 Ordner = 520 SEARCHes, und jeder SEARCH auf dem großen INBOX ~250 ms dauert → ~130 s. Immer noch grenzwertig.

---

## 3. Nächste Schritte

### 3a. Diagnose mit test12 auswerten

Nach Installation und sauberem HA-Neustart (kein zwischenzeitliches Stoppen):

```
DEBUG ... Pre-fetching N unique queries across 13 folder(s) (M total before dedup)
DEBUG ... Batch pre-fetch: folder INBOX — 40 queries in X.Xs
DEBUG ... Batch pre-fetch: folder Pakete — 40 queries in X.Xs
...
DEBUG ... Pre-fetch complete in XX.Xs (13 SELECTs + up to 520 SEARCHes)
```

→ `N` (unique Queries) und `XX.X` (Gesamtzeit Pre-Fetch) sind die entscheidenden Zahlen.

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

Wenn weitere Änderungen nötig: `v0.5.4-test13`, gleicher Ablauf:

```bash
# Code ändern
ruff check . && ruff format .
python3 -c "
import zipfile, os
with zipfile.ZipFile('mail_and_packages.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('custom_components/mail_and_packages'):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if not file.endswith('.pyc'): zf.write(os.path.join(root, file))
"
git add custom_components/mail_and_packages/ mail_and_packages.zip
git commit -m "..."
git push origin test/all-features
git tag v0.5.4-test13 && git push origin v0.5.4-test13
# Release auf GitHub: über Web-UI oder gh CLI anlegen und zip hochladen
```

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

---

## 5. Bekannte offene Punkte / Risiken

- **Test-Environment kaputt**: `uv run pytest` schlägt mit `ModuleNotFoundError: No module named 'pkg_resources'` fehl – Python-Versions-Mismatch (.venv ist 3.9, Code zielt auf 3.13/3.14). Unabhängig von unseren Änderungen.
- `tests/shippers/test_dpd_gls_international.py` und `uv.lock` haben unstaged Changes – nicht committen, bis der Test-Stand klar ist.
- **`collect_queries` deckt nicht 100 % der Shipper ab**: Nur `GenericShipper` implementiert `collect_queries`. Shipper ohne diese Methode (z. B. `DHLBriefankundigungShipper`) fallen durch in den normalen Per-Sensor-IMAP-Flow. Das ist korrekt – sie nutzen einfach keinen Pre-Fetch.
- **Ob Pre-Fetch schnell genug ist**, hängt von den test12-Logs ab (siehe Abschnitt 3a).

---

## 6. Entscheidungen aus früheren Sessions

- Kein direkter Carrier-API-Aufruf außer 17track (explizit genehmigt).
- Kein LLM/Ollama/OpenAI.
- Kein Amazon-Cookie-Scraping.
- Credentials/Tokens nur im HA ConfigEntry, nirgendwo sonst.
