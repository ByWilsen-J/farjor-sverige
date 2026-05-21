# Finnlines — API-rapport (reverse engineering)
**Datum:** 2026-05-18  
**Metod:** JS-bundle-analys, nätverkstrafik, live API-test  
**Status:** ✅ Verifierade, fungerande endpoints

---

## 1. Arkitekturöversikt

| Lager | Teknik |
|---|---|
| Huvudsajt | WordPress (custom theme) + Cloudflare CDN |
| CMS API | WordPress REST API (`/wp-json/finnlines/v1/`) |
| Boknings-SPA | React 18.3.1, Vite-bundle, hosting: `booking.finnlines.com` |
| GraphQL-backend | AWS AppSync (eu-central-1) |
| GraphQL-klient | AWS Amplify |
| Auth (publikt) | API_KEY (hårdkodad i bundle) |
| Auth (konto) | AWS Cognito (identity pool + user pools) |
| Betalning | NETS NetAxept |
| Frakt B2B | Grimaldi externt system |

---

## 2. Primär GraphQL-endpoint

```
URL:     https://dm3xyy44wbeivgqmeymvmw22be.appsync-api.eu-central-1.amazonaws.com/graphql
Metod:   POST
Auth:    x-api-key header
API Key: da2-zvuktusyubbstlw7khps4vyeie
Region:  eu-central-1
```

**Headers:**
```http
Content-Type: application/json
x-api-key: da2-zvuktusyubbstlw7khps4vyeie
```

---

## 3. JS-bundle (boknings-SPA)

```
URL:  https://booking.finnlines.com/assets/index-qGE22Hpa.js
Size: 1,58 MB (minifierad)
```

Bundelns filnamn är content-hashed — vid deploy byts hash. Ny URL hittas via:
```bash
curl -s https://booking.finnlines.com/ | grep -oP 'assets/index-[^"]+\.js'
```

---

## 4. Enum-värden (extraherade ur bundle)

```javascript
// Valutor
Jm = { EUR: "EUR", SEK: "SEK", PLN: "PLN" }

// Språk
Ym = { IT:"IT", DE:"DE", EN:"EN", ES:"ES", FI:"FI", FR:"FR", SV:"SV", PL:"PL", NL:"NL" }

// Passagerartyper
z = { ADULT:"ADULT", CHILD:"CHILD", INFANT:"INFANT", JUNIOR:"JUNIOR" }

// Husdjur
Xm = { PET: "PET" }

// Tariff
eh = { SPECIAL:"SPECIAL", STANDARD:"STANDARD" }
```

**Priser:** representeras i heltal-cent (3020 = €30,20)

---

## 5. Rutter och hamnkoder

### Passagerarrutter
```
FIHEL  = Helsinki
DETRV  = Travemünde
FILAN  = Långnäs (Åland)
SEKPS  = Kapellskär
SEMMA  = Malmö (Värtahamnen)
FINLI  = Naantali
SEUMB  = Umeå
```

**Rutter utan krav på boende (accommodation not required):**
`FINLI, FILAN, SEKPS, SEMMA`
(kortare passager — ingen nattresa)

**Rutter som kräver boende i TimetableQuery:**
`FIHEL ↔ DETRV` (använd `ListSailingsAvailability` för enkla listningar)

### Frakt-rutter
```
Göteborg ↔ Travemünde
Malmö ↔ Rostock
Naantali ↔ Travemünde
Naantali ↔ Stockholm
Norrköping ↔ Travemünde
Helsingborg ↔ Travemünde
```

---

## 6. GraphQL-queries

### 6.1 ListSailingsAvailability (enkel tidtabell utan boende)

```graphql
query ListSailingsAvailability($query: SailingsAvailabilityQuery!) {
  listSailingsAvailability(query: $query) {
    ... on SailingsAvailabilityResult {
      sailings {
        departurePort
        arrivalPort
        departureTime
        arrivalTime
        duration
        availableForBooking
        prices {
          currency
          amount
          tariff
        }
        vessel {
          name
          code
        }
      }
    }
    ... on ApiError {
      code
      message
    }
  }
}
```

