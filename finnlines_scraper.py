"""
Finnlines — Timetable Scraper
=============================
Hämtar avgångar och fartygsnamn via Finnlines publika GraphQL-API.

Returnerar samma format som övriga skrapare:
  { date, avghamn, ankhamn, avgtid, fartyg, rederi }
"""

import logging
from datetime import date, timedelta
from typing import Optional

import requests

GRAPHQL_URL = "https://dm3xyy44wbeivgqmeymvmw22be.appsync-api.eu-central-1.amazonaws.com/graphql"
API_KEY = "da2-zvuktusyubbstlw7khps4vyeie"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
}

PORT_NAMES = {
    "FINLI": "Naantali",
    "SEKPS": "Kapellskär",
    "DETRV": "Travemünde",
    "SEMMA": "Malmö",
}

SHIP_NAMES = {
    "FICO": "Finncanopus",
    "FISI": "Finnsirius",
    "FFEL": "Finnfellow",
    "FIPA": "Finnpartner",
    "FISW": "Finnswan",
    "FITR": "Finntrader",
    "FIST": "Finnstar",
    "FILA": "Finnlady",
    "FIMA": "Finnmaid",
}

RUTTER = [
    ("FINLI", "SEKPS"),
    ("SEKPS", "FINLI"),
    ("DETRV", "SEMMA"),
    ("SEMMA", "DETRV"),
]

SAILINGS_QUERY = """
query ListSailingsAvailability($query: SailingsQuery!) {
  listSailingsAvailability(query: $query) {
    ... on Sailing {
      departurePort
      arrivalPort
      departureDate
      departureTime
      arrivalDate
      arrivalTime
      shipName
      shipCode
    }
    ... on ApiError {
      __typename
    }
  }
}
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("finnlines")


def parse_local_time(dt_str: str) -> tuple[str, str]:
    if not dt_str or len(dt_str) < 16:
        return "", ""
    return dt_str[:10], dt_str[11:16]


def normalize_ship(name: str, code: str = "") -> str:
    if code and code in SHIP_NAMES:
        return SHIP_NAMES[code]
    name = (name or "").strip()
    if name.isupper():
        return name.lower().capitalize()
    return name


def fetch_route(dep: str, arr: str, date_from: date, date_to: date) -> Optional[list]:
    days = max(1, (date_to - date_from).days + 1)
    payload = {
        "query": SAILINGS_QUERY,
        "variables": {
            "query": {
                "currency": "EUR",
                "departurePort": dep,
                "arrivalPort": arr,
                "startDate": date_from.isoformat(),
                "endDate": date_to.isoformat(),
                "numberOfDays": days,
                "numberOfDepartures": 80,
            }
        },
    }
    try:
        resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=25)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            log.warning("Finnlines API-fel %s→%s: %s", dep, arr, payload["errors"])
            return None
        result = (payload.get("data") or {}).get("listSailingsAvailability", [])
        if not isinstance(result, list):
            log.warning("Finnlines svarade med oväntat format för %s→%s", dep, arr)
            return None
        return result
    except requests.exceptions.RequestException as e:
        log.error("Finnlines API-fel (%s→%s): %s", dep, arr, e)
        return None


def fetch_all(date_from: date = None, date_to: date = None) -> list[dict]:
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=14)

    all_sailings = []
    for dep, arr in RUTTER:
        log.info("Hämtar Finnlines %s→%s (%s – %s)…", dep, arr, date_from, date_to)
        data = fetch_route(dep, arr, date_from, date_to)
        if data is None:
            continue
        for sailing in data:
            ds = sailing.get("departureDate", "")
            avgtid = (sailing.get("departureTime", "") or "")[:5]
            ankdatum = sailing.get("arrivalDate", "") or ""
            anktid = (sailing.get("arrivalTime", "") or "")[:5]
            if not ds or not avgtid:
                continue
            fartyg = normalize_ship(sailing.get("shipName", ""), sailing.get("shipCode", ""))
            all_sailings.append({
                "date": ds,
                "avghamn": PORT_NAMES.get(dep, dep),
                "ankhamn": PORT_NAMES.get(arr, arr),
                "avgtid": avgtid,
                "ankomstdatum": ankdatum,
                "anktid": anktid,
                "fartyg": fartyg,
                "rederi": "Finnlines",
            })
        log.info("  %d avgångar.", len(data))
    return all_sailings


if __name__ == "__main__":
    import sys
    from_d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    to_d = from_d + timedelta(days=7)
    for s in fetch_all(from_d, to_d):
        print(f"  {s['date']}  {s['avgtid']}  {s['avghamn']}→{s['ankhamn']}  {s['fartyg']}")
