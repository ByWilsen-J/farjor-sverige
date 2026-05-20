## Projektöversikt

GitHub-sida/statisk webbsida för färjetidtabeller till och från Sverige. Huvudfilerna är `index.html`, `farjor.html` och `farjor_data.json`. Fartygsnamn kommer dels från statiska fält i JSON, dels från `fartyg_datum` som uppdateras av `update_fartyg.py`.

## Aktuell status

Pågående men klart förbättrad. Sidan renderar tidtabeller och datumfilter lokalt. Fartygskolumnen hämtar nu serverförberedda fartygsnamn för Tallink Silja, DFDS, Finnlines, Stena Line och TT-Line där API-tiderna matchar schemat.

## Senaste ändringar

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

## Pågående arbete

- Fartygskolumnen är stabilare i UI, men datatäckningen är inte komplett.
- Projektroten innehåller flera rapport- och testfiler som bör sorteras in i `docs/` eller `archive/` vid separat städpass.

## Problem / blockerare

- Vissa rader saknar fortfarande fartygsnamn när API:ets avgångstid avviker från det normaliserade veckoschemat, t.ex. försenade/ändrade avgångar.
- Viking Lines server-side API-anrop ger 403 Forbidden i `update_fartyg.py`. Frontend/anmarkningsfallback ger fortfarande vissa Viking-namn, men API-flödet behöver återupptäckas.
- Flera filer i arbetskopian verkar ha namn-/normaliseringsdiffar i git, så större filflyttar bör göras försiktigt.

## Nästa steg

- Återupptäck Viking Lines aktuella API eller lägg till en robust server-side fallback.
- Överväg fuzzy matching/tolerans för avgångstider som ändrats av rederiets live-API men ännu inte finns i veckoschemat.
- Städa projektroten genom att flytta analysrapporter till `docs/` och test-/låsfiler till `archive/`.

## TODO / backlog

- [x] Finnlines-skrapare för fartygsnamn.
- [x] Stena Line Freight-skrapare för fartygsnamn.
- [x] TT-Line-skrapare för fartygsnamn.
- [ ] Viking Line API-återupptäckt efter 403 Forbidden.
- [ ] Tidsmatchning med tolerans/fallback för live-ändrade avgångar.
- [ ] Projektstruktur: skapa/uppdatera `docs/`, `archive/`, `temp/`, `exports/`.
- [ ] Kontrollera GitHub Actions efter att fler skrapare kopplats in.

## Historik

- 2026-05-20: Projektlogg skapad efter felsökning av saknade/felaktiga fartygsnamn i listvyn.
