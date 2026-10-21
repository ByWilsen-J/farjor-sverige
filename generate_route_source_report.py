#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from audit_source_links import URL_PATTERN
from route_registry import ACTIVE_BY_ROUTE, REFERENCE_ONLY_ROUTES, active_route_keys, route_key_from_instance


ROOT = Path(__file__).parent
DATA_FILE = ROOT / "farjor_data.json"
REPORT_FILE = ROOT / "docs" / "farjelinjer-kallor.md"
LEDGER_FILE = ROOT / "docs" / "source-link-checks.json"

IMPORTERS = {
    "DFDS": "dfds_scraper.py", "Tallink Silja": "tallink_scraper.py",
    "Finnlines": "finnlines_scraper.py", "Stena Line": "stena_line_scraper.py",
    "TT-Line": "ttline_scraper.py", "Polferries (POLSCA)": "polferries_scraper.py",
    "Bornholmslinjen": "molslinjen_scraper.py", "Øresundslinjen": "molslinjen_scraper.py",
}
STATUS_LABELS = {
    "ok": "Åtkomlig", "broken": "Bekräftad 404/410", "blocked_or_limited": "Blockerad/begränsad – manuell kontroll",
    "api_requires_request": "API kräver metod/parametrar – inget bevis på trasig länk",
    "api_request_or_server_error": "API: ofullständigt GET eller serverfel – inget bevis på trasig länk",
    "temporarily_unavailable": "Tillfälligt serverfel", "network_error": "Nätverks-/TLS-fel – manuell kontroll",
    "needs_review": "Behöver granskas",
}


def check_label(url, checks):
    entry = checks.get(url, {})
    if not entry:
        return "Ej kontrollerad"
    status = STATUS_LABELS.get(entry.get("status"), entry.get("status", "Okänd"))
    return f"{entry.get('checked_at', '-')} · {status} · HTTP {entry.get('http_status', '-')}"


def importer(route):
    if route.source_type == "link_only":
        return "index.html (länkvisare; ingen tidtabellsimport)"
    if route.source_type == "weekly_schedule":
        return "generera_json.py + verified_schema_overrides.py (verifierat reservschema; inte ny livehämtning)"
    return IMPORTERS.get(route.operator, "update_fartyg.py") + " → update_fartyg.py"


def md_link(url: str) -> str:
    return f"[källa]({url})" if url else "-"


SOURCE_TYPE_LABELS = {
    "dynamic_schedule": "Live-/datumkälla",
    "date_table": "Datumtabell",
    "weekly_schedule": "Veckoschema",
    "link_only": "Länkvisare",
}


