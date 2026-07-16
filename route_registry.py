from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable


SWEDISH_PORTS = {
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


def normalize_operator(value: object) -> str:
    text = str(value or "").strip()
    if text == "DFDS (tidigare Tallink Silja)":
        return "DFDS"
    if text.lower() in {"polferries", "polferries (polsca)", "polsca", "unity line"}:
        return "Polferries (POLSCA)"
    return text


@dataclass(frozen=True)
class RouteSource:
    operator: str
    avghamn: str
    ankhamn: str
    source_type: str
    source_detail: str | None
    source_url: str
    note: str = ""
    required: bool = True

    @property
    def key(self) -> tuple[str, str, str]:
        return (normalize_operator(self.operator), self.avghamn, self.ankhamn)


@dataclass(frozen=True)
class RemovedRoute:
    operator: str
    avghamn: str
    ankhamn: str
    reason: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (normalize_operator(self.operator), self.avghamn, self.ankhamn)


DFDS_API = ("dynamic_schedule", "DFDS timetable API", "https://www.dfds.com/api/timetable")
TALLINK_API = ("dynamic_schedule", "Tallink CMS timetable API", "https://cms-web-api-nx.tallink.com/api/seaweb/timetables")
VIKING_API = ("dynamic_schedule", "Viking Protheus ferry API", "https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en")
FINNLINES_API = ("dynamic_schedule", "Finnlines GraphQL timetable API", "https://dm3xyy44wbeivgqmeymvmw22be.appsync-api.eu-central-1.amazonaws.com/graphql")
STENA_API = ("dynamic_schedule", "Stena Freight LiveView", "https://stenalinefreight.com/timetable/")
TTLINE_API = ("dynamic_schedule", "TT-Line timetable endpoint", "https://www.ttline.com/en/timetables/")
POLSCA_WEEKLY = ("weekly_schedule", None, "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html")
POLSCA_YS_TIMETABLE = (
    "date_table",
    "Polferries Świnoujście-Ystad timetable",
    "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=ys",
)
POLSCA_GDANSK_KARLSHAMN = (
    "weekly_schedule",
    "Polferries Gdańsk-Karlshamn timetable",
    "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=gh",
)
MOLSLINJEN_BORNHOLM_API = ("dynamic_schedule", "Molslinjen AI schedule catalog", "https://new.api.molslinjen.dk/api/v1/ai/markup/data-catalog?language=da&line=2")
MOLSLINJEN_ORESUND_API = ("dynamic_schedule", "Molslinjen AI schedule catalog", "https://new.api.molslinjen.dk/api/v1/ai/markup/data-catalog?language=da&line=7")
SUNDBUSSERNE_WEEKLY = ("weekly_schedule", "Sundbusserne sejlplan 2026-03-20", "https://sundbusserne.dk/fartplan/")


def one_way(operator: str, avghamn: str, ankhamn: str, source: tuple[str, str | None, str], note: str = "") -> RouteSource:
    source_type, source_detail, source_url = source
    return RouteSource(operator, avghamn, ankhamn, source_type, source_detail, source_url, note)


def two_way(operator: str, left: str, right: str, source: tuple[str, str | None, str], note: str = "") -> list[RouteSource]:
    return [
        one_way(operator, left, right, source, note),
        one_way(operator, right, left, source, note),
    ]


ACTIVE_ROUTES: tuple[RouteSource, ...] = (
    # Sverige-Finland / Åland
    *two_way("Wasaline", "Umeå", "Vasa", ("weekly_schedule", None, "https://www.wasaline.com/en/timetable/")),
    *two_way("Eckerö Linjen", "Eckerö", "Grisslehamn", ("weekly_schedule", None, "https://www.eckerolinjen.se/en/timetable")),
    *two_way("Viking Line", "Stockholm", "Helsingfors", ("weekly_schedule", None, "https://www.sales.vikingline.com/find-trip/timetable/stockholm-helsinki/"), "Viking Protheus API gav 403 i lokal körning 2026-05-31; publicerad primärkälla är därför officiellt veckoschema."),
    *two_way("Viking Line", "Stockholm", "Åbo", ("weekly_schedule", None, "https://www.sales.vikingline.com/find-trip/timetable/stockholm-turku/"), "Viking Protheus API gav 403 i lokal körning 2026-05-31; publicerad primärkälla är därför officiellt veckoschema."),
    *two_way("Tallink Silja", "Stockholm", "Helsingfors", TALLINK_API),
    *two_way("Tallink Silja", "Stockholm", "Åbo", TALLINK_API),
    *two_way("Tallink Silja", "Stockholm", "Tallinn", TALLINK_API),
    *two_way("Bornholmslinjen", "Ystad", "Rønne", MOLSLINJEN_BORNHOLM_API),

    # DFDS är primär källa för Klaipėda-linjerna mot Sverige för att undvika
    # dubbelpublicering av samma samtrafikerade avgångar via TT-Line.
    *two_way("DFDS", "Paldiski", "Kapellskär", DFDS_API),
    *two_way("DFDS", "Klaipėda", "Karlshamn", DFDS_API, "Samtrafik med TT-Line; DFDS API används som ensam publicerad källa."),
    *two_way("DFDS", "Klaipėda", "Trelleborg", DFDS_API, "Samtrafik med TT-Line; DFDS API används som ensam publicerad källa."),
    *two_way("DFDS", "Immingham", "Göteborg", DFDS_API),
    *two_way("DFDS", "Ghent", "Göteborg", DFDS_API),
    *two_way("DFDS", "Brevik", "Göteborg", DFDS_API),
    *two_way("DFDS", "Zeebrugge", "Göteborg", DFDS_API),

    # Finnlines
    *two_way("Finnlines", "Naantali", "Kapellskär", FINNLINES_API),
    *two_way("Finnlines", "Travemünde", "Malmö", FINNLINES_API),
    *two_way("Finnlines", "Świnoujście", "Malmö", ("weekly_schedule", None, "https://www.finnlines.com/sv/rutter/malmo-swinoujscie/")),

    # Stena Line
    *two_way("Stena Line", "Frederikshavn", "Göteborg", STENA_API),
    *two_way("Stena Line", "Kiel", "Göteborg", STENA_API),
    *two_way("Stena Line", "Gdynia", "Karlskrona", STENA_API),
    *two_way("Stena Line", "Rostock", "Trelleborg", STENA_API),
    *two_way("Stena Line", "Nynäshamn", "Ventspils", STENA_API),
    *two_way("Øresundslinjen", "Helsingør", "Helsingborg", MOLSLINJEN_ORESUND_API),
    *two_way("Sundbusserne", "Helsingør", "Helsingborg", SUNDBUSSERNE_WEEKLY),

    # TT-Line. Klaipėda-linjerna hanteras via DFDS ovan för att inte dubbla
    # samma samtrafikerade avgångar.
    *two_way("TT-Line", "Travemünde", "Trelleborg", TTLINE_API),
    *two_way("TT-Line", "Rostock", "Trelleborg", TTLINE_API),
    *two_way("TT-Line", "Świnoujście", "Trelleborg", TTLINE_API),
    *two_way("TT-Line", "Travemünde", "Karlshamn", TTLINE_API),
    one_way(
        "TT-Line",
        "Rostock",
        "Karlshamn",
        ("weekly_schedule", None, "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026-karcon.pdf"),
    ),

    # Polferries / POLSCA
    *two_way("Polferries (POLSCA)", "Świnoujście", "Ystad", POLSCA_YS_TIMETABLE),
    *two_way("Polferries (POLSCA)", "Świnoujście", "Trelleborg", POLSCA_WEEKLY),
    *two_way("Polferries (POLSCA)", "Gdańsk", "Nynäshamn", POLSCA_WEEKLY),
    *two_way("Polferries (POLSCA)", "Gdańsk", "Karlshamn", POLSCA_GDANSK_KARLSHAMN),
)


REFERENCE_ONLY_ROUTES: tuple[RouteSource, ...] = (
    *two_way(
        "Color Line",
        "Sandefjord",
        "Strömstad",
        ("link_only", "Color Line official route/timetable pages", "https://www.colorline.se/tidtabeller"),
        "Aktiv linje i länkvisaren. Exakt datumimport och fartygsnamn är inte materialiserade; ingen gissning publiceras.",
    ),
)


DISCONTINUED_ROUTES: tuple[RemovedRoute, ...] = (
    RemovedRoute("Stena Line", "Grenaa", "Halmstad", "Nedlagd 2026-04-30."),
    RemovedRoute("Stena Line", "Halmstad", "Grenaa", "Nedlagd 2026-04-30."),
)


SUPPRESSED_DUPLICATE_ROUTES: tuple[RemovedRoute, ...] = (
    RemovedRoute("TT-Line", "Klaipėda", "Karlshamn", "Samma samtrafikerade avgångar publiceras kanoniskt via DFDS API."),
    RemovedRoute("TT-Line", "Karlshamn", "Klaipėda", "Samma samtrafikerade avgångar publiceras kanoniskt via DFDS API."),
    RemovedRoute("TT-Line", "Klaipėda", "Trelleborg", "Samma samtrafikerade avgångar publiceras kanoniskt via DFDS API."),
    RemovedRoute("TT-Line", "Trelleborg", "Klaipėda", "Samma samtrafikerade avgångar publiceras kanoniskt via DFDS API."),
)


ACTIVE_BY_ROUTE = {route.key: route for route in ACTIVE_ROUTES}
REFERENCE_BY_ROUTE = {route.key: route for route in REFERENCE_ONLY_ROUTES}
DISCONTINUED_BY_ROUTE = {route.key: route for route in DISCONTINUED_ROUTES}
SUPPRESSED_BY_ROUTE = {route.key: route for route in SUPPRESSED_DUPLICATE_ROUTES}


def route_key_from_instance(inst: dict) -> tuple[str, str, str]:
    return (
        normalize_operator(inst.get("rederi") or inst.get("source_operator")),
        str(inst.get("avghamn") or "").strip(),
        str(inst.get("ankhamn") or "").strip(),
    )


def route_touches_sweden(avghamn: str, ankhamn: str) -> bool:
    return avghamn in SWEDISH_PORTS or ankhamn in SWEDISH_PORTS


def source_matches(inst: dict, route: RouteSource) -> bool:
    if str(inst.get("source_type") or "").strip() != route.source_type:
        return False
    if route.source_detail and str(inst.get("source_detail") or "").strip() != route.source_detail:
        return False
    return True


def source_identity(inst: dict) -> tuple[str, str, str, str]:
    return (
        normalize_operator(inst.get("rederi") or inst.get("source_operator")),
        str(inst.get("source_type") or "").strip(),
        str(inst.get("source_detail") or "").strip(),
        str(inst.get("kalla") or "").strip(),
    )


def filter_instances_to_primary_sources(instances_by_date: dict[str, list[dict]]) -> Counter:
    """Mutera avgangsinstanser så endast ruttens utsedda primärkälla återstår.

    Om primärkällan saknas helt för en rutt i en körning behålls verifierad
    fallbackdata, annars kan en tillfällig API-blockering radera aktiva linjer.
    """
    removed: Counter = Counter()
    primary_present_routes: set[tuple[str, str, str]] = set()

    for entries in instances_by_date.values():
        for inst in entries or []:
            key = route_key_from_instance(inst)
            route = ACTIVE_BY_ROUTE.get(key)
            if route and source_matches(inst, route):
                primary_present_routes.add(key)

    for dep_date, entries in list(instances_by_date.items()):
        kept: list[dict] = []
        for inst in entries or []:
            key = route_key_from_instance(inst)
            if key in DISCONTINUED_BY_ROUTE:
                removed["discontinued_route"] += 1
                continue
            if key in SUPPRESSED_BY_ROUTE:
                removed["suppressed_duplicate_route"] += 1
                continue
            route = ACTIVE_BY_ROUTE.get(key)
            if route and key in primary_present_routes and not source_matches(inst, route):
                removed["non_primary_source"] += 1
                continue
            kept.append(inst)
        instances_by_date[dep_date] = kept
    return removed


def active_route_keys(required_only: bool = True) -> set[tuple[str, str, str]]:
    return {route.key for route in ACTIVE_ROUTES if route.required or not required_only}


def removed_route_keys() -> set[tuple[str, str, str]]:
    return set(DISCONTINUED_BY_ROUTE) | set(SUPPRESSED_BY_ROUTE)


def all_registry_route_keys() -> set[tuple[str, str, str]]:
    return active_route_keys(required_only=False) | set(REFERENCE_BY_ROUTE) | removed_route_keys()


def iter_sweden_instances(instances_by_date: dict[str, list[dict]]) -> Iterable[dict]:
    for entries in instances_by_date.values():
        for inst in entries or []:
            if route_touches_sweden(str(inst.get("avghamn") or ""), str(inst.get("ankhamn") or "")):
                yield inst
