#!/usr/bin/env python3
"""Publication gate: data age, current window, source refresh and major data loss."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import tempfile
from zoneinfo import ZoneInfo

import requests

from route_registry import route_key_from_instance

ROOT = Path(__file__).resolve().parent


def route_counts(data, today):
    end = today + timedelta(days=14)
    return Counter(route_key_from_instance(row) for day, rows in data.get("avgangsinstanser", {}).items() if today.isoformat() <= day <= end.isoformat() for row in rows)


def check_data(data, now=None, baseline=None, max_age_hours=48):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("Europe/Stockholm")).date()
    errors, warnings = [], []
    meta = data.get("meta", {})
    try:
        updated = datetime.fromisoformat(meta["uppdaterad"].replace("Z", "+00:00"))
        age = (now - updated).total_seconds() / 3600
        if age > max_age_hours or age < -1:
            errors.append(f"Dataålder {age:.1f} timmar; tillåtet 0–{max_age_hours} timmar.")
    except (KeyError, ValueError, TypeError):
        errors.append("meta.uppdaterad saknar en giltig tidsstämpel med tidszon.")
    try:
        start, end = (date.fromisoformat(item.strip()) for item in meta["publiceringsfonster"].split(" till "))
        if not start <= today <= end or end < today + timedelta(days=14):
            errors.append("Publiceringsfönstret täcker inte idag och kommande 14 dagar.")
    except (KeyError, ValueError, TypeError):
        errors.append("Publiceringsfönstret är ogiltigt.")
    counts = route_counts(data, today)
    if not counts:
        errors.append("Inga avgångsinstanser för idag/kommande 14 dagar.")
    for key, old in route_counts(baseline or {}, today).items():
        current = counts[key]
        if (old > 0 and current == 0) or (old >= 10 and current < old * 0.5):
            errors.append(f"Kraftigt tapp för {' / '.join(key)}: {old} → {current} avgångar kommande 14 dagar. Kräver granskning.")
    refresh = meta.get("source_refresh", {})
    entries = list(refresh.values()) if isinstance(refresh, dict) else refresh
    if entries and all(item.get("status") not in {"ok", "partial"} or not item.get("accepted_rows", item.get("received_rows", 0)) for item in entries):
        errors.append("Ingen dynamisk källa levererade data; publicering stoppas.")
    for name, item in (refresh.items() if isinstance(refresh, dict) else []):
        if item.get("status") in {"empty", "error", "partial"}:
            warnings.append(f"{name}: {item.get('status')}; kontrollera reservkällans giltighet.")
    return errors, warnings


LIVE_SOURCE_NAMES = ("Viking Line", "Tallink Silja", "DFDS", "Finnlines", "Stena Line", "TT-Line", "Polferries (POLSCA)", "Molslinjen")


def live_source_issues(data, now=None):
    """Track live collection separately from whether fallback data can publish."""
    now = now or datetime.now(timezone.utc)
    refresh = data.get("meta", {}).get("source_refresh", {})
    issues = []
    for name in LIVE_SOURCE_NAMES:
        entry = refresh.get(name, {})
        status = entry.get("status", "not_checked")
        checked = entry.get("checked_at")
        reason = None
        if status == "disabled":
            reason = "Livehämtning avstängd; behöver återverifieras. Avstängning bevisar ingen blockering."
        elif status != "ok" or not entry.get("accepted_rows", entry.get("received_rows", 0)):
            reason = "Ingen fullständigt godkänd livehämtning; fortsatt felsökning behövs."
        else:
            try:
                age = (now - datetime.fromisoformat(checked.replace("Z", "+00:00"))).total_seconds() / 3600
                if age > 26 or age < -1:
                    reason = "Livekällans kontroll är äldre än 26 timmar eller har ogiltig framtidstid."
            except (AttributeError, TypeError, ValueError):
                reason = "Livekällan saknar en giltig kontrolltid."
        if reason:
            issues.append({"source": name, "status": status, "checked_at": checked, "reason": reason})
    return issues


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inline = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.inline = not attrs.get("src") and attrs.get("type", "text/javascript") in {"text/javascript", "module"}

    def handle_endtag(self, tag):
        if tag == "script":
            self.inline = False

    def handle_data(self, text):
        if self.inline:
            self.scripts.append(text)


def check_javascript(root=ROOT):
    errors = []
    for page in root.glob("*.html"):
        scripts = Scripts()
        scripts.feed(page.read_text())
        for index, text in enumerate(scripts.scripts):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".js") as handle:
                handle.write(text)
                handle.flush()
                try:
                    result = subprocess.run(["node", "--check", handle.name], capture_output=True, text=True)
                except FileNotFoundError:
                    errors.append("Node.js saknas; JavaScript-kontroll kunde inte utföras.")
                    return errors
                if result.returncode:
                    errors.append(f"{page.name} skript {index + 1}: {result.stderr.strip()}")
    return errors


def check_published(base_url="https://farjor.axling.nu", get=requests.get):
    errors, observations = [], []
    for path in ("/", "/farjor.html", "/farjor_data.json"):
        url = base_url.rstrip("/") + path
        record = {"url": url, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        try:
            response = get(url, timeout=(10, 30), headers={"Cache-Control": "no-cache", "User-Agent": "FarjorSourceMonitor/1.0"})
            record.update(http_status=response.status_code, final_url=response.url)
            if response.status_code != 200:
                errors.append(f"Publicerad sida {url}: HTTP {response.status_code}.")
            elif path.endswith(".json"):
                data = response.json()
                data_errors, _ = check_data(data)
                errors.extend(f"Publicerade data: {error}" for error in data_errors)
                record["data_updated_at"] = data.get("meta", {}).get("uppdaterad")
                record["data_errors"] = data_errors
            elif path == "/" and "farjor_data.json" not in response.text:
                errors.append(f"Publicerad startsida {url} saknar förväntad datakoppling.")
            elif path == "/farjor.html" and not any(marker in response.text for marker in ("index.html", "url=./", "location.replace('./')")):
                errors.append(f"Publicerad äldre adress {url} saknar väntad redirect till index.html.")
        except (requests.RequestException, ValueError, TypeError) as exc:
            record.update(error=type(exc).__name__, detail=str(exc)[:500])
            errors.append(f"Publicerad sida {url}: {type(exc).__name__}.")
        observations.append(record)
    return errors, observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--max-age-hours", type=int, default=48)
    parser.add_argument("--skip-javascript", action="store_true")
    parser.add_argument("--published-only", action="store_true", help="Kontrollera den verkliga publicerade sidan separat från kandidatens publiceringsgrind.")
    parser.add_argument("--live-sources-only", action="store_true", help="Markera otillgängliga eller oprövade livekällor som fortsatt arbete, separat från publiceringsgrinden.")
    args = parser.parse_args()
    if args.live_sources_only:
        issues = live_source_issues(json.loads((ROOT / "farjor_data.json").read_text()))
        (ROOT / "docs/live-source-status.json").write_text(json.dumps({"assessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issues": issues}, ensure_ascii=False, indent=2) + "\n")
        for item in issues:
            print(f"ÖPPEN LIVEKÄLLA: {item['source']}: {item['reason']}")
        return bool(issues)
    if args.published_only:
        errors, observations = check_published()
        (ROOT / "docs/site-health-checks.json").write_text(json.dumps({"checks": observations, "errors": errors}, ensure_ascii=False, indent=2) + "\n")
        for error in errors:
            print(f"FEL: {error}")
        print(f"Kontroll av publicerad webbplats: {len(errors)} fel.")
        return bool(errors)
    baseline = json.loads(args.baseline.read_text()) if args.baseline else None
    errors, warnings = check_data(json.loads((ROOT / "farjor_data.json").read_text()), baseline=baseline, max_age_hours=args.max_age_hours)
    if not args.skip_javascript:
        errors.extend(check_javascript())
    for message in warnings:
        print(f"VARNING: {message}")
    for message in errors:
        print(f"FEL: {message}")
    print(f"Hälsokontroll: {len(errors)} fel, {len(warnings)} varningar.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
