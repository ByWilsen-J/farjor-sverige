"""
update_fartyg.py — Masterscript för fartygsnamn
================================================
Hämtar fartygsnamn per avgång från respektive rederis API och
uppdaterar avsnittet "fartyg_datum" i farjor_data.json.

Körs var 14:e dag via GitHub Actions (se .github/workflows/update-timetables.yml).
Kan även köras manuellt: python3 update_fartyg.py [YYYY-MM-DD]

Källdataformat i farjor_data.json:
  fartyg_datum → { "YYYY-MM-DD" → { "Rederi:Avghamn→Ankhamn:HH:MM" → "Fartygsnamn" } }
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import viking_line_scraper as vl
import tallink_scraper      as tl
import dfds_scraper         as dfds

DATA_FILE = Path(__file__).parent / "farjor_data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("update_fartyg")


def bygg_nyckel(rederi: str, avghamn: str, ankhamn: str, avgtid: str) -> str:
    """Bygg uppslagsnyckel: 'Rederi:Avghamn→Ankhamn:HH:MM'"""
    return f"{rederi}:{avghamn}\u2192{ankhamn}:{avgtid}"


def main():
    from_date = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    to_date   = from_date + timedelta(days=14)
    log.info("Uppdaterar fartygsnamn %s – %s", from_date, to_date)

    # Ladda befintlig JSON
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    fartyg_datum: dict = data.get("fartyg_datum", {})

    # Rensa datum äldre än igår
    cutoff = (from_date - timedelta(days=1)).isoformat()
    for d in list(fartyg_datum.keys()):
        if d < cutoff:
            del fartyg_datum[d]
            log.debug("Rensade gammalt datum: %s", d)

    def lägg_till(sailings: list[dict]):
        for s in sailings:
            ds     = s.get("date","")
            if not (from_date.isoformat() <= ds <= to_date.isoformat()):
                continue
            rederi  = s.get("rederi","")
            avghamn = s.get("avghamn","")
            ankhamn = s.get("ankhamn","")
            avgtid  = s.get("avgtid","") or s.get("departure_time","")
            fartyg  = s.get("fartyg","") or s.get("ship_name","")
            if not (ds and rederi and avgtid and fartyg):
                continue
            if ds not in fartyg_datum:
                fartyg_datum[ds] = {}
            key = bygg_nyckel(rederi, avghamn, ankhamn, avgtid)
            fartyg_datum[ds][key] = fartyg

    # ── Viking Line ──
    log.info("=== Viking Line ===")
    # Veckovy returnerar 7 dagar; gör 2 anrop för att täcka 14 dagar
    for offset in [0, 7]:
        fd = from_date + timedelta(days=offset)
        vl_data = vl.fetch_all_routes(from_date=fd.isoformat())
        sailings = []
        for route_key, route_sailings in vl_data.items():
            for s in route_sailings:
                sailings.append({
                    "date":    s["date"],
                    "avghamn": s["pol"],
                    "ankhamn": s["pod"],
                    "avgtid":  s["departure_time"],
                    "fartyg":  s["ship_name"],
                    "rederi":  "Viking Line",
                })
        lägg_till(sailings)

    # ── Tallink Silja ──
    log.info("=== Tallink Silja ===")
    tl_sailings = tl.fetch_all(from_date, to_date)
    lägg_till(tl_sailings)

    # ── DFDS ──
    log.info("=== DFDS ===")
    dfds_sailings = dfds.fetch_all(from_date, to_date)
    lägg_till(dfds_sailings)

    # Spara tillbaka
    data["fartyg_datum"] = fartyg_datum
    data["meta"]["uppdaterad"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Räkna
    totalt = sum(len(v) for v in fartyg_datum.values())
    log.info("Totalt %d fartygsuppslag över %d datum.", totalt, len(fartyg_datum))

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))

    log.info("farjor_data.json uppdaterad.")


if __name__ == "__main__":
    main()
