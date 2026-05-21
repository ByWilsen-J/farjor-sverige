# DFDS Freight Timetable API — Teknisk utredning
**Utförd:** 2026-05-19  
**Målsida:** https://www.dfds.com/sv-se/fraktfarjor-och-logistik/rutter-och-tidtabeller  
**Metod:** Live browsing + nätverksinspektión + direkt API-testning via curl/Python

---

## Sammanfattning (TL;DR)

DFDS exponerar ett **öppet, autentiseringsfritt REST-API** (`/api/timetable`) som returnerar strukturerad avgångsdata i JSON-format. Ingen inloggning, inga cookies, inga API-nycklar krävs. Direkt programmatisk åtkomst är fullt möjlig och rekommenderas som primär integrationsstrategi.

---

## 1. Findings — Systemöversikt

### Frontend-ramverk & infrastruktur
| Komponent | Detalj |
|---|---|
| Framework | **Next.js** (SSG, `__NEXT_DATA__` hydration) |
| CMS | **Contentful** (space ID: `z860498abl84`, env: `master`) |
| Hosting | **Vercel** (server: Vercel) |
| CDN | **AWS CloudFront** (PoP: CPH50-P2 = Köpenhamn) |
| Bot-skydd | Inget CloudFlare/Akamai-skydd. Inga rate limits påträffades vid test. |
| Analytics | Google Tag Manager, Segment, VWO FME A/B-testning |

### Sidrendering
Rutt/tidtabellssidor är **statiskt genererade (SSG)** via Next.js. Sidans chrome (navigation, hero, brödtext) levereras som pre-renderad HTML. Avgångsdata hämtas **client-side via fetch** mot `/api/timetable` när sidan laddas i webbläsaren — dvs. tidtabellsdata är **inte** inbäddad i HTML-källan.

### Frakt vs. passagerare
Fraktsektionen (`/fraktfarjor-och-logistik/`) och passagerarsektionen är separerade. Denna utredning täcker enbart fraktsidan. Tidtabellsdata serveras från samma `/api/timetable`-endpoint, men med fraktspecifika portidentifierare.

---

## 2. APIs Discovered

### Primär endpoint: `/api/timetable`

Detta är den centrala, rekommenderade datakällan.

```
GET https://www.dfds.com/api/timetable
```

**Parametrar:**

| Parameter | Typ | Krav | Beskrivning |
|---|---|---|---|
| `portOfLoading` | string | **Obligatorisk** | 5-teckens terminal-ID för avgångshamn |
| `portOfDischarge` | string | **Obligatorisk** | 5-teckens terminal-ID för ankomsthamn |
| `dateFrom` | string | Valfri | ISO 8601 UTC datetime, fönstrets start |
| `dateTo` | string | Valfri | ISO 8601 UTC datetime, fönstrets slut |

**Beteende utan datumparametrar:**  
API:et returnerar ett ~14-dagars rullande standardfönster (bakåt och framåt från dagens datum). Fungerar felfritt.

**Beteende med datum:**  
Flexibelt datumfönster — testat med upp till 90 dagar, fungerar utan problem. Ingen begränsning identifierad.

**Felhantering:**  
- Ogiltiga port-koder → `[]` (tom array)  
- Saknade port-koder → `{"message":"Invalid or missing port parameters"}` (HTTP 400)  
- HEAD-metod → HTTP 405 (only GET supported)

---

### Sekundär endpoint: `/api/unified/timetable`

```
GET https://www.dfds.com/api/unified/timetable?fromDate=YYYY-MM-DD&routeCode=XXXX&reverse=false
```

Används av en alternativ CMS-komponent (`B2B`-sektion). `routeCode` är ett CMS-internt värde (ej UN/LOCODE). Returnerar `{"error":"Bad Request"}` utan giltig CMS-routekod. **Ej rekommenderad för extern integration** — använd `/api/timetable` istället.

---

### Övriga endpoints (ej relevanta för tidtabeller)

