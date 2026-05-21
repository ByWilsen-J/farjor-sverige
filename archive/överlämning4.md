# Överlämning 4 — Nuläge och instruktioner till nästa chat

**Datum:** 2026-05-19
**Mål:** Alla färjetabeller för färjor som ankommer eller lämnar Sverige, automatiskt uppdaterade.  Och helst fullt automatiserat via script, dvs minimalt handpåläggning i GitHub pages. 

---

## Vad vi bestämt i denna session

### Principer
- Arbeta långsamt och metodiskt — inga ändringar utan Janes godkännande
- Visa förslag, låt Jane besluta, utför sedan
- Alltid två separata kolumner i visningstabellerna:(avgångshamn) och (ankomsthamn) — aldrig kombinerad "sträcka"
- Fartygsnamn skall med **på alla rutter där det är möjligt**
- Uppdatering skall ske **automatiskt via schemalagda skriptkörningar**
- Tabellordning = Länk-tidtabell, Rederi, Avgtid, Anktid, AvgHamn AnkHamn, Färjenamn, "ev annat"

### Sidans struktur (beslutad)
**Dagslistan** — tidtabellstabeller  
**Generell info-ruta (sidoruta)** — rutter utan meningsfull tidtabell eller där länk räcker:
- Color Line Strömstad ↔ Sandefjord
- Bornholmslinjen Ystad ↔ Rønne
- Öresundslinjen Helsingborg ↔ Helsingör
- Sundbusserne Helsingborg ↔ Helsingör
- CLdN, Wallenius SOL, Wagenborg Piteå, SCA Logistics (tas bort helt från listan)

### Namnändring
- "DFDS (f.d. Tallink Silja)" → bara **"DFDS"** för Kapellskär ↔ Paldiski

---

## Statuslista — alla rutter

### ✅ KLARA (statisk HTML-scraper eller API — fartygsnamn tillgängliga)

| Rederi | POL | POD | Källa | Fartyg |
|---|---|---|---|---|
| Eckerö Linjen | Grisslehamn | Eckerö | eckerolinjen.se/turlista | M/S Eckerö |
| Wasaline | Umeå | Vasa | wasaline.com/tidtabell/ | Aurora Botnia (accepterat utan per avgång) |
| Viking Line | Stockholm | Helsingfors | Protheus API (sales.vikingline.com) | CI/GA/GR/GL per avgång ✓ |
| Viking Line | Stockholm | Åbo | Protheus API (sales.vikingline.com) | CI/GA/GR/GL per avgång ✓ |

**Färdiga skript:**
- `viking_line_scraper.py` — hämtar STO↔HEL och STO↔TKU via API, fartygsnamn per avgång
- `viking_line_api_rediscovery_prompt.md` — prompt för att hitta nytt API om det slutar fungera



---

## Instruktioner till nästa chat

### Vad du gör härnäst

Uppdatera VikingLine så det även innefattar tarfiken till och från Åland. Lägg även in färjorna Birka Gotland och Cinderella men markera dem i ljusare grå text. Alla VikingLines rader skall länken man klickar på gåtill denna sida: https://www.sales.vikingline.com/find-trip/timetable/traffic-bulletin/

Jane kommer att ge dig **tekniska analysrapporter** (markdown-filer, liknande `viking-line-api-technical-report.md`) för respektive rederi. Så fort du får en fil med ett rederinamn i filnamnet:

1. **Läs filen** och identifiera:
   - API-endpoint (URL, metod, parametrar)
   - Responsstruktur (var finns avgångstid, ankomsttid, fartygsnamn)
   - Autentiseringskrav (om något)
   - Port-koder/rutt-koder

2. **Skapa två filer** (samma mönster som Viking Line):
   - `{rederi}_scraper.py` — Python-skript med fetch-funktion, schemavalidering, fartygslookup och tydliga felmeddelanden
   - `{rederi}_api_rediscovery_prompt.md` — återupptäckningsprompt + felsökningschecklista

3. **Presentera filerna** med `present_files`-verktyget

4. **Fråga Jane** om det är något hon vill justera innan nästa rederi

### Rederier som väntar på rapport (i prioritetsordning enligt Jane)
1. Finnlines
2. Polsca (Polferries & UnityLine) 
3. Tallink Silja
4. TT-Line
5. DFDS
6. Stena Line

### Viktiga designprinciper för alla skript
- Alltid **avg.hamn + ank.hamn som separata fält** (inte kombinerad sträcka)
- Alltid **fartygsnamn** där tillgängligt — lookup-tabell med koder
- **Schemavalidering** — logga tydlig varning om API-svaret ser annorlunda ut
- **Felhantering** — HTTP-fel ska ge läsbar varning med hänvisning till rediscovery-prompten
- Vecko-endpoint föredras framför dag-endpoint (effektivare)
- Skripten ska kunna köras schemalagt (inga interaktiva inputs krävs)
- Se filen lankar.md i projektmappen för instruktioner om vart alla rederiernas radlänkar skall gå.

### Filer att känna till

| Fil | Plats | Roll |
|---|---|---|
| `överlämning3.md` | Weblänksida/ | Bakgrund, pipeline, JSON-struktur |
| `överlämning4.md` | Weblänksida/ | Denna fil — nuläge och instruktioner |
| `farjor_data.json` | Weblänksida/ | Datakälla för webbsidan |
| `viking_line_scraper.py` | Weblänksida/ | Klar scraper för Viking Line |
| `viking_line_api_rediscovery_prompt.md` | Weblänksida/ | Återupptäckningsprompt Viking Line |
| `generera_json.py` | Weblänksida/ | Bygger farjor_data.json från xlsx |
| `normalisera.py` | Weblänksida/ | Bygger v2.xlsx från v1 |

### Startinstruktion för nästa chat
1. Läs `överlämning4.md` (denna fil)
2. Läs `överlämning3.md` för djupare bakgrund vid behov
3. Vänta på att Jane ger dig en analysrapport-fil
4. Bygg scraper + rediscovery-prompt för det rederi som rapporten gäller
5. Repetera för varje rederi, se till att alla färjor som går til eller från Sverige tas med i tabellen.

---

*Nästa steg efter alla scrapers är klara: integrera dem i den schemalagda månadsskillet och koppla ihop med generera_json.py så att farjor_data.json uppdateras automatiskt.*
