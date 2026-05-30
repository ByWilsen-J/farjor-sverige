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
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import viking_line_scraper as vl
import tallink_scraper      as tl
import dfds_scraper         as dfds
import finnlines_scraper    as finn
import stena_line_scraper   as stena
import ttline_scraper       as ttline
import molslinjen_scraper   as molslinjen
from route_registry import filter_instances_to_primary_sources
from schedule_instances import build_base_instances, merge_dynamic_sailings, parse_time_minutes, public_window

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


def normalize_fartyg_datum(raw: object) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    if not isinstance(raw, dict):
        return normalized
    for ds, poster in raw.items():
        if isinstance(poster, dict):
            normalized[str(ds)] = {
                str(nyckel): str(fartyg or "")
                for nyckel, fartyg in poster.items()
            }
            continue
        if isinstance(poster, list):
            normalized[str(ds)] = {
                str(nyckel): ""
                for nyckel in poster
                if isinstance(nyckel, str)
            }
    return normalized


def normalize_avgangar_datum(raw: object) -> dict[str, dict[str, dict]]:
    normalized: dict[str, dict[str, dict]] = {}
    if not isinstance(raw, dict):
        return normalized
    for ds, poster in raw.items():
        day_entries: dict[str, dict] = {}
        if isinstance(poster, dict):
            for nyckel, meta in poster.items():
                day_entries[str(nyckel)] = meta if isinstance(meta, dict) else {}
        elif isinstance(poster, list):
            for nyckel in poster:
                if isinstance(nyckel, str):
                    day_entries[nyckel] = {}
        normalized[str(ds)] = day_entries
    return normalized


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
    "Bornholmslinjen": {
        "kalla": "https://www.bornholmslinjen.dk/fartplan",
        "source_label": "Live-tidtabell",
        "source_detail": molslinjen.SOURCE_DETAIL,
        "source_type": "dynamic_schedule",
    },
    "Øresundslinjen": {
        "kalla": "https://www.oresundslinjen.dk/fartplan",
        "source_label": "Live-tidtabell",
        "source_detail": molslinjen.SOURCE_DETAIL,
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
            # Veckoscheman ska behålla sin radkälla; dynamiska standardvärden
            # används bara när en dynamisk rad saknar metadata.
            if str(inst.get("source_type") or "") == "weekly_schedule":
                if not inst.get("source_label"):
                    inst["source_label"] = "Veckoschema"
                continue
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


def refresh_meta_lists(data: dict, instances_by_date: dict[str, list[dict]]) -> None:
    rederier = {
        str(row.get("rederi") or "").strip()
        for row in data.get("schema") or []
        if str(row.get("rederi") or "").strip()
    }
    hamnar = {
        str(row.get(field) or "").strip()
        for row in data.get("schema") or []
        for field in ("avghamn", "ankhamn")
        if str(row.get(field) or "").strip()
    }
    for entries in instances_by_date.values():
        for inst in entries or []:
            rederi = str(inst.get("rederi") or "").strip()
            if rederi:
                rederier.add(rederi)
            for field in ("avghamn", "ankhamn"):
                hamn = str(inst.get(field) or "").strip()
                if hamn:
                    hamnar.add(hamn)
    data.setdefault("meta", {})["rederier"] = sorted(rederier)
    data.setdefault("meta", {})["hamnar"] = sorted(hamnar)


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


def instance_route_key(inst: dict) -> tuple[str, str, str]:
    return (
        str(inst.get("rederi") or "").strip(),
        str(inst.get("avghamn") or "").strip(),
        str(inst.get("ankhamn") or "").strip(),
    )


def instance_time_key(inst: dict) -> tuple[str, str, str, str]:
    route_key = instance_route_key(inst)
    dep_time = str(inst.get("avgtid") or "").strip()
    return route_key + (dep_time,)


def choose_most_common_arrival(candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    counts = Counter(
        (
            str(item.get("anktid") or "").strip(),
            str(item.get("ankomstdatum") or "").strip(),
        )
        for item in candidates
        if str(item.get("anktid") or "").strip()
    )
    best: dict | None = None
    best_count = -1
    best_priority = -1
    for item in candidates:
        arr_time = str(item.get("anktid") or "").strip()
        if not arr_time:
            continue
        arr_date = str(item.get("ankomstdatum") or "").strip()
        count = counts[(arr_time, arr_date)]
        priority = int(item.get("source_priority", 0) or 0)
        if count > best_count or (count == best_count and priority > best_priority):
            best = item
            best_count = count
            best_priority = priority
    return best


def infer_duration_minutes(inst: dict) -> int | None:
    dep_time = parse_time_minutes(str(inst.get("avgtid") or ""))
    arr_time = parse_time_minutes(str(inst.get("anktid") or ""))
    dep_date = str(inst.get("datum") or "").strip()
    arr_date = str(inst.get("ankomstdatum") or dep_date).strip()
    if dep_time is None or arr_time is None or not dep_date:
        return None
    day_offset = 0
    if arr_date and dep_date:
        try:
            day_offset = (date.fromisoformat(arr_date) - date.fromisoformat(dep_date)).days
        except ValueError:
            day_offset = 1 if "+1" in str(inst.get("anktid") or "") else 0
    minutes = arr_time - dep_time + (day_offset * 1440)
    if minutes <= 0 and "+1" in str(inst.get("anktid") or ""):
        minutes += 1440
    if minutes <= 0 or minutes >= 72 * 60:
        return None
    return minutes


def format_duration_fallback(minutes: list[int]) -> str:
    valid = sorted(m for m in minutes if 0 < m < 72 * 60)
    if not valid:
        return ""
    min_hours = max(1, valid[0] // 60)
    max_hours = max(min_hours, (valid[-1] + 59) // 60)
    return f"+{min_hours} h" if min_hours == max_hours else f"+{min_hours}–{max_hours} h"


def backfill_incomplete_instances(instances_by_date: dict[str, list[dict]]) -> None:
    exact_candidates: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    route_durations: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    for entries in instances_by_date.values():
        for inst in entries or []:
            arr_time = str(inst.get("anktid") or "").strip()
            if arr_time:
                exact_candidates[instance_time_key(inst)].append(inst)
                duration = infer_duration_minutes(inst)
                if duration is not None:
                    route_durations[instance_route_key(inst)].append(duration)

    exact_fallbacks = {
        key: choose_most_common_arrival(candidates)
        for key, candidates in exact_candidates.items()
    }
    route_fallbacks = {
        key: format_duration_fallback(minutes)
        for key, minutes in route_durations.items()
    }

    for dep_date, entries in instances_by_date.items():
        for inst in entries or []:
            if str(inst.get("anktid") or "").strip():
                continue
            exact = exact_fallbacks.get(instance_time_key(inst))
            if exact:
                inst["anktid"] = str(exact.get("anktid") or "").strip()
                if not inst.get("ankomstdatum") and exact.get("ankomstdatum"):
                    inst["ankomstdatum"] = str(exact.get("ankomstdatum") or dep_date).strip()
            if not str(inst.get("anktid") or "").strip():
                route_fallback = route_fallbacks.get(instance_route_key(inst), "")
                if route_fallback:
                    inst["anktid"] = route_fallback
            if not inst.get("ankomstdatum") and "+1" in str(inst.get("anktid") or ""):
                inst["ankomstdatum"] = (date.fromisoformat(dep_date) + timedelta(days=1)).isoformat()


def main():
    from_date = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    public_anchor_raw = os.getenv("FERRY_PUBLIC_ANCHOR_DATE", "").strip()
    public_anchor = date.fromisoformat(public_anchor_raw) if public_anchor_raw else from_date
    public_start, public_end = public_window(public_anchor)
    dynamic_start, dynamic_end = public_start, public_end
    public_start_iso = public_start.isoformat()
    public_end_iso = public_end.isoformat()
    log.info("Uppdaterar dynamiska avgångar %s – %s", dynamic_start, dynamic_end)
    log.info("Publiceringsfönster %s – %s", public_start, public_end)

    # Ladda befintlig JSON
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Legacy-fälten har förekommit både som datum->dict och datum->list.
    # Normalisera tidigt så äldre JSON-varianter inte kraschar workflowen.
    fartyg_datum: dict[str, dict[str, str]] = normalize_fartyg_datum(data.get("fartyg_datum", {}))
    avgangar_datum: dict[str, dict[str, dict]] = normalize_avgangar_datum(data.get("avgangar_datum", {}))
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
            is_exact = s.get("is_exact", True)
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
                "is_exact": is_exact,
            })
            if not (dynamic_start.isoformat() <= ds <= dynamic_end.isoformat()):
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
                "is_exact": is_exact,
            }

    # ── Viking Line ──
    log.info("=== Viking Line ===")
    if os.getenv("FERRY_ENABLE_VIKING_API", "").strip().lower() in {"1", "true", "yes"}:
        # Veckovy returnerar sju dagar; stega över hela publiceringsfönstret.
        for offset in range(0, (dynamic_end - dynamic_start).days + 1, 7):
            fd = dynamic_start + timedelta(days=offset)
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
    else:
        log.info("Hoppar över Viking Line API; officiellt veckoschema är primärkälla tills API:t är återverifierat.")

    # ── Tallink Silja ──
    log.info("=== Tallink Silja ===")
    tl_sailings = tl.fetch_all(dynamic_start, dynamic_end)
    lägg_till(tl_sailings)

    # ── DFDS ──
    log.info("=== DFDS ===")
    dfds_sailings = dfds.fetch_all(dynamic_start, dynamic_end)
    lägg_till(dfds_sailings)

    # ── Finnlines ──
    log.info("=== Finnlines ===")
    finn_sailings = finn.fetch_all(dynamic_start, dynamic_end)
    lägg_till(finn_sailings)

    # ── Stena Line ──
    log.info("=== Stena Line ===")
    stena_sailings = stena.fetch_all(dynamic_start, dynamic_end)
    lägg_till(stena_sailings)

    # ── TT-Line ──
    log.info("=== TT-Line ===")
    ttline_sailings = ttline.fetch_all(dynamic_start, dynamic_end)
    lägg_till(ttline_sailings)

    # ── Bornholmslinjen / Øresundslinjen ──
    log.info("=== Molslinjen family ===")
    molslinjen_sailings = molslinjen.fetch_all(dynamic_start, dynamic_end)
    lägg_till(molslinjen_sailings)

    merge_dynamic_sailings(avgangsinstanser, dynamic_sailings)
    prune_weekly_fallbacks_for_live_routes(avgangsinstanser, dynamic_sailings)
    enrich_instance_sources(avgangsinstanser)
    source_filter_stats = filter_instances_to_primary_sources(avgangsinstanser)
    if source_filter_stats:
        log.info(
            "Rensade %d avgångsinstanser från sekundära/nedlagda källor: %s",
            sum(source_filter_stats.values()),
            dict(source_filter_stats),
        )
    backfill_incomplete_instances(avgangsinstanser)
    fartyg_datum, avgangar_datum = sync_legacy_fields_from_instances(avgangsinstanser)

    # Spara tillbaka
    data["fartyg_datum"] = fartyg_datum
    data["avgangar_datum"] = avgangar_datum
    data["avgangsinstanser"] = avgangsinstanser
    data["meta"]["uppdaterad"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["meta"]["avgangsinstans_dagar"] = len(avgangsinstanser)
    data["meta"]["publiceringsfonster"] = f"{public_start_iso} till {public_end_iso}"
    data["meta"]["dynamic_window"] = f"{dynamic_start.isoformat()} till {dynamic_end.isoformat()}"
    refresh_meta_lists(data, avgangsinstanser)

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