| Endpoint | Ändamål |
|---|---|
| `/api/search/initial-results?locale=sv-se` | Sök-pre-populering (Algolia) |
| `/api/trpc/dxpCareer.getPostings` | Jobbannonser |
| `/api/unified/subscribe` | Nyhetsbrev-prenumeration |
| `/api/revalidate` | Next.js ISR (kräver hemlig token, 401) |

---

## 3. Komplett portkodsregister

Alla bekräftade fraktrutter och deras portidentifierare. `tableVariant` anger om live-API:et används (`detailed`/`departures`) eller statisk CMS-data (`manual`).

| Region | Rutt | POL-kod | POD-kod | API-variant |
|---|---|---|---|---|
| **Östersjön** | Klaipeda–Fredericia | LTKLJ | DKFRC | `detailed` ✅ |
| **Östersjön** | Klaipeda–Karlshamn | LTKLJ | SEKAN | `detailed` ✅ |
| **Östersjön** | Klaipeda–Kiel | LTKLJ | DEKEL | `detailed` ✅ |
| **Östersjön** | Klaipeda–Køge | LTKLJ | DKKOG | `detailed` ✅ |
| **Östersjön** | Klaipeda–Trelleborg | LTKLJ | SETRG | `detailed` ✅ |
| **Östersjön** | Klaipeda–Travemünde | LTKLJ | DETRV | `detailed` ✅ |
| **Östersjön** | Paldiski–Kapellskär | EEPLN | SEKPS | `detailed` ✅ |
| **Östersjön** | Muuga–Nordsjö | EEMUG | FIVSS | `detailed` ✅ |
| **Nordsjön** | Amsterdam–Newcastle | NLIJM | GBNCL | `detailed` ✅ |
| **Nordsjön** | Esbjerg–Immingham | DKEBJ | GBIMM | `detailed` ✅ |
| **Nordsjön** | Rotterdam–Immingham | NLRTM | GBIMM | `detailed` ✅ |
| **Nordsjön** | Rotterdam–Felixstowe | NLRTM | GBFXT | `detailed` ✅ |
| **Nordsjön** | Cuxhaven–Immingham | DECUX | GBIMM | `detailed` ✅ |
| **Nordsjön** | Göteborg–Brevik | SEGOT | NOBVK | `manual` ⚠️ |
| **Nordsjön** | Göteborg–Gent | SEGOT | BEGNE | `manual` ⚠️ |
| **Nordsjön** | Göteborg–Immingham | SEGOT | GBIMM | `manual` ⚠️ |
| **Nordsjön** | Göteborg–Zeebrugge | SEGOT | BEZEE | `manual` ⚠️ |
| **Nordsjön** | Brevik–Immingham | NOBVK | GBIMM | `manual` ⚠️ |
| **Nordsjön** | Brevik–Gent | NOBVK | BEGNE | `manual` ⚠️ |
| **Engelska kanalen** | Dover–Calais | GBDVR | FRCQF | `departures` ✅ |

> **⚠️ `manual`-rutter:** Göteborg- och Brevik-rutterna visas med statisk CMS-data på webbplatsen. API:et returnerar ändå data för dessa portkoder men det är oklart om data är komplett — verifiera manuellt mot publicerad PDF.

---

## 4. Response-schema (fullständigt)

Varje avgång i JSON-arrayen har följande struktur:

```json
{
  "portOfLoading":          "LTKLJ",
  "portOfDischarge":        "SEKAN",
  "status":                 "TALLIED",
  "maxNumberOfDrivers":     66,
  "transportId":            "4694083",
  "transportType":          "Voyage",
  "vehicleId":              "9188427",
  "vehicleName":            "Optima Seaways",
  "scheduledDeparture":     "2026-05-19T19:00:00+03:00",
  "scheduledArrival":       "2026-05-20T08:30:00+02:00",
  "actualDeparture":        "2026-05-19T18:41:00+03:00",
  "actualArrival":          null,
  "openForNewBookingsAt":   "2025-11-11T22:00:00+00:00",
  "closedForNewBookingsAt": null,
  "openForAllocationsAt":   "2025-11-11T22:00:00+00:00",
  "closedForAllocationsAt": null,
  "closedOnlineAt":         null,
  "remark":                 null,
  "portOfLoadingTerminal":  "CKT",
  "portOfDischargeTerminal":"KAN",
  "isSpaceCharterVessel":   false
}
```

