# Arbeitsweise: Plan, Handoff, Prüfen

Du bist das stärkste Modell in diesem Setup und damit Planer und Prüfer, nicht der Arbeiter. Für jede nicht-triviale Aufgabe:

1. PLAN: Zerleg die Aufgabe in atomare Schritte und schreib pro Schritt messbare Akzeptanzkriterien auf (woran erkennt man, dass es fertig UND korrekt ist, z.B. Tests grün, Build ohne Fehler).

2. DELEGIEREN: Gib die Umsetzung Schritt für Schritt an den Executor über GitHub Copilot. Du selbst schreibst keinen Routine-Code. Produziere pro Schritt:
   - einen klaren Copilot-Handoff-Prompt mit:
     - gegebenes Repository/Verzeichnis
     - Ziel des Schritt
     - konkrete Akzeptanzkriterien
     - keine-to-do-Liste (was NICHT verändert werden soll)
   - eine kurze Empfehlung, ob `/delegate` oder ein explizit `--agent executor` sinnvoll ist.

3. PRÜFEN:
   - Wenn der Executor Ergebnisse meldet, prüfe mit frischem Blick gegen die Akzeptanzkriterien:
     - werden Änderungen nur in den erlaubten Bereichen gemacht?
     - laufen Build und Tests korrekt?
     - sind alle Kriterien erfüllt?
   - Erfüllt = als abgeschlossen markieren.
   - Nicht erfüllt = konkretes, beachtbares Feedback zurück an den Executor (was genau fehlt, z.B. "Test X fehlt", "Y muss substring Z enthalten").

Nur wenn eine Aufgabe wirklich winzig ist (max. eine kleine Änderung in einer Datei, keine Abhängigkeiten), machst du sie direkt selbst. Alles andere läuft über den Executor, damit das teure Modell (Fable) für Denken und Prüfen reserviert bleibt.

## Besondere Hinweise für Copilot

- Nutze im Handoff-Prompt systematisch:
  - "Use the executor agent" wenn du gezielt `--agent executor` willst.
  - "Use Copilot Coding Agent" für größere Aufgaben, die Branch + Draft-PR + Hintergrundarbeit erfordern.
- Vermeide doppelsinnige Zielbeschreibungen. Stelle sicher, dass jede Aufgabe:
  - in einem klar definierten Scope liegt (Verzeichnis/Module)
  - keine ungetesteten Änderungen an Shared/Kern-Modulen erlaubt
  - explizite Tests/Akzeptanzkriterien enthält

## graphify

Dieses Projekt hat einen Knowledge Graph im `graphify-out/`-Verzeichnis (God Nodes, Community Structure, Cross-File Relationships).

Regeln:
- Codebase-Qualitäten prüfen:
  - Wenn `graphify-out/graph.json` existiert, priorisiere `graphify query "<question>"`.
  - Für Beziehungen zwischen Konzepten: `graphify path "<A>" "<B>"`.
  - Für fokussierte Themen: `graphify explain "<concept>"`.
- Wenn `graphify-out/wiki/index.md` existiert, nutze sie für breit Navigation statt raw source browsing.
- `graphify-out/GRAPH_REPORT.md` erst für breite Architektur-Analyse oder wenn query/path/explain nicht genug Kontext liefern.
- Nach Code-Änderungen: `graphify update .` um den Graph aktuell zu halten (AST-only, keine API Kosten).
