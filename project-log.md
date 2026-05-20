## Projektöversikt

GitHub-sida/statisk webbsida för färjetidtabeller till och från Sverige. Huvudfilerna är `index.html`, `farjor.html` och `farjor_data.json`. Fartygsnamn kommer dels från statiska fält i JSON, dels från `fartyg_datum` som uppdateras av `update_fartyg.py`.

## Aktuell status

Pågående men klart förbättrad. Sidan renderar nu en renare tabellvy där alla valbara kontroller ligger i högerpanelen, med rederifilter, rederiöversikt och färgkodade rederinamn. `index.html` och `farjor.html` är åter synkade. Stena Line `Göteborg ↔ Frederikshavn` finns nu i `farjor_data.json` och ska visas i tidtabellen. Fartygskolumnen hämtar serverförberedda fartygsnamn där möjligt och visar tydlig rotationsfallback när exakt tur-fartyg saknas.

## Senaste ändringar

- 2026-05-20: Lade in Stena Line `Göteborg ↔ Frederikshavn` i datalagret.
  - Hämtade officiella veckotider från Stena Line Freight route `GOFR` och skrev in rutten i `farjor_data.json`.
  - Lade till `Frederikshavn` i hamnlistan och `FRH` som UI-kod.
  - Lade till Stena-fallback för `Göteborg ↔ Frederikshavn` som `Stena Danica / Stena Jutlandica`.
  - Uppdaterade `stena_line_scraper.py` så `GOFR` följer med i framtida fartygsuppslag och normaliserar `Stena Danica` / `Stena Jutlandica`.
- 2026-05-20: Gjorde om UI-strukturen i `index.html` och `farjor.html`.
  - Flyttade dagflikar, datumväljare, visningslägen, Excel-export och nytt rederifilter till högerpanelen.
  - Toppfältet visar nu bara aktuell listas datum och veckodag.
  - Lade till rederiöversikt i sidpanelen som grupperar normaliserade rederier med deduplicerade fartyg och ruttpar.
  - Lade till färgkodning per rederi i tabellen för snabbare scanning.
  - Förkortade hamnrubriker till `Avg.hamn` / `Ank.hamn`, lade in smal separator-kolumn och uppdaterade hamnkoder:
    `GRI`, `TKU`, `KAR`, `VAS`, `GHE`, `KAA`.
  - Tog bort texten `Tidpunkt passerad`; passerade avgångar markeras nu endast visuellt med grå rad/text.
  - Tog bort `ca` från visade avgångs- och ankomsttider samt från exporterad tidsvisning.
  - Lade till rederifilter som samverkar med vyerna `alla`, `mot Sverige`, `ankomster till Sverige` och `från Sverige`, samt påverkar radantal och Excel-filnamn/export.
  - Normaliserar nu `Polferries (POLSCA)`, `Polferries`, `POLSCA` och `Unity Line` till ett UI-namn: `Polsca`.
  - Lade till `routeFleetFallback(...)` för ruttrotationer när `getFar(...)` inte hittar exakt fartyg, bl.a. för Stena, Viking, Finnlines och Polsca.
- 2026-05-20: Gick igenom ruttäckning mot officiella källor.
  - POLSCA officiellt: `Świnoujście–Ystad`, `Świnoujście–Trelleborg` och `Gdańsk–Nynäshamn` är aktiva; `Gdańsk–Karlshamn` anges som under operativ förberedelse med planerad start slutet av Q2 2026.
  - Unity Line officiellt: trafikerar `Świnoujście–Ystad` och `Świnoujście–Trelleborg`; nuvarande JSON saknar separat Unity-källa men UI:t visar dessa under `Polsca` där de finns i data/fallback.
  - Stena officiellt: `Göteborg–Frederikshavn` finns som route på Stena Line Freight, men saknas fortfarande i `farjor_data.json`.
  - TT-Line officiellt: ruttnätet omfattar fler Sverigekopplade rutter än nuvarande schema visar, bl.a. båda riktningar för `Travemünde–Trelleborg` och `Świnoujście–Trelleborg`, samt `Klaipėda–Karlshamn`; dessa saknas helt eller delvis i nuvarande JSON.
