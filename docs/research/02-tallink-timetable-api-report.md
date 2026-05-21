# Tallink Silja Line — Timetable API Technical Report

**Investigated:** 2026-05-20  
**Method:** Live browser reverse engineering (DevTools + JS bundle analysis + API probing)  
**Target:** https://www.tallink.com/en/timetables

---

## Summary

Tallink's timetable page is a Next.js application backed by an undocumented but publicly accessible JSON API at `cms-web-api-nx.tallink.com`. The timetable data is **not embedded in the page HTML as static content** — it is fetched server-side by Next.js (`getServerSideProps`) from the internal API and injected into the rendered HTML. The same API is also called client-side when the user changes route or date. **No authentication is required** to call the API directly. Server-to-server calls (Python, curl, Node.js) work without restriction.

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | Next.js (SSR, `getServerSideProps`) |
| CMS | WordPress with ACF (Advanced Custom Fields) — page content only |
| Timetable data | Internal REST API: `cms-web-api-nx.tallink.com` |
| Auth (user accounts) | NextAuth + SSO via `cms-web-api.tallink.com/api/torpedo/clients/` |
| Analytics | Google Analytics 4, Microsoft Clarity, CrazyEgg |
| CDN / Bot protection | Not detected at API level |

---

## Primary Timetable Endpoint

```
GET https://cms-web-api-nx.tallink.com/api/seaweb/timetables
```

For cruise routes:

```
GET https://cms-web-api-nx.tallink.com/api/seaweb/cruise/timetables
```

### Query Parameters

| Parameter | Required | Example | Notes |
|---|---|---|---|
| `locale` | Yes | `en` | Language: `en`, `fi`, `sv`, `et`, `de`, `ru`… |
| `country` | Yes | `XZ` | Market code. Use `XZ` for international/generic |
| `from` | Yes | `hel` | 3-letter lowercase port code (see below) |
| `to` | Yes | `tal` | 3-letter lowercase port code |
| `dateFrom` | Yes | `2026-06-01` | ISO date, start of range |
| `dateTo` | Yes | `2026-06-07` | ISO date, end of range |
| `voyageType` | Yes | `ROUTETRIP` | `ROUTETRIP` or `CRUISE` |
| `oneWay` | Yes | `false` | Always `false` |
| `includeOvernight` | Yes | `true` | Include overnight sailings |
| `searchFutureSails` | Yes | `false` | Always `false` |

### Port Codes (confirmed by live API)

| Port | Code |
|---|---|
| Helsinki | `hel` |
| Tallinn | `tal` |
| Stockholm | `sto` |
| Turku | `tur` |
| Paldiski | `pal` |
| Kapellskär | `kap` |

> **Note:** Codes are all lowercase 3-letter. `tal` for Tallinn (not `tll`), `tur` for Turku (not `tku`).

---

## Response Structure

```json
{
  "defaultSelections": {
    "outwardSail": null,
    "returnSail": null
  },
  "trips": {
    "2026-05-19": {
      "outwards": [ /* array of sailing objects */ ],
      "returns":  [ /* array of sailing objects, reverse direction */ ]
    },
    "2026-05-20": { ... },
    "2026-05-21": { ... }
  },
  "isClubOneOnlyPromotion": null
}
```

`trips` is keyed by date (`YYYY-MM-DD`). Each date contains an `outwards` array (requested direction) and a `returns` array (reverse direction). The API typically returns more dates than the range requested.

### Sailing Object Fields

```json
{
  "sailId": 2380164,
  "sailPackageCode": "HEL-TAL",
  "sailPackageName": "Helsinki-Tallinn",
  "shipCode": "MEGASTAR",
  "departureIsoDate": "2026-05-19T07:30",
  "arrivalIsoDate": "2026-05-19T09:30",
  "duration": 2,
  "personPrice": 38.90,
  "vehiclePrice": null,
  "pierFrom": "LSA2",
  "pierTo": "DTER",
  "cityFrom": "HEL",
  "cityTo": "TAL",
  "isOvernight": false,
  "isDisabled": true,
  "hasRoom": true,
  "promotionApplied": false,
  "marketingMessage": null,
  "isVoucherApplicable": false,
  "shoppingCruiseEligibleSailId": 2378943,
  "secondLegDepartureIsoDate": null
}
```

