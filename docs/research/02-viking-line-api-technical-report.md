# Viking Line Timetable System — Technical Investigation Report

**Target:** https://www.sales.vikingline.com/find-trip/timetable/  
**Investigation date:** 2026-05-19  
**Investigator:** Claude (Cowork mode)  
**Scope:** API discovery, endpoint documentation, authentication analysis, automation viability

---

## Executive Summary

Viking Line's public-facing timetable page is statically server-rendered with no API calls — there is no timetable-specific REST or GraphQL endpoint accessible from that URL. However, the booking engine SPA at `/ferry/eng/en/select-ferry/` exposes a fully functional, unauthenticated JSON API (`/protheus-api/v1/`) that returns sailing schedules, departure times, ship assignments, intermediate stops, availability status, and pricing. This API is the correct integration target for programmatic access to sailing data.

**Bottom line:** Programmatic access is viable and straightforward. The API requires no authentication token, no session cookie, and has open CORS headers. It caches responses for 180 seconds.

---

## 1. Findings

### 1.1 Timetable page is purely server-rendered

The page at `/find-trip/timetable/stockholm-helsinki/` (and equivalent routes) is rendered entirely on the server by the Episerver/Optimizely CMS. Network monitoring on page load captures approximately 20 requests — all analytics and tracking (Google Analytics, Cookiebot, Akamai). Zero AJAX/XHR/fetch calls are made for timetable data after the initial HTML response.

The timetable HTML itself is structured as seasonal blocks:

```
H3: "13.04.2026–16.06.2026"
  H4: "Stockholm–Helsinki"
    TABLE:
      <tr> Stockholm dep 16:00 | Åland* arr 23:00 dep 23:05 | Helsinki arr 10:10 </tr>
```

**Consequence:** HTML scraping of the timetable page only yields the seasonal published schedule (e.g., "every day 16:00"). It does not give real-time availability, ship assignment, actual vs. planned times, or pricing.

### 1.2 The booking engine uses a React SPA with a Protheus API backend

When the user submits a booking form, the flow is:

1. **POST** `/BookingModuleBlock/ValidateBooking` (Episerver MVC controller) — validates form fields and builds query params
2. **Redirect** to `/ferry/eng/en/market.vl?action=select-sailings&...` — legacy entry point (Akamai-protected)
3. **Redirect** to `/ferry/eng/en/select-ferry/?searchParams={base64-json}` — the React SPA
4. SPA makes **GET** requests to `/protheus-api/v1/ferry/eng/en/search-ferry/{day|week}/{base64-json}` — the real data API

### 1.3 Technology stack

| Component | Technology |
|-----------|-----------|
| CMS / main site | Episerver/Optimizely, AngularJS 1.7.7 |
| Booking widget | Vue.js (booking.bundle.js, 258 KB) |
| Booking SPA | React (index-vl.C6iEPhUQ.1.1.23.js, 5.3 MB) |
| Bot protection (main) | Kasada (obfuscated JS at `/udict-Thus-Messe-Witch-see-befors-at-be-King-out`) |
| Bot protection (legacy booking entry) | Akamai Bot Manager |
| Cookie consent | Cookiebot |
| Data API | Protheus API (`/protheus-api/v1/`) behind nginx |

---

## 2. APIs Discovered

### 2.1 Protheus API — Search Ferry (Day View)

**This is the primary data endpoint.**

```
GET /protheus-api/v1/{locale}/search-ferry/day/{base64-params}
```

- **Base URL:** `https://www.sales.vikingline.com`
- **Locale path segment:** `ferry/eng/en` (ferry product, English, EN market)
- **Authentication:** None required
- **CORS:** `Access-Control-Allow-Origin: *`
- **Cache:** `Cache-Control: public, max-age=180` (3-minute public cache)
- **Content-Type:** `application/json`

**Confirmed working without:**
- `VL-CST` header
- Session cookies
- Any `Authorization` header

### 2.2 Protheus API — Search Ferry (Week View)

