"""
TT-Line — Timetable Scraper
===========================
Hämtar avgångar och fartygsnamn från TT-Lines timetable endpoint.

Returnerar samma format som övriga skrapare:
  { date, avghamn, ankhamn, avgtid, fartyg, rederi }
"""

import html
import logging
import os
import re
import subprocess
import tempfile
import time
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Optional

import requests
try:
    import certifi
except ImportError:
    certifi = None

BASE_URL = "https://www.ttline.com"
TIMETABLE_URL = f"{BASE_URL}/en/timetables/"
SAILING_URL = f"{BASE_URL}/sailing/info/"
SOURCE_DETAIL = "TT-Line timetable endpoint"

ROUTES = [
    "TRA;TRE", "TRE;TRA",
    "ROS;TRE", "TRE;ROS",
    "KLA;TRE", "TRE;KLA",
    "SWI;TRE", "TRE;SWI",
]

SHIP_CODES = {
    "TS": "Tom Sawyer",
    "NH": "Nils Holgersson",
    "HF": "Huckleberry Finn",
    "PP": "Peter Pan",
    "MP": "Marco Polo",
    "ND": "Nils Dacke",
    "TB": "Tinker Bell",
    "RH": "Robin Hood",
}

PORT_NAMES = {
    "Travemunde": "Travemünde",
    "Travemünde": "Travemünde",
    "Rostock": "Rostock",
    "Trelleborg": "Trelleborg",
    "Klaipeda": "Klaipėda",
    "Klaipėda": "Klaipėda",
    "Swinoujscie": "Świnoujście",
    "Swinoujście": "Świnoujście",
    "Świnoujście": "Świnoujście",
}

MONTHS = {
    "jan": 1, "january": 1, "januar": 1,
    "feb": 2, "february": 2, "februar": 2,
    "mar": 3, "march": 3, "mars": 3, "mär": 3, "maerz": 3, "märz": 3,
    "apr": 4, "april": 4,
    "may": 5, "maj": 5, "mai": 5,
    "jun": 6, "june": 6, "juni": 6,
    "jul": 7, "july": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "okt": 10, "october": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dec": 12, "dez": 12, "december": 12, "dezember": 12,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ttline")


class TTTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self.links: list[list[str]] = []
        self._in_tr = False
        self._in_td = False
        self._current_cells: list[str] = []
        self._current_links: list[str] = []
        self._buf: list[str] = []
        self._skip_abbr_data = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._in_tr = True
            self._current_cells = []
            self._current_links = []
        elif self._in_tr and tag == "td":
            self._in_td = True
            self._buf = []
        elif self._in_tr and tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self._current_links.append(html.unescape(href))
        elif self._in_td and tag == "abbr":
            title = dict(attrs).get("title", "")
            if title:
                self._buf.append(title)
                self._skip_abbr_data = True

    def handle_data(self, data):
        if self._in_td and not self._skip_abbr_data:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self._in_td:
            self._current_cells.append(" ".join(html.unescape("".join(self._buf)).split()))
            self._in_td = False
            self._skip_abbr_data = False
        elif tag == "abbr":
            self._skip_abbr_data = False
        elif tag == "tr" and self._in_tr:
            if self._current_cells:
                self.rows.append(self._current_cells)
                self.links.append(self._current_links)
            self._in_tr = False


def resolve_ship(code: str) -> str:
    code = (code or "").strip()
    return SHIP_CODES.get(code, code)


def normalize_port(port: str) -> str:
    return PORT_NAMES.get(port.strip(), port.strip())


def split_route(route_text: str) -> tuple[str, str]:
    parts = re.split(r"\s+[–-]\s+", route_text or "", maxsplit=1)
    if len(parts) != 2:
        return "", ""
    return normalize_port(parts[0]), normalize_port(parts[1])