| Field | Type | Description |
|---|---|---|
| `sailId` | int | Unique sailing ID |
| `sailPackageCode` | string | Route code, e.g. `HEL-TAL`, `TUR-STO` |
| `sailPackageName` | string | Human-readable route name |
| `shipCode` | string | Vessel: `MEGASTAR`, `MYSTAR`, `VICTORIA`, `PRINCESS` |
| `departureIsoDate` | string | Local time, no timezone, format `YYYY-MM-DDTHH:MM` |
| `arrivalIsoDate` | string | Local time, no timezone |
| `duration` | int | Journey length in hours |
| `personPrice` | float | Lowest available person price in EUR |
| `vehiclePrice` | float\|null | Lowest vehicle price in EUR, null if not sold |
| `pierFrom` / `pierTo` | string | Terminal pier codes (e.g. `LSA2`, `DTER`, `TSAT`, `VHAM`) |
| `cityFrom` / `cityTo` | string | 3-letter uppercase city codes |
| `isOvernight` | bool | True if arrival is next calendar day |
| `isDisabled` | bool | True if departure has passed or sales are closed |
| `hasRoom` | bool | Cabin availability indicator |
| `promotionApplied` | bool | Whether a discounted price is applied |
| `shoppingCruiseEligibleSailId` | int\|null | Related cruise ID for shopping cruises |
| `secondLegDepartureIsoDate` | string\|null | For two-leg itineraries |

### Vessel Pier Codes (observed)

| Route | Pier Origin | Pier Destination |
|---|---|---|
| Helsinki→Tallinn | `LSA2` (West Harbour T2) | `DTER` (D-terminal Tallinn) |
| Turku→Stockholm | `TSAT` (Turku harbour) | `VHAM` (Värtahamnen Stockholm) |

---

## Live Data Verified

All 8 sailings for Helsinki→Tallinn on 2026-05-19 were returned and matched the website exactly:

| Departure | Arrival | Ship | Price | Status |
|---|---|---|---|---|
| 07:30 | 09:30 | MEGASTAR | €38.90 | Departed |
| 10:30 | 12:30 | MYSTAR | €52.90 | Departed |
| 13:30 | 15:30 | MEGASTAR | €40.90 | Departed |
| 16:30 | 18:30 | MYSTAR | €38.90 | Departed |
| 18:35 | 22:45 | VICTORIA | €40.30 | Departed |
| 18:35 | 08:00+1 | VICTORIA | €90.30 | Overnight — Departed |
| 19:30 | 21:30 | MEGASTAR | €40.90 | Departed |
| 23:00 | 01:00+1 | MYSTAR | €38.90 | **On sale** |

---

## Authentication & CORS

- **No API key or token required** for timetable data. Plain GET request works.
- **CORS**: The API allows `www.tallink.com` as origin. Calling it directly from a browser on another domain will be blocked by CORS. **Server-to-server calls (curl, Python, Node.js backend) are completely unaffected — they work without special headers.**
- The `torpedo/clients/` endpoint requires SSO authentication (HTTP 401 without it). Not needed for timetable data.
- No session cookie is required.

---

## Code Examples

### curl

```bash
curl -s \
  "https://cms-web-api-nx.tallink.com/api/seaweb/timetables?locale=en&country=XZ&from=hel&to=tal&oneWay=false&dateFrom=2026-06-01&dateTo=2026-06-07&voyageType=ROUTETRIP&includeOvernight=true&searchFutureSails=false" \
  -H "Accept: application/json" \
  -H "Accept-Language: en" \
  | python3 -m json.tool
```

### Python

```python
import requests
from datetime import date, timedelta

API = "https://cms-web-api-nx.tallink.com/api/seaweb/timetables"
HEADERS = {"Accept": "application/json", "Accept-Language": "en"}

def get_timetable(from_port: str, to_port: str, date_from: date, date_to: date,
                  locale: str = "en", country: str = "XZ") -> dict:
    params = {
        "locale": locale,
        "country": country,
        "from": from_port,
        "to": to_port,
        "oneWay": "false",
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "voyageType": "ROUTETRIP",
        "includeOvernight": "true",
        "searchFutureSails": "false",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def print_timetable(data: dict):
    for day, trips in sorted(data["trips"].items()):
        print(f"\n=== {day} ===")
        for sail in trips.get("outwards", []):
            status = "PAST" if sail["isDisabled"] else "OPEN"
            overnight = " (overnight)" if sail["isOvernight"] else ""
            print(
                f"  {sail['departureIsoDate'][11:]} → {sail['arrivalIsoDate'][11:]}"
                f"  {sail['shipCode']:<10}"
                f"  €{sail['personPrice']:.2f}"
                f"  [{status}]{overnight}"
            )


if __name__ == "__main__":
    today = date.today()
    data = get_timetable("hel", "tal", today, today + timedelta(days=6))
    print_timetable(data)
```

