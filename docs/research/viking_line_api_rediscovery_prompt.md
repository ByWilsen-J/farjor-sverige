# Viking Line API — Återupptäckningsprompt

Använd denna fil om `viking_line_scraper.py` slutar fungera och API:et verkar ha förändrats.
Ge prompten nedan till Claude (eller annan AI-assistent med webbläsartillgång).

---

## Bakgrund

Viking Lines timetable-scraper använder ett internt, odokumenterat JSON-API
som hittades genom att analysera nätverkstrafiken i bokningsflödet.

**Tidigare känd endpoint (kan ha förändrats):**
```
GET https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en/search-ferry/week/{base64-json}
```

**Tidigare känd parameterstruktur (base64-kodad JSON):**
```json
{
  "searchDate": "YYYY-MM-DD",
  "departurePort": "STO",
  "arrivalPort": "HEL",
  "numberOfAdults": 1,
  "childrenAges": [],
  "vehicle": {"code": "NONE", "quantity": 1},
  "club": "NONE"
}
```

**Port-koder:** STO (Stockholm), HEL (Helsingfors), TKU (Åbo), KAP (Kapellskär), MAR (Mariehamn), TAL (Tallinn)

---

## Prompt att ge Claude när API:et slutar fungera

```
Jag har en scraper för Viking Lines tidtabeller som slutat fungera.
Den använde tidigare detta API-anrop:

  GET https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en/search-ferry/week/{base64-json}

där parametern är base64-kodad JSON med fälten searchDate, departurePort, arrivalPort m.fl.

Jag behöver att du hittar det nya sättet att hämta samma data. Gör så här:

1. Gå till https://www.sales.vikingline.com/find-trip/timetable/stockholm-helsinki/
   och kontrollera om sidan fortfarande är statisk server-renderad HTML med tidtabellsdata
   inbäddad direkt. Om ja — scrapa den istället och skippa resten.

2. Om sidan är tom/JS-renderad: Gå till bokningsflödet på
   https://www.sales.vikingline.com/find-trip/
   Välj Stockholm → Helsingfors, ange ett datum ca 2 veckor fram, 1 vuxen, inga fordon.
   Klicka "Sök" / "Search" och observera alla nätverksanrop (XHR/Fetch) som görs.

3. Identifiera det anrop som returnerar JSON med avgångstider, fartygsnamn och
   tillgänglighet. Det ska innehålla fält som departure_time/departureDate, ship/vessel
   och arrival_time/arrivalDate.

4. Dokumentera:
   - Exakt URL (inkl. bas-URL och path)
   - HTTP-metod (GET/POST)
   - Eventuella headers som krävs (auth-token, cookies etc.)
   - Parameterstruktur (query-params, request body, eller path-segment)
   - Responsstruktur med de viktigaste fälten

5. Testa att anropet fungerar utan inloggning och utan session-cookies
   (credentials: omit). Om det kräver auth — beskriv hur token/cookie erhålls.

6. Returnera ett fungerande Python-exempel med requests-biblioteket som hämtar
   avgångar för STO→HEL en vecka framåt och skriver ut datum, avgångstid,
   ankomsttid och fartygsnamn.

Tidigare hittades API:et via React SPA:n på /ferry/eng/en/select-ferry/ som
anropade /protheus-api/v1/. Om den pathen inte längre finns, leta i nätverkstrafiken
efter andra JSON-endpoints med liknande data.
```

---

## Felsökningschecklista

Kontrollera dessa saker innan du kör återupptäckningsprompten:

- [ ] Returnerar API:et HTTP 404 eller 401? → Endpoint/auth har förändrats → kör prompten
- [ ] Returnerar API:et 200 men med tomt `dateHits`-array? → Parameterformat kan ha ändrats
- [ ] Returnerar API:et 200 men saknas `outwardJourney` i svaret? → Responsschema har ändrats
- [ ] Fungerar curl-anropet manuellt? → Problem i scrapern, inte API:et
- [ ] Har `VL-CST` blivit obligatorisk? → Hämta token från `window.vlCst` på sales-sidan

**Manuellt test:**
```bash
PARAMS=$(echo -n '{"searchDate":"'$(date -d "+7 days" +%Y-%m-%d)'","departurePort":"STO","arrivalPort":"HEL","numberOfAdults":1,"childrenAges":[],"vehicle":{"code":"NONE","quantity":1},"club":"NONE"}' | base64 -w0)
curl -s "https://www.sales.vikingline.com/protheus-api/v1/ferry/eng/en/search-ferry/day/${PARAMS}" | python3 -m json.tool | head -50
```

---

*Senast verifierad: 2026-05-19*
*Källa: viking-line-api-technical-report.md*
