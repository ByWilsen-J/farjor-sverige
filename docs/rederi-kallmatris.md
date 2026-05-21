# Källmatris per rederi

## Syfte

Detta dokument sammanfattar hur information hämtas i dag och vad som bör vara
målbild per rederi i ombyggnaden.

## Matris

| Rederi | Nuvarande tidtabellskälla | Nuvarande uppdatering | Huvudrisk idag | Rekommenderad primär källa | Rekommenderad fallback |
| --- | --- | --- | --- | --- | --- |
| Viking Line | Excel-baserat veckoschema från officiella tidtabellssidor, plus browser-live mot Protheus och trasig server-side-kedja | Schema statiskt, browser-live per besökare, ingen fungerande central datumimport i `avgangar_datum` | Veckoschema dominerar, Viking kan visa fel fartyg eller fel avgångstid när dagsdata avviker | Server-side Protheus dag-/veckokälla materialiserad till datuminstanser varje timme | Veckoschema inom giltig period |
| Tallink Silja | Excel-vecka plus fungerande CMS-API i `tallink_scraper.py` | Datumimport 15 dagar, workflow var 14:e dag | API-data finns men är inte primär visningsmodell | CMS-API till `date_schedule` varje timme | Veckoschema för rutter utan datumdata |
| DFDS | Excel/PDF-vecka plus öppet REST-API i `dfds_scraper.py` | Datumimport 15 dagar, workflow var 14:e dag, viss browser-live för DFDS i frontend | API-data riskerar att blandas med gamla veckotider | REST-API till datuminstanser varje timme | Statisk PDF-baserad schemafallback |
| Finnlines | Excel-baserat schema, GraphQL för `Naantali ↔ Kapellskär` och `Malmö ↔ Travemünde` | Datumimport 15 dagar, workflow var 14:e dag | `Malmö ↔ Świnoujście` saknar motsvarande datumkälla i nuvarande kedja | GraphQL där det finns, separat exakt dagkälla för `Malmö ↔ Świnoujście` om sådan hittas | Verifierat veckoschema |
| Stena Line | Excel-baserat schema från flera officiella sidor, plus WordPress-AJAX i `stena_line_scraper.py` | Datumimport 15 dagar, workflow var 14:e dag | Statusfält och exakta dagsrader används inte fullt ut som primär sanning | Stena Freight AJAX till datuminstanser varje timme | Verifierat veckoschema per rutt |
| TT-Line | Excel-baserat schema plus dagvis HTML-kedja i `ttline_scraper.py` | Datumimport 15 dagar, workflow var 14:e dag | Fler rutter finns i dagskällan än i veckoschemat, men veckoschema lever kvar som bas | TT-Line dagskälla till datuminstanser varje timme | Veckoschema endast för rutter utan dagskälla |
| Polferries / Polsca | Excel-schema för `Ystad ↔ Świnoujście` och `Gdańsk ↔ Nynäshamn`, separat `polsca_datum` för `Świnoujście ↔ Trelleborg` | `polsca_datum` ligger statiskt i JSON över längre period, ingen timvis automation | Delad modell, olika rutter lever i olika dataspår och Unity Line saknas som egen källa | Separata datumkedjor för Polferries och Unity Line, sammanslagna till `Polsca` i normaliseringslagret | Verifierat veckoschema för rutter utan dagkälla |
| Wasaline | Verifierat statiskt schema i Excel/JSON | Manuell/statiskt verifierad | Saknar central automatisk dags- och trafikbevakning | Officiell dagtabell om tillgänglig, annars veckovis verifierad statisk källa | Ingen ytterligare fallback |
| Eckerö Linjen | Verifierat statiskt schema i Excel/JSON | Manuell/statiskt verifierad | Samma som Wasaline | Officiell dagtabell om tillgänglig, annars veckovis verifierad statisk källa | Ingen ytterligare fallback |
| DFDS (tidigare Tallink Silja) | Legacy-schema för `Paldiski ↔ Kapellskär` | Statiskt i schema, medan motsvarande datumdata finns via annan kedja | Dubbla modeller för samma trafik | Låt samma datumkälla som DFDS/Tallink äga rutten | Legacy-schemat avvecklas |
| CLdN / Cobelfret | PDF-/dokumentschema | Statisk kontroll | Risk för gamla dokument och lång ledtid | Veckovis dokumentkontroll | Senast verifierade schema |
| Wagenborg | PDF-/dokumentschema | Statisk kontroll | Samma som CLdN | Veckovis dokumentkontroll | Senast verifierade schema |
| Wallenius SOL | Statiskt schema | Statisk kontroll | Samma som CLdN | Veckovis dokumentkontroll | Senast verifierade schema |
| SCA Logistics | Statiskt schema | Statisk kontroll | Samma som CLdN | Veckovis dokumentkontroll | Senast verifierade schema |
| Bornholmslinjen / Molslinjen | Intervall-/frekvensdata, inte exakta dagsrader | Statisk kontroll | Risk att exakta tider ser mer precisa ut än källan tillåter | Riktig dagkälla om tillgänglig, annars särskild intervallvisning | Ingen exakt klockslagsvisning utan verifierbar källa |
| Color Line | Intervall-/frekvensdata | Statisk kontroll | Samma som Bornholmslinjen | Riktig dagkälla om tillgänglig | Intervallvisning |
| Sundbusserne | Intervall-/frekvensdata | Statisk kontroll | Samma som Bornholmslinjen | Riktig dagkälla om tillgänglig | Intervallvisning |
| Öresundslinjen | Intervall-/frekvensdata | Statisk kontroll | Samma som Bornholmslinjen | Riktig dagkälla om tillgänglig | Intervallvisning |

## Prioritet för ombyggnad

### Högst

- Viking Line
- Tallink Silja
- DFDS
- Finnlines
- Stena Line
- TT-Line
- Polsca

### Därefter

- Wasaline
- Eckerö Linjen
- DFDS (tidigare Tallink Silja)

### Sist

- Övriga rederier med statiska eller intervallbaserade källor

## Kommentar

Rederier med verklig dag-/livekälla ska inte längre visas utifrån veckologik som
bas. Där ska veckoschema bara fungera som reserv när dagskällan är nere eller
saknas för en viss rutt.
