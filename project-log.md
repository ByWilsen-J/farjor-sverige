## Projektöversikt

GitHub-sida/statisk webbsida för färjetidtabeller till och från Sverige. Huvudfilerna är `index.html`, `farjor.html` och `farjor_data.json`. Fartygsnamn kommer dels från statiska fält i JSON, dels från `fartyg_datum` som uppdateras av `update_fartyg.py`.

## Aktuell status

Genomförd huvudombyggnad 2026-05-21. `farjor_data.json` bygger nu ett publiceringsfönster på `idag - 1 månad` till `idag + 3 månader` som `avgangsinstanser`, och `index.html` renderar dessa instanser först när de finns. Veckoschema används därmed som fallback-datakälla i backend i stället för som primär renderkälla i frontend.

Sidan behåller den nya högerpanelen, rederifiltret och den gemensamma tabellvyn, men visar nu också källchippar för live-/datumrader. Dynamiska källor kan bära med sig källmeta och statuskommentarer ända fram till info-rutan per avgång. `farjor.html` är fortsatt redirect till startsidan.

Automationen är nu uppdelad i faktisk driftmodell: timvis uppdatering för dynamiska datumkällor och daglig backfill för hela publiceringsfönstret. Kvarvarande större luckor gäller främst separat trafikbevakning från särskilda rederi-sidor, Viking Lines blockerade server-side-källa och full separering av `Polferries`/`Unity Line` under `Polsca`.

Efter innehållsrevisionen 2026-05-21 visar UI:t tydligare skillnad mellan exakt fartyg och verifierad ruttrotation, mer konsekventa källetiketter (`Live`, `Datum`, `Veckoschema`) och renare info-rutor utan generiska `Källa`- eller revisionsrester i tooltip-text.

TT-Lines tidigare fallbackluckor i grundschemat för `Travemünde ↔ Trelleborg`, `Świnoujście ↔ Trelleborg` och `Klaipėda ↔ Trelleborg` är nu kompletterade i själva genereringskedjan, så att rutterna finns i publiceringsfönstret även utanför det dynamiska 14-dagarsfönstret.

Stena Line prioriteras nu konsekvent route-day-first i det dynamiska fönstret: när officiell livekälla finns för en Stena-rutt på ett visst datum rensas motsvarande veckofallback bort från samma datum/rutt i `avgangsinstanser`.

## Senaste ändringar

- 2026-05-21: Tog bort `CLdN / Cobelfret` helt ur publicerad data och dokumentation.
  - Uppdaterade [generera_json.py](/Users/jane/Documents/Claude/Projects/Weblänksida/generera_json.py) så `CLdN / Cobelfret` filtreras bort redan vid JSON-generering från Excel-källan, i stället för att bara döljas i frontend.
  - Synkade [farjor_data.json](/Users/jane/Documents/Claude/Projects/Weblänksida/farjor_data.json) så rederiet, dess `Göteborg ↔ Killingholme`-veckorader, intervallelement och tillhörande datuminstanser inte längre publiceras.
  - Tog bort den nu överflödiga frontend-exkluderingen i [index.html](/Users/jane/Documents/Claude/Projects/Weblänksida/index.html) och rensade `docs/rederi-kallmatris.md` från CLdN-raden.
  - Bekräftade att den enda förekomsten av `Logent Ports Ro-Ro terminal` låg i den gamla CLdN-anmärkningen och därmed försvann samtidigt.