```
GET /protheus-api/v1/{locale}/search-ferry/week/{base64-params}
```

Same base URL, locale and parameter schema as the day view. Returns results across a 7-day window centered on `searchDate`. Useful for building calendar-style availability views.

### 2.3 Booking module block (not timetable-relevant)

```
POST /BookingModuleBlock/ValidateBooking
```

Episerver server-side MVC controller. Validates booking form state and redirects to the SPA. Not directly useful for programmatic timetable/schedule access — it requires form session state and returns HTML redirects, not JSON.

---

## 3. Request Parameter Schema

The `{base64-params}` path segment is a standard Base64-encoded JSON object (no URL-safe variant — uses `+` and `=` which must be URL-encoded if placed in a query string, but here they appear in the path and are accepted as-is).

### Parameter object schema

```json
{
  "searchDate": "2026-06-20",
  "departurePort": "STO",
  "arrivalPort": "HEL",
  "numberOfAdults": 2,
  "childrenAges": [],
  "vehicle": {
    "code": "NONE",
    "quantity": 1
  },
  "club": "NONE"
}
```

### Field reference

| Field | Type | Notes |
|-------|------|-------|
| `searchDate` | string (YYYY-MM-DD) | The sailing date to search |
| `departurePort` | string | 3-letter port code (see below) |
| `arrivalPort` | string | 3-letter port code |
| `numberOfAdults` | integer | Minimum 1 |
| `childrenAges` | array of int | Ages of children, e.g. `[5, 8]` |
| `vehicle` | object | `code`: `"NONE"`, `"CAR"`, etc. `quantity`: 1 |
| `club` | string | `"NONE"` or Viking Line Club member number |

### Port codes

| Code | Port |
|------|------|
| `STO` | Stockholm (Stadsgården) |
| `KAP` | Kapellskär |
| `HEL` | Helsinki (Katajanokka) |
| `TKU` | Turku (Åbo) |
| `MAR` | Mariehamn (Åland) |
| `LAN` | Långnäs (Åland) |
| `TAL` | Tallinn |

### Valid direct routes (from booking.bundle.js)

| From | To options |
|------|-----------|
| STO | HEL, TKU, MAR, LAN, TAL |
| HEL | STO, TAL, MAR |
| KAP | MAR |
| TAL | HEL, MAR, STO |
| TKU | STO, MAR, LAN |
| MAR | KAP, STO, HEL, TKU, TAL |
| LAN | TKU, STO |

---

## 4. Response Schema

### Top-level structure

```json
{
  "result": {
    "dateHits": [
      {
        "date": "2026-06-20",
        "historicalDate": false,
        "hits": [ ... ]
      }
    ]
  },
  "status": "..."
}
```

The day endpoint returns one `dateHit` object. The week endpoint returns up to 7.

### Hit object structure

Each `hit` inside `dateHits[n].hits[]`:

```json
{
  "availability": "AVAILABLE",
  "price": {
    "clubPrice": false,
    "normalPrice": { "amount": 127, "currency": "EUR", "priceType": "ABSOLUTE", "signedAmount": 127 },
    "yourPrice":  { "amount": 127, "currency": "EUR", "priceType": "ABSOLUTE", "signedAmount": 127 }
  },
  "details": {
    "birkaVehiclesNotAllowed": false,
    "hasDiscount": false,
    "vehiclesNotAllowed": false,
    "youthOnlyBirkaNotAllowed": false,
    "youthOnlyHelTalNotAllowed": false,
    "youthOnlyPermissionNeeded": false
  },
  "booking": { ... },
  "hasRemovedContent": false,
  "transferredContent": null
}
```

### booking.outwardJourney — sailing details