def source_label(identity: tuple[str, str, str]) -> str:
    source_type, source_detail, source_url = identity
    detail = source_detail or SOURCE_TYPE_LABELS.get(source_type, source_type) or "okänd källa"
    return f"{source_type or '-'} / {detail} / {md_link(source_url)}"


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    meta = data.get("meta") or {}
    checks = json.loads(LEDGER_FILE.read_text()).get("links", {}) if LEDGER_FILE.exists() else {}
    inventory = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pages": {}, "routes": []}

    route_rows: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for entries in (data.get("avgangsinstanser") or {}).values():
        for inst in entries or []:
            key = route_key_from_instance(inst)
            if key in ACTIVE_BY_ROUTE:
                route_rows[key].append(inst)

    lines = [
        "# Färjelinjer, fartyg och källor",
        "",
        f"Genererad från `farjor_data.json`. Publiceringsfönster: `{meta.get('publiceringsfonster', '-')}`. Dynamiskt fönster: `{meta.get('dynamic_window', '-')}`.",
        "",
        "Länkkontrollens datum kommer endast från verkliga HTTP-försök i `source-link-checks.json`; rapportgenerering flyttar aldrig fram dem. HTTP 200 visar åtkomst, inte att tidtabellens innehåll är korrekt. API-GET utan rätt parametrar och 403/429 är kontrollbegränsningar, inte bekräftade trasiga länkar. En datagenerering förnyar heller inte ett gammalt reservschemas verifieringsdatum.",
        "",
        "Regel: varje rutt ska ha exakt en publicerad primärkälla. Om källan saknar exakt fartygsnamn används ingen gissning, förutom dokumenterad ruttfallback där detta markeras som fallback.",
        "",
        "| Rederi | Rutt | Avgångar | Datum | Fartyg i publicerad data | Primär källa | Kommentar |",
        "|---|---|---:|---|---|---|---|",
    ]

    for key in sorted(active_route_keys()):
        route = ACTIVE_BY_ROUTE[key]
        rows = route_rows.get(key, [])
        dates = sorted({str(row.get("datum") or "") for row in rows if row.get("datum")})
        date_range = f"{dates[0]} - {dates[-1]}" if dates else "-"
        vessels = Counter(str(row.get("fartyg") or "").strip() for row in rows)
        vessels.pop("", None)
        vessel_text = ", ".join(name for name, _ in vessels.most_common(12)) or "Källan anger inte exakt fartyg"
        if len(vessels) > 12:
            vessel_text += f", +{len(vessels) - 12} fler"
        sources = Counter(
            (
                str(row.get("source_type") or ""),
                str(row.get("source_detail") or ""),
                str(row.get("kalla") or ""),
            )
            for row in rows
        )
        primary = source_label(sources.most_common(1)[0][0]) if sources else source_label((route.source_type, route.source_detail or "", route.source_url))
        fallback_count = sum(1 for row in rows if row.get("is_exact") is False)
        comments = []
        if route.note:
            comments.append(route.note)
        if fallback_count:
            if vessels:
                comments.append(f"{fallback_count} rader kommer från schema/fallback och är inte markerade som live-exakta.")
            else:
                comments.append("Veckoschemat saknar exakt fartygsnamn i publicerad data.")
        lines.append(
            "| "
            + " | ".join([
                route.operator,
                f"{route.avghamn} -> {route.ankhamn}",
                str(len(rows)),
                date_range,
                vessel_text,
                primary,
                " ".join(comments) or "-",
            ])
            + " |"
        )

    if REFERENCE_ONLY_ROUTES:
        lines.extend([
            "",
            "## Aktiva länkvisare",
            "",
            "Dessa linjer finns med på sidan som länkvisare eftersom vi ännu inte har en säker datumimport som kan publicera exakta avgångsrader utan att riskera fel eller dubbletter.",
            "",
            "| Rederi | Rutt | Källa | Kommentar |",
            "|---|---|---|---|",
        ])
        for route in sorted(REFERENCE_ONLY_ROUTES, key=lambda item: (item.operator, item.avghamn, item.ankhamn)):
            lines.append(
                "| "
                + " | ".join([
                    route.operator,
                    f"{route.avghamn} -> {route.ankhamn}",
                    source_label((route.source_type, route.source_detail or "", route.source_url)),
                    route.note or "-",
                ])
                + " |"
            )

    lines.extend(["", "## Varifrån varje sida hämtar information", "", "| Sida | Innehåll/källa |", "|---|---|"])
    for page, source in (("index.html", "farjor_data.json → avgangsinstanser; reservvisning från schema. Live-/datumdata hämtas av Python-jobben nedan; frontend har även direkta API-anrop som komplettering."), ("farjor.html", "Omdirigering till index.html; ingen separat tidtabell.")):
        inventory["pages"][page] = {"description": source, "data_file": "farjor_data.json" if page == "index.html" else None}
        lines.append(f"| [{page}](../{page}) | {source} |")

    lines.extend(["", "## Rutternas faktiska källor och senaste länkkontroll", "", "Primärkällan i registret och alla olika käll-URL:er i publicerade rader redovisas tillsammans. Reservkällor kan därför synas även när en API-källa är utsedd som primär. Tider får inte härledas från att en länk fungerar. Senaste datahämtning är separat från länkkontroll; cache återanvänder gamla verifierade datumrader och förnyar aldrig deras källtidsstämpel.", "", "| Rederi / riktning | Hämtning i kod | Senaste lyckade datahämtning / cache | Käll-URL och senaste länkkontroll (UTC) |", "|---|---|---|---|"])
    for route in sorted((*ACTIVE_BY_ROUTE.values(), *REFERENCE_ONLY_ROUTES), key=lambda item: item.key):
        urls = sorted({route.source_url, *(str(row.get("kalla")) for row in route_rows.get(route.key, []) if row.get("kalla"))})
        checked = []
        for url in urls:
            entry = checks.get(url, {})
            final = entry.get("final_url")
            checked.append(f"[{url}]({url}) — {check_label(url, checks)}" + (f" → [{final}]({final})" if final and final != url else ""))
        rows = route_rows.get(route.key, [])
        timestamps = sorted({str(row['source_checked_at']) for row in rows if row.get('source_checked_at')})
        cached = sum(bool(row.get('source_cached')) for row in rows)
        data_checked = (timestamps[-1] if timestamps else 'Ingen registrerad lyckad livehämtning') + f'; {cached} cachade rader'
        inventory["routes"].append({"operator": route.operator, "from": route.avghamn, "to": route.ankhamn, "source_type": route.source_type, "importer": importer(route), "registry_url": route.source_url, "last_successful_data_at": timestamps[-1] if timestamps else None, "cached_rows": cached, "sources": [{"url": url, "check": checks.get(url)} for url in urls]})
        lines.append(f"| {route.operator}: {route.avghamn} → {route.ankhamn} | `{importer(route)}` | {data_checked} | {'<br>'.join(checked)} |")

    lines.extend(["", "## Alla externa länkar på sidorna", "", "Inkluderar sidopanel, datakällor och externa skript. Varje URL kontrolleras separat; redirectens slutadress sparas. Länkar med dynamiska `${…}` måste kontrolleras genom rätt scraper-anrop.", "", "| Sida | Länk | Senaste försök (UTC) / resultat | Slutadress |", "|---|---|---|---|"])
    for path in sorted(ROOT.glob("*.html")):
        urls = sorted({url for url in URL_PATTERN.findall(path.read_text()) if "${" not in url})
        inventory["pages"].setdefault(path.name, {})["external_links"] = [{"url": url, "check": checks.get(url)} for url in urls]
        for url in urls:
            lines.append(f"| {path.name} | [{url}]({url}) | {check_label(url, checks)} | {checks.get(url, {}).get('final_url', '-')} |")

    lines.extend(["", "## Drift och automatisk felsökning", "", "Se [drift-och-lankkontroll.md](drift-och-lankkontroll.md) för körschema, larm, publiceringsgrindar och gränserna för säkra automatiska rättningar.", ""])

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    (ROOT / "docs/source-inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    print(f"Skrev {REPORT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