- 2026-05-21: Gjorde Stena-prioritering och UI-normalisering efter användar-QA.
  - Uppdaterade [update_fartyg.py](/Users/jane/Documents/Claude/Projects/Weblänksida/update_fartyg.py) med route-day-pruning så `weekly_schedule` tas bort för samma datum/rutt när `dynamic_schedule` finns, vilket gör Stena-rutterna konsekventa i det dynamiska fönstret.
  - Synkade [farjor_data.json](/Users/jane/Documents/Claude/Projects/Weblänksida/farjor_data.json) mot den nya prioriteringslogiken och verifierade att Stena Line för aktuell dag nu bara visar live-rader för sina live-rutter.
  - Uppdaterade [index.html](/Users/jane/Documents/Claude/Projects/Weblänksida/index.html) så källchipsen inte längre visas i listan, men källtypen ligger kvar sist i info-rutans tooltip.
  - Bytte standardvyn vid första laddning från `Ankomster till Sverige` till `Avgångar mot Sverige`.
  - Kortade riktningsbadges i tabellen till `↓ IN`, `↑ UT` och `Avg→SE` utan att röra valknapparna i högerpanelen.
  - Tog bort prefixet `Rotation:` i fartygskolumnen men behöll tooltip-förklaringen om verifierad ruttrotation.
  - Fixade tidsstämpeln i `Om sidan` så `DATA.meta.uppdaterad` visas i svensk lokal tid i stället för rå UTC, och lade till cache-busting/no-store vid hämtning av `farjor_data.json`.
- 2026-05-21: Lade in verifierad TT-Line-fallback i genereringskedjan.
  - Lade till [verified_schema_overrides.py](/Users/jane/Documents/Claude/Projects/Weblänksida/verified_schema_overrides.py) som ersätter ofullständiga Excel-rader för TT-Line med verifierade officiella standardtidtabeller för `Travemünde ↔ Trelleborg`, `Świnoujście ↔ Trelleborg` och `Klaipėda ↔ Trelleborg`.
  - Uppdaterade [generera_json.py](/Users/jane/Documents/Claude/Projects/Weblänksida/generera_json.py) så att override-lagret alltid appliceras innan `farjor_data.json` och `avgangsinstanser` byggs.
  - Synkade nuvarande [farjor_data.json](/Users/jane/Documents/Claude/Projects/Weblänksida/farjor_data.json) mot override-lagret och bekräftade att TT-Line-rutterna nu materialiseras som `weekly_schedule` även långt utanför det dynamiska fönstret.
  - Normaliserade [index.html](/Users/jane/Documents/Claude/Projects/Weblänksida/index.html) så TT-Lines `Klaipėda`-rader inte får avvikande kategori mot övriga TT-Line-rader i fallback-/extraradslogiken.
- 2026-05-21: Gjorde innehålls- och källtextrevision efter datuminstans-ombyggnaden.
  - Verifierade prioriterade rederier/rutter mot officiella källor med fokus på `Polferries (POLSCA)`, `TT-Line`, `Stena Line`, `Tallink Silja`, `DFDS`, `Finnlines` och `Viking Line`.
  - Uppdaterade [index.html](/Users/jane/Documents/Claude/Projects/Weblänksida/index.html) så fallbackfartyg med flera möjliga fartyg visas som `Rotation: ...` i stället för att se ut som exakt fartyg.
  - Rensade info-tooltipar från generisk revisionsprosa och gamla prefix som `KORRIGERING:` / `STATUSÄNDRING:` / `STRUKTURÄNDRING:`, men bevarade riktiga användarkommentarer.
  - Gjorde datakälltexten i tooltipen råfältsbaserad i stället för badge-baserad, så exakta rader kan visa t.ex. `Live-tidtabell · TT-Line timetable endpoint` även när chippen bara visar `Live`.
  - Förtydligade operatörsraden i tooltipen när UI-visningsnamn skiljer sig från faktisk källa, t.ex. `Polferries (POLSCA)` bakom `Polsca`.
  - Uppdaterade [update_fartyg.py](/Users/jane/Documents/Claude/Projects/Weblänksida/update_fartyg.py) och [farjor_data.json](/Users/jane/Documents/Claude/Projects/Weblänksida/farjor_data.json) så exakta datumrader får komplett källmeta (`kalla`, `source_label`, `source_detail`, `source_type`) och så legacy-fälten speglas från `avgangsinstanser`.
  - Normaliserade flera gamla anmärkningar i [farjor_data.json](/Users/jane/Documents/Claude/Projects/Weblänksida/farjor_data.json), särskilt för `Tallink Silja`, `DFDS (tidigare Tallink Silja)`, `Stena Line`, `Polferries (POLSCA)` och Viking/Birka-rader där äldre text blivit missvisande efter ombyggnaden.