**Fältbeskrivningar:**

| Fält | Typ | Beskrivning |
|---|---|---|
| `portOfLoading` | string | Avgångshamnkod (5 tecken, UN/LOCODE-derivat) |
| `portOfDischarge` | string | Ankomstshamnkod |
| `status` | string\|null | `null` = planerad; `"TALLIED"` = genomförd |
| `maxNumberOfDrivers` | int | Max ledsagade fordon (0 = enbart obemannad last) |
| `transportId` | string | Unikt rese-ID (numerisk sträng) |
| `vehicleId` | string | Fartygets IMO-nummer |
| `vehicleName` | string\|null | Fartygsnamn (`null` för Dover-Calais) |
| `scheduledDeparture` | ISO 8601 | Planerad avgång med lokal tidszon |
| `scheduledArrival` | ISO 8601 | Planerad ankomst med lokal tidszon |
| `actualDeparture` | ISO 8601\|null | Faktisk avgång (fylls i efter avresa) |
| `actualArrival` | ISO 8601\|null | Faktisk ankomst |
| `openForNewBookingsAt` | ISO 8601 | Bokning öppnade |
| `closedForNewBookingsAt` | ISO 8601\|null | Bokning stänger (`null` = fortfarande öppen) |
| `portOfLoadingTerminal` | string | Specifik terminal-kod i avgångshamn |
| `portOfDischargeTerminal` | string | Specifik terminal-kod i ankomsthamn |
| `isSpaceCharterVessel` | boolean | `true` = tredjepartsfartyg (DFDS hyr utrymme) |

---

## 5. Example Requests

### curl

```bash
# Enklast möjliga - standardfönster, inga datumparametrar
curl "https://www.dfds.com/api/timetable?portOfLoading=LTKLJ&portOfDischarge=SEKAN"

# Specifikt veckofönster
curl "https://www.dfds.com/api/timetable?\
dateFrom=2026-05-18T22%3A00%3A00.000Z&\
dateTo=2026-05-25T21%3A59%3A59.999Z&\
portOfLoading=LTKLJ&portOfDischarge=SEKAN"

# Omvänd riktning (Karlshamn → Klaipeda)
curl "https://www.dfds.com/api/timetable?portOfLoading=SEKAN&portOfDischarge=LTKLJ"

# 30-dagars fönster
curl "https://www.dfds.com/api/timetable?\
dateFrom=2026-05-01T00%3A00%3A00.000Z&\
dateTo=2026-05-31T23%3A59%3A59.999Z&\
portOfLoading=LTKLJ&portOfDischarge=SEKAN"

# Dover-Calais (84 avgångar/vecka)
curl "https://www.dfds.com/api/timetable?portOfLoading=GBDVR&portOfDischarge=FRCQF"
```

### Python (requests)

