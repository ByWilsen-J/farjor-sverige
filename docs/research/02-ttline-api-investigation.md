# TT-Line Timetable & Booking System — Technical Investigation Report

**Date:** 2026-05-19  
**Target:** https://www.ttline.com  
**Scope:** Public network traffic only. No credential attacks, no bypasses.

---

## 1. FINDINGS — System Architecture

### Infrastructure
| Property | Value |
|---|---|
| Web Server | Microsoft-IIS/10.0 |
| Backend Framework | ASP.NET MVC |
| Main site JS | jQuery 1.7.2 + Bootstrap |
| Booking site JS | jQuery 1.10.2 |
| HTTP Client (timetable) | Axios (wrapped as factory function) |
| Rendering mode | Server-side rendered HTML (main site) |
| CDN | CloudFront (d1igp3oop3iho5.cloudfront.net) |
| Bot protection | None detected (no Cloudflare, no Akamai) |
| CSRF protection | ASP.NET `__RequestVerificationToken` anti-forgery pattern |

### Domains
| Domain | Purpose |
|---|---|
| `www.ttline.com` | Main public site — timetable pages, info pages |
| `booking.ttline.com` | Full booking engine (passenger flow) |
| `services.ttline.com` | Login/auth services (PaxLogin, GetZsession) |

### Key JavaScript Chunk Files (main site)
| File | Purpose |
|---|---|
| `/Static/js/ttline.min.js` | Module registry |
| `/Static/js/timetableblock.chnk.js` | Timetable AJAX logic |
| `/Static/js/freightcalculator.chnk.js` | Freight calculator logic |
| `/Static/js/669.chnk.js` | Axios HTTP client dependency |
| `/Static/js/637.chnk.js` | Large vendor bundle |

---

## 2. APIs DISCOVERED

### 2.1 Primary Timetable Endpoint

```
POST https://www.ttline.com/sailing/info/
```

**Purpose:** Returns departure schedule as an HTML table fragment for a given route and date window.

**Required:** Session cookie + CSRF token (both mandatory — see Authentication section).

**Request fields (multipart/form-data):**

| Field | Type | Example | Notes |
|---|---|---|---|
| `route` | string | `TRA;TRE` | 3-letter port code pairs |
| `sdate` | string | `2026-05-25` | ISO date — window starts here |
| `Language` | string | `en` | `en`, `de`, `sv`, `lt`, `pl` |
| `IsHomepageMode` | string | `False` | `True` when called from homepage widget |
| `IsFreightMode` | string | `False` | `True` for freight timetable |
| `ExcludedHarbours` | string | `` | Comma-separated harbour codes to exclude |
| `__RequestVerificationToken` | string | `CfDJ8Nu...` | ASP.NET CSRF token from page HTML |

**Response:** `text/html` — partial `<table>` fragment injected into DOM.

**Response columns:** Departure | Arrival | Ship | Route | Price | Status

**Example decoded response rows:**
```
24 Mai, 1:00  | 24 Mai, 9:15  | NH | Travemünde - Trelleborg | From 252 € | On time | [Book link]
24 Mai, 10:00 | 24 Mai, 19:30 | TS | Travemünde - Trelleborg | From 78 €  | On time | [Book link]
24 Mai, 22:00 | 25 Mai, 7:00  | NH | Travemünde - Trelleborg | From 188 € | On time | [Book link]
```

**Book links embedded in response:**
```
https://booking.ttline.com/passage/en/Step1?lang=en&GoToStep2=false&WayType=1
  &Passengers[0].Count=1&Passengers[0].PAS_Code=P01
  &Vehicles[0].Count=1&Vehicles[0].VEH_Code=VE1
  &route=3&RouteDate=2026-05-24&RouteReturnDate=2026-05-24
```

---

### 2.2 Timetable Printout Endpoint

```
GET https://www.ttline.com/sailing/printout/?{URLSearchParams}
```

**Purpose:** Printable HTML timetable page. Uses same form fields as `/sailing/info/` serialised as query string via `URLSearchParams(FormData)`.

---

### 2.3 Freight Calculator Endpoint

```
POST https://www.ttline.com/freightcalculatoruser/add/
```

