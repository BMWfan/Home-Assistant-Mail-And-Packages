#!/usr/bin/env python3
"""Setzt Land/Zeitzone/Einheiten in HAs Kernkonfiguration nach.

Das Onboarding markiert `core_config` als erledigt, ohne ein Land zu setzen --
HA meldet danach die Reparatur "Das Land wurde nicht konfiguriert". Es gibt
dafuer keinen REST-Endpunkt; die Aenderung laeuft ueber das WebSocket-Kommando
`config/core/update`.

Zugangsdaten kommen aus der .env (HA_OWNER_USERNAME / HA_OWNER_PASSWORD).

  python3 scripts/set-core-config.py [--country DE] [--timezone Europe/Berlin]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets

REPO = Path(__file__).resolve().parent.parent


def load_env() -> dict:
    env = {}
    f = REPO / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


async def get_token(session, base: str, user: str, password: str) -> str:
    """Login-Flow durchlaufen und Access-Token holen."""
    import urllib.parse
    import urllib.request

    client_id = f"{base}/"

    def post(url, data, as_json=True):
        body = json.dumps(data).encode() if as_json else urllib.parse.urlencode(data).encode()
        ctype = "application/json" if as_json else "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": ctype})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    flow = post(f"{base}/auth/login_flow", {
        "client_id": client_id,
        "handler": ["homeassistant", None],
        "redirect_uri": client_id,
    })
    step = post(f"{base}/auth/login_flow/{flow['flow_id']}", {
        "client_id": client_id,
        "username": user,
        "password": password,
    })
    if "result" not in step:
        raise SystemExit(f"Login fehlgeschlagen: {step}")
    tok = post(f"{base}/auth/token", {
        "grant_type": "authorization_code",
        "code": step["result"],
        "client_id": client_id,
    }, as_json=False)
    return tok["access_token"]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="DE")
    ap.add_argument("--timezone", default="Europe/Berlin")
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--language", default="de")
    ap.add_argument("--port", default="8123")
    args = ap.parse_args()

    env = load_env()
    user = env.get("HA_OWNER_USERNAME")
    password = env.get("HA_OWNER_PASSWORD")
    if not user or not password:
        sys.exit("HA_OWNER_USERNAME/HA_OWNER_PASSWORD fehlen in .env")

    base = f"http://localhost:{args.port}"
    token = await get_token(None, base, user, password)

    async with websockets.connect(f"ws://localhost:{args.port}/api/websocket") as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            sys.exit("WebSocket-Auth fehlgeschlagen")

        await ws.send(json.dumps({
            "id": 1, "type": "config/core/update",
            "country": args.country, "time_zone": args.timezone,
            "currency": args.currency, "language": args.language,
        }))
        resp = json.loads(await ws.recv())
        if not resp.get("success"):
            sys.exit(f"config/core/update fehlgeschlagen: {resp}")
        print(f"-> Land={args.country} Zeitzone={args.timezone} "
              f"Waehrung={args.currency} Sprache={args.language} gesetzt")


if __name__ == "__main__":
    asyncio.run(main())
