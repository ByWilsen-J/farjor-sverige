"""
update_fartyg.py — Masterscript för dynamiska avgångar
======================================================
Hämtar exakta datumavgångar, fartygsnamn och källmeta från respektive
rederis dagskällor och uppdaterar `farjor_data.json`.

Kan köras manuellt: `python3 update_fartyg.py [YYYY-MM-DD]`

Källdataformat i farjor_data.json:
  fartyg_datum → { "YYYY-MM-DD" → { "Rederi:Avghamn→Ankhamn:HH:MM" → "Fartygsnamn" } }
  avgangar_datum → { "YYYY-MM-DD" → { "Rederi:Avghamn→Ankhamn:HH:MM" → { fartyg, anktid, ankomstdatum, kalla, kalllabel, kalldetalj } } }
  avgangsinstanser → { "YYYY-MM-DD" → [ ... ] }
"""

import json
import logging
import os
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import viking_line_scraper as vl
import tallink_scraper      as tl
import dfds_scraper         as dfds
import finnlines_scraper    as finn
import stena_line_scraper   as stena
import ttline_scraper       as ttline
from schedule_instances import build_base_instances, merge_dynamic_sailings, public_window

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


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def legacy_dynamic_sailings(avgangar_datum: dict) -> list[dict]:
    sailings: list[dict] = []
    for ds, poster in (avgangar_datum or {}).items():
        for nyckel, meta in (poster or {}).items():
            match = re.match(r"^([^:]+):(.+?)→(.+?):(\d{2}:\d{2})$", nyckel)
            if not match:
                continue
            rederi, avghamn, ankhamn, avgtid = match.groups()
            sailings.append({
                "date": ds,
                "rederi": rederi,
                "avghamn": avghamn,
                "ankhamn": ankhamn,
                "avgtid": avgtid,
                "anktid": meta.get("anktid", "") if isinstance(meta, dict) else "",
                "ankomstdatum": meta.get("ankomstdatum", ds) if isinstance(meta, dict) else ds,
                "fartyg": meta.get("fartyg", "") if isinstance(meta, dict) else str(meta or ""),
                "kalla": meta.get("kalla", "") if isinstance(meta, dict) else "",
                "source_label": meta.get("kalllabel", "") if isinstance(meta, dict) else "",
                "source_detail": meta.get("kalldetalj", "") if isinstance(meta, dict) else "",
                "source_type": meta.get("kalltyp", "") if isinstance(meta, dict) else "",
                "status": meta.get("status", "") if isinstance(meta, dict) else "",
                "traffic_comment": meta.get("traffic_comment", "") if isinstance(meta, dict) else "",
            })
    return sailings


