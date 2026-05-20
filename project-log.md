## Projektöversikt

GitHub-sida/statisk webbsida för färjetidtabeller till och från Sverige. Huvudfilerna är `index.html`, `farjor.html` och `farjor_data.json`. Fartygsnamn kommer dels från statiska fält i JSON, dels från `fartyg_datum` som uppdateras av `update_fartyg.py`.

## Aktuell status

Pågående men klart förbättrad. Sidan renderar tidtabeller och datumfilter lokalt. Fartygskolumnen hämtar nu serverförberedda fartygsnamn för Tallink Silja, DFDS, Finnlines, Stena Line och TT-Line där API-tiderna matchar schemat. Frontenden visar nu tider i svensk tid, överfartstid i egen kolumn och markerar passerade avgångar visuellt.

## Senaste ändringar

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
- Exakta fartygsnamn för fler rederier bör lösas via schemalagda API-skrapare, inte genom att hårdkoda gissningar i frontenden.
- Tidssträngar normaliseras i frontenden i stället för att skriva om hela `farjor_data.json`, eftersom källdatan blandar klockslag, tidszonstexter och rena varaktigheter.
- POLSCA/Unity Line hanteras tills vidare som nuvarande datakälla tillåter: Unity Line exponeras i UI som egen direktlänk, men avgångarna ligger fortfarande inte som separat rederinamn i JSON.

## Pågående arbete

- Fartygskolumnen är stabilare i UI, men datatäckningen är inte komplett.
- POLSCA-rader använder fortfarande gemensam datakälla utan separat `Unity Line`-etikett per avgång.
- Projektroten innehåller flera rapport- och testfiler som bör sorteras in i `docs/` eller `archive/` vid separat städpass.

## Problem / blockerare

- Vissa rader saknar fortfarande fartygsnamn när API:ets avgångstid avviker från det normaliserade veckoschemat, t.ex. försenade/ändrade avgångar.
- Viking Lines server-side API-anrop ger 403 Forbidden i `update_fartyg.py`. Frontend/anmarkningsfallback ger fortfarande vissa Viking-namn, men API-flödet behöver återupptäckas.
- Unity Line finns inte som eget rederifält i nuvarande JSON-källa, så separat listning kräver källdataändring eller ny importkedja.
- Flera filer i arbetskopian verkar ha namn-/normaliseringsdiffar i git, så större filflyttar bör göras försiktigt.

## Nästa steg

- Återupptäck Viking Lines aktuella API eller lägg till en robust server-side fallback.
- Överväg fuzzy matching/tolerans för avgångstider som ändrats av rederiets live-API men ännu inte finns i veckoschemat.
- Avgör om Unity Line ska brytas ut som eget rederi i datakällan eller fortsätta presenteras via POLSCA-branding + direktlänk.
- Städa projektroten genom att flytta analysrapporter till `docs/` och test-/låsfiler till `archive/`.

## TODO / backlog

- [x] Finnlines-skrapare för fartygsnamn.
- [x] Stena Line Freight-skrapare för fartygsnamn.
- [x] TT-Line-skrapare för fartygsnamn.
- [x] Frontend: svenska tider, överfartskolumn och markering av passerade avgångar.
- [ ] Viking Line API-återupptäckt efter 403 Forbidden.
- [ ] Tidsmatchning med tolerans/fallback för live-ändrade avgångar.
- [ ] Unity Line som eget rederi i JSON/importflöde om användaren vill särskilja det från POLSCA/Polferries.
- [ ] Projektstruktur: skapa/uppdatera `docs/`, `archive/`, `temp/`, `exports/`.
- [ ] Kontrollera GitHub Actions efter att fler skrapare kopplats in.

## Historik

- 2026-05-20: Projektlogg skapad efter felsökning av saknade/felaktiga fartygsnamn i listvyn.