```python
import requests
from datetime import datetime, timedelta, timezone
import time

BASE_URL = "https://www.dfds.com/api/timetable"

ROUTE_CODES = {
    "klaipeda-karlshamn":   ("LTKLJ", "SEKAN"),
    "klaipeda-fredericia":  ("LTKLJ", "DKFRC"),
    "klaipeda-kiel":        ("LTKLJ", "DEKEL"),
    "klaipeda-koge":        ("LTKLJ", "DKKOG"),
    "klaipeda-trelleborg":  ("LTKLJ", "SETRG"),
    "klaipeda-travemunde":  ("LTKLJ", "DETRV"),
    "paldiski-kapellskar":  ("EEPLN", "SEKPS"),
    "muuga-nordsjo":        ("EEMUG", "FIVSS"),
    "amsterdam-newcastle":  ("NLIJM", "GBNCL"),
    "esbjerg-immingham":    ("DKEBJ", "GBIMM"),
    "rotterdam-immingham":  ("NLRTM", "GBIMM"),
    "rotterdam-felixstowe": ("NLRTM", "GBFXT"),
    "cuxhaven-immingham":   ("DECUX", "GBIMM"),
    "dover-calais":         ("GBDVR", "FRCQF"),
}

def get_sailings(pol: str, pod: str, days: int = 14) -> list[dict]:
    now = datetime.now(timezone.utc)
    date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
    date_to = date_from + timedelta(days=days)
    
    r = requests.get(BASE_URL, params={
        "portOfLoading": pol,
        "portOfDischarge": pod,
        "dateFrom": date_from.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "dateTo": date_to.strftime("%Y-%m-%dT%H:%M:%S.999Z"),
    }, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    
    r.raise_for_status()
    return r.json()

def fetch_all_routes(days: int = 14) -> dict:
    results = {}
    for route_name, (pol, pod) in ROUTE_CODES.items():
        results[route_name] = get_sailings(pol, pod, days)
        time.sleep(0.5)  # Var artig mot servern
    return results

# Användningsexempel
if __name__ == "__main__":
    sailings = get_sailings("LTKLJ", "SEKAN", days=7)
    for s in sorted(sailings, key=lambda x: x["scheduledDeparture"]):
        dep = s["scheduledDeparture"][:16]
        arr = s["scheduledArrival"][:16]
        vessel = s["vehicleName"] or "?"
        status = s["status"] or "Planerad"
        charter = " [Charter]" if s["isSpaceCharterVessel"] else ""
        print(f"{dep} → {arr}  |  {vessel}{charter}  |  {status}")
```

### JavaScript (fetch)

```javascript
const BASE_URL = "https://www.dfds.com/api/timetable";

const ROUTE_CODES = {
  "klaipeda-karlshamn":   ["LTKLJ", "SEKAN"],
  "klaipeda-fredericia":  ["LTKLJ", "DKFRC"],
  "paldiski-kapellskar":  ["EEPLN", "SEKPS"],
  "amsterdam-newcastle":  ["NLIJM", "GBNCL"],
  "rotterdam-immingham":  ["NLRTM", "GBIMM"],
  "dover-calais":         ["GBDVR", "FRCQF"],
};

async function getSailings(pol, pod, days = 14) {
  const now = new Date();
  const dateTo = new Date(now.getTime() + days * 864e5);
  
  const params = new URLSearchParams({
    portOfLoading: pol,
    portOfDischarge: pod,
    dateFrom: now.toISOString(),
    dateTo: dateTo.toISOString(),
  });
  
  const res = await fetch(`${BASE_URL}?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Hämta alla rutter
async function fetchAllRoutes(days = 14) {
  const results = {};
  for (const [name, [pol, pod]] of Object.entries(ROUTE_CODES)) {
    results[name] = await getSailings(pol, pod, days);
    await new Promise(r => setTimeout(r, 500)); // rate limit-vänlighet
  }
  return results;
}

// Exempel
const sailings = await getSailings("LTKLJ", "SEKAN", 7);
sailings
  .sort((a, b) => a.scheduledDeparture.localeCompare(b.scheduledDeparture))
  .forEach(s => {
    const status = s.status || "Planerad";
    const charter = s.isSpaceCharterVessel ? " [Charter]" : "";
    console.log(`${s.scheduledDeparture.slice(0,16)} → ${s.scheduledArrival.slice(0,16)} | ${s.vehicleName || "?"}${charter} | ${status}`);
  });