**Purpose:** Stores/submits freight calculation request. Same ASP.NET CSRF protection pattern applies.

---

### 2.4 Session Keepalive

```
GET https://www.ttline.com/keepalive
```

**Purpose:** Pings the server to keep the session alive. Called periodically by the timetable block JS.

---

### 2.5 Booking Engine — Step 1

```
POST https://booking.ttline.com/passage/en/Step1
```

**Purpose:** Booking search — submits passenger/vehicle/route config and returns departure listing.

**Request fields (HTML form POST):**

| Field | Example | Notes |
|---|---|---|
| `WayType` | `1` | `1` = one-way, `2` = return |
| `Route` | `3` | Numeric route ID (see table below) |
| `RouteDate` | `2026-05-25` | Outbound departure date |
| `RouteReturn` | `4` | Return route ID (if WayType=2) |
| `RouteReturnDate` | `2026-05-25` | Return date |
| `Passengers[n].Count` | `1` | Number of passengers of type n |
| `Passengers[n].PAS_Code` | `P01` | Passenger type code |
| `Animals[n].Count` | `0` | Number of animals |
| `Animals[n].ANI_Code` | `A001` | Animal type code |
| `Vehicles[n].Count` | `1` | Number of vehicles |
| `Vehicles[n].VEH_Code` | `VE1` | Vehicle type code |

---

## 3. REFERENCE DATA

### 3.1 Route Codes — Timetable Form (`route` field)

| Code | Route |
|---|---|
| `TRA;TRE` | Travemünde → Trelleborg |
| `ROS;TRE` | Rostock → Trelleborg |
| `TRA;KAR` | Travemünde → Karlshamn |
| `TRA;ROS` | Travemünde → Rostock |
| `ROS;TRA` | Rostock → Travemünde |
| `ROS;KLA` | Rostock → Klaipėda |
| `TRA;KLA` | Travemünde → Klaipėda |
| `KLA;TRE` | Klaipėda → Trelleborg |

### 3.2 Numeric Route IDs — Booking Engine (`Route` field)

| ID | Route |
|---|---|
| 1 | Continent → Trelleborg |
| 2 | Trelleborg → Continent |
| 3 | Travemünde → Trelleborg |
| 4 | Trelleborg → Travemünde |
| 5 | Rostock → Trelleborg |
| 6 | Trelleborg → Rostock |
| 7 | Świnoujście → Trelleborg |
| 8 | Trelleborg → Świnoujście |
| 13 | Travemünde → Rostock |
| 14 | Rostock → Travemünde |
| 15 | Klaipėda → Trelleborg |
| 16 | Trelleborg → Klaipėda |
| 17 | Rostock → Klaipėda |
| 18 | Klaipėda → Travemünde |
| 19 | Klaipėda → Rostock |
| 20 | Continent → Klaipėda |
| 21 | Klaipėda → Continent |
| 22 | Travemünde → Klaipėda |
| 24 | Karlshamn → Klaipėda |
| 25 | Klaipėda → Karlshamn |
| 26 | Travemünde → Karlshamn |
| 27 | Karlshamn → Travemünde |
| 28 | Karlshamn → Rostock |
| 29 | Rostock → Karlshamn |
| 30 | Karlshamn → Trelleborg |
| 31 | Trelleborg → Karlshamn |

### 3.3 Passenger Type Codes (PAS_Code)

| Code | Type |
|---|---|
| `P01` | Adult |
| `P13` | Child |
| `P75` | Youth |
| `P76` | Senior |
| `P05` | Infant |

### 3.4 Vehicle Type Codes (VEH_Code)

| Code | Type |
|---|---|
| `VE1` | Car (standard) |
| `VE07` | Motorcycle |
| `VE09` | Bicycle |
| `VE18` | Car + trailer |
| `VE19` | Car + caravan |
| `VE20` | Campervan/motorhome |

### 3.5 Animal Codes (ANI_Code)

| Code | Type |
|---|---|
| `A001` | Small animal |
| `A002` | Large animal |

### 3.6 Vessel Ship Codes (observed in timetable)

