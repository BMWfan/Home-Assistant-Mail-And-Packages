#!/usr/bin/env bash
set -euo pipefail

# Legt den initialen HA-Owner-Account nicht-interaktiv über die Onboarding-API an,
# damit der manuelle Onboarding-Wizard im Browser entfällt.
#
# Hinweis: Das betrifft NUR das Home-Assistant-Onboarding. Der Config-Flow der
# Integration selbst (IMAP-Zugang, 17track) ist davon unabhängig.
#
# Passwort NIE in einer Datei ablegen -> nur zur Laufzeit per Env-Var übergeben:
#   HA_OWNER_USERNAME=daniel HA_OWNER_PASSWORD='...' bash scripts/bootstrap-owner.sh
#
# Ungetestet gegen eine konkrete laufende Instanz -- die Onboarding-API ist intern
# und nicht offiziell versioniert, das Schema kann sich zwischen HA-Releases ändern.
# Bei Fehlern die rohe JSON-Antwort prüfen, die das Skript bei Bedarf ausgibt.

cd "$(dirname "$0")/.."

: "${HA_OWNER_USERNAME:?HA_OWNER_USERNAME nicht gesetzt}"
: "${HA_OWNER_PASSWORD:?HA_OWNER_PASSWORD nicht gesetzt}"
HA_OWNER_NAME="${HA_OWNER_NAME:-$HA_OWNER_USERNAME}"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
HA_DEV_PORT="${HA_DEV_PORT:-8123}"
# HA_BASE_URL wird vom bootstrap-owner-Compose-Service gesetzt (interner
# Service-Hostname); lokal ohne Compose fällt es auf localhost:HA_DEV_PORT zurück.
BASE_URL="${HA_BASE_URL:-http://localhost:${HA_DEV_PORT}}"

echo "-> Prüfe Onboarding-Status auf ${BASE_URL}..."
http_code=$(curl -sS -o /tmp/onboarding-status.json -w '%{http_code}' "${BASE_URL}/api/onboarding")

if [ "$http_code" = "404" ]; then
  echo "-> Onboarding-API meldet 404 -> Onboarding ist bereits vollständig abgeschlossen, überspringe."
  exit 0
elif [ "$http_code" != "200" ]; then
  echo "FEHLER: Unerwarteter Status ${http_code} von ${BASE_URL}/api/onboarding:"
  cat /tmp/onboarding-status.json
  exit 1
fi

user_done=$(jq -r '.[] | select(.step=="user") | .done' /tmp/onboarding-status.json)
if [ "$user_done" = "true" ]; then
  echo "-> Onboarding-Schritt 'user' bereits abgeschlossen, überspringe Account-Anlage."
  exit 0
fi

echo "-> Lege initialen Owner-Account '${HA_OWNER_USERNAME}' an..."
response=$(curl -sS -X POST "${BASE_URL}/api/onboarding/users" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg client_id "${BASE_URL}/" \
    --arg name "$HA_OWNER_NAME" \
    --arg username "$HA_OWNER_USERNAME" \
    --arg password "$HA_OWNER_PASSWORD" \
    '{client_id: $client_id, name: $name, username: $username, password: $password, language: "de"}')")

auth_code=$(echo "$response" | jq -r '.auth_code // empty')
if [ -z "$auth_code" ]; then
  echo "FEHLER: Kein auth_code erhalten. Antwort der Onboarding-API:"
  echo "$response"
  exit 1
fi

echo "-> Tausche auth_code gegen Access-Token..."
token_response=$(curl -sS -X POST "${BASE_URL}/auth/token" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=${auth_code}" \
  --data-urlencode "client_id=${BASE_URL}/")

access_token=$(echo "$token_response" | jq -r '.access_token // empty')
if [ -z "$access_token" ]; then
  echo "FEHLER: Kein access_token erhalten. Antwort:"
  echo "$token_response"
  exit 1
fi

echo "-> Schließe verbleibende Onboarding-Schritte ab (core_config, analytics, integration)..."
curl -sS -X POST "${BASE_URL}/api/onboarding/core_config" \
  -H "Authorization: Bearer ${access_token}" >/dev/null || true

curl -sS -X POST "${BASE_URL}/api/onboarding/analytics" \
  -H "Authorization: Bearer ${access_token}" \
  -H "Content-Type: application/json" -d '{}' >/dev/null || true

curl -sS -X POST "${BASE_URL}/api/onboarding/integration" \
  -H "Authorization: Bearer ${access_token}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg cid "${BASE_URL}/" --arg ru "${BASE_URL}/" '{client_id: $cid, redirect_uri: $ru}')" >/dev/null || true

echo "-> Owner-Account angelegt. Login unter ${BASE_URL} mit Benutzername '${HA_OWNER_USERNAME}'."
echo "   Das Access-Token wurde nur für den Onboarding-Abschluss verwendet, nicht gespeichert."
