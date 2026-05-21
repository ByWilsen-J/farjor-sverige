# 🛳️ Polsca / Polferries Schedule System — Technical Investigation Report

**Datum:** 2026-05-19  
**Källa:** `https://www.polsca.com/schedule`  
**Metod:** Live browser-analys med nätverksinspektion och JS-bundle-reverse-engineering

---

## FINDINGS

### 1. Frontend-arkitektur

- **Framework:** React 18 med [Mantine UI](https://mantine.dev/), bundlad med Vite
- **Bundle:** `https://www.polsca.com/assets/index-XREp1Et2.js` (2,35 MB)
- **State management:** Redux Toolkit (bekräftat i bundle)
- **Routing:** React Router v7

### 2. Renderingsmodell

Schemasidan är **client-side rendered**. All schemadata hämtas vid sidladdning via 3 bakgrunds-GET-förfrågningar genom en proxy. Därefter är datumfiltrering **helt client-side** — att byta datum triggar noll nya nätverksanrop. Att byta rutt triggar heller inga nya schemahämtningar (alla 3 ruttar laddas simultant vid sidöppning).

### 3. Datakälla

Det finns **ingen strukturerad schema-API**. Schemadatan kommer från fullständiga HTML-sidor på `polferries.pl` som hämtas via en transparent proxyserver. Proxyn är det faktiska gränssnittet.

---

## APIS DISCOVERED

### Endpoint A — Schema-proxy (PRIMÄR SCHEMADATA)

```
GET https://ull.qvistorp.net:6798/?target_url=https://polferries.pl/rozklad-i-cennik/rozklad.html?code={CODE}
```

| Kod | Rutt |
|-----|------|
| `gn` | Gdańsk ↔ Nynäshamn (båda riktningarna i en sida) |
| `sy` | Świnoujście ↔ Ystad (båda riktningarna) |
| `st` | Świnoujście ↔ Trelleborg (båda riktningarna) |

**Autentisering:** Ingen krävs. Inga cookies. Inga tokens. Helt öppen.  
**Svar:** Fullständig HTML-sida. `gn` ≈ 390 KB, `sy` ≈ 703 KB (fler avgångar per dag).  
**Språkvarianter:** Bundle-koden visar att polferries.pl-sökvägarna skiljer sig per språk (`en`, `se`, `pl`) — `pl`-versionen är mest komplett.

---

### Endpoint B — JSF Booking Engine

```
POST https://ull.qvistorp.net:6789/ic/relations/relations.xhtml
Content-Type: application/x-www-form-urlencoded
```

Detta är en **JavaServer Faces (JSF) partial AJAX-endpoint**. Den driver bokningsdatum/timme-widgeten, inte schemadisplayen. Kräver ett `jakarta.faces.ViewState`-token från en föregående GET till samma URL. Är stateful och sessionsbaserad — inte användbar för schemadatautvinning.

---

### Endpoint C — Cargo Booking API (AWS)

```
POST https://vesnsj9xt7.execute-api.eu-central-1.amazonaws.com/
Authorization: Bearer uJxtEtXd82BFHi91N8yWY4l8M685OEEC
Content-Type: application/json
```

Hårdkodat Bearer-token i JS-bundlen. Används för godsbokningsformulär. Inte schemarelaterat.

---

### Endpoints D & E — Ytterligare AWS-endpoints

```
POST https://0dgii8r90d.execute-api.eu-central-1.amazonaws.com/   → betalning/transaktionshantering
POST https://uhlf6gj3w5.execute-api.eu-central-1.amazonaws.com/   → okänt syfte
```

Inte schemarelaterade.

---

## SCHEMADATASTRUKTUR

### HTML Tab Panel ID-mönster

Varje proxiad HTML-sida innehåller månadsbaserade tab-paneler med ID:n enligt detta mönster:

```
r{ruttIndex}{månad}{år}
```

| Sida (kod) | Rutt-index | Exempel-ID | Betydelse |
|-----------|------------|------------|-----------|
| `gn` | 1 | `r152026` | Gdańsk→Nynäshamn, maj 2026 |
| `gn` | 2 | `r252026` | Nynäshamn→Gdańsk, maj 2026 |
| `sy` | 3 | `r352026` | Świnoujście→Ystad, maj 2026 |
| `sy` | 4 | `r452026` | Ystad→Świnoujście, maj 2026 |
| `st` | 5/6 | `r552026` | Świnoujście↔Trelleborg, maj 2026 |

### Tabellradsstruktur (per månadsPanel)

Varje panel innehåller en `<table>` med minst 3 rader:

| Rad | Innehåll |
|-----|---------|
| Rad 0 (header) | `"odejście - przyjście"` sedan dagnummer 1–31 |
| Rad 1 | Rutt-namn sedan veckodagsförkortningar (pn=mån, wt=tis, śr=ons, czw=tor, pt=fre, sob=lör, nie=sön) |
| Rad 2+ | Avgångs-ankomsttid i kolumn 0, sedan fartygskod eller tom per dag |

### Exempel: Świnoujście→Ystad, maj 2026

```
Avgång-Ankomst  | Dag:  1    2    3    4    5  ...
05:45 - 13:10   |      GAL   –   GAL  GAL  GAL ...
12:30 - 19:00   |      VAR   –    –   VAR  VAR ...
13:00 - 20:15   |      POL  POL  POL  POL  POL ...
22:30 - 06:15*  |      MAZ  VAR  MAZ  MAZ  MAZ ...
23:00 - 06:30*  |      SKA  SKA  SKA  SKA  SKA ...
```

`*` = ankomst nästa dag.

**Fartygskoder:**

| Kod | Fartyg |
|-----|--------|
| WAW | Wawel |
| GAL | Gryf |
| POL | Polonia |
| MAZ | Mazovia |
| SKA | Skania |
| VAR | Varlberga |
| NS  | No Service (markering) |

Tom cell = ingen avgång. `–` = explicit inställd.

### Rutt-ID-format (för booking engine)

```
{RuttNamn}_{BookingEngineID}_{Kod}
```

| Fullt ID | Booking Engine ID | Kod |
|---------|-------------------|-----|
| `Gdańsk-Nynäshamn_9_GN` | 9 | GN |
| `Nynäshamn-Gdańsk_10_NG` | 10 | NG |
| `Świnoujście-Ystad_7_SY` | 7 | SY |
| `Ystad-Świnoujście_8_YS` | 8 | YS |
| `Świnoujście-Trelleborg_21_ST` | 21 | ST |
| `Trelleborg-Świnoujście_22_TS` | 22 | TS |

---

## EXEMPELANROP

### curl — Hämta helårsschema för Gdańsk↔Nynäshamn

```bash
curl -s "https://ull.qvistorp.net:6798/?target_url=https://polferries.pl/rozklad-i-cennik/rozklad.html?code=gn" \
  -H "User-Agent: Mozilla/5.0" \
  -o schedule_gn.html
```

### curl — Hämta Świnoujście↔Ystad (rikast dataset — 5 avgångar/dag)

```bash
curl -s "https://ull.qvistorp.net:6798/?target_url=https://polferries.pl/rozklad-i-cennik/rozklad.html?code=sy" \
  -H "User-Agent: Mozilla/5.0" \
  -o schedule_sy.html
```

### curl — Ladda ner alla tre rutterna

```bash
#!/bin/bash
for code in gn sy st; do
  curl -s -A "Mozilla/5.0" \
    "https://ull.qvistorp.net:6798/?target_url=https://polferries.pl/rozklad-i-cennik/rozklad.html?code=${code}" \
    -o "schedule_${code}_$(date +%Y%m%d).html"
done
```

---

## PYTHON-PARSER (komplett exempel)

```python
import requests
from bs4 import BeautifulSoup
import re

PROXY_BASE = "https://ull.qvistorp.net:6798/?target_url="
ROUTE_CODES = {
    "gn": "Gdańsk-Nynäshamn / Nynäshamn-Gdańsk",
    "sy": "Świnoujście-Ystad / Ystad-Świnoujście",
    "st": "Świnoujście-Trelleborg / Trelleborg-Świnoujście"
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; schedule-fetcher/1.0)"}

def fetch_schedule(route_code: str) -> dict:
    url = f"{PROXY_BASE}https://polferries.pl/rozklad-i-cennik/rozklad.html?code={route_code}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return parse_schedule_html(resp.text)

def parse_schedule_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    schedule = {}

    for panel in soup.find_all("div", id=re.compile(r"^r\d+$")):
        panel_id = panel["id"]
        table = panel.find("table")
        if not table:
            continue
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue

        day_cells = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        days = day_cells[1:]
        route_cells = [td.get_text(strip=True) for td in rows[1].find_all(["td", "th"])]
        route_name = route_cells[0] if route_cells else "unknown"
        weekdays = route_cells[1:]

        sailings = []
        for data_row in rows[2:]:
            cells = [td.get_text(strip=True) for td in data_row.find_all(["td", "th"])]
            if not cells:
                continue
            time_slot = cells[0]
            for i, vessel in enumerate(cells[1:]):
                if vessel and vessel not in ("–", "NS", ""):
                    if i < len(days):
                        sailings.append({
                            "day": days[i],
                            "weekday": weekdays[i] if i < len(weekdays) else "",
                            "time_slot": time_slot,
                            "vessel": vessel,
                            "next_day_arrival": time_slot.endswith("*")
                        })

        schedule[panel_id] = {"route": route_name, "sailings": sailings}

    return schedule

if __name__ == "__main__":
    for code in ["gn", "sy", "st"]:
        print(f"\n=== {ROUTE_CODES[code]} ===")
        data = fetch_schedule(code)
        for panel_id, panel in sorted(data.items()):
            if panel["sailings"]:
                print(f"  {panel_id} | {panel['route']} | {len(panel['sailings'])} avgångar")
```

---

## JAVASCRIPT-FETCH (webbläsarkontext)

```javascript
const PROXY = 'https://ull.qvistorp.net:6798/?target_url=';
const POLFERRIES = 'https://polferries.pl/rozklad-i-cennik/rozklad.html';

async function fetchSchedule(routeCode) {
  const resp = await fetch(`${PROXY}${POLFERRIES}?code=${routeCode}`);
  const html = await resp.text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const result = {};

  doc.querySelectorAll('[id]').forEach(el => {
    if (!/^r\d+$/.test(el.id)) return;
    const table = el.querySelector('table');
    if (!table) return;
    const rows = [...table.querySelectorAll('tr')];
    if (rows.length < 3) return;

    const days = [...rows[0].querySelectorAll('th,td')].map(c => c.textContent.trim()).slice(1);
    const routeName = rows[1].querySelector('td,th')?.textContent.trim() || '';
    const weekdays = [...rows[1].querySelectorAll('td,th')].map(c => c.textContent.trim()).slice(1);

    const sailings = [];
    rows.slice(2).forEach(row => {
      const cells = [...row.querySelectorAll('td,th')].map(c => c.textContent.trim());
      const timeSlot = cells[0];
      cells.slice(1).forEach((vessel, i) => {
        if (vessel && !['–', 'NS', ''].includes(vessel))
          sailings.push({ day: days[i], weekday: weekdays[i], timeSlot, vessel });
      });
    });
    result[el.id] = { routeName, sailings };
  });
  return result;
}

// Hämta alla tre ruttar parallellt
const [gnData, syData, stData] = await Promise.all(['gn','sy','st'].map(fetchSchedule));
```

---

## AUTENTISERINGS- OCH SESSIONSANALYS

| Endpoint | Auth krävs | Session krävs | Anteckningar |
|----------|-----------|--------------|--------------|
| Proxy port 6798 | ❌ Ingen | ❌ Ingen | Helt stateless, öppen |
| `relations.xhtml` port 6789 | ⚠️ ViewState | ✅ JSF-session | Stateful, kräver bootstrap-GET |
| AWS cargo-endpoint | ✅ Bearer-token | ❌ Ingen | Token hårdkodad i bundle |

**Proxy-endpointen är helt öppen** — inga cookies, inga tokens, ingen session.

---

## REKOMMENDERAD STRATEGI

**För schemadisplay / custom frontend:** Hämta de tre proxy-URL:erna direkt. Ingen autentisering. Tolka HTML-tabellpanelerna. Cacha resultatet — schemat är ett helårsdataset som ändras sällan.

**För automatiserad download (cron):** Kör dagligen, en hämtning per rutpar per dygn räcker. Lägg till fallback mot polferries.pl direkt om proxyn slutar fungera.

**Undvik:** `relations.xhtml` för schemadata (stateful JSF), Polsca React-sidan som skrapningsmål (client-side rendering med fördröjning).

---

## RISKER OCH BEGRÄNSNINGAR

| Risk | Allvarlighetsgrad | Anteckningar |
|------|-------------------|--------------|
| Proxy-URL ändras | Medel | `ull.qvistorp.net` är tredjepartsoperatör — kan byta hostname |
| polferries.pl HTML-struktur ändras | Medel | Tabellstrukturen är ren men kan redesignas |
| Proxy blockerar icke-webbläsarklienter | Låg | Inga tecken på botskydd, testat utan problem |
| Ruttkoder ändras | Låg | `gn`, `sy`, `st` är stabila förkortningar |
| Fartygskodtolkning saknar dokumentation | Medel | Kräver separat uppslagstabell |

---

## SLUTBEDÖMNING

| Fråga | Svar |
|-------|------|
| Automatiserbart? | **Ja** |
| Direkt API-åtkomst möjlig? | **Ja** — via proxyn, ingen auth |
| Webbläsarautomatisering krävs? | **Nej** — enkel HTTP GET räcker |
| HTML-skrapning krävs? | **Ja** — men HTML är ren och stabil |
| Metodstabilitet? | **Medel-hög** |
| Rekommendation | 3 GET-anrop dagligen → HTML-tolkning → lokal JSON-cache. Fallback direkt mot polferries.pl. |