| Code | Vessel |
|---|---|
| `TS` | Tom Sawyer |
| `NH` | Nils Holgersson |
| `HF` | Huckleberry Finn |
| `PP` | Peter Pan |
| `MP` | Marco Polo |
| `ND` | Nils Dacke |
| `TB` | Thomas Becket |
| `RH` | Robin Hood |

---

## 4. AUTHENTICATION & SESSION ANALYSIS

### How it works

TT-Line uses ASP.NET's built-in anti-forgery token system, which works as a **double-submit** pattern:

1. **GET** any timetable page (e.g. `https://www.ttline.com/en/timetables/`)
   - Server sets two HttpOnly cookies: a session cookie and an antiforgery cookie
   - Server embeds a matching CSRF token in the HTML form

2. **Extract** the `__RequestVerificationToken` value from:
   ```html
   <input type="hidden" name="__RequestVerificationToken" value="CfDJ8NuG5L6G..." />
   ```

3. **POST** to `/sailing/info/` including:
   - Both HttpOnly cookies (sent automatically by HTTP client if cookies are stored)
   - The `__RequestVerificationToken` as a form field

### Authentication test results (verified empirically)

| Scenario | Result |
|---|---|
| No CSRF token, no cookies | **404** |
| CSRF token, no cookies | **404** |
| Cookies, no CSRF token | **404** |
| CSRF token + cookies | **200 ✓** |

The server returns **404** (not 400/403) for all CSRF failures — an intentional security obscuration. Both the session cookie and the CSRF token are **mandatory**.

### Session lifecycle
- Sessions are initialized on the first GET to the main site
- The keepalive endpoint (`GET /keepalive`) maintains the session
- Cookie expiry is browser-session-scoped (no observed persistent cookie for CSRF)
- A new CSRF token must be fetched each session

---

## 5. EXAMPLE REQUESTS

### 5.1 curl

**Step 1: Initialise session and extract CSRF token**
```bash
# Get the timetable page, save cookies, extract token
curl -c cookies.txt -s "https://www.ttline.com/en/timetables/" \
  -o page.html

# Extract the CSRF token from the HTML
CSRF=$(grep -o 'name="__RequestVerificationToken" value="[^"]*"' page.html \
  | sed 's/.*value="//;s/"//')

echo "CSRF Token: $CSRF"
```

**Step 2: Fetch timetable data**
```bash
curl -b cookies.txt -c cookies.txt \
  -X POST "https://www.ttline.com/sailing/info/" \
  -H "Accept: text/html, */*" \
  -H "User-Agent: Mozilla/5.0 (compatible)" \
  -F "route=TRA;TRE" \
  -F "sdate=2026-05-25" \
  -F "Language=en" \
  -F "IsHomepageMode=False" \
  -F "IsFreightMode=False" \
  -F "ExcludedHarbours=" \
  -F "__RequestVerificationToken=$CSRF"
```

---

### 5.2 Python (requests)

```python
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ttline.com"

def get_timetable(route: str, date: str, language: str = "en") -> list[dict]:
    """
    Fetch TT-Line timetable for a given route and date.

    Args:
        route:    Route code, e.g. "TRA;TRE", "ROS;TRE", "KLA;TRE"
        date:     ISO date string, e.g. "2026-05-25"
        language: Language code: "en", "de", "sv", "lt", "pl"

    Returns:
        List of dicts with keys: departure, arrival, ship, route, price, status
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # Step 1: Initialize session and get CSRF token
    resp = session.get(f"{BASE_URL}/en/timetables/")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token_input:
        raise ValueError("CSRF token not found on page")
    csrf_token = token_input["value"]

    # Step 2: POST to timetable API
    payload = {
        "route": route,
        "sdate": date,
        "Language": language,
        "IsHomepageMode": "False",
        "IsFreightMode": "False",
        "ExcludedHarbours": "",
        "__RequestVerificationToken": csrf_token,
    }
    api_resp = session.post(
        f"{BASE_URL}/sailing/info/",
        data=payload,
        headers={"Accept": "application/json, text/plain, */*"},
    )
    api_resp.raise_for_status()

    # Step 3: Parse HTML table response
    table_soup = BeautifulSoup(api_resp.text, "html.parser")
    rows = table_soup.select("tbody tr")

    sailings = []
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) >= 6:
            sailings.append({
                "departure": cells[0],
                "arrival":   cells[1],
                "ship":      cells[2],
                "route":     cells[3],
                "price":     cells[4],
                "status":    cells[5],
            })
    return sailings


# All available route codes
ROUTES = [
    "TRA;TRE",  # Travemunde -> Trelleborg
    "ROS;TRE",  # Rostock -> Trelleborg
    "TRA;KAR",  # Travemunde -> Karlshamn
    "ROS;KLA",  # Rostock -> Klaipeda
    "KLA;TRE",  # Klaipeda -> Trelleborg
    "TRA;KLA",  # Travemunde -> Klaipeda
    "TRA;ROS",  # Travemunde -> Rostock
    "ROS;TRA",  # Rostock -> Travemunde
]

if __name__ == "__main__":
    for route in ROUTES:
        sailings = get_timetable(route, "2026-05-25")
        print(f"\n=== {route} ===")
        for s in sailings:
            print(f"  {s['departure']} -> {s['arrival']}  [{s['ship']}]  {s['price']}  {s['status']}")
```

