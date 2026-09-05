# dhl-code-helper

Windows-Helfer, der den `dhllogin://`-Redirect abfängt, den DHL beim Login-/2FA-Flow
über den Browser auslöst. Registriert `dhllogin://` als Custom-URL-Protocol in der
Windows-Registry (`HKCU\Software\Classes\dhllogin`); jeder Klick auf einen solchen
Link ruft dann dieses Skript statt eines Browsers auf.

Zwei Varianten sind hier drin:
- `1-REGISTRIEREN.reg` registriert einen Inline-PowerShell-Befehl, der die
  empfangene URL in die Zwischenablage kopiert und in einer MessageBox anzeigt.
- `dhl-code-helper.ps1` ist die stille Variante ohne UI: schreibt die URL
  zusätzlich in `letzter-code.txt` neben dem Skript (nicht Teil dieses Imports -
  reiner Laufzeit-Output, wird lokal neu erzeugt) und kopiert sie in die
  Zwischenablage.
- `2-ENTFERNEN.reg` entfernt die Registry-Registrierung wieder.

Grund für den Import hierher: gehört inhaltlich zur mail_and_packages-Integration
(DHL-Login/Tracking-Handling), lag bisher als eigenständiges Repo unter
`C:\Users\danie\dhl-code-helper` auf dem Notebook. Diese Kopie ist nur zur
Sicherung/Dokumentation - die aktive, registrierte Installation bleibt unverändert
unter `C:\Users\danie\dhl-code-helper` bestehen.
