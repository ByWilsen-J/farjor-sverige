# Stena Line Freight — Timetable API: Teknisk undersökning

**Datum:** 2026-05-20  
**Metod:** Live browser-analys (nätverkstrafik, DOM-inspektion, API-testning)  
**Målsida:** https://stenalinefreight.com/timetable/

---

## Sammanfattning

Det finns ett fullt fungerande, direkt anropbart API bakom Stena Line Freights tidtabellssida. Ingen inloggning krävs, inga sessionscookies krävs — bara en tidsbegränsad "nonce" som kan hämtas automatiskt från sidans HTML. Hela flödet kan automatiseras med vanliga HTTP-anrop (Python, curl etc.) utan webbläsarautomation.

---

## 1. Teknisk arkitektur

- **CMS:** WordPress med eget tema (`slfreight`)
- **JS-stack:** jQuery 3.7.1 + kompilerat appbundle (`app.991bac.js`)
- **CDN/skydd:** Cloudflare (ingen JS-utmaning aktiv, `cf-cache-status: DYNAMIC`)
- **Rendering:** Klientsiderendering — sidan laddas som ett tomt skal, tidtabellsdata hämtas via AJAX efter att användaren väljer rutt
- **Backend:** Gemensam WordPress-infrastruktur för hela sajten (inget separat freight-system)

---

## 2. API-endpunkt

```
POST https://stenalinefreight.com/wp/wp-admin/admin-ajax.php
```

WordPress-action-parametern `timetable` routar anropet till rätt PHP-handler.

### Request-parametrar

| Parameter | Typ | Beskrivning | Exempel |
|---|---|---|---|
| `action` | string | WordPress AJAX-action | `timetable` |
| `data[from]` | string | Startdatum, YYYY-MM-DD | `2026-05-19` |
| `data[to]` | string | Slutdatum, YYYY-MM-DD | `2026-05-25` |
| `data[routeCode]` | string | 4-bokstavs ruttkod | `EUHC` |
| `security` | string | WordPress nonce, 10 tecken | *(se sektion 3)* |

### Request-headers

```
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36
```

### Response-format

```json
{
  "success": true,
  "data": {
    "content": "<HTML-sträng med tidtabell>"
  }
}
```

Svaret är **inte ren JSON-data** — det är ett förrenderat HTML-fragment inbäddat i ett JSON-kuvert. HTML:en måste parsas för att extrahera enskilda avgångar.

---

## 3. Autentisering och sessionshantering

**Kritiskt fynd: Inga cookies krävs.**

Noncen (`security`-parametern) är en standard WordPress public nonce genererad för icke-inloggade besökare:

- Inbäddad i sidans HTML som `var ajax_object = {"ajax_url":"...","security":"<nonce>"}`
- Extraherbar med ett enkelt regex: `/"security"\s*:\s*"([^"]{8,12})"/`
- Giltig i ca **12–24 timmar** (WordPress dubbel nonce-period)
- **Inte knuten till någon sessionscookie** — bekräftat via tester med `credentials: 'omit'`

Vid anrop utan nonce returneras `-1` (WordPress nonce-fel). Med giltig nonce och utan cookies returneras full data.

### Automatiseringsflöde

```
1. GET https://stenalinefreight.com/timetable/   ← ingen cookie behövs
2. Extrahera nonce med regex från HTML
3. POST till admin-ajax.php med ruttkod + datumintervall + nonce
4. Återanvänd samma nonce för alla rutter under samma 12-timmarsperiod
5. Upprepa steg 1–2 när nonce går ut
```

---

## 4. Ruttkoder — komplett lista

Extraherade från `data-routecodemain`-attribut i DOM:en:

```
BECN  →  Belfast – Cairnryan
BEHY  →  Belfast – Heysham
BELP  →  Belfast – Liverpool
DUHO  →  Dublin – Holyhead
DULP  →  Dublin – Liverpool
ROFI  →  Rosslare – Fishguard
GDKA  →  Gdynia – Karlskrona
NYVE  →  Nynäshamn – Ventspils
TRLI  →  Travemünde – Liepaja
GOFR  →  Gothenburg – Frederikshavn
GOKI  →  Gothenburg – Kiel
TGRO  →  Trelleborg – Rostock
HKHA  →  Hoek Van Holland – Harwich
HKIM  →  Hoek Van Holland – Immingham
EUHC  →  Rotterdam – Harwich
EUIM  →  Rotterdam – Immingham
```

Koderna är stabila — de förekommer både som DOM-attribut och i URL-slug (`/timetable/EUHC`).

---

## 5. HTML-responsens datastruktur

`data.content` innehåller alltid **två** `<section class="timetable-content-box">` — en per riktning. Inuti varje box finns en `.Rtable`-div vars **direkta barn** (inte barnbarn) är:

| Elementklass | Betydelse |
|---|---|
| `Rtable-cell head` | Kolumnhuvud — hoppa över |
| `line-break` | Visuell separator |
| `date` | Datumetikett, t.ex. `"TUESDAY 2026-05-19"` |
| `Rtable-cell` (ej head) | Datavärde — gruppera i set om 4: Dep, Arr, Vessel, Status |

