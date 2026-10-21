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
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import viking_line_scraper as vl
import tallink_scraper      as tl
import dfds_scraper         as dfds
import finnlines_scraper    as finn
import stena_line_scraper   as stena
import ttline_scraper       as ttline
import molslinjen_scraper   as molslinjen
import polferries_scraper   as polferries
from route_registry import ACTIVE_BY_ROUTE, filter_instances_to_primary_sources, normalize_operator, source_matches
from schedule_instances import build_base_instances, merge_dynamic_sailings, parse_time_minutes, public_window
from verified_schema_overrides import apply_verified_schema_overrides

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
                "source_checked_at": meta.get("source_checked_at", "") if isinstance(meta, dict) else "",
                "source_cached": True,
                "is_exact": meta.get("is_exact", True) if isinstance(meta, dict) else True,
            })
    return sailings


def sailing_route_day(sailing: dict) -> tuple[str, str, str, str]:
    return (
        str(sailing.get("date") or sailing.get("datum") or ""),
        normalize_operator(sailing.get("rederi")),
        str(sailing.get("avghamn") or ""),
        str(sailing.get("ankhamn") or ""),
    )


def coverage_route_days(coverage: list[dict], start: date, end: date) -> set[tuple[str, str, str, str]]:
    """Accept an explicit checked source period only from a route's primary source."""
    covered = set()
    for item in coverage:
        if not isinstance(item, dict):
            continue
        _, operator, dep, arr = sailing_route_day(item)
        route = ACTIVE_BY_ROUTE.get((operator, dep, arr))
        if not route or not source_matches(item, route):
            continue
        try:
            first = max(start, date.fromisoformat(item["date_from"]))
            last = min(end, date.fromisoformat(item["date_to"]))
        except (KeyError, TypeError, ValueError):
            continue
        while first <= last:
            covered.add((first.isoformat(), operator, dep, arr))
            first += timedelta(days=1)
    return covered


def retain_verified_coverage(data: dict, refresh: dict, start: date, end: date) -> dict:
    """Keep known empty/cancelled dates authoritative during the next outage.

    Current refresh coverage controls cache replacement; this retained coverage
    only prevents weekly rows from resurrecting dates known to have no service.
    """
    meta = data.get("meta") or {}
    previous = meta.get("source_coverage")
    if not isinstance(previous, dict):
        previous = {name: result.get("coverage", []) for name, result in meta.get("source_refresh", {}).items()}
    retained = {}
    for name in previous.keys() | refresh.keys():
        periods = {}
        current = [dict(item, checked_at=refresh[name].get("checked_at", ""))
                   for item in refresh.get(name, {}).get("coverage", []) if isinstance(item, dict)]
        for item in list(previous.get(name) or []) + current:
            if not isinstance(item, dict):
                continue
            try:
                first, last = date.fromisoformat(item["date_from"]), date.fromisoformat(item["date_to"])
            except (KeyError, TypeError, ValueError):
                continue
            if last < start or first > end:
                continue
            key = (sailing_route_day(item)[1:], item["date_from"], item["date_to"],
                   item.get("source_type"), item.get("source_detail"))
            periods[key] = item
        if periods:
            retained[name] = list(periods.values())
    return retained


def combine_cached_and_fresh_sailings(
    cached: list[dict], fresh: list[dict], covered_route_days: set | None = None,
) -> list[dict]:
    """Replace only route-days actually returned by a source.

    Empty/failed routes keep their last published rows. Successful route-days
    replace the old snapshot, so a changed departure time does not leave a
    second, obsolete sailing behind. An empty list is not proof of cancellation.
    """
    # Molslinjen's catalog is a limited list of upcoming departures, not a
    # full daily snapshot. Preserve departures before the check and beyond the
    # returned horizon, including the morning rows on an evening refresh.
    upcoming_routes: dict[tuple, tuple[datetime, datetime]] = {}
    stockholm = ZoneInfo("Europe/Stockholm")  # All four Molslinjen ports share it.

    def local_departure(row):
        try:
            ds = row.get("date") or row.get("datum")
            clock = row.get("avgtid") or row.get("departure_time")
            return datetime.fromisoformat(f"{ds}T{clock}").replace(tzinfo=stockholm)
        except (TypeError, ValueError):
            return None

    refreshed = set(covered_route_days or set())
    for row in fresh:
        if row.get("source_detail") != molslinjen.SOURCE_DETAIL:
            refreshed.add(sailing_route_day(row))
            continue
        route = sailing_route_day(row)[1:]
        departure = local_departure(row)
        try:
            checked = datetime.fromisoformat(row["source_checked_at"].replace("Z", "+00:00")).astimezone(stockholm)
        except (KeyError, TypeError, ValueError):
            continue
        if departure is None:
            continue
        previous = upcoming_routes.get(route)
        upcoming_routes[route] = (min(checked, previous[0]) if previous else checked,
                                  max(departure, previous[1]) if previous else departure)

    def replaced(row):
        key = sailing_route_day(row)
        if key in refreshed:
            return True
        horizon = upcoming_routes.get(key[1:])
        departure = local_departure(row) if horizon else None
        return bool(horizon and departure and horizon[0] <= departure <= horizon[1])

    return [row for row in cached if not replaced(row)] + fresh