```json
{
  "departurePort": "STO",
  "arrivalPort": "HEL",
  "departureDate": {
    "localDate": "2026-06-20",
    "localDateTime": "2026-06-20T16:00:00",
    "localTime": "16:00:00",
    "timeZoneInfo": "Europe/Stockholm",
    "instant": 1781964000000
  },
  "arrivalDate": {
    "localDate": "2026-06-21",
    "localDateTime": "2026-06-21T09:15:00",
    "localTime": "09:15:00",
    "timeZoneInfo": "Europe/Helsinki",
    "instant": 1782022500000
  },
  "ship": "CI",
  "departureKey": "7338356769",
  "stops": [
    {
      "port": "MAR",
      "start": {
        "localDateTime": "2026-06-20T22:50:00",
        "timeZoneInfo": "Europe/Helsinki"
      },
      "end": {
        "localDateTime": "2026-06-20T22:55:00",
        "timeZoneInfo": "Europe/Helsinki"
      },
      "boardingEnds": {
        "localDateTime": "2026-06-20T22:35:00",
        "timeZoneInfo": "Europe/Helsinki"
      }
    }
  ],
  "price": { "amount": 127, "currency": "EUR", "priceType": "ABSOLUTE", "signedAmount": 127 },
  "passengers": [
    {
      "category": "ADULT",
      "quantity": 2,
      "price": { "amount": 14, "currency": "EUR" }
    }
  ],
  "isBookingClosed": false,
  "isCheckinOpen": false
}
```

### Ship codes observed

| Code | Ship |
|------|------|
| `CI` | Viking Cinderella |
| `GA` | Gabriella |
| `GR` | Viking Grace |
| `XP` | Viking XPRS |
| `AB` | Amorella |

*(CI confirmed directly from API response. Others inferred from GA event product codes and timetable HTML.)*

---

## 5. Confirmed Full Example — STO→HEL, 2026-06-20

**Sailing:** Stockholm → Mariehamn → Helsinki  
**Ship:** Viking Cinderella (`CI`)  
**Departs:** 2026-06-20 16:00 (Europe/Stockholm)  
**Stop Mariehamn:** arr 22:50, dep 22:55 (Europe/Helsinki)  
**Arrives Helsinki:** 2026-06-21 09:15 (Europe/Helsinki)  
**Availability:** AVAILABLE  
**Base price:** 127 EUR (2 adults, no cabin)  
**Climate surcharge:** 14 EUR  

---

## 6. Authentication Analysis

### window.vlCst

The React SPA initializes an Axios HTTP client with:

```javascript
baseUrl + "/protheus-api/v1/",
headers: { "VL-CST": window.vlCst }
```

`window.vlCst` is a UUID-format string (e.g. `772b3346-4e42-4ded-804c-299b09c4eec2`, 36 chars) injected into the page at SSR time. It appears to be a client session token, not a secret API key.

**Critical finding:** Direct API calls without any `VL-CST` header and with `credentials: 'omit'` (no cookies) return HTTP 200 with full data. The token is not enforced server-side for read operations on the search endpoints. This is consistent with the response headers:

```
Access-Control-Allow-Origin: *
Cache-Control: public, max-age=180
```

Public caching (`public`) and wildcard CORS together confirm the API is designed to be publicly readable. The `VL-CST` header is likely used for booking write operations (cabin selection, passenger registration, payment), not for search.

### Akamai Bot Manager

The legacy entry point `/ferry/eng/en/market.vl` is protected by Akamai and returns "Pardon Our Interruption" for direct HTTP clients. This does **not** affect the Protheus API — the search endpoints sit behind nginx on a different routing path and have no bot detection active.

### Kasada

Kasada protection is present on the main `sales.vikingline.com` domain. It does not appear to affect the Protheus API search endpoints.

---

## 7. Code Examples

### curl

