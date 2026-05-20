"""
Tallink Silja — Timetable Scraper
==================================
Hämtar avgångar och fartygsnamn för rutter som berör Sverige
via Talllinks publika CMS-API (cms-web-api-nx.tallink.com).

Inga API-nycklar krävs. CORS blockerar browser-anrop men server-side
fungerar utan begränsningar.

Rutter som täcks (mot/från Sverige):
  hel ↔ sto   (Helsingfors – Stockholm, Silja Line)
  tur ↔ sto   (Åbo – Stockholm, Silja Line)
  pal ↔ kap   (Paldiski – Kapellskär, Tallink)
  tal ↔ sto   (Tallinn – Stockholm, Tallink)
"""

import logging
import requests
from datetime import date, timedelta
from typing import Optional

BASE_URL = "https://cms-web-api-nx.tallink.com/api/seaweb/timetables"
HEADERS  = {"Accept": "application/json", "Accept-Language": "en"}

# Fartyg: API-kod → visningsnamn
FARTYG = {
    "MEGASTAR":    "Megastar",
    "MYSTAR":      "MyStar",
    "VICTORIA":    "Victoria I",
    "PRINCESS":    "Baltic Princess",
    "SERENADE":    "Silja Serenade",
    "SYMPHONY":    "Silja Symphony",
    "GALAXY":      "Galaxy",
    "ROMANTIKA":   "Romantika",
    "ISABELLE":    "Isabelle",
    "AURORA":      "Silja Aurora",
    "EUROPA":      "Star",          # Tallink Star
    "SILJA_SERENADE": "Silja Serenade",
    "SILJA_SYMPHONY": "Silja Symphony",
    "SILJA_EUROPA":   "Silja Europa",
}

# Portnamn: API-kod → svenska visningsnamn
PORT_NAMES = {
    "hel": "Helsingfors",
    "sto": "Stockholm",
    "tur": "Åbo",
    "tal": "Tallinn",
    "pal": "Paldiski",
    "kap": "Kapellskär",
}

# Rederimärke per rutt (för nyckelbyggnad i fartyg_datum)
REDERI_PER_RUTT = {
    ("hel","sto"): "Tallink Silja",
    ("sto","hel"): "Tallink Silja",
    ("tur","sto"): "Tallink Silja",
    ("sto","tur"): "Tallink Silja",
    ("tal","sto"): "Tallink Silja",
    ("sto","tal"): "Tallink Silja",
    ("pal","kap"): "DFDS",
    ("kap","pal"): "DFDS",
}

# Rutter att hämta
RUTTER = [
    ("hel","sto"), ("sto","hel"),
    ("tur","sto"), ("sto","tur"),
    ("pal","kap"), ("kap","pal"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("tallink")


def resolve_fartyg(code: str) -> str:
    """Konvertera ship-code till läsbart fartygsnamn."""
    if not code:
        return ""
    if code in FARTYG:
        return FARTYG[code]
    # Fallback: title-case på koden
    return code.replace("_", " ").title()


def fetch_route(dep: str, arr: str, date_from: date, date_to: date) -> Optional[dict]:
    params = {
        "locale": "en",
        "country": "XZ",
        "from": dep,
        "to": arr,
        "oneWay": "false",
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "voyageType": "ROUTETRIP",
        "includeOvernight": "true",
        "searchFutureSails": "false",
    }
    try:
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        log.error("Tallink API-fel (%s→%s): %s", dep, arr, e)
        return None


def extract_sailings(data: dict, dep: str, arr: str) -> list[dict]:
    """
    Returnerar lista av dicts:
      { date, avghamn, ankhamn, avgtid, fartyg, rederi }
    """
    if not isinstance(data, dict) or "trips" not in data:
        log.warning("Oväntat schema för %s→%s", dep, arr)
        return []

    sailings = []
    rederi = REDERI_PER_RUTT.get((dep, arr), "Tallink Silja")
    for ds, trips in data["trips"].items():
        for sail in trips.get("outwards", []):
            dep_dt = sail.get("departureIsoDate", "")   # "2026-05-20T16:00"
            arr_dt = sail.get("arrivalIsoDate", "")
            avgtid = dep_dt[11:16] if len(dep_dt) >= 16 else ""
            ankdatum = arr_dt[:10] if len(arr_dt) >= 10 else ""
            anktid = arr_dt[11:16] if len(arr_dt) >= 16 else ""
            if not avgtid:
                continue
            fartyg = resolve_fartyg(sail.get("shipCode", ""))
            sailings.append({
                "date":     ds,
                "avghamn":  PORT_NAMES.get(dep, dep),
                "ankhamn":  PORT_NAMES.get(arr, arr),
                "avgtid":   avgtid,
                "ankomstdatum": ankdatum,
                "anktid": anktid,
                "fartyg":   fartyg,
                "rederi":   rederi,
            })
    return sailings


def fetch_all(date_from: date = None, date_to: date = None) -> list[dict]:
    """
    Hämta alla rutter. Returnerar platt lista av sailing-dicts.
    """
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=14)

    all_sailings = []
    for dep, arr in RUTTER:
        log.info("Hämtar Tallink %s→%s (%s – %s)…", dep, arr,
                 date_from.isoformat(), date_to.isoformat())
        data = fetch_route(dep, arr, date_from, date_to)
        if data is None:
            continue
        sailings = extract_sailings(data, dep, arr)
        log.info("  %d avgångar.", len(sailings))
        all_sailings.extend(sailings)
    return all_sailings


if __name__ == "__main__":
    import sys
    from_d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    to_d   = from_d + timedelta(days=7)
    for s in fetch_all(from_d, to_d):
        print(f"  {s['date']}  {s['avgtid']}  {s['avghamn']}→{s['ankhamn']}  {s['fartyg']}")
