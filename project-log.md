## Projektöversikt

GitHub-sida/statisk webbsida för färjetidtabeller till och från Sverige. Huvudfilerna är `index.html`, `farjor.html` och `farjor_data.json`. Fartygsnamn kommer dels från statiska fält i JSON, dels från `fartyg_datum` som uppdateras av `update_fartyg.py`.

## Aktuell status

Pågående men klart förbättrad. Sidan renderar nu en renare tabellvy där alla valbara kontroller ligger i högerpanelen, med rederifilter, rederiöversikt och färgkodade rederinamn. `index.html` är huvudvyn och `farjor.html` är nu en redirect till startsidan. Standardvyn är nu `Ankomster till Sverige` för dagens datum, och `Alla ankomster / avgångar` visas i en enda gemensam tabell utan separat pax-/fraktuppdelning. Fartygskolumnen hämtar serverförberedda fartygsnamn där möjligt och visar nu bredare ruttfallback även när exakt tur-fartyg saknas.

Senaste UI-iteration: tabellen visar nu irrelevanta tidskolumner i ljusgrått per riktning (`Inkommande`, `Utgående`, `Mot Sverige`) i stället för att tona ned hela raden. Högerpanelen har samtidigt gjorts om till ett tydligare block- och chipbaserat kontrollkort för datum, rederi, listtyp, aktualitet och export.

## Senaste ändringar

- 2026-05-20: Justerade riktningstider och byggde om användarpanelen i `index.html`.
  - `Inkommande`: avgångstiden tonas nu ned i ljusgrått eftersom svensk ankomst är den relevanta händelsen.
  - `Utgående`: ankomsttiden tonas nu ned i ljusgrått eftersom svensk avgång är den relevanta händelsen.
  - `Mot Sverige`: ankomsttiden tonas ned i ljusgrått i UI, men raden räknas som passerad först när både avgångstid och ankomsttid/-datum har passerat.
  - Tog bort generell nedtoning av hela passerade rader och flyttade i stället passerad-markeringen till den tidskolumn som faktiskt är operativt relevant.
  - Gjorde om högerpanelen till en mer kompakt blocklayout med tydligare sektioner, pillknappar för listtyp och större knappar för `Hela dygnet` respektive `Endast aktuella`.
- 2026-05-20: Förbättrade TT-Line-fartygslogiken i `index.html`.
  - TT-Line använder nu same-day-matchning med tolerans mot `avgangar_datum` på exakt samma rutt när dagsvyn och veckoschemat skiljer sig något i avgångstid.
  - Det gör att aktuellt fartyg från TT-Lines dagsvy kan användas i fler rader i stället för att falla tillbaka till stora rotationslistor.
  - När exakt eller tolerant dagsmatchning ändå saknas visas TT-Lines fallback som kompakta fartygskoder, t.ex. `HF`, `ND`, `PP`, i stället för långa namnlistor.
  - Synkade också TT-Lines `TB`-kod mellan frontend och scraper så att både nuvarande och äldre värden komprimeras till samma kortformat.
- 2026-05-20: Rättade passerad-logik och lade till kommandefilter i `index.html`.
  - Inkommande rader markeras nu som passerade först när svensk ankomsttid har passerat, inte när utländsk avgångstid har passerat.
  - Utgående rader markeras fortsatt utifrån svensk avgångstid, så samma regel används konsekvent i blandad vy och i respektive riktning.
  - Lade till två knappar i sidpanelen: `Visa bara kommande` och `Visa alla`, så färdiga turer kan döljas utan att ändra datum eller rederifilter.
- 2026-05-20: Teknisk QA och datumlogik-fix i `index.html`.
  - Rättade `passerad`-logiken så att tidigare avgångar bedöms mot radens faktiska avgångsdatum, inte bara valt visningsdatum.
  - Rättade ankomstdatum för exakt importerade datumrader så att nattankomster grupperas på verkligt ankomstdygn även när källmetadatan anger samma datum som avgången.
  - Lade till defensiv felhantering i Excel-exporten så sidan inte kraschar om `XLSX`-biblioteket från CDN inte har laddats.