**Viktigt:** `.date`-elementet är ett **syskon** till datacellerna, inte ett barn. Använd `rtable.children` (direkt iteration), inte `querySelectorAll('.Rtable-cell')` (som missar `.date`-separatorerna).

**Avgångscell med två tider:** Cellen kan innehålla `"07:30 07:16"` — planerad tid (visas med genomstrykning i CSS) följt av faktisk tid. Hantera med split på whitespace: index 0 = planerad, index 1 = faktisk (None om inga avvikelser).

---

## 6. Exempeldata (parsad output)

```
Riktning              | Datum               | Avg (plan) | Avg (fakt) | Ank   | Fartyg                | Status
----------------------|---------------------|------------|------------|-------|-----------------------|----------
Rotterdam – Harwich   | TUESDAY 2026-05-19  | 11:15      | -          | 18:30 | MV MISTRAL (C)        | Departed
Rotterdam – Harwich   | TUESDAY 2026-05-19  | 21:00      | -          | 04:00 | MV Thuleland (C)      |
Harwich – Rotterdam   | TUESDAY 2026-05-19  | 08:00      | 07:15      | 17:00 | MV Thuleland (C)      | Arrived
Harwich – Rotterdam   | TUESDAY 2026-05-19  | 22:30      | -          | 07:30 | MV MISTRAL (C)        |
Belfast – Cairnryan   | TUESDAY 2026-05-19  | 03:30      | -          | 05:52 | STENA SUPERFAST VII   | Arrived
Belfast – Cairnryan   | TUESDAY 2026-05-19  | 07:30      | 07:16      | 09:52 | STENA SUPERFAST VIII  | Arrived
```

---

## 7. Kodexempel

### curl

```bash
# Steg 1: Hämta nonce
NONCE=$(curl -s https://stenalinefreight.com/timetable/ \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36" \
  | grep -oP '"security"\s*:\s*"\K[^"]{8,12}')

# Steg 2: Hämta tidtabell
curl -s https://stenalinefreight.com/wp/wp-admin/admin-ajax.php \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Requested-With: XMLHttpRequest" \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36" \
  --data-urlencode "action=timetable" \
  --data-urlencode "data[from]=2026-05-19" \
  --data-urlencode "data[to]=2026-05-25" \
  --data-urlencode "data[routeCode]=EUHC" \
  --data-urlencode "security=$NONCE"
```

### Python (requests + BeautifulSoup)

```python
import re, time, json, requests
from bs4 import BeautifulSoup
from datetime import date, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
}
AJAX_URL = "https://stenalinefreight.com/wp/wp-admin/admin-ajax.php"

ROUTES = {
    "BECN": "Belfast – Cairnryan",     "BEHY": "Belfast – Heysham",
    "BELP": "Belfast – Liverpool",     "DUHO": "Dublin – Holyhead",
    "DULP": "Dublin – Liverpool",      "ROFI": "Rosslare – Fishguard",
    "GDKA": "Gdynia – Karlskrona",     "NYVE": "Nynäshamn – Ventspils",
    "TRLI": "Travemünde – Liepaja",    "GOFR": "Gothenburg – Frederikshavn",
    "GOKI": "Gothenburg – Kiel",       "TGRO": "Trelleborg – Rostock",
    "HKHA": "Hoek Van Holland – Harwich", "HKIM": "Hoek Van Holland – Immingham",
    "EUHC": "Rotterdam – Harwich",     "EUIM": "Rotterdam – Immingham",
}


def get_nonce() -> str:
    """Hämtar en giltig nonce. Giltig ~12 timmar — återanvänd för alla rutter."""
    resp = requests.get("https://stenalinefreight.com/timetable/", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    m = re.search(r'"security"\s*:\s*"([^"]{8,12})"', resp.text)
    if not m:
        raise ValueError("Nonce hittades inte i sidans HTML")
    return m.group(1)


def fetch_timetable_html(route_code: str, date_from: date, date_to: date, nonce: str) -> str:
    payload = {
        "action": "timetable",
        "data[from]": date_from.isoformat(),
        "data[to]": date_to.isoformat(),
        "data[routeCode]": route_code,
        "security": nonce,
    }
    resp = requests.post(AJAX_URL, data=payload, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise ValueError(f"API-fel: {result}")
    return result["data"]["content"]


def parse_timetable(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    sailings = []

    for box in soup.select(".timetable-content-box"):
        h3 = box.find("h3")
        direction = h3.get_text(strip=True) if h3 else "unknown"
        rtable = box.find(class_="Rtable")
        if not rtable:
            continue

        current_date = ""
        data_cells = []

        for child in rtable.children:
            if not hasattr(child, "get"):
                continue
            cls = " ".join(child.get("class", []))
            if "date" in cls:
                current_date = child.get_text(strip=True)
            elif "Rtable-cell" in cls and "head" not in cls:
                data_cells.append((current_date, child.get_text(separator=" ", strip=True)))

        for i in range(0, len(data_cells) - 3, 4):
            dep_parts = data_cells[i][1].split()
            sailings.append({
                "direction":     direction,
                "date":          data_cells[i][0],
                "dep_scheduled": dep_parts[0] if dep_parts else "",
                "dep_actual":    dep_parts[1] if len(dep_parts) > 1 else None,
                "arr":           data_cells[i+1][1],
                "vessel":        data_cells[i+2][1],
                "status":        data_cells[i+3][1],
            })
    return sailings


if __name__ == "__main__":
    nonce = get_nonce()
    today = date.today()
    week_end = today + timedelta(days=6)
    all_data = {}

    for code, name in ROUTES.items():
        print(f"Hämtar {name} ({code})...")
        try:
            html = fetch_timetable_html(code, today, week_end, nonce)
            sailings = parse_timetable(html)
            all_data[code] = {"route": name, "sailings": sailings}
            print(f"  -> {len(sailings)} avgångar")
        except Exception as e:
            print(f"  -> FEL: {e}")
        time.sleep(2)  # Var snäll mot Cloudflare

    with open("stena_timetable.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("Sparat: stena_timetable.json")
```