**Variabler:**
```json
{
  "query": {
    "currency": "EUR",
    "departurePort": "FIHEL",
    "arrivalPort": "DETRV",
    "startDate": "2026-06-01",
    "endDate": "2026-06-21",
    "numberOfDays": 20,
    "numberOfDepartures": 21
  }
}
```

---

### 6.2 TimetableQuery (full bokning med passagerare/boende)

Variabelstruktur extraherad ur `$j()`-funktionen i bundle:

```json
{
  "currency": "EUR",
  "language": "SV",
  "tariff": [],
  "passengers": [
    { "legCode": 1, "id": 1, "type": "ADULT" }
  ],
  "pets": [],
  "vehicles": [],
  "sailings": [
    {
      "legCode": 1,
      "departurePort": "FINLI",
      "arrivalPort": "SEKPS",
      "startDate": "2026-06-01",
      "endDate": "2026-06-21",
      "numberOfDays": 20,
      "numberOfDepartures": 21
    }
  ],
  "accommodations": [],
  "onboards": []
}
```

> **OBS:** Datum ligger i `sailings[].startDate` — INTE på toppnivå.
> **OBS:** Minst 1 passagerare krävs, annars Lambda:Unhandled error.

---

## 7. WordPress REST API (frakt-tidtabell)

```
Base: https://www.finnlines.com/wp-json
Namespace: finnlines/v1
```

### Rutter-endpoint
```
GET https://www.finnlines.com/wp-json/finnlines/v1/routes?from={from}&to={to}
```

**Landskoder (custom — EJ ISO):**
```
Sverige  → se
Finland  → fi
Tyskland → ge   ← OBS: inte "de"
Polen    → pl
```

**Exempel:**
```bash
curl "https://www.finnlines.com/wp-json/finnlines/v1/routes?from=se&to=ge"
```

---

## 8. Komplett Python-automationsskript

```python
#!/usr/bin/env python3
"""
Finnlines timetable fetcher
Hämtar passagerarseglar och fraktrutter via live API.
Kör utan inloggning — använder publik API-nyckel.
"""

import requests
import json
from datetime import date, timedelta

GRAPHQL_URL = (
    "https://dm3xyy44wbeivgqmeymvmw22be.appsync-api.eu-central-1.amazonaws.com/graphql"
)
API_KEY = "da2-zvuktusyubbstlw7khps4vyeie"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
}
FREIGHT_BASE = "https://www.finnlines.com/wp-json/finnlines/v1"

SAILINGS_QUERY = """
query ListSailingsAvailability($query: SailingsAvailabilityQuery!) {
  listSailingsAvailability(query: $query) {
    ... on SailingsAvailabilityResult {
      sailings {
        departurePort arrivalPort departureTime arrivalTime
        duration availableForBooking
        prices { currency amount tariff }
        vessel { name code }
      }
    }
    ... on ApiError { code message }
  }
}
"""

def list_sailings(dep_port, arr_port, start_date, days=20):
    end_date = (date.fromisoformat(start_date) + timedelta(days=days)).isoformat()
    payload = {
        "query": SAILINGS_QUERY,
        "variables": {"query": {
            "currency": "EUR",
            "departurePort": dep_port, "arrivalPort": arr_port,
            "startDate": start_date, "endDate": end_date,
            "numberOfDays": days, "numberOfDepartures": 50,
        }},
    }
    resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]["listSailingsAvailability"]

def freight_schedule(country_from, country_to):
    r = requests.get(
        f"{FREIGHT_BASE}/routes",
        params={"from": country_from, "to": country_to},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def format_sailing(s):
    dep = s.get("departureTime", "?")[:16].replace("T", " ")
    arr = s.get("arrivalTime", "?")[:16].replace("T", " ")
    vessel = s.get("vessel", {}).get("name", "?")
    prices = s.get("prices", [])
    price_str = ", ".join(
        f"{p['currency']} {p['amount']/100:.2f} ({p['tariff']})" for p in prices
    )
    avail = "OK" if s.get("availableForBooking") else "EJ"
    return f"{avail} {dep} -> {arr}  [{vessel}]  {price_str}"

if __name__ == "__main__":
    today = date.today().isoformat()
    routes = [
        ("FIHEL", "DETRV"), ("DETRV", "FIHEL"),
        ("FINLI", "SEKPS"), ("SEKPS", "FINLI"),
        ("FILAN", "SEKPS"), ("SEKPS", "FILAN"),
        ("SEMMA", "FINLI"), ("FINLI", "SEMMA"),
    ]
    for dep, arr in routes:
        print(f"\n{dep} -> {arr}")
        result = list_sailings(dep, arr, today, days=30)
        sailings = result.get("sailings", []) if isinstance(result, dict) else []
        for s in sailings[:5]:
            print(" ", format_sailing(s))

    print("\nFrakt SE->DE:")
    print(json.dumps(freight_schedule("se", "ge"), ensure_ascii=False, indent=2))
```

