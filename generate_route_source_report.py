#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from route_registry import ACTIVE_BY_ROUTE, REFERENCE_ONLY_ROUTES, active_route_keys, route_key_from_instance


ROOT = Path(__file__).parent
DATA_FILE = ROOT / "farjor_data.json"
REPORT_FILE = ROOT / "docs" / "farjelinjer-kallor.md"


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

    route_rows: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for entries in (data.get("avgangsinstanser") or {}).values():
        for inst in entries or []:
            key = route_key_from_instance(inst)
            if key in ACTIVE_BY_ROUTE:
                route_rows[key].append(inst)

    lines = [
        "# Färjelinjer, fartyg och källor",
        "",
        f"Genererad från `farjor_data.json` efter kvalitetskontroll. Publiceringsfönster: `{meta.get('publiceringsfonster', '-')}`. Dynamiskt fönster: `{meta.get('dynamic_window', '-')}`.",
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

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Skrev {REPORT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
