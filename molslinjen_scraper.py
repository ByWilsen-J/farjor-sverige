"""
Molslinjen family — AI schedule catalog scraper
===============================================
Hämtar aktuella avgångar och fartygsnamn från Molslinjens officiella
JSON-LD-katalog för linjer som berör Sverige:

  Bornholmslinjen   Ystad ↔ Rønne
  Øresundslinjen    Helsingør ↔ Helsingborg

Katalogen är avsedd som officiell, aktuell tidtabellskälla. Den returnerar
normalt nuvarande/kommande katalogfönster, inte hela projektets tremånaders-
fönster, så den används som dynamisk datumkälla där den har data.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import requests


BASE_URL = "https://new.api.molslinjen.dk/api/v1/ai/markup/data-catalog"
SOURCE_DETAIL = "Molslinjen AI schedule catalog"

ROUTES = [
    {
        "line": "2",
        "route_id": "SVE7",
        "operator": "Bornholmslinjen",
        "avghamn": "Ystad",
        "ankhamn": "Rønne",
    },
    {
        "line": "2",
        "route_id": "BOR7",
        "operator": "Bornholmslinjen",
        "avghamn": "Rønne",
        "ankhamn": "Ystad",
    },
    {
        "line": "7",
        "route_id": "SJÆ22",
        "operator": "Øresundslinjen",
        "avghamn": "Helsingør",
        "ankhamn": "Helsingborg",
    },
    {
        "line": "7",
        "route_id": "SVE22",
        "operator": "Øresundslinjen",
        "avghamn": "Helsingborg",
        "ankhamn": "Helsingør",
    },
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("molslinjen")


def headers_for(line: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Language": "da",
        "User-Agent": "Mozilla/5.0",
        "source": "web",
        "contentsource": "U12",
        "clientPlatform": "Nuxt",
        "site": line,
        "line": line,
        "language": "da",
        "lang": "da",
    }


def source_url(line: str, route_id: str) -> str:
    return f"{BASE_URL}?language=da&line={line}&routeId={route_id}"


def parse_time(value: str) -> tuple[str, str]:
    if not value or len(value) < 16:
        return "", ""
    return value[:10], value[11:16]


def parse_vessel(description: str) -> str:
    # "Ystad - Rønne, Express 5" -> "Express 5"
    parts = [part.strip() for part in str(description or "").split(",")]
    return parts[-1] if len(parts) > 1 else ""


def fetch_route(route: dict) -> list[dict]:
    line = route["line"]
    route_id = route["route_id"]
    try:
        response = requests.get(
            BASE_URL,
            params={"language": "da", "line": line, "routeId": route_id},
            headers=headers_for(line),
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        log.error("Molslinjen API-fel (%s): %s", route_id, exc)
        return []
    except ValueError as exc:
        log.error("Molslinjen svarade inte med JSON (%s): %s", route_id, exc)
        return []

    entries = ((payload.get("dataset") or {}).get("mainEntity") or [])
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        log.warning("Oväntat Molslinjen-schema för %s", route_id)
        return []

    sailings: list[dict] = []
    for item in entries:
        dep_date, dep_time = parse_time(str(item.get("departureTime") or ""))
        arr_date, arr_time = parse_time(str(item.get("arrivalTime") or ""))
        if not dep_date or not dep_time:
            continue
        vessel = parse_vessel(str(item.get("description") or ""))
        sailings.append({
            "date": dep_date,
            "avghamn": route["avghamn"],
            "ankhamn": route["ankhamn"],
            "avgtid": dep_time,
            "ankomstdatum": arr_date or dep_date,
            "anktid": arr_time,
            "fartyg": vessel,
            "rederi": route["operator"],
            "kalla": source_url(line, route_id),
            "source_label": "Live-tidtabell",
            "source_detail": SOURCE_DETAIL,
            "source_type": "dynamic_schedule",
            "is_exact": bool(vessel),
        })
    return sailings


def fetch_all(date_from: date | None = None, date_to: date | None = None) -> list[dict]:
    # API:t ignorerar datumparametrar i nuläget, men signaturen matchar övriga
    # skrapare så masterkedjan kan anropa den konsekvent.
    all_sailings: list[dict] = []
    for route in ROUTES:
        log.info("Hämtar Molslinjen %s (%s)…", route["route_id"], route["operator"])
        sailings = fetch_route(route)
        log.info("  %d avgångar.", len(sailings))
        all_sailings.extend(sailings)
    return all_sailings


if __name__ == "__main__":
    for sailing in fetch_all(date.today(), date.today() + timedelta(days=1)):
        print(
            f"{sailing['date']} {sailing['avgtid']} "
            f"{sailing['avghamn']}→{sailing['ankhamn']} {sailing['fartyg']}"
        )