def collect_source(name: str, fetch, start: date, end: date, statuses: dict) -> list[dict]:
    """Isolate source failures and record checks separately from successful data."""
    checked_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {"checked_at": checked_at, "status": "error", "received_rows": 0, "accepted_rows": 0}
    statuses[name] = result
    try:
        rows = fetch()
        if not isinstance(rows, list):
            raise ValueError("Källan returnerade inte en lista med avgångar")
        result["received_rows"] = len(rows)
        accepted = []
        invalid = 0
        for original in rows:
            if not isinstance(original, dict):
                invalid += 1
                continue
            row = dict(original)
            ds = str(row.get("date") or row.get("datum") or "")
            dep_time = str(row.get("avgtid") or row.get("departure_time") or "")
            try:
                dep_date = date.fromisoformat(ds)
            except ValueError:
                invalid += 1
                continue
            if not (start <= dep_date <= end):
                continue
            arrival = row.get("ankomstdatum") or row.get("arrival_date")
            if arrival:
                try:
                    arrival_date = date.fromisoformat(str(arrival))
                except ValueError:
                    invalid += 1
                    continue
                if arrival_date < dep_date:
                    invalid += 1
                    continue
            if not all(row.get(field) for field in ("rederi", "avghamn", "ankhamn")) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", dep_time):
                invalid += 1
                continue
            row.update(date=ds, source_checked_at=checked_at, source_cached=False)
            accepted.append(row)
        result["accepted_rows"] = len(accepted)
        result["invalid_rows"] = invalid
        # A malformed partial snapshot is not safe evidence for removing old
        # departures. Preserve this source's last complete snapshot instead.
        if invalid:
            result["accepted_rows"] = 0
            accepted = []
        coverage = getattr(rows, "coverage", []) if not invalid else []
        result["coverage"] = coverage if isinstance(coverage, list) else []
        result["status"] = "partial" if invalid else ("ok" if accepted or result["coverage"] else "empty")
        if not accepted or invalid:
            log.warning("%s: %s (%d godkända, %d ogiltiga); tidigare datumdata behålls där svar saknas", name, result["status"], len(accepted), invalid)
        return accepted
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        log.exception("%s kunde inte uppdateras; tidigare datumdata och verifierad fallback behålls", name)
        return []


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
        "kalla": "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html",
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
                "source_checked_at": str(inst.get("source_checked_at") or "").strip(),
                "source_cached": bool(inst.get("source_cached", False)),
                "is_exact": bool(inst.get("is_exact", True)),
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
    """Fill missing arrival only from the same dated departure.

    A route/time on another day is not evidence for this sailing's arrival.
    Copying that row also used to copy its absolute calendar date, producing
    arrivals before departure. Leave unknown values unknown instead.
    """
    for entries in instances_by_date.values():
        candidates: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
        for inst in entries or []:
            if str(inst.get("anktid") or "").strip():
                candidates[instance_time_key(inst)].append(inst)
        for inst in entries or []:
            if str(inst.get("anktid") or "").strip():
                continue
            matches = candidates.get(instance_time_key(inst), [])
            arrivals = {
                (str(row.get("anktid") or ""), str(row.get("ankomstdatum") or ""))
                for row in matches
            }
            if len(arrivals) != 1:
                continue
            inst["anktid"], inst["ankomstdatum"] = next(iter(arrivals))


