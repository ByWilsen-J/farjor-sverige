from __future__ import annotations

from copy import deepcopy

from route_registry import DISCONTINUED_BY_ROUTE, SUPPRESSED_BY_ROUTE, normalize_operator

TTLINE_STANDARD_NOTE = (
    "Officiell TT-Line standardtidtabell 2026. "
    "Standardtidtabellen är en avgångsrekommendation; aktuell bindande tidtabell finns hos TT-Line Freight."
)

STENA_NYVE_NOTE = (
    "Verifierat 2026-05-30 mot Stena Line Freight LiveView route NYVE "
    "(Nynäshamn–Ventspils). Tiderna följer officiell per-dag-tidtabell från Stena."
)

FINNLINES_SWIMMA_NOTE = (
    "Verifierat 2026-05-20 mot Finnlines officiella ruttsida för Malmö–Świnoujście. "
    "Veckoschemat används som primärkälla eftersom Finnlines GraphQL-källan inte returnerar denna rutt."
)

POLSCA_TRELLEBORG_NOTE = (
    "Verifierat 2026-05-31 mot POL-AGENTs officiella POLSCA-tabell "
    "för Świnoujście–Trelleborg, giltig 2026-05-04 till 2026-06-20. "
    "Rader med Epsilon/Jantar följer tabellens jämn/udda vecka-markering."
)

SUNDBUSSERNE_NOTE = (
    "Verifierat 2026-05-31 mot Sundbussernes officiella sejlplan-bild "
    "gällande från 2026-03-20. Restiden anges till cirka 18 minuter."
)