---

### 5.3 JavaScript (fetch, server-side / Node.js proxy)

```javascript
const https = require('https');

async function fetchTimetable(route, date, language = 'en') {
  // Step 1: GET timetable page to initialise session + get CSRF token
  const { cookies, html } = await httpGet('https://www.ttline.com/en/timetables/');

  const tokenMatch = html.match(
    /name="__RequestVerificationToken"\s+(?:type="hidden"\s+)?value="([^"]+)"/
  );
  if (!tokenMatch) throw new Error('CSRF token not found');
  const csrfToken = tokenMatch[1];

  // Step 2: POST to timetable API
  const body = new URLSearchParams({
    route,
    sdate: date,
    Language: language,
    IsHomepageMode: 'False',
    IsFreightMode: 'False',
    ExcludedHarbours: '',
    __RequestVerificationToken: csrfToken,
  }).toString();

  const { html: tableHtml } = await httpPost(
    'https://www.ttline.com/sailing/info/',
    body,
    cookies,
    { 'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json, text/plain, */*' }
  );

  // Step 3: Parse rows from HTML table (use cheerio or regex)
  const rows = [];
  const rowRe = /<tr[^>]*>([\s\S]*?)<\/tr>/g;
  const cellRe = /<td[^>]*>([\s\S]*?)<\/td>/g;
  let rowMatch;
  while ((rowMatch = rowRe.exec(tableHtml)) !== null) {
    const cells = [];
    let cellMatch;
    while ((cellMatch = cellRe.exec(rowMatch[1])) !== null) {
      cells.push(cellMatch[1].replace(/<[^>]+>/g, '').trim());
    }
    if (cells.length >= 6) {
      rows.push({
        departure: cells[0], arrival: cells[1], ship: cells[2],
        route: cells[3], price: cells[4], status: cells[5],
      });
    }
  }
  return rows;
}
```

---

## 6. EXAMPLE RESPONSE (Annotated)

Raw HTML fragment returned by `POST /sailing/info/`:

```html
<table>
  <thead>
    <tr>
      <th>Departure</th>
      <th>Arrival</th>
      <th>Ship</th>
      <th>Route</th>
      <th>Price</th>
      <th>Status</th>
      <th aria-hidden="true" class="u-sr-only">table head</th>
      <th aria-hidden="true" class="u-sr-only">table head</th>
    </tr>
  </thead>
  <tbody class="js-timetable-block__tbody">
    <tr class="">
      <td>24 Mai, 1:00</td>
      <td>24 Mai, 9:15</td>
      <td>NH</td>
      <td>Travemunde - Trelleborg</td>
      <td>From 252 EUR</td>
      <td class="c-timetable__status">On time</td>
      <td class="c-timetable__green-ferry"></td>
      <td>
        <a href="https://booking.ttline.com/passage/en/Step1?lang=en
          &GoToStep2=false&WayType=1
          &Passengers[2].Count=1&Passengers[2].PAS_Code=P01
          &Vehicles[0].Count=1&Vehicles[0].VEH_Code=VE1
          &route=3&RouteDate=2026-05-24&RouteReturnDate=2026-05-24">
          Book
        </a>
      </td>
    </tr>
  </tbody>
</table>
```