- 2026-05-21: Slutförde första produktionsversionen av den nya datuminstans-modellen.
  - Lade till [schedule_instances.py](/Users/jane/Documents/Claude/Projects/Weblänksida/schedule_instances.py) som materialiserar veckoschema till datuminstanser inom ett fast publiceringsfönster och merge:ar in exakta dags-/liveavgångar.
  - Uppdaterade [generera_json.py](/Users/jane/Documents/Claude/Projects/Weblänksida/generera_json.py) så att `farjor_data.json` alltid innehåller `avgangsinstanser` redan från basgenereringen.
  - Byggde om [update_fartyg.py](/Users/jane/Documents/Claude/Projects/Weblänksida/update_fartyg.py) så att dynamiska källor uppdaterar samma instanslager, bevarar källmeta och inte längre kräver fartygsnamn för att en exakt avgång ska få existera.
  - Rättade fallback-parsern för äldre dynamiska nycklar så att tider som `13:30` inte längre feltolkas som rutttext.
  - Lät scrapers för `DFDS`, `Tallink`, `Finnlines`, `Stena Line`, `TT-Line` och `Viking Line` bära med `kalla`, `source_label`, `source_detail` och i förekommande fall status/kommentar.
  - Uppdaterade [index.html](/Users/jane/Documents/Claude/Projects/Weblänksida/index.html) så att `DATA.avgangsinstanser` är primär kandidatlistekälla och så att live-/datumkällor märks upp i rederikolumn och info-ruta.
  - Delade upp GitHub Actions i timvis uppdatering av dynamiska avgångar och separat daglig backfill via [update-timetables.yml](/Users/jane/Documents/Claude/Projects/Weblänksida/.github/workflows/update-timetables.yml) och [daily-backfill.yml](/Users/jane/Documents/Claude/Projects/Weblänksida/.github/workflows/daily-backfill.yml).
  - Städade projektroten genom att flytta research-rapporter till [docs/research](/Users/jane/Documents/Claude/Projects/Weblänksida/docs/research) och äldre backup-/överlämningsfiler till [archive](/Users/jane/Documents/Claude/Projects/Weblänksida/archive).
- 2026-05-21: Förberedde automation- och dokumentationsspåret för den nya körmodellen.
  - Lade till `docs/automation-kormodell.md` med fyra tydliga körspår: `statisk bas`, `timvis dynamisk uppdatering`, `daglig backfill` och `daglig trafikbevakning`.
  - Länkade `docs/ombyggnadsarkitektur.md` till den nya körmodellen så målarkitektur och driftupplägg hänger ihop.
  - Uppdaterade `.github/workflows/update-timetables.yml` med tydligare namn, `concurrency` och manuella bridge-lägen för `dynamic_refresh` respektive `daily_backfill`, utan att ändra nuvarande schemalagda 14-dagarskörning.
- 2026-05-21: Gjorde en full nulägeskartläggning av tidtabellskedjan inför planerat omtag av logiken.
  - Bekräftade att `farjor_data.json` genereras från Excel-arken `Schemaregister` och `Schemaregister_Intervall` via `generera_json.py`, alltså med veckoschema/intervall som grundkälla.
  - Bekräftade att `update_fartyg.py` bara uppdaterar `fartyg_datum` och `avgangar_datum` för 15 dagar framåt och att GitHub Actions i dag bara kör detta var 14:e dag.
  - Bekräftade att frontend i `index.html` fortfarande bygger kandidatlistan från `DATA.schema` för alla datum och först därefter lägger på `polsca_datum`, `avgangar_datum` och `fartyg_datum` med högre prioritet.
  - Hittade att renderingsnyckeln inkluderar exakt avgångstid, vilket innebär att en live-/datumrad med justerad tid inte säkert ersätter veckoraden utan kan visas parallellt med den.
  - Bekräftade att `DATA.intervall` i praktiken inte används i nuvarande rendering och att trafikinformation/avvikelsemeddelanden ännu inte hämtas in maskinellt.
  - Kartlade källor per rederi: server-side datumimport finns för `Tallink Silja`, `DFDS`, `Finnlines`, `Stena Line` och `TT-Line`; `Viking Line` saknas just nu i `avgangar_datum`; `Polsca` använder separat `polsca_datum`; `Wasaline`, `Eckerö Linjen` och flera mindre rederier är fortsatt statiska.
