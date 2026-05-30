#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from route_registry import (
    ACTIVE_BY_ROUTE,
    DISCONTINUED_BY_ROUTE,
    SUPPRESSED_BY_ROUTE,
    active_route_keys,
    all_registry_route_keys,
    iter_sweden_instances,
    normalize_operator,
    removed_route_keys,
    route_key_from_instance,
    route_touches_sweden,
    source_identity,
    source_matches,
)


DATA_FILE = Path(__file__).parent / "farjor_data.json"
INVALID_VESSEL_NAMES = {"-", "–", "—", "?", "n/a", "na", "unknown", "okänt", "okant"}


def load_data(path: Path = DATA_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_route_key(row: dict) -> tuple[str, str, str]:
    return (
        normalize_operator(row.get("rederi")),
        str(row.get("avghamn") or "").strip(),
        str(row.get("ankhamn") or "").strip(),
    )


def event_key(inst: dict) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(inst.get("datum") or "").strip(),
        str(inst.get("avghamn") or "").strip(),
        str(inst.get("ankhamn") or "").strip(),
        str(inst.get("avgtid") or "").strip(),
        str(inst.get("anktid") or "").strip(),
        str(inst.get("ankomstdatum") or "").strip(),
        str(inst.get("fartyg") or "").strip(),
    )


def main() -> int:
    data = load_data()
    instances_by_date = data.get("avgangsinstanser") or {}
    meta = data.get("meta") or {}
    today_iso = date.today().isoformat()

    route_counts: Counter = Counter()
    route_sources: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    event_counts: Counter = Counter()
    wrong_sources: Counter = Counter()
    invalid_vessels: Counter = Counter()
    blank_dynamic_vessels: Counter = Counter()

    issues: list[str] = []
    warnings: list[str] = []

    for inst in iter_sweden_instances(instances_by_date):
        key = route_key_from_instance(inst)
        route_counts[key] += 1
        route_sources[key][source_identity(inst)] += 1
        event_counts[event_key(inst)] += 1

        route = ACTIVE_BY_ROUTE.get(key)
        if route and not source_matches(inst, route):
            wrong_sources[(key, source_identity(inst), route.source_type, route.source_detail or "*")] += 1

        vessel = str(inst.get("fartyg") or "").strip()
        if vessel.lower() in INVALID_VESSEL_NAMES or vessel.lower().startswith("okant fartyg"):
            invalid_vessels[(key, vessel)] += 1
        elif (
            not vessel
            and str(inst.get("source_type") or "") == "dynamic_schedule"
            and str(inst.get("datum") or "") >= today_iso
        ):
            blank_dynamic_vessels[key] += 1

    for key in sorted(active_route_keys()):
        if route_counts[key] == 0:
            route = ACTIVE_BY_ROUTE[key]
            issues.append(
                f"Saknad aktiv rutt: {route.operator} {route.avghamn} -> {route.ankhamn} "
                f"({route.source_type}, {route.source_url})."
            )

    for key in sorted(removed_route_keys()):
        if route_counts[key] > 0:
            removed = DISCONTINUED_BY_ROUTE.get(key) or SUPPRESSED_BY_ROUTE.get(key)
            issues.append(
                f"Rutt ska inte publiceras: {key[0]} {key[1]} -> {key[2]} "
                f"finns {route_counts[key]} gånger. Orsak: {removed.reason if removed else 'borttagen'}"
            )

    for (key, identity, expected_type, expected_detail), count in sorted(wrong_sources.items()):
        issues.append(
            f"Fel källa: {key[0]} {key[1]} -> {key[2]} har {count} rader från {identity}, "
            f"men primärkälla är {expected_type}/{expected_detail}."
        )

    for row in data.get("schema") or []:
        key = schema_route_key(row)
        if key in DISCONTINUED_BY_ROUTE:
            removed = DISCONTINUED_BY_ROUTE[key]
            issues.append(
                f"Nedlagd rutt finns kvar i schema: {key[0]} {key[1]} -> {key[2]}. "
                f"Orsak: {removed.reason}"
            )
        if key in SUPPRESSED_BY_ROUTE:
            removed = SUPPRESSED_BY_ROUTE[key]
            issues.append(
                f"Dubbelpublicerad rutt finns kvar i schema: {key[0]} {key[1]} -> {key[2]}. "
                f"Orsak: {removed.reason}"
            )

    for key, sources in sorted(route_sources.items()):
        if key in ACTIVE_BY_ROUTE and len(sources) > 1:
            source_list = "; ".join(f"{count}x {identity}" for identity, count in sources.most_common())
            issues.append(f"Flera aktuella källor för {key[0]} {key[1]} -> {key[2]}: {source_list}")

    for event, count in event_counts.items():
        if count > 1:
            issues.append(f"Dubbel avgång: {count}x {event}")

    for (key, vessel), count in sorted(invalid_vessels.items()):
        issues.append(f"Ogiltigt fartygsnamn: {key[0]} {key[1]} -> {key[2]} har {count} rader med '{vessel}'.")

    registered = all_registry_route_keys()
    for key, count in sorted(route_counts.items()):
        if key not in registered and route_touches_sweden(key[1], key[2]):
            warnings.append(f"Oregistrerad Sverige-rutt i publicerad data: {key[0]} {key[1]} -> {key[2]} ({count} rader)")

    for key, count in sorted(blank_dynamic_vessels.items()):
        warnings.append(f"Dynamisk källa saknar exakt fartygsnamn: {key[0]} {key[1]} -> {key[2]} ({count} rader)")

    print("Route coverage check")
    print(f"  Publiceringsfönster: {meta.get('publiceringsfonster', '-')}")
    print(f"  Dynamiskt fönster: {meta.get('dynamic_window', '-')}")
    print(f"  Aktiva rutter i register: {len(active_route_keys())}")
    print(f"  Publicerade Sverige-rutter: {len(route_counts)}")

    if warnings:
        print("\nVarningar:")
        for warning in warnings[:50]:
            print(f"  - {warning}")
        if len(warnings) > 50:
            print(f"  - ... {len(warnings) - 50} fler")

    if issues:
        print("\nFel:")
        for issue in issues[:80]:
            print(f"  - {issue}")
        if len(issues) > 80:
            print(f"  - ... {len(issues) - 80} fler")
        return 1

    print("\nOK: alla aktiva rutter finns, borttagna rutter saknas och varje registrerad rutt har en primärkälla.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