def main():
    from_date = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(ZoneInfo("Europe/Stockholm")).date()
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
    # Daily/hourly refresh must apply reviewed corrections without requiring the
    # original local Excel workbook used by generera_json.py.
    data["schema"] = apply_verified_schema_overrides(data.get("schema") or [])
    data.setdefault("meta", {})["schema_rader"] = len(data["schema"])

    # Start from the last published exact rows. A source outage must not erase
    # unrelated sources or route-days; fresh non-empty snapshots replace cache.
    avgangsinstanser = build_base_instances(data, anchor=public_anchor)
    cached_sailings = [
        row for row in legacy_dynamic_sailings(normalize_avgangar_datum(data.get("avgangar_datum", {})))
        if public_start_iso <= row["date"] <= public_end_iso
    ]
    source_refresh: dict[str, dict] = {}
    fresh_sailings: list[dict] = []

    def fetch_viking() -> list[dict]:
        sailings = []
        for offset in range(0, (dynamic_end - dynamic_start).days + 1, 7):
            fd = dynamic_start + timedelta(days=offset)
            for route_sailings in vl.fetch_all_routes(from_date=fd.isoformat()).values():
                for row in route_sailings:
                    sailings.append({
                        "date": row["date"], "avghamn": row["pol"], "ankhamn": row["pod"],
                        "avgtid": row["departure_time"], "anktid": row.get("arrival_time", ""),
                        "ankomstdatum": row.get("arrival_date", ""), "fartyg": row["ship_name"],
                        "rederi": "Viking Line", "kalla": row.get("kalla", ""),
                        "source_label": row.get("source_label", ""),
                        "source_detail": row.get("source_detail", ""),
                        "source_type": row.get("source_type", ""),
                        "status": row.get("availability", ""),
                    })
        return sailings

    if os.getenv("FERRY_ENABLE_VIKING_API", "").strip().lower() in {"1", "true", "yes"}:
        fresh_sailings.extend(collect_source("Viking Line", fetch_viking, dynamic_start, dynamic_end, source_refresh))
    else:
        log.info("Hoppar över Viking Line API; officiellt veckoschema är primärkälla tills API:t är återverifierat.")
        source_refresh["Viking Line"] = {"status": "disabled", "reason": "Officiellt veckoschema används"}

    collectors = [
        ("Tallink Silja", lambda: tl.fetch_all(dynamic_start, dynamic_end)),
        ("DFDS", lambda: dfds.fetch_all(dynamic_start, dynamic_end)),
        ("Finnlines", lambda: finn.fetch_all(dynamic_start, dynamic_end)),
        ("Stena Line", lambda: stena.fetch_all(dynamic_start, dynamic_end)),
        ("TT-Line", lambda: ttline.fetch_all(dynamic_start, dynamic_end)),
        ("Polferries (POLSCA)", polferries.fetch_all),
        ("Molslinjen", lambda: molslinjen.fetch_all(dynamic_start, dynamic_end)),
    ]
    for name, fetch in collectors:
        log.info("=== %s ===", name)
        fresh_sailings.extend(collect_source(name, fetch, dynamic_start, dynamic_end, source_refresh))

    coverage = [item for result in source_refresh.values() for item in result.get("coverage", [])]
    covered_days = coverage_route_days(coverage, public_start, public_end)
    retained_coverage = retain_verified_coverage(data, source_refresh, public_start, public_end)
    known_covered_days = coverage_route_days(
        [item for periods in retained_coverage.values() for item in periods], public_start, public_end,
    )
    dynamic_sailings = combine_cached_and_fresh_sailings(cached_sailings, fresh_sailings, covered_days)
    # Explicit published empty dates (e.g. Christmas cancellations) are
    # authoritative too. Do not resurrect weekly rows on those dates.
    for ds, entries in avgangsinstanser.items():
        avgangsinstanser[ds] = [
            row for row in entries if sailing_route_day(row) not in known_covered_days
        ]
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
    data["meta"]["source_refresh"] = source_refresh
    data["meta"]["source_coverage"] = retained_coverage
    data["meta"]["dynamic_window"] = f"{dynamic_start.isoformat()} till {dynamic_end.isoformat()}"
    refresh_meta_lists(data, avgangsinstanser)

    # Räkna
    totalt = sum(len(v) for v in fartyg_datum.values())
    log.info("Totalt %d fartygsuppslag över %d datum.", totalt, len(fartyg_datum))
    instans_totalt = sum(len(v) for v in avgangsinstanser.values())
    log.info("Totalt %d avgångsinstanser över %d datum.", instans_totalt, len(avgangsinstanser))

    # Replace atomically so an interrupted write cannot publish truncated JSON.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=DATA_FILE.parent, suffix=".json.tmp", delete=False) as handle:
        temp_path = Path(handle.name)
        try:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
    try:
        temp_path.replace(DATA_FILE)
    finally:
        temp_path.unlink(missing_ok=True)

    log.info("farjor_data.json uppdaterad.")


if __name__ == "__main__":
    main()
