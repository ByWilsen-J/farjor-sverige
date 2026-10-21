from __future__ import annotations

import html
import logging
import re
from calendar import monthrange
from datetime import date, timedelta

import requests


SOURCE_URL_YS = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=ys"
SOURCE_DETAIL_YS = "Polferries Świnoujście-Ystad timetable"
SOURCE_URL_ST = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=st"
SOURCE_DETAIL_ST = "Polferries Świnoujście-Trelleborg timetable"
SOURCE_URL_GH = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=gh"
SOURCE_DETAIL_GH = "Polferries Gdańsk-Karlshamn timetable"
SOURCE_URL_GN = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=gn"
SOURCE_DETAIL_GN = "Polferries Gdańsk-Nynäshamn timetable"
SOURCE_LABEL = "Datumtabell"

VESSEL_CODES = {
    "VAR": "Varsovia",
    "MAZ": "Mazovia",
    "EPS": "Epsilon",
    "JAN": "Jantar",
    "GAL": "Galileusz",
    "POL": "Polonia",
    "SKA": "Skania",
    "COP": "Copernicus",
    "NS": "Nova Star",
    "WAW": "Wawel",
    "BUR": "Bursztyn Unity",
}

ROUTE_PORTS = {
    "Ystad - Świnoujście": ("Ystad", "Świnoujście"),
    "Świnoujście - Ystad": ("Świnoujście", "Ystad"),
    "Świnoujście - Trelleborg": ("Świnoujście", "Trelleborg"),
    "Trelleborg - Świnoujście": ("Trelleborg", "Świnoujście"),
    "Gdańsk - Karlshamn": ("Gdańsk", "Karlshamn"),
    "Karlshamn - Gdańsk": ("Karlshamn", "Gdańsk"),
    "Gdańsk - Nynäshamn": ("Gdańsk", "Nynäshamn"),
    "Nynäshamn - Gdańsk": ("Nynäshamn", "Gdańsk"),
}

log = logging.getLogger("polferries")


class SailingBatch(list):
    """Datumrader samt perioder där även tomma dagar är auktoritativa."""

    def __init__(self, rows=(), coverage=()):
        super().__init__(rows)
        self.coverage = list(coverage)


def _strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _table_blocks(page_html: str) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    # Section ids have one OR two digits (e.g. r10102026 = section 10,
    # October 2026). Splitting the numeric id with a one-digit section
    # silently lost Trelleborg return sailings and every Karlshamn table.
    # Read the explicit month label instead: January's id is ambiguous.
    months = {name: number for number, name in enumerate(
        ("January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"), start=1)}
    periods: dict[str, tuple[int, int]] = {}
    for anchor in re.finditer(r'<a\b[^>]*href=[\"\']#(r\d+)[\"\'][^>]*>(.*?)</a>', page_html, re.S):
        label = re.sub(r"<[^>]+>", " ", anchor.group(2))
        period = re.search(r"(" + "|".join(months) + r")\s*(\d{4})", label)
        if period:
            periods[anchor.group(1)] = (months[period.group(1)], int(period.group(2)))
    pattern = re.compile(
        r'<div id="(?P<id>r\d+)"\s+class="tab-pane[^>]*>(?P<body>.*?</table>)',
        re.S,
    )
    for match in pattern.finditer(page_html):
        body = match.group("body")
        if "rozklad-tabela" not in body or match.group("id") not in periods:
            continue
        table_end = body.find("</table>")
        if table_end == -1:
            continue
        month, year = periods[match.group("id")]
        blocks.append((month, year, body[: table_end + 8]))
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


def _fetch_timetable(source_url: str, source_detail: str) -> SailingBatch:
    try:
        response = requests.get(source_url, timeout=(10, 25))
        response.raise_for_status()
    except Exception as exc:
        log.error("Kunde inte hämta %s: %s", source_detail, exc)
        return SailingBatch()

    sailings = SailingBatch()
    for month, year, table_html in _table_blocks(response.text):
        table_rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.S)
        if len(table_rows) < 3:
            continue
        header_cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", table_rows[1], flags=re.S)
        ports = ROUTE_PORTS.get(_strip_tags(header_cells[0])) if header_cells else None
        day_cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", table_rows[0], flags=re.S)
        days = [int(_strip_tags(cell)) for cell in day_cells[1:] if _strip_tags(cell).isdigit()]
        if not ports or days != list(range(1, monthrange(year, month)[1] + 1)):
            log.warning("Ofullständig Polferries-tabell %s %s-%02d", source_detail, year, month)
            continue
        data_rows = [
            [_strip_tags(cell) for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
            for row in table_rows[2:]
        ]
        time_pattern = r"(?:[01]\d|2[0-3]):[0-5]\d"
        range_pattern = time_pattern + r" - " + time_pattern + r"\*?"
        if not data_rows or any(
            len(row) != len(days) + 1 or not re.fullmatch(range_pattern, row[0])
            for row in data_rows
        ):
            # A truncated row is NOT evidence that its missing dates were
            # cancelled. Do not allow malformed HTML to clear cached sailings.
            log.warning("Felaktig Polferries-datarad %s %s-%02d", source_detail, year, month)
            continue
        sailings.extend(_parse_table(month, year, table_html, source_url, source_detail))
        sailings.coverage.append({
            "rederi": "Polferries (POLSCA)", "avghamn": ports[0], "ankhamn": ports[1],
            "date_from": date(year, month, 1).isoformat(),
            "date_to": date(year, month, monthrange(year, month)[1]).isoformat(),
            "source_type": "date_table", "source_detail": source_detail,
        })
    log.info("Hämtade %d rader från %s.", len(sailings), source_detail)
    return sailings


def fetch_ystad_swinoujscie() -> list[dict]:
    return _fetch_timetable(SOURCE_URL_YS, SOURCE_DETAIL_YS)


def fetch_swinoujscie_trelleborg() -> list[dict]:
    sailings = _fetch_timetable(SOURCE_URL_ST, SOURCE_DETAIL_ST)
    return SailingBatch([
        sailing
        for sailing in sailings
        if {sailing.get("avghamn"), sailing.get("ankhamn")} == {"Świnoujście", "Trelleborg"}
    ], sailings.coverage)


def fetch_all() -> list[dict]:
    sailings = SailingBatch()
    for source_url, source_detail in (
        (SOURCE_URL_YS, SOURCE_DETAIL_YS), (SOURCE_URL_ST, SOURCE_DETAIL_ST),
        (SOURCE_URL_GH, SOURCE_DETAIL_GH), (SOURCE_URL_GN, SOURCE_DETAIL_GN),
    ):
        batch = _fetch_timetable(source_url, source_detail)
        sailings.extend(batch)
        sailings.coverage.extend(batch.coverage)
    return sailings