```

---

## 6. Authentication & Session Analysis

| Aspekt | Resultat |
|---|---|
| API-nyckel | ❌ Krävs inte |
| Cookies | ❌ Krävs inte |
| Referer-header | ❌ Krävs inte |
| User-Agent | ❌ Krävs inte (inga headers alls ger HTTP 200) |
| CORS-restriktioner | ❌ Inga `access-control`-headers — anrop från valfri origin lyckas |
| Rate limiting | ❌ Ej detekterat (5 snabba anrop = 5× HTTP 200) |
| Bot-skydd | ❌ Inget Cloudflare/Akamai/reCAPTCHA |
| Sessions | ✅ Stateless — varje request är oberoende |
| Cachning | `public, max-age=0, must-revalidate` — CDN-cache är avstängd, data alltid färsk |

**Slutsats:** API:et är 100% öppet för direkt åtkomst utan någon autentisering.

> ⚠️ **Juridisk notering:** Teknisk tillgänglighet ≠ juridisk tillåtelse. Kontrollera DFDS användarvillkor och `robots.txt` innan produktionsanvändning. Överväg att kontakta DFDS för ett officiellt partner-API om integrationen är affärskritisk.

---

## 7. Supplementära PDF-tidtabeller

Varje ruttida-sida innehåller en länk till en statisk PDF-fil (lagras på Contentful CDN):

| Rutt | PDF-fil | Storlek |
|---|---|---|
| Klaipeda–Fredericia/Køge | DFDS_schedule_Klaipeda_Koge_Fredericia_2025.pdf | 34 KB |
| Klaipeda–Karlshamn | Easter_schedule_KLJ-KAN_v.v._2026_adjusted.pdf | 111 KB |
| Klaipeda–Kiel | Easter_schedule_KLJ-KEL_v.v._2026.pdf | 76 KB |
| Klaipeda–Trelleborg | Easter_schedule_on_KLJ-TRE_v.v._2026.pdf | 73 KB |
| Klaipeda–Travemünde | Easter_schedule_on_KLJ-TRA_v.v._2026.pdf | 76 KB |
| Paldiski–Kapellskär | Schedule_Paldiski_Kapellskär.pdf | 45 KB |
| Rotterdam–Immingham | RTM-IMM-W08-11-2026.pdf | 95 KB |
| Rotterdam–Felixstowe | RTM-FXT-W08-11-2026.pdf | 162 KB |
| Cuxhaven–Immingham | Cuxhaven_Immingham_Sailing_Schedule_May_2026.pdf | 98 KB |
| Brevik–Immingham | Got-Bvk-Imm_W_619-628_2026.pdf | 508 KB |

PDF-URL:er kan hämtas programmatiskt ur `__NEXT_DATA__` på respektive ruttida-sida via Contentful-domänen `assets.ctfassets.net`. De är statiska och uppdateras manuellt av DFDS (oregelbundet).

---

## 8. Recommended Approach

### Primär: Live JSON via `/api/timetable`
- Använd för alla rutter med `tableVariant: detailed` eller `departures`
- Hämta var 15–60 minut för realtidsvisning
- Hämta dagligen för planeringsverktyg

### Sekundär: PDF-tidtabeller (via Contentful CDN)
- Använd för `manual`-rutter (Göteborg, Brevik) som fallback
- Parsning kräver PDF-extraheringsbibliotek (pdfplumber, PyMuPDF)
- Uppdateras oregelbundet — kräva manuell omsorg

### Caching-strategi
```
Realtidsvisning:    TTL 15 min
Planeringsverktyg:  TTL 60 min
Historikdatabas:    Spara alla TALLIED-avgångar permanent
```

### Portkodsunderhåll
Portkodsregistret är stabilt (UN/LOCODE-derivat) men kan behöva uppdateras om DFDS lägger till/tar bort rutter. Scrapa `__NEXT_DATA__` från indexsidan månadsvis för att hålla registret aktuellt.

---

## 9. Final Assessment

| Fråga | Svar |
|---|---|
| Realistiskt automatiserbart? | **Ja, fullt ut** |
| Direkt API-åtkomst möjlig? | **Ja, utan begränsningar** |
| Browser-automatisering nödvändigt? | **Nej** |
| HTML/PDF-scraping bästa alternativ? | **Nej** (API är överlägset; PDF som fallback) |
| Frakt vs. passagerare — skilda system? | **Troligen ja** (ej undersökt) |
| Metodens stabilitet? | **Medelhög** — API är odokumenterat och kan ändras utan förvarning |
| Rekommenderad strategi? | **Direkt GET mot `/api/timetable`** med lokal caching och månadsvis portkodsvalidering |

---

*Rapport genererad 2026-05-19 via live-utredning av DFDS.com*