- 2026-05-20: Gjorde om visningslogiken, standardvyn och ruttkomplettering i `index.html`, `farjor.html` och `farjor_data.json`.
  - Tog bort dagfliksknapparna helt och införde i stället en tydlig knappstyrd tillämpning av datum/listval/rederifilter i sidpanelen.
  - Sidan startar nu i `Ankomster till Sverige` för dagens datum.
  - `Alla ankomster / avgångar` ligger nu i en enda tabell och sorteras efter svensk hamnhändelse, dvs ankomsttid till svensk hamn respektive avgångstid från svensk hamn.
  - `Ankomster till Sverige` bygger nu på ankomstdatum till svensk hamn, inklusive turer som avgått föregående dygn.
  - Flyttade kolumnen `Överfart` till efter `Fartyg` och högerställde `Avg.hamn`.
  - List-/sektionstitlar visar nu också valt datum och veckodag direkt i rubriken.
  - Lade till bredare dynamiska ruttfallbacks från `fartyg_datum` så att färjenamnskolumnen fylls även när exakta avgångstider inte matchar veckoschemat.
  - Lät datumrader från `fartyg_datum` komplettera saknade/underrapporterade TT-Line- och DFDS-rutter till/från Sverige i UI:t.
  - Lade in Finnlines `Malmö ↔ Świnoujście` i `farjor_data.json` med officiella tider från Finnlines ruttsida.
  - Verifierade att Unity Line-/POLSCA-trafiken `Świnoujście ↔ Trelleborg` kommer med i kandidatunderlaget via datumdatan och nu syns i logiken för ankomster/avgångar.
- 2026-05-20: Tog bort gråmarkeringen av passerade turer i `index.html` och `farjor.html`.
  - Passerade turer markeras inte längre visuellt, eftersom markeringen blev missvisande när man bytte lista eller datum.
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

- Visuell nedtoning ska ske på den irrelevanta tidskolumnen, inte på hela raden. Det gör att operatören fortfarande direkt ser den tidpunkt som är viktig för respektive listtyp.
- `Mot Sverige` ska fortsätta ses som aktuell tills både avgång och ankomst har passerat. Motiveringen är att färjan fortfarande är operativt relevant efter avgång så länge den ännu inte nått Sverige.
- `Alla ankomster / avgångar` ska vara en enda kronologisk tabell, inte delas upp efter färjetyp. Användarbehovet är att se svenska hamnhändelser i tidsordning oavsett om turen är pax, RoRo eller frakt.
- Datum, listval och rederifilter ska inte auto-uppdatera vid varje klick/ändring. De ska först väljas och sedan tillämpas med en knapp för att ge förutsägbar styrning.
- För `Ankomster till Sverige` måste urvalet baseras på ankomstdatum i svensk hamn, inte bara avgångsdatum från utrikeshamn. Därför tittar frontend nu bakåt flera dygn i källdatat.
- När officiella eller semiofficiella datumrader redan finns i `fartyg_datum` används de som komplement för att få in rutter som saknas eller är underrepresenterade i veckoschemat.
- Fartygsnamn ska bara visas när datan faktiskt ser ut som fartygsdata. Verifierings-/källtext ska ligga kvar i info-tooltip, inte i fartygskolumnen.
- För rader där bara en rotationslista finns i källdatan visas rotationslistan, eftersom exakt avgångsfartyg saknas i nuvarande JSON.
- `Polferries`, `POLSCA` och `Unity Line` visas gemensamt som `Polsca` i UI för att matcha nuvarande användarbehov och den sammanslagna POLSCA-brandingen från 2026-03-30.
- Unity Line bryts inte ut som separat tabellrederi förrän vi har en faktisk egen importkedja eller datumkälla. Att bara länka till Unity Line räcker inte för tabellbehovet.
- Ruttluckor som bekräftas på officiella rederisidor dokumenteras i loggen först och läggs in i JSON först när vi har verifierbar tidtabell/importväg, för att undvika att gissa avgångstider.
- Exakta fartygsnamn för fler rederier bör lösas via schemalagda API-skrapare, inte genom att hårdkoda gissningar i frontenden.
- Tidssträngar normaliseras i frontenden i stället för att skriva om hela `farjor_data.json`, eftersom källdatan blandar klockslag, tidszonstexter och rena varaktigheter.
- POLSCA/Unity Line hanteras tills vidare som nuvarande datakälla tillåter: UI:t visar ett enhetligt rederinamn `Polsca`, men Unity Lines avgångar ligger fortfarande inte som egen källa i JSON.

