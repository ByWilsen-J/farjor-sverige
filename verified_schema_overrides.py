from __future__ import annotations

from copy import deepcopy

TTLINE_STANDARD_NOTE = (
    "Officiell TT-Line standardtidtabell 2026. "
    "Standardtidtabellen är en avgångsrekommendation; aktuell bindande tidtabell finns hos TT-Line Freight."
)

TTLINE_ROUTE_SOURCES = {
    ("Trelleborg", "Travemünde"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_tra.pdf",
    ("Travemünde", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_tra.pdf",
    ("Trelleborg", "Świnoujście"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_swi.pdf",
    ("Świnoujście", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_swi.pdf",
    ("Trelleborg", "Klaipėda"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_klatre.pdf",
    ("Klaipėda", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_klatre.pdf",
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
    ("Trelleborg", "Klaipėda"): {
        "Lör": [("10:30", "10:30+1 (LT)")],
    },
    ("Klaipėda", "Trelleborg"): {
        "Mån": [("23:00", "18:30+1")],
        "Tis": [("17:30", "11:30+1")],
        "Tor": [("17:00", "13:00+1")],
        "Lör": [("19:00", "14:00+1")],
    },
}


def override_route_keys() -> set[tuple[str, str, str]]:
    return {("TT-Line", avghamn, ankhamn) for avghamn, ankhamn in TTLINE_ROUTE_TIMETABLES}


def _make_row(avghamn: str, ankhamn: str, veckodag: str, avgtid: str, anktid: str, source_url: str) -> dict:
    return {
        "id": 0,
        "kategori": "Passagerare",
        "rederi": "TT-Line",
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
        "anmarkning": TTLINE_STANDARD_NOTE,
        "verifiering": "Verifierad",
        "kalla": source_url,
    }


def _build_ttline_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in TTLINE_ROUTE_TIMETABLES.items():
        source_url = TTLINE_ROUTE_SOURCES[(avghamn, ankhamn)]
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row(avghamn, ankhamn, veckodag, avgtid, anktid, source_url))
    return rows


def apply_verified_schema_overrides(schema: list[dict]) -> list[dict]:
    route_keys = override_route_keys()
    preserved = [
        deepcopy(row)
        for row in schema
        if (row.get("rederi"), row.get("avghamn"), row.get("ankhamn")) not in route_keys
    ]
    merged = preserved + _build_ttline_rows()
    for idx, row in enumerate(merged, start=1):
        row["id"] = idx
        row["avgtid_raw"] = row.get("avgtid_raw") or row.get("avgtid") or ""
    return merged