```bash
# Build the Base64-encoded parameter (Linux: base64 -w0, macOS: base64)
PARAMS=$(echo -n '{"searchDate":"2026-06-20","departurePort":"STO","arrivalPort":"HEL","numberOfAdults":2,"childrenAges":[],"vehicle":{"code":"NONE","quantity":1},"club":"NONE"}' | base64 -w0)

# Day view
curl -s "https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en/search-ferry/day/${PARAMS}" \
  -H "Accept: application/json" \
  | jq '.result.dateHits[0].hits[0].booking.outwardJourney
        | {ship, dep: .departureDate.localDateTime, arr: .arrivalDate.localDateTime, stops: [.stops[].port]}'

# Week view
curl -s "https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en/search-ferry/week/${PARAMS}" \
  -H "Accept: application/json" \
  | jq '[.result.dateHits[] | {date, hits: [.hits[].booking.outwardJourney
        | {ship, dep: .departureDate.localTime, arr: .arrivalDate.localTime}]}]'
```

### Python

```python
import base64
import json
import requests

BASE_URL = "https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en"

def build_params(search_date, departure_port, arrival_port,
                 adults=2, children_ages=None, vehicle_code="NONE"):
    """Encode search parameters as Base64 JSON for the Protheus API."""
    payload = {
        "searchDate": search_date,
        "departurePort": departure_port,
        "arrivalPort": arrival_port,
        "numberOfAdults": adults,
        "childrenAges": children_ages or [],
        "vehicle": {"code": vehicle_code, "quantity": 1},
        "club": "NONE",
    }
    return base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


def search_day(search_date, dep, arr, **kwargs):
    """Fetch sailings for a specific day."""
    encoded = build_params(search_date, dep, arr, **kwargs)
    url = f"{BASE_URL}/search-ferry/day/{encoded}"
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
    r.raise_for_status()
    return r.json()


def search_week(search_date, dep, arr, **kwargs):
    """Fetch sailings for the 7-day window around search_date."""
    encoded = build_params(search_date, dep, arr, **kwargs)
    url = f"{BASE_URL}/search-ferry/week/{encoded}"
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
    r.raise_for_status()
    return r.json()


def extract_sailings(response):
    """Parse the API response into a flat list of sailing summaries."""
    sailings = []
    for date_hit in response["result"]["dateHits"]:
        for hit in date_hit["hits"]:
            oj = hit["booking"]["outwardJourney"]
            sailings.append({
                "date": date_hit["date"],
                "departure_port": oj["departurePort"],
                "arrival_port": oj["arrivalPort"],
                "departure_time": oj["departureDate"]["localDateTime"],
                "departure_tz": oj["departureDate"]["timeZoneInfo"],
                "arrival_time": oj["arrivalDate"]["localDateTime"],
                "arrival_tz": oj["arrivalDate"]["timeZoneInfo"],
                "ship": oj["ship"],
                "departure_key": oj["departureKey"],
                "availability": hit["availability"],
                "price_eur": hit["price"]["normalPrice"]["amount"],
                "stops": [s["port"] for s in oj.get("stops", [])],
            })
    return sailings


# --- Example usage ---
if __name__ == "__main__":
    result = search_day("2026-06-20", "STO", "HEL", adults=2)
    for s in extract_sailings(result):
        print(
            f"{s['departure_time']} ({s['departure_tz']}) "
            f"{s['departure_port']} → {s['arrival_port']} "
            f"via {s['stops']} | Ship: {s['ship']} | "
            f"{s['availability']} | {s['price_eur']} EUR"
        )
    # Output:
    # 2026-06-20T16:00:00 (Europe/Stockholm) STO → HEL via ['MAR'] | Ship: CI | AVAILABLE | 127 EUR
```

### JavaScript (Node.js / browser)

