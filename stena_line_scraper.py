"""
Stena Line Freight — Timetable Scraper
======================================
Hämtar avgångar och fartygsnamn från Stena Line Freights WordPress-AJAX.

Returnerar samma format som övriga skrapare:
  { date, avghamn, ankhamn, avgtid, fartyg, rederi }
"""

import html
import logging
import re
import time
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Optional

import requests

BASE_URL = "https://stenalinefreight.com"
TIMETABLE_URL = f"{BASE_URL}/timetable/"
AJAX_URL = f"{BASE_URL}/wp/wp-admin/admin-ajax.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
}

ROUTES = {
    "GOFR": "Gothenburg – Frederikshavn",
    "GDKA": "Gdynia – Karlskrona",
    "GOKI": "Gothenburg – Kiel",
    "TGRO": "Trelleborg – Rostock",
}

PORT_NAMES = {
    "Frederikshavn": "Frederikshavn",
    "Gothenburg": "Göteborg",
    "Göteborg": "Göteborg",
    "Kiel": "Kiel",
    "Gdynia": "Gdynia",
    "Karlskrona": "Karlskrona",
    "Trelleborg": "Trelleborg",
    "Rostock": "Rostock",
}

SHIP_NAMES = {
    "STENA DANICA": "Stena Danica",
    "STENA JUTLANDICA": "Stena Jutlandica",
    "STENA JUTLANDICA (C)": "Stena Jutlandica",
    "STENA EBBA": "Stena Ebba",
    "STENA ESTELLE": "Stena Estelle",
    "STENA SPIRIT": "Stena Spirit",
    "STENA GERMANICA": "Stena Germanica",
    "STENA SCANDINAVICA": "Stena Scandinavica",
    "MECKLENBURG VORPOMMERN": "Mecklenburg-Vorpommern",
    "MECKLENBURG VORPOMMERN (C)": "Mecklenburg-Vorpommern",
    "SKAANE": "Skåne",
    "SKÅNE": "Skåne",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("stena")


class StenaTimetableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self.current_date = ""
        self.direction = ""
        self._target = None
        self._buf: list[str] = []
        self._cells: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if tag == "h3":
            self._start("h3")
        elif "date" in cls:
            self._start("date")
        elif "Rtable-cell" in cls and "head" not in cls:
            self._start("cell")

    def handle_data(self, data):
        if self._target:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if not self._target:
            return
        if self._target == "h3" and tag == "h3":
            self.direction = self._text()
            self._target = None
        elif self._target == "date":
            self.current_date = self._text()
            self._target = None
        elif self._target == "cell":
            self._cells.append((self.current_date, self._text()))
            self._target = None

    def close(self):
        super().close()
        self._flush_cells()

    def _start(self, target: str):
        if target == "h3":
            self._flush_cells()
        self._target = target
        self._buf = []

    def _text(self) -> str:
        return " ".join(html.unescape("".join(self._buf)).split())

    def _flush_cells(self):
        for i in range(0, len(self._cells) - 3, 4):
            dep_parts = self._cells[i][1].split()
            self.rows.append({
                "direction": self.direction,
                "date_label": self._cells[i][0],
                "dep": dep_parts[0] if dep_parts else "",
                "arr": self._cells[i + 1][1],
                "vessel": self._cells[i + 2][1],
                "status": self._cells[i + 3][1],
            })
        self._cells = []


def normalize_port(port: str) -> str:
    return PORT_NAMES.get(port.strip(), port.strip())


def normalize_ship(name: str) -> str:
    name = " ".join((name or "").split())
    return SHIP_NAMES.get(name, name.title() if name.isupper() else name)


def split_direction(direction: str) -> tuple[str, str]:
    parts = re.split(r"\s+[–-]\s+", direction, maxsplit=1)
    if len(parts) != 2:
        return "", ""
    return normalize_port(parts[0]), normalize_port(parts[1])


def parse_date_label(label: str) -> str:
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", label or "")
    return m.group(1) if m else ""


def parse_time_only(text: str) -> str:
    m = re.search(r"\b(\d{1,2}:\d{2})\b", text or "")
    return m.group(1).zfill(5) if m else ""


def get_nonce() -> Optional[str]:
    try:
        resp = requests.get(TIMETABLE_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        match = re.search(r'"security"\s*:\s*"([^"]{8,12})"', resp.text)
        return match.group(1) if match else None
    except requests.exceptions.RequestException as e:
        log.error("Kunde inte hämta Stena nonce: %s", e)
        return None


def fetch_route(route_code: str, date_from: date, date_to: date, nonce: str) -> Optional[str]:
    payload = {
        "action": "timetable",
        "data[from]": date_from.isoformat(),
        "data[to]": date_to.isoformat(),
        "data[routeCode]": route_code,
        "security": nonce,
    }
    try:
        resp = requests.post(AJAX_URL, data=payload, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("success"):
            log.warning("Stena API-fel %s: %s", route_code, result)
            return None
        return result.get("data", {}).get("content", "")
    except requests.exceptions.RequestException as e:
        log.error("Stena API-fel (%s): %s", route_code, e)
        return None


def parse_timetable(html_text: str) -> list[dict]:
    parser = StenaTimetableParser()
    parser.feed(html_text or "")
    parser.close()
    return parser.rows


def fetch_all(date_from: date = None, date_to: date = None) -> list[dict]:
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=14)

    nonce = get_nonce()
    if not nonce:
        log.error("Ingen Stena nonce hittades.")
        return []

    all_sailings = []
    for route_code, route_name in ROUTES.items():
        log.info("Hämtar Stena %s (%s – %s)…", route_name, date_from, date_to)
        html_text = fetch_route(route_code, date_from, date_to, nonce)
        if not html_text:
            continue
        rows = parse_timetable(html_text)
        for row in rows:
            ds = parse_date_label(row.get("date_label", ""))
            avghamn, ankhamn = split_direction(row.get("direction", ""))
            if not ds or not avghamn or not ankhamn or not row.get("dep"):
                continue
            anktid = parse_time_only(row.get("arr", ""))
            all_sailings.append({
                "date": ds,
                "avghamn": avghamn,
                "ankhamn": ankhamn,
                "avgtid": row["dep"],
                "ankomstdatum": ds,
                "anktid": anktid,
                "fartyg": normalize_ship(row.get("vessel", "")),
                "rederi": "Stena Line",
            })
        log.info("  %d avgångar.", len(rows))
        time.sleep(1)
    return all_sailings


if __name__ == "__main__":
    import sys
    from_d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    to_d = from_d + timedelta(days=7)
    for s in fetch_all(from_d, to_d):
        print(f"  {s['date']}  {s['avgtid']}  {s['avghamn']}→{s['ankhamn']}  {s['fartyg']}")