## Pågående arbete

- Fartygskolumnen är stabilare i UI, men datatäckningen är inte komplett för alla rutter utan serverförberedd dagsdata.
- Rederiöversikten och rederifiltret fungerar i UI, men bygger fortfarande på nuvarande JSON + fallback snarare än fullständig route-import för alla rederier.
- Den nya paneldesignen är införd i kod men bör gärna visuell-QA:as i riktig browser igen när lokal förhandsvisning är tillgänglig i miljön.
- POLSCA-rader använder fortfarande gemensam datakälla utan separat Unity-import.
- Projektroten innehåller flera rapport- och testfiler som bör sorteras in i `docs/` eller `archive/` vid separat städpass.

## Problem / blockerare

- Vissa rader saknar fortfarande fartygsnamn när API:ets avgångstid avviker från det normaliserade veckoschemat, t.ex. försenade/ändrade avgångar.
- Viking Lines server-side API-anrop ger 403 Forbidden i `update_fartyg.py`. Frontend/anmarkningsfallback ger fortfarande vissa Viking-namn, men API-flödet behöver återupptäckas.
- Unity Line finns inte som egen datumkälla i nuvarande JSON, så full separering eller exakt avgångsimport kräver ny importkedja.
- Officiellt bekräftade rutter saknas fortfarande helt eller delvis i själva veckoschemat `farjor_data.json`, även om flera nu kompletteras i UI från datumdata:
  - TT-Line `Travemünde → Trelleborg`, `Świnoujście → Trelleborg` och delar av `Klaipėda ↔ Trelleborg`
  - Unity Line/POLSCA `Świnoujście ↔ Trelleborg` utanför nuvarande datumperiod
  - Eventuell framtida POLSCA `Gdańsk ↔ Karlshamn` när den faktiskt öppnar
- Flera filer i arbetskopian verkar ha namn-/normaliseringsdiffar i git, så större filflyttar bör göras försiktigt.

## Nästa steg

- Kör visuell browser-QA av den nya panelen och de kolumnspecifika tidsgråtoningarna för att finjustera spacing/kontrast vid behov.
- Bygg eller hitta en riktig importkälla för Unity Line/POLSCA-datum så `Świnoujście ↔ Ystad` och `Świnoujście ↔ Trelleborg` inte behöver förlita sig på blandade schema-/fallbackkällor.
- Lägg till officiellt verifierade men saknade rutter direkt i veckoschemat `farjor_data.json`, med prioritet:
  - TT-Line kompletta Sverigekopplade riktningar och Klaipėda-/Trelleborg-rutter
  - Finnlines `Malmö ↔ Świnoujście` i framtida genereringskedja, inte bara manuellt i JSON
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
- [x] Frontend: en enda gemensam tabell för `Alla ankomster / avgångar`.
- [x] Frontend: knappstyrd tillämpning av datum/listval/rederifilter.
- [x] Frontend: `Ankomster till Sverige` baseras på verkligt ankomstdatum till svensk hamn.
- [x] Lägg till Finnlines `Malmö ↔ Świnoujście` i datalagret.
- [ ] Lägg till saknade TT-Line-riktningar/rutter i datalagret med verifierad tidtabell.
- [ ] Projektstruktur: skapa/uppdatera `docs/`, `archive/`, `temp/`, `exports/`.
- [ ] Kontrollera GitHub Actions efter att fler skrapare kopplats in.

## Historik

- 2026-05-20 16:29 CEST: UI-justering för riktningstider och användarpanel dokumenterad i projektloggen.
- 2026-05-20: Projektlogg skapad efter felsökning av saknade/felaktiga fartygsnamn i listvyn.