- 2026-05-20: Förbättrade tabell-UI och tidsnormalisering i `index.html` och `farjor.html`.
  - Lade till kolumn för total överfartstid och normaliserar ankomsttider till riktiga klockslag även när källdatan bara anger varaktighet, t.ex. DFDS `+27h`.
  - Tar bort `+1`, `(SE)`, `(FI)` och `nästa dag` från själva tidraden och visar i stället veckodag under tiden.
  - Konverterar visade tider till svensk tid i frontenden för både avgång och ankomst.
  - Markerar passerade avgångar med grå rad + texten `Tidpunkt passerad`.
  - Förkortar hamnar till koder i tabellen, t.ex. `TRE`, `TRA`, `GOT`.
  - Gör aktiv sorteringskolumn fet och övriga kolumnrubriker normala.
  - Rättade POLSCA/Unity-relaterade fartygskoder så `GAL` visas som `Galileusz` och `EPS` som `Epsilon`.
  - Lade till separat Unity Line-länk i sidomenyn och uppdaterade texten i `Om sidan`.
  - Fixade trasig HTML-länk i MarineTraffic-raden för Trelleborg/Ystad.
- 2026-05-20: Fixade fartygslogiken i `index.html` och `farjor.html`.
  - Slutade tolka verifieringstexter som `Verifierat mot finnlines` och `Verifierat via rostocktrelleborg` som fartygsnamn.
  - Plockar ut kända faktiska fartygsnamn ur anmärkningar, t.ex. `Viking Glory`, `Viking Cinderella` och Stenas Gdynia-Karlskrona-rotation.
  - Fixade datumbyte så live-uppslag hämtas om när användaren byter datum via datumfält.
  - Fixade ankomstdagens veckodag och dubbel `+1` i ankomsttider.
  - Lade till DFDS Göteborg-rutter i live-/backend-uppslag.
- 2026-05-20: Uppdaterade `dfds_scraper.py` med DFDS-rutterna Immingham-Göteborg och Ghent-Göteborg.
- 2026-05-20: Lade till `finnlines_scraper.py`, `stena_line_scraper.py` och `ttline_scraper.py`.
  - Kopplade in alla tre i `update_fartyg.py`.
  - Anpassade Finnlines till aktuellt GraphQL-schema (`SailingsQuery` + union-fragment).
  - Parser för Stena Line Freight läser WordPress-AJAX och normaliserar fartygsnamn.
  - Parser för TT-Line hanterar CSRF-token, cookies, HTML-tabell och `abbr title` för fullständiga fartygsnamn.
  - Körning 2026-05-20 fyllde `farjor_data.json` med 713 fartygsuppslag över 15 datum.
  - Fixade lokal datumformatering i frontend (`dStr`) så `fartyg_datum` inte slår en dag fel vid datumväljare.

## Beslut och motiveringar

- Fartygsnamn ska bara visas när datan faktiskt ser ut som fartygsdata. Verifierings-/källtext ska ligga kvar i info-tooltip, inte i fartygskolumnen.
- För rader där bara en rotationslista finns i källdatan visas rotationslistan, eftersom exakt avgångsfartyg saknas i nuvarande JSON.
- `Polferries`, `POLSCA` och `Unity Line` visas gemensamt som `Polsca` i UI för att matcha nuvarande användarbehov och den sammanslagna POLSCA-brandingen från 2026-03-30.
- Unity Line bryts inte ut som separat tabellrederi förrän vi har en faktisk egen importkedja eller datumkälla. Att bara länka till Unity Line räcker inte för tabellbehovet.
- Ruttluckor som bekräftas på officiella rederisidor dokumenteras i loggen först och läggs in i JSON först när vi har verifierbar tidtabell/importväg, för att undvika att gissa avgångstider.
- Exakta fartygsnamn för fler rederier bör lösas via schemalagda API-skrapare, inte genom att hårdkoda gissningar i frontenden.
- Tidssträngar normaliseras i frontenden i stället för att skriva om hela `farjor_data.json`, eftersom källdatan blandar klockslag, tidszonstexter och rena varaktigheter.
- POLSCA/Unity Line hanteras tills vidare som nuvarande datakälla tillåter: UI:t visar ett enhetligt rederinamn `Polsca`, men Unity Lines avgångar ligger fortfarande inte som egen källa i JSON.

