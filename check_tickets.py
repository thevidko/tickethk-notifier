#!/usr/bin/env python3
"""Hlídá, jestli se na tickethk.cz neuvolnily vstupenky, a pošle notifikaci přes ntfy.

Stránka akce je Inertia.js aplikace – veškerá data o zónách (cena, zbývající
kapacita, is_sellable) jsou v JSONu v atributu data-page, takže není potřeba
prohlížeč ani parsování HTML.

Notifikuje jen při změně stavu (vyprodáno -> dostupné a zpět), stav si pamatuje
v STATE_FILE. Spouštěj z cronu / systemd timeru, nebo nastav INTERVAL (sekundy)
a skript poběží ve smyčce sám (tak běží v Dockeru).
"""
import base64
import html
import json
import os
import re
import random
import sys
import time
import urllib.request

EVENT_URL = os.environ.get("EVENT_URL", "https://tickethk.cz/event/uhkhall26")
NTFY_URL = os.environ.get("NTFY_URL")  # např. https://ntfy.sh/muj-tajny-topic-123
STATE_FILE = os.environ.get(
    "STATE_FILE", os.path.expanduser("~/.cache/tickethk-notifier.json")
)
# Volitelně jen některé zóny, např. ZONES="Student" (porovnává se s českým názvem)
ZONES = [z.strip().lower() for z in os.environ.get("ZONES", "").split(",") if z.strip()]
# Pokud je nastaveno, skript běží ve smyčce a kontroluje každých INTERVAL sekund
INTERVAL = int(os.environ.get("INTERVAL", "0"))

UA = "Mozilla/5.0 (X11; Linux x86_64) tickethk-notifier/1.0"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_zones(page):
    m = re.search(r'data-page="([^"]+)"', page)
    if not m:
        raise ValueError("na stránce chybí data-page – změnil se web?")
    event = json.loads(html.unescape(m.group(1)))["props"]["event"]
    zones = []
    for z in event["zones"]:
        name = (z.get("name") or {}).get("cs") or str(z["id"])
        if ZONES and name.lower() not in ZONES:
            continue
        if not z.get("show", 1):
            continue
        zones.append(
            {
                "id": z["id"],
                "name": name,
                "price": z.get("price"),
                "left": z.get("capacity") or 0,
                "sellable": bool(z.get("is_sellable")),
            }
        )
    return event, zones


def notify(title, message, priority="default", tags=""):
    print(f"[notify] {title}: {message}")
    if not NTFY_URL:
        return
    req = urllib.request.Request(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            # HTTP hlavičky musí být latin-1, ntfy umí RFC 2047 pro UTF-8
            "Title": "=?UTF-8?B?" + base64.b64encode(title.encode()).decode() + "?=",
            "Priority": priority,
            "Tags": tags,
            "Click": EVENT_URL,
        },
    )
    urllib.request.urlopen(req, timeout=30).read()


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main():
    state = load_state()
    try:
        event, zones = parse_zones(fetch(EVENT_URL))
    except Exception as e:  # síť, změna struktury webu...
        print(f"chyba: {e}", file=sys.stderr)
        if not state.get("error"):
            notify("Ticket notifier: chyba", f"{e}", tags="warning")
        state["error"] = True
        save_state(state)
        return 1

    available = [z for z in zones if z["left"] > 0 and z["sellable"]]
    was_available = state.get("available", False)
    summary = ", ".join(f"{z['name']} {z['price']} Kč: {z['left']} ks" for z in available)

    if available and not was_available:
        notify(
            f"Vstupenky zpět v prodeji: {event['name']['cs']}",
            summary,
            priority="urgent",
            tags="tada,ticket",
        )
    elif not available and was_available:
        notify(f"Zase vyprodáno: {event['name']['cs']}", "Vstupenky jsou pryč.", tags="x")

    print(
        "dostupné: " + summary
        if available
        else "vyprodáno (" + ", ".join(f"{z['name']}={z['left']}" for z in zones) + ")"
    )
    save_state({"available": bool(available), "error": False})
    return 0


if __name__ == "__main__":
    if not INTERVAL:
        sys.exit(main())
    while True:
        main()
        sys.stdout.flush()
        time.sleep(INTERVAL + random.uniform(0, INTERVAL / 4))
