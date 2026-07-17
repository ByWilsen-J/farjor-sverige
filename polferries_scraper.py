from __future__ import annotations

import html
import logging
import re
from datetime import date, timedelta

import requests


SOURCE_URL_YS = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=ys"
SOURCE_DETAIL_YS = "Polferries Świnoujście-Ystad timetable"
SOURCE_URL_ST = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=st"
SOURCE_DETAIL_ST = "Polferries Świnoujście-Trelleborg timetable"
SOURCE_LABEL = "Datumtabell"

VESSEL_CODES = {
    "VAR": "Varsovia",
    "MAZ": "Mazovia",
    "EPS": "Epsilon",
    "JAN": "Jantar",
    "GAL": "Galileusz",
    "POL": "Polonia",
    "SKA": "Skania",
}

ROUTE_PORTS = {
    "Ystad - Świnoujście": ("Ystad", "Świnoujście"),
    "Świnoujście - Ystad": ("Świnoujście", "Ystad"),
    "Świnoujście - Trelleborg": ("Świnoujście", "Trelleborg"),
    "Trelleborg - Świnoujście": ("Trelleborg", "Świnoujście"),
}

log = logging.getLogger("polferries")


def _strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _table_blocks(page_html: str) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    pattern = re.compile(
        r'<div id="r(?P<section>\d)(?P<month>\d{1,2})(?P<year>\d{4})" '
        r'class="tab-pane[^>]*>(?P<body>.*?)(?=<div id="r\d|</div>\s*</div>\s*<div class="container|$)',
        re.S,
    )
    for match in pattern.finditer(page_html):
        body = match.group("body")
        if "rozklad-tabela" not in body:
            continue
        table_end = body.find("</table>")
        if table_end == -1:
            continue
        blocks.append((int(match.group("month")), int(match.group("year")), body[: table_end + 8]))
    return blocks


def _parse_time_range(value: str) -> tuple[str, str, str]:
    if " - " not in value:
        return "", "", ""
    departure, arrival = [part.strip() for part in value.split(" - ", 1)]
    next_day = "*" in arrival
    arrival = arrival.replace("*", "").strip()
    return departure, f"{arrival}+1" if next_day else arrival, "next_day" if next_day else ""


def _arrival_date(dep_date: date, next_day_marker: str) -> str:
    if next_day_marker:
        return (dep_date + timedelta(days=1)).isoformat()
    return ""


def _parse_table(month: int, year: int, table_html: str, source_url: str, source_detail: str) -> list[dict]:
    table_rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.S)
    if len(table_rows) < 3:
        return []

    parsed_rows = []
    for row in table_rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)
        parsed_rows.append([_strip_tags(cell) for cell in cells])

    day_numbers = [int(cell) for cell in parsed_rows[0][1:] if cell.isdigit()]
    route_name = parsed_rows[1][0] if parsed_rows[1] else ""
    ports = ROUTE_PORTS.get(route_name)
    if not day_numbers or not ports:
        return []

    avghamn, ankhamn = ports
    sailings: list[dict] = []
    for row in parsed_rows[2:]:
        if not row:
            continue
        departure_time, arrival_time, next_day_marker = _parse_time_range(row[0])
        if not departure_time or not arrival_time:
            continue
        for day_number, vessel_code in zip(day_numbers, row[1:]):
            vessel_code = vessel_code.strip()
            if not vessel_code or vessel_code in {"-", "–", "—"}:
                continue
            try:
                dep_date = date(year, month, day_number)
            except ValueError:
                continue
            vessel = VESSEL_CODES.get(vessel_code, vessel_code)
            sailings.append({
                "date": dep_date.isoformat(),
                "rederi": "Polferries (POLSCA)",
                "avghamn": avghamn,
                "ankhamn": ankhamn,
                "avgtid": departure_time,
                "anktid": arrival_time,
                "ankomstdatum": _arrival_date(dep_date, next_day_marker),
                "fartyg": vessel,
                "kalla": source_url,
                "source_label": SOURCE_LABEL,
                "source_detail": source_detail,
                "source_type": "date_table",
                "is_exact": True,
            })
    return sailings


def _fetch_timetable(source_url: str, source_detail: str) -> list[dict]:
    try:
        response = requests.get(source_url, timeout=(10, 25))
        response.raise_for_status()
    except Exception as exc:
        log.error("Kunde inte hämta %s: %s", source_detail, exc)
        return []

    sailings: list[dict] = []
    for month, year, table_html in _table_blocks(response.text):
        sailings.extend(_parse_table(month, year, table_html, source_url, source_detail))
    log.info("Hämtade %d rader från %s.", len(sailings), source_detail)
    return sailings


def fetch_ystad_swinoujscie() -> list[dict]:
    return _fetch_timetable(SOURCE_URL_YS, SOURCE_DETAIL_YS)


def fetch_swinoujscie_trelleborg() -> list[dict]:
    sailings = _fetch_timetable(SOURCE_URL_ST, SOURCE_DETAIL_ST)
    return [
        sailing
        for sailing in sailings
        if {sailing.get("avghamn"), sailing.get("ankhamn")} == {"Świnoujście", "Trelleborg"}
    ]


def fetch_all() -> list[dict]:
    sailings: list[dict] = []
    sailings.extend(fetch_ystad_swinoujscie())
    sailings.extend(fetch_swinoujscie_trelleborg())
    return sailings