### JavaScript (fetch)

```javascript
const AJAX_URL = 'https://stenalinefreight.com/wp/wp-admin/admin-ajax.php';

async function getNonce() {
  const resp = await fetch('https://stenalinefreight.com/timetable/');
  const html = await resp.text();
  const m = html.match(/"security"\s*:\s*"([^"]{8,12})"/);
  if (!m) throw new Error('Nonce hittades inte');
  return m[1];
}

async function fetchTimetable(routeCode, dateFrom, dateTo, nonce) {
  const body = new URLSearchParams({
    action: 'timetable',
    'data[from]': dateFrom,
    'data[to]': dateTo,
    'data[routeCode]': routeCode,
    security: nonce,
  });
  const resp = await fetch(AJAX_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: body.toString(),
  });
  const json = await resp.json();
  if (!json.success) throw new Error('API-fel');
  return json.data.content;
}

function parseTimetable(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  const sailings = [];

  doc.querySelectorAll('.timetable-content-box').forEach(box => {
    const direction = box.querySelector('h3')?.textContent?.trim() ?? 'unknown';
    const rtable = box.querySelector('.Rtable');
    if (!rtable) return;

    let currentDate = '';
    const dataCells = [];

    for (const child of rtable.children) {
      const cls = child.className;
      if (cls.includes('date')) {
        currentDate = child.textContent.trim();
      } else if (cls.includes('Rtable-cell') && !cls.includes('head')) {
        dataCells.push({ date: currentDate, text: child.textContent.trim().replace(/\s+/g, ' ') });
      }
    }

    for (let i = 0; i + 3 < dataCells.length; i += 4) {
      const parts = dataCells[i].text.split(' ');
      sailings.push({
        direction,
        date:         dataCells[i].date,
        depScheduled: parts[0],
        depActual:    parts[1] ?? null,
        arr:          dataCells[i+1].text,
        vessel:       dataCells[i+2].text,
        status:       dataCells[i+3].text,
      });
    }
  });
  return sailings;
}
```

---

## 8. Risker och begränsningar

| Risk | Allvarlighet | Kommentar |
|---|---|---|
| Svar är HTML, inte ren JSON | Medel | Strukturen är konsistent men kan brytas vid temauppdatering. Använd CSS-klassväljare, inte positionsantaganden. |
| Nonce upphör var ~12:e timme | Låg | Lätt att förnya — en extra GET per halvdag |
| Cloudflare bot-detektering | Medel | Ingen aktiv utmaning nu, men hög anropsfrekvens eller saknad User-Agent kan trigga den |
| WordPress `action`-namn kan ändras | Låg | `timetable` är en intern WP-action; stabil om inte temat omstruktureras |
| Odokumenterat internt API | Medel | Inget offentligt SLA — Stena kan ändra det utan varning |

---

## 9. Slutbedömning

| Fråga | Svar |
|---|---|
| Är direkt API-åtkomst möjlig? | Ja — bekräftat fungerande, inga cookies, ingen inloggning |
| Krävs webbläsarautomation? | Nej — ren requests/curl räcker |
| Är HTML-skrapning acceptabel fallback? | Ja — renderad sida och AJAX-svar har identisk HTML-struktur |
| Hur stabil är metoden? | Medel-stabil — odokumenterat internt endpoint |
| Rekommenderad strategi | Tvåstegs nonce+POST, Python requests + BeautifulSoup, förnya nonce var 10:e timme, cachelagra lokalt |
| Största risk | Cloudflare skärper bot-regler, eller temauppdatering ändrar HTML-strukturen |

### Rekommenderad produktionsarkitektur

1. Schemalägg nonce-hämtning var 10:e timme
2. Hämta alla 16 rutter med 2 sekunders mellanrum
3. Cachelagra som JSON lokalt
4. Exponera cachad data i eget system — anropa inte Stenas API direkt per slutanvändaranrop
5. Övervaka HTTP-statuskoder: om admin-ajax.php returnerar 403 eller Cloudflare-block, lägg till backoff och justera User-Agent