```javascript
const BASE_URL = 'https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en';

function buildParams({ searchDate, departurePort, arrivalPort,
                       numberOfAdults = 2, childrenAges = [], vehicleCode = 'NONE' }) {
  const payload = { searchDate, departurePort, arrivalPort, numberOfAdults,
                    childrenAges, vehicle: { code: vehicleCode, quantity: 1 }, club: 'NONE' };
  const json = JSON.stringify(payload);
  return typeof btoa !== 'undefined'
    ? btoa(json)
    : Buffer.from(json).toString('base64');  // Node.js
}

async function searchDay(params) {
  const url = `${BASE_URL}/search-ferry/day/${buildParams(params)}`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function searchWeek(params) {
  const url = `${BASE_URL}/search-ferry/week/${buildParams(params)}`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function extractSailings(data) {
  return data.result.dateHits.flatMap(({ date, hits }) =>
    hits.map(hit => {
      const oj = hit.booking.outwardJourney;
      return {
        date,
        departurePort: oj.departurePort,
        arrivalPort: oj.arrivalPort,
        departureTime: oj.departureDate.localDateTime,
        departureTz: oj.departureDate.timeZoneInfo,
        arrivalTime: oj.arrivalDate.localDateTime,
        arrivalTz: oj.arrivalDate.timeZoneInfo,
        ship: oj.ship,
        departureKey: oj.departureKey,
        availability: hit.availability,
        priceEur: hit.price.normalPrice.amount,
        stops: (oj.stops || []).map(s => s.port),
      };
    })
  );
}

// Usage
const result = await searchDay({ searchDate: '2026-06-20', departurePort: 'STO', arrivalPort: 'HEL' });
console.table(extractSailings(result));
```

---

## 8. Recommended Approach

### For published timetable data only (no availability needed)

Scrape the HTML at `/find-trip/timetable/{route}/`. Pages are fully SSR'd, stable, and no JavaScript is required. Yields seasonal departure/arrival times and stop information.

**Limitations:** No real-time availability, no pricing, no ship assignment.

### For live sailing data (recommended)

Call the Protheus API directly. No authentication, no session, open CORS, public caching. This is the correct integration target for any serious integration.

**Recommended calling pattern:**
- Use **day** endpoint for specific-date queries.
- Use **week** endpoint for calendar-view fetches (7× more efficient).
- Poll no more frequently than every 3 minutes per route/date (respects the `max-age=180` cache).
- No headers required beyond `Accept: application/json`.

---

## 9. Risks and Limitations

**Undocumented private API.** The Protheus API has no public documentation, versioning, or SLA. Viking Line could change parameter schemas, add authentication, or move the path without notice. Validate response structure on every call and alert on unexpected shapes.

**VL-CST may become enforced.** Currently not validated server-side for search reads. If it becomes mandatory, it can still be obtained by fetching the SPA page and extracting `window.vlCst` from the rendered HTML (it's injected server-side as a plain script variable).

**Rate limiting unknown.** No rate-limit headers observed, but the `comcs: YES` nginx header may indicate a commercial proxy layer. Stay within the natural 3-minute cache cycle per route.

**Ship codes are undocumented.** The `ship` field returns short codes (`CI`, `GA`, `GR`, `XP`, `AB`). Maintain a lookup table and handle unknown codes gracefully.

**Pricing is passenger-count-dependent.** Keep `numberOfAdults`, `childrenAges`, and `vehicle` constant across price comparisons.

**No multi-leg support per request.** Round trips and connections require separate calls.

---

## 10. Response Headers Reference

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, HEAD
Access-Control-Allow-Headers: origin, content-type, accept, authorization
Access-Control-Allow-Credentials: true
Cache-Control: public, max-age=180
Content-Type: application/json
Server: nginx
comcs: YES
```

---

## 11. Quick Reference

| Endpoint | Method | Auth | Returns |
|----------|--------|------|---------|
| `/protheus-api/v1/ferry/eng/en/search-ferry/day/{base64}` | GET | None | Sailings for one date |
| `/protheus-api/v1/ferry/eng/en/search-ferry/week/{base64}` | GET | None | Sailings for 7-day window |
| `/find-trip/timetable/{route}/` | GET (HTML) | None | Published seasonal schedule |
| `/BookingModuleBlock/ValidateBooking` | POST | Session state | HTML redirect (not useful for data) |

---

*Empirically confirmed against the live production system on 2026-05-19. All API calls were read-only GET requests. No booking transactions were initiated.*