- 2026-05-20: Lade till generell schemadedupering i `index.html`.
  - Gick igenom dubblettmönster systematiskt i `schema`, `avgangar_datum` och `polsca_datum`.
  - Datumimporterna visade inga motsvarande när-dubbletter; problemet låg i veckoschemat.
  - Lade därför in en kandidatfiltrering som tar bort uppenbara schemadubletter innan rendering:
    exakta kopior med samma rutt/tid samt nästan-identiska schemaavgångar inom 15 minuter med samma rutt och ankomsttid.
  - Det fångar bl.a. POLSCA `Świnoujście → Ystad` `22:45/22:55` och dubbla Viking-rader `Stockholm ↔ Mariehamn` utan att röra datumrader eller live-import.
- 2026-05-20: Filtrerade bort felaktig Viking-specialtid i `index.html`.
  - Hittade att en avvikande Viking Line-rad för `Helsingfors → Stockholm` låg kvar som om den vore normal veckotrafik, vilket skapade en extra inkommande 10:00-rad i majvyn.
  - Lade till datumstyrd filtrering för den avvikande Viking-tiden så den bara visas inom sitt marsintervall i stället för året runt.
  - Resultatet är att den extra tredje 10:00-ankomsten från Helsingfors försvinner, medan Tallinks verifierade 10:00-rad lämnas kvar.
  - Lade också till Viking-fallback i fartygskolumnen så `Viking Cinderella / Gabriella` visas när live-/datumdata saknas, i stället för tomt streck.
- 2026-05-20: Rättade riktningstolkning i `index.html` efter regressionsfel i tabellrader.
  - Flyttade beslut om `passerad`-status och vilken tidskolumn som ska vara visuellt primär från ruttbygget till den faktiska radlabeln (`Inkommande`, `Utgående`, `Mot Sverige`).
  - Det gör att samma resa nu kan visas korrekt i olika vyer utan att återanvända fel status eller fel fetmarkerad tid från en annan riktning.
  - `Inkommande` använder nu alltid ankomsttid som primär/aktuell tid, `Utgående` avgångstid och `Mot Sverige` avgångstid, samtidigt som `Mot Sverige` fortsatt kräver att både avgång och ankomst har passerat för att räknas som inaktuell.
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

- `CLdN / Cobelfret` ska inte längre publiceras alls i webbplatsens data eller dokumenterade källmatris. Motiveringen är att användarbehovet nu är att helt ta bort rederiet och dess terminalreferenser, inte bara dölja det i UI:t.
- Nästa större omtag bör bygga på avgångsinstanser per datum, inte på att veckoschemat alltid renderas först. Motiveringen är att exakt dagsdata då kan vara systemets sanning i stället för ett overlay-lager.
- Live-/datumkällor ska prioriteras per rutt och rederi i en uttrycklig källhierarki. Motiveringen är att undvika dagens blandning där vissa rader kommer från veckoschema, andra från exakta datum och andra från browsercache utan gemensam regelmotor.
- Browser-side livehämtning ska inte vara primär uppdateringsmekanism för produktionsdata. Motiveringen är att GitHub-sidan annars saknar gemensam, automatiskt uppdaterad källa och olika besökare kan se olika resultat.
- Trafikinformation ska behandlas som egen datakälla separat från tidtabell. Motiveringen är att avvikelser, inställda avgångar och kommentarer per avgång inte passar som fri text i dagens statiska anmärkningar.
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