**Notes on response behaviour:**
- Returns departures for the specified date and surrounding days (typically a 24-48 hour window)
- Empty tbody returned when no sailings exist for that route/date
- Prices are "from" prices (cheapest available cabin/deck class)
- Status values observed: `On time`, `Arrived`, `Delayed`
- Dates in response are locale-formatted (e.g. "24 Mai" in German/Swedish locale) — parse from booking link `RouteDate` param for reliable ISO dates

---

## 7. RECOMMENDED APPROACH

### For a custom timetable frontend

The most practical pattern is a **server-side Python proxy**:

```
Client browser -> Your API server -> TT-Line /sailing/info/
```

Your proxy:
1. Maintains a persistent `requests.Session()` with stored cookies
2. Re-GETs the timetable page when session expires (404 response = expired session)
3. Translates requests from your own clean API into TT-Line's form POST
4. Parses HTML response and returns clean JSON

### Caching strategy

| Data type | Recommended TTL |
|---|---|
| Departure times + prices | 15 minutes |
| Vessel assignments | 1 hour |
| Status (on time / delayed) | 5 minutes |
| Route/code reference data | Indefinite (changes rarely) |

### Robust session handler (Python)

```python
class TTLineClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.csrf_token = None

    def _init_session(self):
        resp = self.session.get("https://www.ttline.com/en/timetables/")
        soup = BeautifulSoup(resp.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})
        self.csrf_token = token["value"] if token else None

    def get_timetable(self, route: str, date: str) -> list[dict]:
        if not self.csrf_token:
            self._init_session()

        resp = self.session.post(
            "https://www.ttline.com/sailing/info/",
            data={
                "route": route, "sdate": date, "Language": "en",
                "IsHomepageMode": "False", "IsFreightMode": "False",
                "ExcludedHarbours": "",
                "__RequestVerificationToken": self.csrf_token,
            }
        )

        if resp.status_code == 404:
            # Session expired — reinitialize and retry once
            self._init_session()
            return self.get_timetable(route, date)

        soup = BeautifulSoup(resp.text, "html.parser")
        return [
            {
                "departure": cells[0], "arrival": cells[1], "ship": cells[2],
                "route": cells[3], "price": cells[4], "status": cells[5],
            }
            for row in soup.select("tbody tr")
            for cells in [[td.get_text(strip=True) for td in row.find_all("td")]]
            if len(cells) >= 6
        ]
```

---

## 8. RISKS & LIMITATIONS

| Risk | Severity | Notes |
|---|---|---|
| No public API / no documented contract | Medium | TT-Line can change endpoints without notice |
| CSRF + session cookie requirement | Medium | Requires session init step; straightforward but not zero-cost |
| HTML response (not JSON) | Low-Medium | Must parse HTML; fragile if template changes |
| No date range batching observed | Low | Window is ~48 hours; must call once per date if you need a week |
| No rate limiting observed | Low | No 429s or throttling detected during testing |
| No anti-bot system detected | Low | No Cloudflare, no CAPTCHA, no fingerprinting |
| Session expiry | Low | Keepalive endpoint exists; standard ASP.NET session lifetime |
| Locale-formatted dates in response | Low | Parse from booking link RouteDate param for ISO dates |

---

## 9. FINAL ASSESSMENT

**Realistically automatable:** Yes. The timetable data is accessible via a well-defined POST endpoint with a standard ASP.NET session/CSRF pattern that is straightforward to implement in any HTTP library.

**Browser automation required:** No. A plain `requests.Session()` in Python is sufficient for all timetable data. Browser automation (Playwright/Selenium) would only be needed for the full booking flow.

**Direct API access viable:** Yes, with the session bootstrapping pattern above.

**API stability:** Moderate. The site runs on a mature IIS/ASP.NET stack with jQuery — not a trendy SPA that gets rebuilt every year. The endpoint URLs are conventional and non-versioned. Expect years of stability but monitor for changes.

**Recommended integration strategy:** Server-side Python proxy with 15-minute cache, session auto-renewal on 404, and clean JSON output to your own frontend. Do not attempt to automate the booking side.