### JavaScript (Node.js / server-side)

```javascript
const API = 'https://cms-web-api-nx.tallink.com/api/seaweb/timetables';

async function getTimetable({ from, to, dateFrom, dateTo, locale = 'en', country = 'XZ' }) {
  const params = new URLSearchParams({
    locale, country, from, to,
    oneWay: 'false',
    dateFrom,
    dateTo,
    voyageType: 'ROUTETRIP',
    includeOvernight: 'true',
    searchFutureSails: 'false',
  });

  const res = await fetch(`${API}?${params}`, {
    headers: { Accept: 'application/json', 'Accept-Language': locale },
  });

  if (!res.ok) throw new Error(`Tallink API error: HTTP ${res.status}`);
  return res.json();
}

// Example: fetch Helsinki–Tallinn for the next 7 days
const today = new Date().toISOString().slice(0, 10);
const nextWeek = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);

const data = await getTimetable({ from: 'hel', to: 'tal', dateFrom: today, dateTo: nextWeek });

for (const [day, { outwards }] of Object.entries(data.trips).sort()) {
  console.log(`\n=== ${day} ===`);
  for (const s of outwards) {
    const dep = s.departureIsoDate.slice(11);
    const arr = s.arrivalIsoDate.slice(11);
    console.log(`  ${dep} → ${arr}  ${s.shipCode.padEnd(10)}  €${s.personPrice}`);
  }
}
```

---

## Timezone Note

All timestamps are in **local time at the port of departure** with no UTC offset or timezone suffix. Apply the correct offset when converting to UTC:

| Region | Summer (CEST/EEST) | Winter (CET/EET) |
|---|---|---|
| Helsinki, Tallinn | UTC+3 (EEST) | UTC+2 (EET) |
| Stockholm, Turku | UTC+2 (CEST) | UTC+1 (CET) |

---

## Caching & Refresh Strategy

- **Recommended cache TTL**: 1–4 hours for schedule data, 15–30 minutes if prices are critical.
- **Date range**: Request up to 30 days at once — the API handles wide ranges efficiently.
- **Stale detection**: If the API changes structure or requires auth, you will get HTTP 401/403 or an empty `trips: {}`. Add monitoring for these states.
- **Safe polling rate**: One request per route pair per refresh cycle. No observed rate limits, but there is no official quota.

---

## Risks & Limitations

| Risk | Severity | Notes |
|---|---|---|
| API is undocumented / unofficial | High | No SLA, no public contract. Could break without notice |
| CORS blocks browser-direct calls | Medium | Must route through own backend — not a problem for server use |
| Auth may be added later | Medium | Monitor for HTTP 401/403 responses |
| No timezone in timestamps | Low | Known, handle with port→timezone mapping |
| `cms-web-api-nx` vs `cms-web-api` | Low | Two hostnames observed; `nx` appears to be the current one |
| Freight/cargo is a separate system | N/A | `freight.tallink.com` uses a completely different system |

---

## Final Assessment

| Question | Answer |
|---|---|
| Is timetable data automatable? | ✅ Yes — straightforwardly |
| Authentication required? | ✅ No |
| Browser automation required? | ✅ No |
| HTML scraping required? | ✅ No — clean JSON API |
| Works from server (Python/curl)? | ✅ Yes |
| Passenger and freight same system? | ❌ No — separate systems |
| Recommended integration? | Server-side polling → local cache → own frontend/API |
| Stability rating | ⚠️ Moderate — works now, undocumented, monitor it |

---

*Report produced by automated browser reverse engineering. All findings are based on publicly observable network traffic and publicly served JavaScript bundles. No credentials were extracted, bypassed, or used.*