TTLINE_ROUTE_SOURCES = {
    ("Trelleborg", "Travemünde"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_tra.pdf",
    ("Travemünde", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_tra.pdf",
    ("Trelleborg", "Świnoujście"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_swi.pdf",
    ("Świnoujście", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_swi.pdf",
    ("Rostock", "Karlshamn"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026-karcon.pdf",
}

TTLINE_ROUTE_TIMETABLES = {
    ("Trelleborg", "Travemünde"): {
        "Mån": [("16:00", "00:45+1"), ("22:00", "07:30+1")],
        "Tis": [("09:30", "20:15"), ("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Ons": [("06:30", "14:15"), ("09:30", "20:15"), ("13:00", "22:30"), ("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Tor": [("09:30", "20:15"), ("16:00", "01:00+1"), ("22:30", "07:15+1")],
        "Fre": [("09:30", "20:15"), ("16:00", "00:45+1"), ("22:00", "07:45+1")],
        "Lör": [("10:00", "20:00"), ("22:00", "08:15+1")],
        "Sön": [("16:00", "01:00+1"), ("23:15", "08:15+1")],
    },
    ("Travemünde", "Trelleborg"): {
        "Mån": [("03:00", "11:45"), ("10:30", "21:30"), ("22:00", "07:00+1")],
        "Tis": [("02:30", "11:15"), ("09:30", "19:30"), ("22:00", "07:00+1")],
        "Ons": [("02:30", "11:15"), ("09:30", "19:30"), ("15:30", "23:00"), ("22:00", "07:00+1")],
        "Tor": [("01:00", "14:40"), ("02:30", "11:15"), ("09:30", "19:30"), ("15:15", "22:45"), ("22:00", "07:00+1")],
        "Fre": [("03:00", "11:45"), ("09:30", "19:30"), ("22:30", "07:45+1")],
        "Lör": [("02:30", "11:15"), ("10:00", "20:00"), ("22:00", "09:15+1")],
        "Sön": [("01:00", "09:15"), ("21:30", "06:15+1")],
    },
    ("Trelleborg", "Świnoujście"): {
        "Mån": [("07:45", "14:00"), ("23:55", "07:00+1")],
        "Tis": [("07:00", "13:30"), ("16:30", "23:55")],
        "Ons": [("10:00", "16:00")],
        "Tor": [("02:30", "09:30"), ("22:00", "05:00+1")],
        "Fre": [("07:30", "14:00"), ("16:30", "23:10")],
        "Lör": [("09:00", "16:30")],
        "Sön": [("08:30", "14:30"), ("15:00", "23:15")],
    },
    ("Świnoujście", "Trelleborg"): {
        "Mån": [("01:00", "08:30"), ("16:00", "23:00")],
        "Tis": [("08:30", "15:00"), ("15:30", "22:30")],
        "Ons": [("02:00", "09:00"), ("18:05", "01:05+1")],
        "Tor": [("14:30", "20:30")],
        "Fre": [("06:30", "14:00"), ("15:00", "22:15")],
        "Lör": [("00:30", "07:45")],
        "Sön": [("00:30", "07:30"), ("16:00", "22:00")],
    },
    ("Rostock", "Karlshamn"): {
        "Fre": [("23:45", "17:30+1")],
    },
}

STENA_ROUTE_SOURCES = {
    ("Nynäshamn", "Ventspils"): "https://stenalinefreight.com/timetable/NYVE/",
    ("Ventspils", "Nynäshamn"): "https://stenalinefreight.com/timetable/NYVE/",
}

STENA_ROUTE_TIMETABLES = {
    ("Nynäshamn", "Ventspils"): {
        "Mån": [("21:15", "07:45+1")],
        "Tis": [("21:15", "07:45+1")],
        "Ons": [("21:15", "07:45+1")],
        "Tor": [("21:15", "07:45+1")],
        "Fre": [("21:15", "07:45+1")],
        "Lör": [("21:15", "07:45+1")],
        "Sön": [("21:15", "07:45+1")],
    },
    ("Ventspils", "Nynäshamn"): {
        "Mån": [("23:00", "07:30+1")],
        "Tis": [("23:00", "07:30+1")],
        "Ons": [("23:00", "07:30+1")],
        "Tor": [("22:45", "07:45+1")],
        "Fre": [("22:45", "07:45+1")],
        "Lör": [("22:45", "07:45+1")],
        "Sön": [("22:30", "07:30+1")],
    },
}

FINNLINES_ROUTE_SOURCES = {
    ("Malmö", "Świnoujście"): "https://www.finnlines.com/sv/rutter/malmo-swinoujscie/",
    ("Świnoujście", "Malmö"): "https://www.finnlines.com/sv/rutter/malmo-swinoujscie/",
}

FINNLINES_ROUTE_TIMETABLES = {
    ("Malmö", "Świnoujście"): {
        "Mån": [("10:15", "19:15")],
        "Tis": [("11:00", "19:15")],
        "Ons": [("11:00", "19:15")],
        "Tor": [("11:00", "19:15")],
        "Fre": [("11:00", "19:15")],
        "Lör": [("11:00", "19:15")],
        "Sön": [("10:15", "19:15")],
    },
    ("Świnoujście", "Malmö"): {
        "Mån": [("21:30", "06:45+1")],
        "Tis": [("21:30", "06:45+1")],
        "Ons": [("21:30", "06:45+1")],
        "Tor": [("21:30", "06:45+1")],
        "Fre": [("21:30", "06:45+1")],
        "Lör": [("21:30", "06:45+1")],
        "Sön": [("21:30", "06:45+1")],
    },
}

POLSCA_TRELLEBORG_SOURCE = "https://polagent.com/en/sailing-schedule/"
POLSCA_TRELLEBORG_VALID_FROM = "2026-05-04"
POLSCA_TRELLEBORG_VALID_TO = "2026-06-20"
SUNDBUSSERNE_SOURCE = "https://sundbusserne.dk/fartplan/"

POLSCA_TRELLEBORG_ROWS = [
    ("Mån", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Mån", "Epsilon", "even", "10:00", "17:00", "", ""),
    ("Mån", "Jantar Unity", "odd", "10:00", "17:00", "", ""),
    ("Mån", "Jantar Unity", "even", "20:30", "03:00+1", "10:15", "16:30"),
    ("Mån", "Epsilon", "odd", "20:30", "03:00+1", "10:15", "16:30"),
    ("Tis", "Epsilon", "even", "", "", "01:30", "09:45"),
    ("Tis", "Jantar Unity", "odd", "", "", "01:30", "09:45"),
    ("Tis", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Tis", "Epsilon", "even", "14:00", "21:00", "10:15", "16:30"),
    ("Tis", "Jantar Unity", "odd", "14:00", "21:00", "10:15", "16:30"),
    ("Tis", "Jantar Unity", "even", "20:30", "03:00+1", "24:00", "07:00+1"),
    ("Tis", "Epsilon", "odd", "20:30", "03:00+1", "24:00", "07:00+1"),
    ("Ons", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Ons", "Epsilon", "even", "10:30", "17:30", "22:30", "07:00+1"),
    ("Ons", "Jantar Unity", "odd", "10:30", "17:30", "22:30", "07:00+1"),
    ("Ons", "Jantar Unity", "even", "20:30", "03:00+1", "10:15", "16:30"),
    ("Ons", "Jantar Unity", "odd", "20:30", "03:00+1", "10:15", "16:30"),
    ("Tor", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Tor", "Epsilon", "even", "09:00", "16:00", "23:55", "07:15+1"),
    ("Tor", "Jantar Unity", "odd", "09:00", "16:00", "23:55", "07:15+1"),
    ("Tor", "Jantar Unity", "even", "20:30", "03:00+1", "10:00", "16:30"),
    ("Tor", "Epsilon", "odd", "20:30", "03:00+1", "10:00", "16:30"),
    ("Fre", "Copernicus", None, "02:00", "09:00", "13:30", "21:15"),
    ("Fre", "Epsilon", "even", "09:00", "15:30", "22:45", "05:15+1"),
    ("Fre", "Jantar Unity", "odd", "09:00", "15:30", "22:45", "05:15+1"),
    ("Fre", "Jantar Unity", "even", "13:30", "21:15", "17:55", "01:00+1"),
    ("Fre", "Epsilon", "odd", "13:30", "21:15", "17:55", "01:00+1"),
    ("Lör", "Copernicus", None, "02:00", "09:30", "12:45", "20:15"),
    ("Sön", "Jantar Unity", "even", "10:00", "17:00", "22:30", "05:30+1"),
    ("Sön", "Epsilon", "odd", "10:00", "17:00", "22:30", "05:30+1"),
    ("Sön", "Epsilon", "even", "20:30", "03:00+1", "", ""),
    ("Sön", "Jantar Unity", "odd", "20:30", "03:00+1", "", ""),
]


def override_route_keys() -> set[tuple[str, str, str]]:
    route_keys = {("TT-Line", avghamn, ankhamn) for avghamn, ankhamn in TTLINE_ROUTE_TIMETABLES}
    route_keys.update({("Stena Line", avghamn, ankhamn) for avghamn, ankhamn in STENA_ROUTE_TIMETABLES})
    route_keys.update({("Finnlines", avghamn, ankhamn) for avghamn, ankhamn in FINNLINES_ROUTE_TIMETABLES})
    route_keys.update({
        ("Sundbusserne", "Helsingborg", "Helsingør"),
        ("Sundbusserne", "Helsingør", "Helsingborg"),
    })
    route_keys.update({
        ("Polferries (POLSCA)", "Świnoujście", "Trelleborg"),
        ("Polferries (POLSCA)", "Trelleborg", "Świnoujście"),
    })
    return route_keys


def _add_minutes(time_text: str, minutes: int) -> str:
    hour, minute = [int(part) for part in time_text.split(":", 1)]
    total = hour * 60 + minute + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _half_hour_times(start: str, end: str) -> list[str]:
    current_h, current_m = [int(part) for part in start.split(":", 1)]
    end_h, end_m = [int(part) for part in end.split(":", 1)]
    current = current_h * 60 + current_m
    end_minutes = end_h * 60 + end_m
    values: list[str] = []
    while current <= end_minutes:
        values.append(f"{current // 60:02d}:{current % 60:02d}")
        current += 30
    return values


def _make_row(
    rederi: str,
    avghamn: str,
    ankhamn: str,
    veckodag: str,
    avgtid: str,
    anktid: str,
    source_url: str,
    note: str,
    *,
    fartyg: str = "",
    giltig_from: str = "",
    giltig_to: str = "",
    iso_week_parity: str = "",
    source_detail: str = "",
) -> dict:
    row = {
        "id": 0,
        "kategori": "Passagerare",
        "rederi": rederi,
        "rutt": f"{avghamn}–{ankhamn}",
        "avghamn": avghamn,
        "ankhamn": ankhamn,
        "veckodag": veckodag,
        "avgtid": avgtid,
        "avgtid_raw": avgtid,
        "anktid": anktid,
        "nasta_dag": "+1" in anktid,
        "mot_sverige": ankhamn in {"Trelleborg", "Karlshamn", "Göteborg", "Malmö", "Ystad", "Nynäshamn", "Kapellskär", "Karlskrona", "Stockholm", "Umeå", "Grisslehamn"},
        "fran_sverige": avghamn in {"Trelleborg", "Karlshamn", "Göteborg", "Malmö", "Ystad", "Nynäshamn", "Kapellskär", "Karlskrona", "Stockholm", "Umeå", "Grisslehamn"},
        "anmarkning": note,
        "verifiering": "Verifierad",
        "kalla": source_url,
    }
    if fartyg:
        row["fartyg"] = fartyg
    if giltig_from:
        row["giltig_from"] = giltig_from
    if giltig_to:
        row["giltig_to"] = giltig_to
    if iso_week_parity:
        row["iso_week_parity"] = iso_week_parity
    if source_detail:
        row["source_detail"] = source_detail
    return row


def _build_ttline_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in TTLINE_ROUTE_TIMETABLES.items():
        source_url = TTLINE_ROUTE_SOURCES[(avghamn, ankhamn)]
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row("TT-Line", avghamn, ankhamn, veckodag, avgtid, anktid, source_url, TTLINE_STANDARD_NOTE))
    return rows


def _build_stena_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in STENA_ROUTE_TIMETABLES.items():
        source_url = STENA_ROUTE_SOURCES[(avghamn, ankhamn)]
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row("Stena Line", avghamn, ankhamn, veckodag, avgtid, anktid, source_url, STENA_NYVE_NOTE))
    return rows


def _build_finnlines_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in FINNLINES_ROUTE_TIMETABLES.items():
        source_url = FINNLINES_ROUTE_SOURCES[(avghamn, ankhamn)]
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row("Finnlines", avghamn, ankhamn, veckodag, avgtid, anktid, source_url, FINNLINES_SWIMMA_NOTE))
    return rows


def _build_polsca_trelleborg_rows() -> list[dict]:
    rows: list[dict] = []
    for veckodag, fartyg, parity, swi_dep, tre_arr, tre_dep, swi_arr in POLSCA_TRELLEBORG_ROWS:
        common = {
            "fartyg": fartyg,
            "giltig_from": POLSCA_TRELLEBORG_VALID_FROM,
            "giltig_to": POLSCA_TRELLEBORG_VALID_TO,
            "iso_week_parity": parity or "",
            "source_detail": "POL-AGENT POLSCA sailing schedule",
        }
        if swi_dep and tre_arr:
            rows.append(_make_row(
                "Polferries (POLSCA)",
                "Świnoujście",
                "Trelleborg",
                veckodag,
                swi_dep,
                tre_arr,
                POLSCA_TRELLEBORG_SOURCE,
                POLSCA_TRELLEBORG_NOTE,
                **common,
            ))
        if tre_dep and swi_arr:
            rows.append(_make_row(
                "Polferries (POLSCA)",
                "Trelleborg",
                "Świnoujście",
                veckodag,
                tre_dep,
                swi_arr,
                POLSCA_TRELLEBORG_SOURCE,
                POLSCA_TRELLEBORG_NOTE,
                **common,
            ))
    return rows


def _build_sundbusserne_rows() -> list[dict]:
    rows: list[dict] = []
    weekday_times = {
        "Mån": _half_hour_times("10:00", "18:00"),
        "Tis": _half_hour_times("10:00", "18:00"),
        "Ons": _half_hour_times("10:00", "18:00"),
        "Tor": _half_hour_times("10:00", "18:00"),
        "Fre": _half_hour_times("10:00", "20:30"),
        "Lör": _half_hour_times("10:00", "20:30"),
        "Sön": _half_hour_times("10:00", "17:30"),
    }
    for avghamn, ankhamn, first_vessel in [
        ("Helsingborg", "Helsingør", "Pernille"),
        ("Helsingør", "Helsingborg", "Jeppe"),
    ]:
        for veckodag, times in weekday_times.items():
            for idx, avgtid in enumerate(times):
                if first_vessel == "Pernille":
                    vessel = "Pernille" if idx % 2 == 0 else "Jeppe"
                else:
                    vessel = "Jeppe" if idx % 2 == 0 else "Pernille"
                rows.append(_make_row(
                    "Sundbusserne",
                    avghamn,
                    ankhamn,
                    veckodag,
                    avgtid,
                    _add_minutes(avgtid, 18),
                    SUNDBUSSERNE_SOURCE,
                    SUNDBUSSERNE_NOTE,
                    fartyg=vessel,
                    source_detail="Sundbusserne sejlplan 2026-03-20",
                ))
    return rows


def apply_verified_schema_overrides(schema: list[dict]) -> list[dict]:
    route_keys = override_route_keys()
    preserved = [
        deepcopy(row)
        for row in schema
        if (row.get("rederi"), row.get("avghamn"), row.get("ankhamn")) not in route_keys
        and (normalize_operator(row.get("rederi")), row.get("avghamn"), row.get("ankhamn")) not in DISCONTINUED_BY_ROUTE
        and (normalize_operator(row.get("rederi")), row.get("avghamn"), row.get("ankhamn")) not in SUPPRESSED_BY_ROUTE
    ]
    merged = (
        preserved
        + _build_ttline_rows()
        + _build_stena_rows()
        + _build_finnlines_rows()
        + _build_polsca_trelleborg_rows()
        + _build_sundbusserne_rows()
    )
    for idx, row in enumerate(merged, start=1):
        row["id"] = idx
        row["avgtid_raw"] = row.get("avgtid_raw") or row.get("avgtid") or ""
    return merged