def extract_token(session: requests.Session) -> Optional[str]:
    try:
        resp = session.get(TIMETABLE_URL, timeout=20)
        resp.raise_for_status()
        for tag in re.findall(r"<input\b[^>]*>", resp.text, flags=re.I):
            if '__RequestVerificationToken' not in tag:
                continue
            match = re.search(r'value="([^"]+)"', tag)
            if match:
                return html.unescape(match.group(1))
        return None
    except requests.exceptions.RequestException as e:
        log.error("Kunde inte hämta TT-Line CSRF-token: %s", e)
        return None


def extract_token_with_curl() -> tuple[Optional[str], Optional[str]]:
    cookie_file = tempfile.NamedTemporaryFile(prefix="ttline_cookie_", suffix=".txt", delete=False)
    cookie_path = cookie_file.name
    cookie_file.close()
    body_file = tempfile.NamedTemporaryFile(prefix="ttline_body_", suffix=".html", delete=False)
    body_path = body_file.name
    body_file.close()
    try:
        subprocess.run(
            [
                "curl",
                "-sS",
                "-L",
                "-A",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                "-H",
                "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-c",
                cookie_path,
                "-o",
                body_path,
                TIMETABLE_URL,
            ],
            check=True,
            timeout=30,
            capture_output=True,
            text=True,
        )
        html_text = open(body_path, encoding="utf-8", errors="ignore").read()
        match = re.search(
            r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
            html_text,
        )
        if not match:
            log.error("Curl-fallback hittade ingen TT-Line CSRF-token i HTML-sidan.")
            return None, None
        return html.unescape(match.group(1)), cookie_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.error("Curl-fallback misslyckades vid tokenhämtning för TT-Line: %s", e)
        return None, None
    finally:
        if os.path.exists(body_path):
            os.unlink(body_path)
        if not os.path.exists(cookie_path):
            cookie_path = ""


def parse_date_time_cell(text: str, fallback_year: int) -> tuple[str, str]:
    text = " ".join((text or "").replace(",", " ").split())
    time_matches = re.findall(r"\b(\d{1,2}:\d{2})\b", text)
    date_matches = re.findall(r"\b(\d{1,2})\s+([A-Za-zÅÄÖåäöüÜ]+)", text)
    if not time_matches:
        return "", ""
    chosen_time = time_matches[-1].zfill(5)
    if not date_matches:
        return "", chosen_time
    day_text, month_text = date_matches[-1]
    day = int(day_text)
    month_key = month_text.lower().strip(".")
    month = MONTHS.get(month_key)
    if not month:
        return "", chosen_time
    return date(fallback_year, month, day).isoformat(), chosen_time


def infer_arrival_date(dep_date: str, dep_time: str, arr_date: str, arr_time: str) -> str:
    if arr_date:
        return arr_date
    if not dep_date:
        return ""
    if not dep_time or not arr_time:
        return dep_date
    if arr_time >= dep_time:
        return dep_date
    return (date.fromisoformat(dep_date) + timedelta(days=1)).isoformat()


def build_traffic_comment(status: str) -> str:
    value = " ".join((status or "").split())
    if not value:
        return ""
    if re.search(r"^(on time|scheduled|planerad)$", value, re.I):
        return ""
    return f"TT-Line-status: {value}"


def fetch_route(session: requests.Session, token: str, route: str, day: date) -> Optional[str]:
    payload = {
        "route": route,
        "sdate": day.isoformat(),
        "Language": "en",
        "IsHomepageMode": "False",
        "IsFreightMode": "False",
        "ExcludedHarbours": "",
        "__RequestVerificationToken": token,
    }
    try:
        resp = session.post(SAILING_URL, data=payload, headers={"Accept": "text/html, */*"}, timeout=25)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException as e:
        log.error("TT-Line API-fel (%s %s): %s", route, day, e)
        return None


