"""
DFDS Freight — Timetable Scraper
==================================
Hämtar avgångar och fartygsnamn för fraktrutter mot/från Sverige
via DFDS öppna REST-API (dfds.com/api/timetable).

Inga API-nycklar krävs. Returnerar vehicleName per avgång.

Rutter som täcks (berör Sverige):
  EEPLN ↔ SEKPS  (Paldiski – Kapellskär)
  LTKLJ ↔ SEKAN  (Klaipeda – Karlshamn)
  LTKLJ ↔ SETRG  (Klaipeda – Trelleborg)
  GBIMM ↔ SEGOT  (Immingham – Göteborg)
  BEGNE ↔ SEGOT  (Ghent – Göteborg)
"""

import logging
import requests
from datetime import date, timedelta, timezone, datetime
from typing import Optional

BASE_URL = "https://www.dfds.com/api/timetable"
HEADERS  = {"Accept": "application/json"}

# Portkoder (DFDS 5-char) → visningsnamn
PORT_NAMES = {
    "EEPLN": "Paldiski",
    "SEKPS": "Kapellskär",
    "LTKLJ": "Klaipėda",
    "SEKAN": "Karlshamn",
    "SETRG": "Trelleborg",
    "SEGOT": "Göteborg",
    "BEGNE": "Ghent",
    "GBIMM": "Immingham",
    "GBNCL": "Newcastle",
    "DKEBJ": "Esbjerg",
    "NLRTM": "Rotterdam",
}

# Rutter att hämta (POL, POD)
RUTTER = [
    ("EEPLN","SEKPS"), ("SEKPS","EEPLN"),
    ("LTKLJ","SEKAN"), ("SEKAN","LTKLJ"),
    ("LTKLJ","SETRG"), ("SETRG","LTKLJ"),
    ("GBIMM","SEGOT"), ("SEGOT","GBIMM"),
    ("BEGNE","SEGOT"), ("SEGOT","BEGNE"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dfds")


def parse_local_time(dt_str: str) -> tuple[str, str]:
    """
    Parsar "2026-05-19T19:00:00+03:00" → ("2026-05-19", "19:00").
    Returnerar datum och tid ur ISO-strängen (lokal tid).
    """
    if not dt_str or len(dt_str) < 16:
        return "", ""
    return dt_str[:10], dt_str[11:16]


def fetch_route(pol: str, pod: str, date_from: date, date_to: date) -> Optional[list]:
    params = {
        "portOfLoading":   pol,
        "portOfDischarge": pod,
        "dateFrom": date_from.isoformat() + "T00:00:00Z",
        "dateTo":   date_to.isoformat()   + "T23:59:59Z",
    }
    try:
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        log.warning("DFDS svarade med oväntat format för %s→%s: %s", pol, pod, type(data))
        return None
    except requests.exceptions.RequestException as e:
        log.error("DFDS API-fel (%s→%s): %s", pol, pod, e)
        return None


def fetch_all(date_from: date = None, date_to: date = None) -> list[dict]:
    """
    Hämta alla rutter. Returnerar platt lista av:
      { date, avghamn, ankhamn, avgtid, fartyg, rederi }
    """
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=14)

    all_sailings = []
    for pol, pod in RUTTER:
        log.info("Hämtar DFDS %s→%s (%s – %s)…", pol, pod,
                 date_from.isoformat(), date_to.isoformat())
        data = fetch_route(pol, pod, date_from, date_to)
        if not data:
            continue
        for avg in data:
            dep_str = avg.get("scheduledDeparture","")
            arr_str = avg.get("scheduledArrival","") or avg.get("estimatedArrival","")
            ds, avgtid = parse_local_time(dep_str)
            ankdatum, anktid = parse_local_time(arr_str)
            if not ds or not avgtid:
                continue
            fartyg = avg.get("vehicleName","") or ""
            all_sailings.append({
                "date":    ds,
                "avghamn": PORT_NAMES.get(pol, pol),
                "ankhamn": PORT_NAMES.get(pod, pod),
                "avgtid":  avgtid,
                "ankomstdatum": ankdatum,
                "anktid": anktid,
                "fartyg":  fartyg,
                "rederi":  "DFDS",
            })
        log.info("  %d avgångar.", sum(1 for a in all_sailings if a.get("avghamn")==PORT_NAMES.get(pol,pol)))
    return all_sailings


if __name__ == "__main__":
    import sys
    from_d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    to_d   = from_d + timedelta(days=7)
    for s in fetch_all(from_d, to_d):
        print(f"  {s['date']}  {s['avgtid']}  {s['avghamn']}→{s['ankhamn']}  {s['fartyg']}")
