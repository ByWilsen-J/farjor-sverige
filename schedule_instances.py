from __future__ import annotations

import re
from calendar import monthrange
from copy import deepcopy
from datetime import date, timedelta

SVENSKA_HAMNAR = {
    "Stockholm",
    "Nynäshamn",
    "Kapellskär",
    "Grisslehamn",
    "Göteborg",
    "Trelleborg",
    "Ystad",
    "Malmö",
    "Helsingborg",
    "Strömstad",
    "Karlskrona",
    "Karlshamn",
    "Oxelösund",
    "Umeå",
    "Gävle",
    "Varberg",
}

VECKODAGAR = ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"]
VECKODAG_INDEX = {namn: idx for idx, namn in enumerate(VECKODAGAR)}

DEFAULT_LOOKBACK_DAYS = 31
DEFAULT_FORWARD_DAYS = 92

SOURCE_PRIORITIES = {
    "weekly_schedule": 10,
    "date_table": 70,
    "dynamic_schedule": 100,
}


def append_note(base: str, extra: str) -> str:
    base_text = str(base or "").strip()
    extra_text = str(extra or "").strip()
    if not extra_text:
        return base_text
    if not base_text:
        return extra_text
    if extra_text.lower() in base_text.lower():
        return base_text
    return f"{base_text} {extra_text}".strip()


def add_months(d: date, months: int) -> date:
    total_month = (d.month - 1) + months
    year = d.year + total_month // 12
    month = (total_month % 12) + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def public_window(anchor: date | None = None) -> tuple[date, date]:
    pivot = anchor or date.today()
    return (add_months(pivot, -1), add_months(pivot, 3))


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def norm_rederi(raw: str) -> str:
    value = str(raw or "").strip()
    if value == "DFDS (tidigare Tallink Silja)":
        return "DFDS"
    if re.match(r"^(polferries(\s*\(polsca\))?|polsca|unity line)$", value, re.I):
        return "Polsca"
    return value