SOURCE_DEFAULTS = {
    "Viking Line": {
        "kalla": "https://www.sales.vikingline.com/find-trip/timetable/traffic-bulletin/",
        "source_label": "Live-tidtabell",
        "source_detail": vl.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "Tallink Silja": {
        "kalla": "https://www.tallink.com/sv/tidtabeller",
        "source_label": "Live-tidtabell",
        "source_detail": tl.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "DFDS": {
        "kalla": "https://www.dfds.com/sv-se/fraktfarjor-och-logistik/rutter-och-tidtabeller",
        "source_label": "Live-tidtabell",
        "source_detail": dfds.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "Finnlines": {
        "kalla": "https://www.finnlines.com/freight/schedules/",
        "source_label": "Live-tidtabell",
        "source_detail": finn.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "Stena Line": {
        "kalla": "https://stenalinefreight.com/timetable/",
        "source_label": "Live-tidtabell",
        "source_detail": stena.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "TT-Line": {
        "kalla": "https://www.ttline.com/en/timetables/",
        "source_label": "Live-tidtabell",
        "source_detail": ttline.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "Polferries (POLSCA)": {
        "kalla": "https://www.polferries.com/schedule-timetable/",
        "source_label": "Datumtabell",
        "source_detail": "Polferries schedule timetable",
        "source_type": "date_table",
    },
}


def enrich_instance_sources(instances_by_date: dict[str, list[dict]]) -> None:
    for entries in instances_by_date.values():
        for inst in entries or []:
            operator = str(inst.get("source_operator") or inst.get("rederi") or "").strip()
            defaults = SOURCE_DEFAULTS.get(operator)
            if not defaults:
                continue
            if not inst.get("kalla"):
                inst["kalla"] = defaults["kalla"]
            if not inst.get("source_label"):
                inst["source_label"] = defaults["source_label"]
            if not inst.get("source_detail"):
                inst["source_detail"] = defaults["source_detail"]
            if not inst.get("source_type"):
                inst["source_type"] = defaults["source_type"]


def sync_legacy_fields_from_instances(instances_by_date: dict[str, list[dict]]) -> tuple[dict, dict]:
    fartyg_datum: dict[str, dict[str, str]] = {}
    avgangar_datum: dict[str, dict[str, dict]] = {}
    for ds, entries in (instances_by_date or {}).items():
        for inst in entries or []:
            if str(inst.get("source_type") or "") not in {"dynamic_schedule", "date_table"}:
                continue
            rederi = str(inst.get("source_operator") or inst.get("rederi") or "").strip()
            avghamn = str(inst.get("avghamn") or "").strip()
            ankhamn = str(inst.get("ankhamn") or "").strip()
            avgtid = str(inst.get("avgtid") or "").strip()
            if not (ds and rederi and avghamn and ankhamn and avgtid):
                continue
            key = bygg_nyckel(rederi, avghamn, ankhamn, avgtid)
            fartyg = str(inst.get("fartyg") or "").strip()
            if fartyg:
                fartyg_datum.setdefault(ds, {})[key] = fartyg
            avgangar_datum.setdefault(ds, {})[key] = {
                "fartyg": fartyg,
                "anktid": str(inst.get("anktid") or "").strip(),
                "ankomstdatum": str(inst.get("ankomstdatum") or ds).strip(),
                "kalla": str(inst.get("kalla") or "").strip(),
                "kalllabel": str(inst.get("source_label") or "").strip(),
                "kalldetalj": str(inst.get("source_detail") or "").strip(),
                "kalltyp": str(inst.get("source_type") or "").strip(),
                "status": str(inst.get("status") or "").strip(),
                "traffic_comment": str(inst.get("traffic_comment") or "").strip(),
            }
    return fartyg_datum, avgangar_datum


def prune_weekly_fallbacks_for_live_routes(
    instances_by_date: dict[str, list[dict]],
    sailings: list[dict],
) -> None:
    live_route_days: set[tuple[str, str, str, str]] = set()
    for sailing in sailings:
        dep_date_iso = str(sailing.get("date") or sailing.get("datum") or "").strip()
        rederi = str(sailing.get("rederi") or "").strip()
        avghamn = str(sailing.get("avghamn") or "").strip()
        ankhamn = str(sailing.get("ankhamn") or "").strip()
        source_type = str(sailing.get("source_type") or "dynamic_schedule").strip()
        if not dep_date_iso or not rederi or not avghamn or not ankhamn:
            continue
        if source_type != "dynamic_schedule":
            continue
        live_route_days.add((dep_date_iso, rederi, avghamn, ankhamn))

    for dep_date_iso, entries in instances_by_date.items():
        filtered: list[dict] = []
        for inst in entries or []:
            route_key = (
                dep_date_iso,
                str(inst.get("rederi") or "").strip(),
                str(inst.get("avghamn") or "").strip(),
                str(inst.get("ankhamn") or "").strip(),
            )
            if route_key in live_route_days and str(inst.get("source_type") or "") == "weekly_schedule":
                continue
            filtered.append(inst)
        instances_by_date[dep_date_iso] = filtered


def main():
    from_date = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    forward_days = env_int("FERRY_DYNAMIC_FORWARD_DAYS", 14)
    to_date = from_date + timedelta(days=forward_days)
    public_anchor_raw = os.getenv("FERRY_PUBLIC_ANCHOR_DATE", "").strip()
    public_anchor = date.fromisoformat(public_anchor_raw) if public_anchor_raw else date.today()
    public_start, public_end = public_window(public_anchor)
    public_start_iso = public_start.isoformat()
    public_end_iso = public_end.isoformat()
    log.info("Uppdaterar dynamiska avgångar %s – %s", from_date, to_date)
    log.info("Publiceringsfönster %s – %s", public_start, public_end)

    # Ladda befintlig JSON
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    fartyg_datum: dict = data.get("fartyg_datum", {})
    avgangar_datum: dict = data.get("avgangar_datum", {})
    avgangsinstanser: dict = build_base_instances(data, anchor=public_anchor)
    dynamic_sailings: list[dict] = legacy_dynamic_sailings(avgangar_datum)

    # Rensa legacy-fält utanför publiceringsfönstret
    for d in list(fartyg_datum.keys()):
        if d < public_start_iso or d > public_end_iso:
            del fartyg_datum[d]
            log.debug("Rensade gammalt datum: %s", d)
    for d in list(avgangar_datum.keys()):
        if d < public_start_iso or d > public_end_iso:
            del avgangar_datum[d]
            log.debug("Rensade gamla avgångsmeta: %s", d)

    def lägg_till(sailings: list[dict]):
        for s in sailings:
            ds     = s.get("date","")
            if not ds or not (public_start_iso <= ds <= public_end_iso):
                continue
            rederi  = s.get("rederi","")
            avghamn = s.get("avghamn","")
            ankhamn = s.get("ankhamn","")
            avgtid  = s.get("avgtid","") or s.get("departure_time","")
            fartyg  = s.get("fartyg","") or s.get("ship_name","")
            anktid = s.get("anktid","") or s.get("arrival_time","")
            ankomstdatum = s.get("ankomstdatum","") or s.get("arrival_date","") or ds
            kalla = s.get("kalla","") or s.get("source","")
            source_label = s.get("source_label", "") or s.get("kalllabel", "")
            source_detail = s.get("source_detail", "") or s.get("kalldetalj", "")
            source_type = s.get("source_type", "") or s.get("kalltyp", "")
            status = s.get("status", "")
            traffic_comment = s.get("traffic_comment", "")
            if not (ds and rederi and avghamn and ankhamn and avgtid):
                continue
            dynamic_sailings.append({
                "date": ds,
                "rederi": rederi,
                "avghamn": avghamn,
                "ankhamn": ankhamn,
                "avgtid": avgtid,
                "anktid": anktid,
                "ankomstdatum": ankomstdatum,
                "fartyg": fartyg,
                "kalla": kalla,
                "source_label": source_label,
                "source_detail": source_detail,
                "source_type": source_type,
                "status": status,
                "traffic_comment": traffic_comment,
            })
            if not (from_date.isoformat() <= ds <= to_date.isoformat()):
                continue
            if ds not in avgangar_datum:
                avgangar_datum[ds] = {}
            if fartyg:
                if ds not in fartyg_datum:
                    fartyg_datum[ds] = {}
            key = bygg_nyckel(rederi, avghamn, ankhamn, avgtid)
            if fartyg:
                fartyg_datum[ds][key] = fartyg
            avgangar_datum[ds][key] = {
                "fartyg": fartyg,
                "anktid": anktid,
                "ankomstdatum": ankomstdatum,
                "kalla": kalla,
                "kalllabel": source_label,
                "kalldetalj": source_detail,
                "kalltyp": source_type,
                "status": status,
                "traffic_comment": traffic_comment,
            }

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
                    "anktid": s.get("arrival_time", ""),
                    "ankomstdatum": s.get("arrival_date", s["date"]),
                    "fartyg":  s["ship_name"],
                    "rederi":  "Viking Line",
                    "kalla": s.get("kalla", ""),
                    "source_label": s.get("source_label", ""),
                    "source_detail": s.get("source_detail", ""),
                    "source_type": s.get("source_type", ""),
                    "status": s.get("availability", ""),
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

    # ── Finnlines ──
    log.info("=== Finnlines ===")
    finn_sailings = finn.fetch_all(from_date, to_date)
    lägg_till(finn_sailings)

    # ── Stena Line ──
    log.info("=== Stena Line ===")
    stena_sailings = stena.fetch_all(from_date, to_date)
    lägg_till(stena_sailings)

    # ── TT-Line ──
    log.info("=== TT-Line ===")
    ttline_sailings = ttline.fetch_all(from_date, to_date)
    lägg_till(ttline_sailings)

    merge_dynamic_sailings(avgangsinstanser, dynamic_sailings)
    prune_weekly_fallbacks_for_live_routes(avgangsinstanser, dynamic_sailings)
    enrich_instance_sources(avgangsinstanser)
    fartyg_datum, avgangar_datum = sync_legacy_fields_from_instances(avgangsinstanser)

    # Spara tillbaka
    data["fartyg_datum"] = fartyg_datum
    data["avgangar_datum"] = avgangar_datum
    data["avgangsinstanser"] = avgangsinstanser
    data["meta"]["uppdaterad"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["meta"]["avgangsinstans_dagar"] = len(avgangsinstanser)
    data["meta"]["publiceringsfonster"] = f"{public_start_iso} till {public_end_iso}"
    data["meta"]["dynamic_window"] = f"{from_date.isoformat()} till {to_date.isoformat()}"

    # Räkna
    totalt = sum(len(v) for v in fartyg_datum.values())
    log.info("Totalt %d fartygsuppslag över %d datum.", totalt, len(fartyg_datum))
    instans_totalt = sum(len(v) for v in avgangsinstanser.values())
    log.info("Totalt %d avgångsinstanser över %d datum.", instans_totalt, len(avgangsinstanser))

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))

    log.info("farjor_data.json uppdaterad.")


if __name__ == "__main__":
    main()