- Slutlig visuell QA av den nya instansrenderingen i riktig browser när lokal browser-runtime finns tillgänglig igen.
- Nästa utbyggnad av trafikinformationsspåret så att separata rederisidor kan generera explicita `traffic_notices`, inte bara kommentarer från livekällornas statusfält.
- Separat källa för `Unity Line`/`Polferries` så att `Polsca` kan vara rent visningsnamn och inte lookup-nyckel.
- Viking Lines server-side-källa behöver fortfarande återvalideras eftersom den i tidigare drift gav 403 och i denna miljö inte kunde nätverkstestas alls.

## Problem / blockerare

- Dedikerade collectors för rederiernas separata trafikinformationssidor finns ännu inte. Nuvarande version kan bära status/kommentar från de livekällor som redan innehåller sådan information, men inte bevaka alla externa trafikbloggar/bulletinsidor.
- `Viking Line` kan fortfarande inte verifieras fullt server-side i den här miljön eftersom alla nätanrop är blockerade lokalt och den tidigare produktionsobservationen var `403 Forbidden`.
- Lokal headless-browserautomation kunde inte återanvändas fullt i denna session eftersom Playwright saknar installerad browser-binary i miljön. Innehållsrevisionen verifierades därför via officiella webbkällor, JSON-audit, funktionsprov av tooltip-normalisering och tidigare lokal preview.
- `polsca_datum` är en separat specialkedja med egen period (`2026-05-01` till `2026-11-30`) och innehåller bara `Świnoujście ↔ Trelleborg`, medan `Ystad ↔ Świnoujście` och `Gdańsk ↔ Nynäshamn` fortfarande ligger i statiskt schema.
- `intervall`-datan i JSON är i praktiken oanvänd i rendering och hjälper därför inte dagens tidtabellsvisning trots att den finns i datalagret.
- Veckoschemat innehåller fortfarande vissa manuellt inlagda undantag och parallella varianter. Frontenden deduperar nu de uppenbara fallen, men datalagret kan fortfarande behöva en separat städning senare.
- Vissa schemaundantag ligger fortfarande som veckorader med anmärkning i datalagret. Den här omgången säkrade Viking-specialtiden, men fler undantag kan på sikt behöva samma typ av datumstyrning.
- Unity Line finns inte som egen datumkälla i nuvarande JSON, så full separering eller exakt avgångsimport kräver ny importkedja.
- Exakt dagsdata kan fortfarande saknas för vissa enskilda datum i slutet av det deklarerade dynamiska fönstret även när route-day-prioritering finns på plats. Då återstår veckofallback tills källfönster eller scraper-horisont justeras.
- Officiellt bekräftade rutter saknas fortfarande helt eller delvis i själva veckoschemat `farjor_data.json`, även om flera nu kompletteras via datuminstanser:
  - Unity Line/POLSCA `Świnoujście ↔ Trelleborg` utanför nuvarande datumperiod
  - Eventuell framtida POLSCA `Gdańsk ↔ Karlshamn` när den faktiskt öppnar

## Nästa steg

- Kör en ny full browser-QA när lokal browser-runtime fungerar igen och kontrollera särskilt tooltipar, rotationsfartyg och källchippar i `In & Ut`-vyn.
- Lägg till separat `traffic_notices`-collector per rederi där officiella trafikmeddelandesidor finns.
- Bygg ut `source_registry` från dokumenterad matris till körbar konfiguration om kommande skript ska styras route-för-route.
- Planera dubbel bevakning för `Polsca` där både `Polferries` och `Unity Line` bevakas separat och sammanfogas först före visning.
- Bygg eller hitta en riktig importkälla för Unity Line/POLSCA-datum så `Świnoujście ↔ Ystad` och `Świnoujście ↔ Trelleborg` inte behöver förlita sig på blandade schema-/fallbackkällor.
- Lägg till officiellt verifierade men saknade rutter direkt i veckoschemat `farjor_data.json` eller i framtida statisk fallbackgenerering, med prioritet:
  - TT-Line kompletta Sverigekopplade riktningar och Klaipėda-/Trelleborg-rutter
  - Finnlines `Malmö ↔ Świnoujście` i framtida genereringskedja, inte bara manuellt i JSON