def operator_id_for(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value == "dfds (tidigare tallink silja)":
        return "dfds"
    if value in {"polferries", "polferries (polsca)"}:
        return "polferries"
    if value == "unity line":
        return "unity_line"
    if value == "polsca":
        return "polsca"
    token = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return token or "unknown"


def build_route_id(avghamn: str, ankhamn: str) -> str:
    left = re.sub(r"[^a-z0-9]+", "_", str(avghamn or "").lower()).strip("_")
    right = re.sub(r"[^a-z0-9]+", "_", str(ankhamn or "").lower()).strip("_")
    return f"{left}_to_{right}"


def parse_time_minutes(text: str) -> int | None:
    match = re.search(r"(\d{1,2}):(\d{2})", str(text or ""))
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def guess_category(raw: str, rederi: str) -> str:
    source = str(raw or "").strip()
    if source:
        return source
    if norm_rederi(rederi) in {"DFDS", "Finnlines"}:
        return "RORO"
    return "Passagerare"


def weekday_match(veckodag_text: str, dep_date: date) -> bool:
    value = str(veckodag_text or "").strip()
    if not value:
        return True
    lower = value.lower()
    if "alla" in lower or "dagligen" in lower:
        return True
    target = VECKODAGAR[dep_date.weekday()]
    target_idx = VECKODAG_INDEX[target]
    if "–" in value:
        first, last = [part.strip() for part in value.split("–", 1)]
        if first in VECKODAG_INDEX and last in VECKODAG_INDEX:
            start_idx = VECKODAG_INDEX[first]
            end_idx = VECKODAG_INDEX[last]
            if start_idx <= end_idx:
                return start_idx <= target_idx <= end_idx
            return target_idx >= start_idx or target_idx <= end_idx
    return target in [part.strip() for part in value.split(",")]


def special_interval_for_schema_row(row: dict) -> tuple[str, str] | None:
    note = str(row.get("anmarkning") or "")
    if re.search(r"avvikande tidtabell 4–9 mars 2026", note, re.I):
        return ("2026-03-04", "2026-03-09")
    if (
        norm_rederi(row.get("rederi", "")) == "Viking Line"
        and row.get("avghamn") == "Helsingfors"
        and row.get("ankhamn") == "Stockholm"
        and (row.get("avgtid_raw") or row.get("avgtid") or "") == "18:10"
    ):
        return ("2026-03-04", "2026-03-09")
    return None


def schema_row_active_for_date(row: dict, dep_date: date) -> bool:
    valid_from = str(row.get("giltig_from") or "").strip()
    valid_to = str(row.get("giltig_to") or "").strip()
    dep_iso = dep_date.isoformat()
    if valid_from and dep_iso < valid_from:
        return False
    if valid_to and dep_iso > valid_to:
        return False
    week_parity = str(row.get("iso_week_parity") or "").strip().lower()
    if week_parity:
        is_even_week = dep_date.isocalendar().week % 2 == 0
        if week_parity == "even" and not is_even_week:
            return False
        if week_parity == "odd" and is_even_week:
            return False
    interval = special_interval_for_schema_row(row)
    if not interval:
        return True
    return interval[0] <= dep_iso <= interval[1]


def infer_arrival_date(dep_date_iso: str, dep_time: str, arr_time: str, explicit_next_day: bool) -> str:
    if explicit_next_day:
        return (date.fromisoformat(dep_date_iso) + timedelta(days=1)).isoformat()
    dep_minutes = parse_time_minutes(dep_time)
    arr_minutes = parse_time_minutes(arr_time)
    if dep_minutes is None or arr_minutes is None:
        return dep_date_iso
    if arr_minutes < dep_minutes:
        return (date.fromisoformat(dep_date_iso) + timedelta(days=1)).isoformat()
    return dep_date_iso


def instance_id(instance: dict) -> str:
    operator = instance.get("operator_id") or operator_id_for(instance.get("source_operator") or instance.get("rederi"))
    dep_date_iso = instance.get("datum") or ""
    dep_time = instance.get("avgtid") or ""
    avghamn = instance.get("avghamn") or ""
    ankhamn = instance.get("ankhamn") or ""
    return f"{operator}|{dep_date_iso}|{avghamn}|{ankhamn}|{dep_time}"


def make_schema_instance(row: dict, dep_date: date) -> dict:
    dep_date_iso = dep_date.isoformat()
    rederi = row.get("rederi", "") or ""
    instance = {
        "rederi": rederi,
        "display_group": norm_rederi(rederi),
        "source_operator": rederi,
        "operator_id": operator_id_for(rederi),
        "route_id": build_route_id(row.get("avghamn", ""), row.get("ankhamn", "")),
        "datum": dep_date_iso,
        "avghamn": row.get("avghamn", "") or "",
        "ankhamn": row.get("ankhamn", "") or "",
        "avgtid": row.get("avgtid_raw") or row.get("avgtid") or "",
        "anktid": row.get("anktid", "") or "",
        "ankomstdatum": "",
        "nasta_dag": bool(row.get("nasta_dag")),
        "mot_sverige": bool(row.get("mot_sverige")) or (row.get("ankhamn") in SVENSKA_HAMNAR),
        "fran_sverige": bool(row.get("fran_sverige")) or (row.get("avghamn") in SVENSKA_HAMNAR),
        "kategori": guess_category(row.get("kategori", ""), rederi),
        "anmarkning": row.get("anmarkning", "") or "",
        "verifiering": row.get("verifiering", "") or "",
        "kalla": row.get("kalla", "") or "",
        "fartyg": row.get("fartyg", "") or "",
        "source_type": "weekly_schedule",
        "source_priority": SOURCE_PRIORITIES["weekly_schedule"],
        "source_label": "Veckoschema",
        "source_detail": row.get("source_detail", "") or "",
        "is_live": False,
        "is_exact": False,
        "status": "",
        "traffic_comment": "",
        "template_id": row.get("id"),
    }
    if instance["nasta_dag"] and parse_time_minutes(instance["anktid"]) is not None:
        instance["ankomstdatum"] = (dep_date + timedelta(days=1)).isoformat()
    instance["id"] = instance_id(instance)
    return instance


def make_polsca_instance(row: dict, dep_date_iso: str) -> dict:
    rederi = row.get("rederi", "") or ""
    arr_time = row.get("anktid", "") or ""
    dep_time = row.get("avgtid", "") or ""
    next_day = bool(row.get("nasta_dag"))
    arr_date_iso = infer_arrival_date(dep_date_iso, dep_time, arr_time, next_day)
    category = "RORO" if str(row.get("typ", "")).upper() == "RORO" else "Passagerare"
    instance = {
        "rederi": rederi,
        "display_group": norm_rederi(rederi),
        "source_operator": rederi,
        "operator_id": operator_id_for(rederi),
        "route_id": build_route_id(row.get("avghamn", ""), row.get("ankhamn", "")),
        "datum": dep_date_iso,
        "avghamn": row.get("avghamn", "") or "",
        "ankhamn": row.get("ankhamn", "") or "",
        "avgtid": dep_time,
        "anktid": arr_time,
        "ankomstdatum": arr_date_iso,
        "nasta_dag": arr_date_iso > dep_date_iso,
        "mot_sverige": bool(row.get("mot_sverige")) or (row.get("ankhamn") in SVENSKA_HAMNAR),
        "fran_sverige": bool(row.get("fran_sverige")) or (row.get("avghamn") in SVENSKA_HAMNAR),
        "kategori": category,
        "anmarkning": "",
        "verifiering": "Verifierad via datumtabell.",
        "kalla": row.get("kalla", "") or "",
        "fartyg": row.get("fartyg", "") or "",
        "source_type": "date_table",
        "source_priority": SOURCE_PRIORITIES["date_table"],
        "source_label": "Datumtabell",
        "source_detail": "",
        "is_live": False,
        "is_exact": True,
        "status": "",
        "traffic_comment": "",
    }
    instance["id"] = instance_id(instance)
    return instance


def empty_instances_by_date(anchor: date | None = None) -> dict[str, list[dict]]:
    start, end = public_window(anchor)
    return {current.isoformat(): [] for current in date_range(start, end)}


def build_base_instances(data: dict, anchor: date | None = None) -> dict[str, list[dict]]:
    instances = empty_instances_by_date(anchor)
    start, end = public_window(anchor)
    for dep_date in date_range(start, end):
        dep_iso = dep_date.isoformat()
        day_instances = instances[dep_iso]
        for row in data.get("schema", []):
            if not weekday_match(row.get("veckodag", ""), dep_date):
                continue
            if not schema_row_active_for_date(row, dep_date):
                continue
            day_instances.append(make_schema_instance(row, dep_date))

    for dep_iso, rows in (data.get("polsca_datum") or {}).items():
        if dep_iso not in instances:
            continue
        for row in rows or []:
            instances[dep_iso].append(make_polsca_instance(row, dep_iso))

    for dep_iso in list(instances.keys()):
        instances[dep_iso].sort(key=lambda inst: (
            inst.get("source_priority", 0),
            parse_time_minutes(inst.get("avgtid")) if parse_time_minutes(inst.get("avgtid")) is not None else 10**9,
            inst.get("avghamn", ""),
            inst.get("ankhamn", ""),
        ))
    return instances


def choose_match(existing: list[dict], sailing: dict) -> dict | None:
    target_rederi = norm_rederi(sailing.get("rederi", ""))
    target_dep = sailing.get("avghamn", "")
    target_arr = sailing.get("ankhamn", "")
    target_time = sailing.get("avgtid", "") or sailing.get("departure_time", "")
    target_minutes = parse_time_minutes(target_time)
    candidates = [
        item for item in existing
        if norm_rederi(item.get("rederi", "")) == target_rederi
        and item.get("avghamn", "") == target_dep
        and item.get("ankhamn", "") == target_arr
    ]
    if not candidates:
        return None
    for item in candidates:
        if item.get("avgtid", "") == target_time:
            return item
    if target_minutes is None:
        return None
    # Fuzzy-matchning är till för att ersätta veckofallbackar när en livekälla
    # har några minuters avvikelse. Den får inte slå ihop två täta liveavgångar.
    fuzzy_candidates = [
        item for item in candidates
        if str(item.get("source_type") or "") != "dynamic_schedule"
    ]
    if not fuzzy_candidates:
        return None
    scored = []
    for item in fuzzy_candidates:
        minutes = parse_time_minutes(item.get("avgtid", ""))
        if minutes is None:
            continue
        diff = abs(minutes - target_minutes)
        if diff <= 60:
            scored.append((diff, item))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def merge_instance_fields(base: dict, updates: dict) -> dict:
    merged = deepcopy(base)
    for key, value in updates.items():
        if value not in (None, ""):
            merged[key] = value
    merged["source_priority"] = max(
        int(base.get("source_priority", 0)),
        int(updates.get("source_priority", 0)),
    )
    merged["source_type"] = updates.get("source_type") or base.get("source_type")
    merged["source_label"] = updates.get("source_label") or base.get("source_label")
    merged["source_detail"] = updates.get("source_detail") or base.get("source_detail")
    merged["is_live"] = bool(updates.get("is_live")) or bool(base.get("is_live"))
    merged["is_exact"] = bool(updates.get("is_exact")) or bool(base.get("is_exact"))
    merged["status"] = updates.get("status") or base.get("status", "")
    merged["traffic_comment"] = updates.get("traffic_comment") or base.get("traffic_comment", "")
    merged["anmarkning"] = append_note(merged.get("anmarkning", ""), updates.get("traffic_comment", ""))
    merged["id"] = instance_id(merged)
    return merged


def make_dynamic_instance(sailing: dict, fallback: dict | None = None) -> dict:
    dep_date_iso = sailing.get("date", "") or sailing.get("datum", "")
    rederi = sailing.get("rederi", "") or (fallback or {}).get("rederi", "")
    dep_time = sailing.get("avgtid", "") or sailing.get("departure_time", "")
    arr_time = sailing.get("anktid", "") or sailing.get("arrival_time", "")
    arr_date_iso = sailing.get("ankomstdatum", "") or sailing.get("arrival_date", "") or ""
    source_label = sailing.get("source_label", "") or sailing.get("kalllabel", "") or "Live-tidtabell"
    source_detail = sailing.get("source_detail", "") or sailing.get("kalldetalj", "")
    source_type = sailing.get("source_type", "") or "dynamic_schedule"
    status = sailing.get("status", "") or ""
    traffic_comment = sailing.get("traffic_comment", "") or ""
    if not arr_date_iso and dep_date_iso:
        arr_date_iso = infer_arrival_date(dep_date_iso, dep_time, arr_time, False)
    base = {
        "rederi": rederi,
        "display_group": norm_rederi(rederi),
        "source_operator": rederi,
        "operator_id": operator_id_for(rederi),
        "route_id": build_route_id(sailing.get("avghamn", ""), sailing.get("ankhamn", "")),
        "datum": dep_date_iso,
        "avghamn": sailing.get("avghamn", "") or "",
        "ankhamn": sailing.get("ankhamn", "") or "",
        "avgtid": dep_time,
        "anktid": arr_time,
        "ankomstdatum": arr_date_iso,
        "nasta_dag": bool(arr_date_iso and dep_date_iso and arr_date_iso > dep_date_iso),
        "mot_sverige": (fallback or {}).get("mot_sverige"),
        "fran_sverige": (fallback or {}).get("fran_sverige"),
        "kategori": guess_category((fallback or {}).get("kategori", ""), rederi),
        "anmarkning": append_note((fallback or {}).get("anmarkning", ""), traffic_comment),
        "verifiering": (fallback or {}).get("verifiering", "") or "Verifierad via datumimport.",
        "kalla": sailing.get("kalla", "") or sailing.get("source", "") or (fallback or {}).get("kalla", ""),
        "fartyg": sailing.get("fartyg", "") or sailing.get("ship_name", "") or sailing.get("ship", ""),
        "source_type": source_type,
        "source_priority": SOURCE_PRIORITIES["dynamic_schedule"],
        "source_label": source_label,
        "source_detail": source_detail,
        "is_live": bool(sailing.get("is_live", True)),
        "is_exact": bool(sailing.get("is_exact", True)),
        "status": status,
        "traffic_comment": traffic_comment,
        "template_id": (fallback or {}).get("template_id"),
    }
    if base["mot_sverige"] is None:
        base["mot_sverige"] = base["ankhamn"] in SVENSKA_HAMNAR
    if base["fran_sverige"] is None:
        base["fran_sverige"] = base["avghamn"] in SVENSKA_HAMNAR
    base["id"] = instance_id(base)
    return base


def merge_dynamic_sailings(
    instances_by_date: dict[str, list[dict]],
    sailings: list[dict],
) -> dict[str, list[dict]]:
    for sailing in sailings:
        dep_date_iso = sailing.get("date", "") or sailing.get("datum", "")
        if dep_date_iso not in instances_by_date:
            continue
        day_instances = instances_by_date[dep_date_iso]
        match = choose_match(day_instances, sailing)
        dynamic = make_dynamic_instance(sailing, fallback=match)
        if match is None:
            day_instances.append(dynamic)
            continue
        idx = day_instances.index(match)
        day_instances[idx] = merge_instance_fields(match, dynamic)

    for dep_iso, entries in instances_by_date.items():
        deduped: dict[str, dict] = {}
        for item in entries:
            key = item.get("id") or instance_id(item)
            current = deduped.get(key)
            if not current or item.get("source_priority", 0) >= current.get("source_priority", 0):
                deduped[key] = item
        instances_by_date[dep_iso] = sorted(
            deduped.values(),
            key=lambda inst: (
                parse_time_minutes(inst.get("avgtid")) if parse_time_minutes(inst.get("avgtid")) is not None else 10**9,
                norm_rederi(inst.get("rederi", "")),
                inst.get("avghamn", ""),
                inst.get("ankhamn", ""),
            ),
        )
    return instances_by_date