---

## 9. curl-testkommandon

```bash
# Avgångar Helsinki -> Travemünde
curl -s -X POST \
  "https://dm3xyy44wbeivgqmeymvmw22be.appsync-api.eu-central-1.amazonaws.com/graphql" \
  -H "Content-Type: application/json" \
  -H "x-api-key: da2-zvuktusyubbstlw7khps4vyeie" \
  -d '{"query":"query L($q:SailingsAvailabilityQuery!){listSailingsAvailability(query:$q){...on SailingsAvailabilityResult{sailings{departurePort arrivalPort departureTime arrivalTime availableForBooking vessel{name}}}...on ApiError{code message}}}","variables":{"q":{"currency":"EUR","departurePort":"FIHEL","arrivalPort":"DETRV","startDate":"2026-06-01","endDate":"2026-07-01","numberOfDays":30,"numberOfDepartures":50}}}' \
  | python3 -m json.tool

# Fraktrutter Sverige -> Tyskland
curl -s "https://www.finnlines.com/wp-json/finnlines/v1/routes?from=se&to=ge" | python3 -m json.tool
```

---

## 10. Risker och begränsningar

| Risk | Sannolikhet | Åtgärd |
|---|---|---|
| API-nyckeln roteras | Medel | Hämta ny nyckel ur bundle vid fel 401 |
| Bundle-URL ändras (ny hash) | Hög vid deploy | Scrapa `booking.finnlines.com/` för ny JS-URL |
| AppSync endpoint byts | Låg | Re-analysera bundle |
| Rate limiting | Okänd | Lägg in `time.sleep(1)` mellan anrop |
| Datumformat förändras | Låg | Testa med ISO 8601 alltid |
| WP REST-slug byts | Låg | Sök `finnlines/v1` i ny bundle |

---

## 11. Rekommenderad automatiseringsstrategi

```
Daglig cron (t.ex. 05:00):
  1. Hämta https://booking.finnlines.com/ -> extrahera ny bundle-URL
  2. Om URL förändrats: re-extrahera API_KEY och endpoint
  3. Kör list_sailings() för alla rutter, 30 dagar framåt
  4. Kör freight_schedule() för relevanta länderpar
  5. Spara till JSON/Excel/DB med timestamp
  6. Jämför mot föregående körning, flagga förändringar
```

---

## 12. Nästa steg (kvarvarande rederier)

Samma metodik appliceras på:

- [ ] Polferries (Polsca)
- [ ] Tallink / Silja Line
- [ ] TT-Line
- [ ] DFDS
- [ ] Stena Line

---

*Rapport genererad: 2026-05-18 | Analyserad av: Claude (Cowork)*