- Återupptäck Viking Lines aktuella API eller lägg till en robust server-side fallback.
- Överväg att slå ihop eller avveckla legacy-fälten `fartyg_datum` och `avgangar_datum` när full parity mot `avgangsinstanser` är verifierad.

## TODO / backlog

- [x] Besluta och dokumentera ny källhierarki per rederi/rutt: `live datumkälla` -> `statisk datumtabell` -> `veckoschema` -> `ingen visning`.
- [x] Bygg om datamodellen så att avgångar lagras som datuminstanser och inte primärt som veckomönster.
- [ ] Inför separat datalager för trafikinformation/avvikelser per rederi och avgång.
- [x] Begränsa synliga/importerade datum till 3 månader framåt och 1 månad bakåt.
- [x] Byt uppdateringsschema från var 14:e dag till timvis för dynamiska källor.
- [ ] Inför daglig bevakning av trafikinformationssidor där sådana finns.
- [x] Inför tydlig UI-märkning för avgångar som kommer från live-/datumkälla.
- [ ] Kartlägg och bygg dubbel bevakning för `Polsca` (`Polferries` + `Unity Line`) innan sammanslagning i UI.
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
- [x] Lägg till saknade TT-Line-riktningar/rutter i datalagret med verifierad tidtabell för `Travemünde ↔ Trelleborg`, `Świnoujście ↔ Trelleborg` och `Klaipėda ↔ Trelleborg`.
- [x] Projektstruktur: skapa/uppdatera `docs/`, `archive/`, `temp/`, `exports/`.
- [ ] Kontrollera GitHub Actions efter att fler skrapare kopplats in.

## Historik

- 2026-05-21 21:39 CEST: Stena route-day-prioritering infördes i dynamiska fönstret, listans källchips togs bort, standardvyn byttes till `Mot Sverige`, badge-texterna kortades, `Rotation:` togs bort ur fartygskolumnen och `Data:`-tidsstämpeln började visas i svensk tid med cache-busting på JSON-hämtningen.
- 2026-05-21 21:13 CEST: TT-Line-fallbacken flyttades upp i genereringskedjan med verifierade officiella standardtidtabeller för `Travemünde ↔ Trelleborg`, `Świnoujście ↔ Trelleborg` och `Klaipėda ↔ Trelleborg`, och aktuell `farjor_data.json` synkades mot den nya override-modellen.
- 2026-05-21 20:45 CEST: Innehållsrevision efter datuminstans-ombyggnaden genomförd; fartygsfallbacks och källtooltipar normaliserades, exakta datumrader fick komplett källmeta och flera gamla verifieringstexter/anmärkningar städades.
- 2026-05-21 10:56 CEST: Ny datuminstans-baserad version kopplades ihop end-to-end med timvis dynamic refresh, daglig backfill, källmärkning i UI och städad projektstruktur.
- 2026-05-21 10:46 CEST: Dokumentation för ny körmodell lades till i `docs/` och befintligt Actions-workflow kompletterades med manuella bridge-lägen för dynamisk refresh och backfill.
- 2026-05-21 10:30 CEST: Full nulägeskartläggning av tidtabellskedjan genomförd inför planerat omtag av logiken kring live-/datumkällor, veckoschema och trafikinformation.
- 2026-05-20 18:22 CEST: Generell dedupering av veckoschema infördes efter genomgång av flera liknande dublettfall.
- 2026-05-20 18:12 CEST: Viking-specialtid för Helsingfors → Stockholm begränsades till rätt datumintervall.
- 2026-05-20 18:07 CEST: Regressionsfix för label-baserad tidslogik dokumenterad i projektloggen.
- 2026-05-20 16:29 CEST: UI-justering för riktningstider och användarpanel dokumenterad i projektloggen.
- 2026-05-20: Projektlogg skapad efter felsökning av saknade/felaktiga fartygsnamn i listvyn.
