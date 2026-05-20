"""
Viking Line — Timetable Scraper
================================
Hämtar avgångar via Viking Lines interna Protheus API.
API:et är odokumenterat men oautentiserat och publikt cacheat (max-age=180s).

Rutter som täcks:
  STO → HEL  (Stockholm → Helsingfors)
  HEL → STO  (Helsingfors → Stockholm)
  STO → TKU  (Stockholm → Åbo)
  TKU → STO  (Åbo → Stockholm)

Felhantering:
  - Varnar om API-svaret har oväntat schema (trolig API-förändring)
  - Varnar om fartygsnamn saknas i lookup-tabellen (ny båt)
  - Varnar om HTTP-fel uppstår

Se viking_line_api_rediscovery_prompt.md om API:et slutar fungera.
"""

import base64
import json
import logging
import sys
from datetime import date
from typing import Optional

import requests

# ── Konfiguration ──────────────────────────────────────────────────────────────

BASE_URL = "https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en"

SHIP_CODES = {
    "CI": "Viking Cinderella",
    "GA": "Gabriella",
    "GR": "Viking Grace",
    "GL": "Viking Glory",
    "XP": "Viking XPRS",
    "AB": "Amorella",
}

PORT_NAMES = {
    "STO": "Stockholm",
    "HEL": "Helsingfors",
    "TKU": "Åbo",
    "KAP": "Kapellskär",
    "MAR": "Mariehamn",
    "LAN": "Långnäs",
    "TAL": "Tallinn",
}

ROUTES = [
    ("STO", "HEL"),
    ("HEL", "STO"),
    ("STO", "TKU"),
    ("TKU", "STO"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("viking_line")


# ── API-anrop ──────────────────────────────────────────────────────────────────

def build_params(search_date: str, dep: str, arr: str) -> str:
    payload = {
        "searchDate": search_date,
        "departurePort": dep,
        "arrivalPort": arr,
        "numberOfAdults": 1,
        "childrenAges": [],
        "vehicle": {"code": "NONE", "quantity": 1},
        "club": "NONE",
    }
    return base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


def fetch_week(search_date: str, dep: str, arr: str) -> Optional[dict]:
    encoded = build_params(search_date, dep, arr)
    url = f"{BASE_URL}/search-ferry/week/{encoded}"
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        log.error("HTTP-fel vid anrop till Viking Line API: %s — %s", url, e)
        log.error(">>> API:et kan ha forandrats. Se viking_line_api_rediscovery_prompt.md")
        return None
    except requests.exceptions.RequestException as e:
        log.error("Natverksfel: %s", e)
        return None


# ── Schemavalidering ───────────────────────────────────────────────────────────

REQUIRED_JOURNEY_FIELDS = {
    "departurePort", "arrivalPort", "departureDate", "arrivalDate", "ship"
}
REQUIRED_DATE_FIELDS = {"localDateTime", "localTime", "timeZoneInfo"}


def validate_response(data: dict, route_label: str) -> bool:
    if "result" not in data or "dateHits" not in data.get("result", {}):
        log.warning(
            "SCHEMAVARNING [%s]: 'result.dateHits' saknas. "
            "API-strukturen kan ha forandrats. Se rediscovery-prompten.",
            route_label,
        )
        return False
    for date_hit in data["result"]["dateHits"]:
        for hit in date_hit.get("hits", []):
            oj = hit.get("booking", {}).get("outwardJourney", {})
            missing = REQUIRED_JOURNEY_FIELDS - set(oj.keys())
            if missing:
                log.warning(
                    "SCHEMAVARNING [%s]: Falt saknas i outwardJourney: %s. "
                    "API-strukturen kan ha forandrats.",
                    route_label, missing,
                )
                return False
            for date_field in ["departureDate", "arrivalDate"]:
                missing_df = REQUIRED_DATE_FIELDS - set(oj.get(date_field, {}).keys())
                if missing_df:
                    log.warning(
                        "SCHEMAVARNING [%s]: Falt saknas i %s: %s.",
                        route_label, date_field, missing_df,
                    )
                    return False
    return True


# ── Parsing ────────────────────────────────────────────────────────────────────

def resolve_ship(code: str, route_label: str) -> str:
    if code not in SHIP_CODES:
        log.warning(
            "OKAND FARTYGSKOD [%s]: '%s' — ny bat i trafik? Uppdatera SHIP_CODES.",
            route_label, code,
        )
        return f"Okant fartyg ({code})"
    return SHIP_CODES[code]


def extract_sailings(data: dict, dep: str, arr: str) -> list:
    route_label = f"{dep}->{arr}"
    if not validate_response(data, route_label):
        return []
    sailings = []
    for date_hit in data["result"]["dateHits"]:
        for hit in date_hit.get("hits", []):
            oj = hit["booking"]["outwardJourney"]
            ship_code = oj.get("ship", "?")
            sailings.append({
                "date":           date_hit["date"],
                "pol":            PORT_NAMES.get(oj["departurePort"], oj["departurePort"]),
                "pod":            PORT_NAMES.get(oj["arrivalPort"], oj["arrivalPort"]),
                "departure_time": oj["departureDate"]["localTime"],
                "departure_tz":   oj["departureDate"]["timeZoneInfo"],
                "arrival_time":   oj["arrivalDate"]["localTime"],
                "arrival_tz":     oj["arrivalDate"]["timeZoneInfo"],
                "ship_code":      ship_code,
                "ship_name":      resolve_ship(ship_code, route_label),
                "stops":          [PORT_NAMES.get(s["port"], s["port"])
                                   for s in oj.get("stops", [])],
                "availability":   hit.get("availability", "UNKNOWN"),
            })
    return sailings


# ── Huvudfunktion ──────────────────────────────────────────────────────────────

def fetch_all_routes(from_date=None):
    search_date = from_date or date.today().isoformat()
    results = {}
    for dep, arr in ROUTES:
        label = f"{dep}->{arr}"
        log.info("Hamtar %s fran %s...", label, search_date)
        data = fetch_week(search_date, dep, arr)
        if data is None:
            results[label] = []
            continue
        sailings = extract_sailings(data, dep, arr)
        log.info("  %d avganger hittade.", len(sailings))
        results[label] = sailings
    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from_date = sys.argv[1] if len(sys.argv) > 1 else None
    all_sailings = fetch_all_routes(from_date)
    for route, sailings in all_sailings.items():
        print(f"\n{'='*60}")
        print(f"  {route}  ({len(sailings)} avganger)")
        print(f"{'='*60}")
        for s in sailings:
            stops = f" via {', '.join(s['stops'])}" if s["stops"] else ""
            print(
                f"  {s['date']}  {s['departure_time']} -> {s['arrival_time']}"
                f"{stops}  |  {s['ship_name']}  |  {s['availability']}"
            )