## Pågående arbete

- Fartygskolumnen är stabilare i UI, men datatäckningen är inte komplett.
- Rederiöversikten och rederifiltret fungerar i UI, men bygger fortfarande på nuvarande JSON + fallback snarare än fullständig route-import för alla rederier.
- POLSCA-rader använder fortfarande gemensam datakälla utan separat Unity-import.
- Projektroten innehåller flera rapport- och testfiler som bör sorteras in i `docs/` eller `archive/` vid separat städpass.

## Problem / blockerare

- Vissa rader saknar fortfarande fartygsnamn när API:ets avgångstid avviker från det normaliserade veckoschemat, t.ex. försenade/ändrade avgångar.
- Viking Lines server-side API-anrop ger 403 Forbidden i `update_fartyg.py`. Frontend/anmarkningsfallback ger fortfarande vissa Viking-namn, men API-flödet behöver återupptäckas.
- Unity Line finns inte som egen datumkälla i nuvarande JSON, så full separering eller exakt avgångsimport kräver ny importkedja.
- Officiellt bekräftade rutter saknas fortfarande i `farjor_data.json`, särskilt:
  - TT-Line `Travemünde → Trelleborg`, `Świnoujście → Trelleborg` och `Klaipėda ↔ Karlshamn` i veckoschemat
  - Eventuell framtida POLSCA `Gdańsk ↔ Karlshamn` när den faktiskt öppnar
- Flera filer i arbetskopian verkar ha namn-/normaliseringsdiffar i git, så större filflyttar bör göras försiktigt.

## Nästa steg

- Bygg eller hitta en riktig importkälla för Unity Line/POLSCA-datum så `Świnoujście ↔ Ystad` och `Świnoujście ↔ Trelleborg` inte behöver förlita sig på blandade schema-/fallbackkällor.
- Lägg till officiellt verifierade men saknade rutter i `farjor_data.json`, med prioritet:
  - TT-Line kompletta Sverigekopplade riktningar och Karlshamn-rutter
- Återupptäck Viking Lines aktuella API eller lägg till en robust server-side fallback.
- Överväg fuzzy matching/tolerans för avgångstider som ändrats av rederiets live-API men ännu inte finns i veckoschemat.
- Städa projektroten genom att flytta analysrapporter till `docs/` och test-/låsfiler till `archive/`.

## TODO / backlog

- [x] Finnlines-skrapare för fartygsnamn.
- [x] Stena Line Freight-skrapare för fartygsnamn.
- [x] TT-Line-skrapare för fartygsnamn.
- [x] Frontend: svenska tider, överfartskolumn och markering av passerade avgångar.
- [x] Frontend: högerpanel med dagflikar/datum/export/vylägen/rederifilter samt rederiöversikt.
- [x] Frontend: Polsca-normalisering i UI och ruttbaserade fartygsfallbacks.
- [ ] Viking Line API-återupptäckt efter 403 Forbidden.
- [ ] Tidsmatchning med tolerans/fallback för live-ändrade avgångar.
- [ ] Unity Line / POLSCA som egen datumimport i JSON, inte bara UI-normalisering.
- [x] Lägg till Stena Line `Göteborg ↔ Frederikshavn` i datalagret med verifierad tidtabell.
- [ ] Lägg till saknade TT-Line-riktningar/rutter i datalagret med verifierad tidtabell.
- [ ] Projektstruktur: skapa/uppdatera `docs/`, `archive/`, `temp/`, `exports/`.
- [ ] Kontrollera GitHub Actions efter att fler skrapare kopplats in.

## Historik

- 2026-05-20: Projektlogg skapad efter felsökning av saknade/felaktiga fartygsnamn i listvyn.