def fetch_route_with_curl(cookie_path: str, token: str, route: str, day: date) -> Optional[str]:
    try:
        resp = subprocess.run(
            [
                "curl",
                "-sS",
                "-b",
                cookie_path,
                "-c",
                cookie_path,
                "-X",
                "POST",
                "-H",
                "Accept: text/html, */*",
                "-H",
                "X-Requested-With: XMLHttpRequest",
                "--data-urlencode",
                f"route={route}",
                "--data-urlencode",
                f"sdate={day.isoformat()}",
                "--data-urlencode",
                "Language=en",
                "--data-urlencode",
                "IsHomepageMode=False",
                "--data-urlencode",
                "IsFreightMode=False",
                "--data-urlencode",
                "ExcludedHarbours=",
                "--data-urlencode",
                f"__RequestVerificationToken={token}",
                SAILING_URL,
            ],
            check=True,
            timeout=35,
            capture_output=True,
            text=True,
        )
        return resp.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.error("TT-Line curl-fallback API-fel (%s %s): %s", route, day, e)
        return None


def parse_table(html_text: str, fallback_year: int) -> list[dict]:
    parser = TTTableParser()
    parser.feed(html_text or "")
    rows = []
    for cells in parser.rows:
        if len(cells) < 4:
            continue
        ds, avgtid = parse_date_time_cell(cells[0], fallback_year)
        ankdatum_raw, anktid = parse_date_time_cell(cells[1], fallback_year)
        avghamn, ankhamn = split_route(cells[3])
        if not ds or not avgtid or not avghamn or not ankhamn:
            continue
        ankdatum = infer_arrival_date(ds, avgtid, ankdatum_raw, anktid)
        rows.append({
            "date": ds,
            "avghamn": avghamn,
            "ankhamn": ankhamn,
            "avgtid": avgtid,
            "ankomstdatum": ankdatum,
            "anktid": anktid,
            "fartyg": resolve_ship(cells[2]),
            "rederi": "TT-Line",
            "kalla": TIMETABLE_URL,
            "source_label": "Live-tidtabell",
            "source_detail": SOURCE_DETAIL,
            "source_type": "dynamic_schedule",
            "status": cells[5] if len(cells) > 5 else "",
            "traffic_comment": build_traffic_comment(cells[5] if len(cells) > 5 else ""),
        })
    return rows


def fetch_all(date_from: date = None, date_to: date = None) -> list[dict]:
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=14)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    if certifi is not None:
        session.verify = certifi.where()

    curl_cookie_path: Optional[str] = None
    use_curl_transport = False
    token = extract_token(session)
    if not token:
        token, curl_cookie_path = extract_token_with_curl()
        use_curl_transport = bool(token and curl_cookie_path)
    if not token:
        log.error("Ingen TT-Line CSRF-token hittades.")
        return []

    seen = set()
    all_sailings = []
    try:
        current = date_from
        while current <= date_to:
            for route in ROUTES:
                if use_curl_transport and curl_cookie_path:
                    html_text = fetch_route_with_curl(curl_cookie_path, token, route, current)
                else:
                    html_text = fetch_route(session, token, route, current)
                    if not html_text:
                        if not curl_cookie_path:
                            token, curl_cookie_path = extract_token_with_curl()
                        if token and curl_cookie_path:
                            use_curl_transport = True
                            html_text = fetch_route_with_curl(curl_cookie_path, token, route, current)
                if not html_text:
                    continue
                rows = parse_table(html_text, current.year)
                for row in rows:
                    if not (date_from.isoformat() <= row["date"] <= date_to.isoformat()):
                        continue
                    key = (row["date"], row["avghamn"], row["ankhamn"], row["avgtid"], row["fartyg"])
                    if key in seen:
                        continue
                    seen.add(key)
                    all_sailings.append(row)
                time.sleep(0.2)
            current += timedelta(days=1)
    finally:
        if curl_cookie_path and os.path.exists(curl_cookie_path):
            os.unlink(curl_cookie_path)
    log.info("Hämtade %d TT-Line-avgångar.", len(all_sailings))
    return all_sailings


if __name__ == "__main__":
    import sys
    from_d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    to_d = from_d + timedelta(days=7)
    for s in fetch_all(from_d, to_d):
        print(f"  {s['date']}  {s['avgtid']}  {s['avghamn']}→{s['ankhamn']}  {s['fartyg']}")
