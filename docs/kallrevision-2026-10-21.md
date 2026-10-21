# Källrevision 21 oktober 2026

Kontroller utförda 2026-10-21 cirka 22:36–22:46, Europe/Stockholm. Detta är en daterad revisionsanteckning. Den löpande källförteckningen finns i `farjelinjer-kallor.md` och de maskinella länkkontrollerna i `source-link-checks.json`.

## Bekräftade fel och rättningar

| Område | Orsak / tidigare uppgift | Rättning och officiellt belägg |
|---|---|---|
| Polferries Trelleborg → Świnoujście | Parsern förutsatte ensiffrigt sektionsnummer i HTML-id. Sektion 10 i oktober–december tappades bort; januari kunde tolkas som november. | Datum läses nu från sidans uttryckliga månad/år-flik. [Officiell datumtabell, code=st](https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=st), åtta månadstabeller oktober 2026–januari 2027. |
| Polferries Gdańsk ↔ Karlshamn | Endast hårdkodade juli/augusti-datum, trots fortsatt officiell hösttrafik. | Båda riktningarna importeras nu automatiskt som datumtabell. [Officiell datumtabell, code=gh](https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=gh), 154 publicerade avgångar, 77 per riktning. Exempel 21/10: Gdańsk 21:00 → Karlshamn 22/10 10:30, Skania; Karlshamn 18:00 → Gdańsk 22/10 08:00, Copernicus. |
| Polferries Gdańsk ↔ Nynäshamn | Veckoschema utan datumimport. | [Officiell datumtabell, code=gn](https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=gn) importeras automatiskt, 156 publicerade avgångar med Nova Star och Wawel. |
| Polferries fartygsnamn | Koder COP/NS/WAW saknades i nya rutter. Ystad-tabellen har dessutom BUR. | Namn hämtade ur rederiets tabell/legend: Copernicus, Nova Star, Wawel, Bursztyn Unity. Inga tider härledda från fartygsnamn. |
| Polferries tomma datum | En publicerad tabell kan ha tomma dagar eller inställda turer. | Hela validerade månadens täckning följer med importen så gammalt veckoschema inte återskapar turer på tomma dagar. Rubrik, månadslängd, samtliga cellantal och tidsformat valideras innan täckning accepteras; nätfel och trunkerad HTML får aldrig radera befintliga uppgifter. |
| TT-Line Travemünde ↔ Karlshamn | Reservschema var begränsat till 6/7–16/8 och försvann efter sommaren. | Bytt till [TT-Lines officiella standardtidtabell 2026 för Karlshamn](https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026-karcon.pdf): fredag Travemünde 22:20 → Karlshamn lördag 17:30; måndag Karlshamn 07:30 → Travemünde 20:15. Årets giltighet slutar 2026-12-31, inklusive Rostock → Karlshamn. Standardtabellen är rederiets avgångsrekommendation och visas som veckoschema, inte bindande liveuppgift. |
| Wasaline | Vårtidtabell från maj hade fortsatt tillämpats i oktober. | [Officiell tidtabell, uppdaterad 13/10 2026](https://www.wasaline.com/en/timetable/), verifierad för 1/9–8/11, 9/11–18/12, jul/nyår och 1/1–25/3 2027. Periodgränser, juluppehåll 24–25/12 och nyårsdagens undantag är uttryckliga. Bl.a. tisdag Umeå 18:15 → Vasa 23:00 samt oktoberlördag Vasa 09:00/Umeå 17:00 ersätter vårens tider. |
| Sundbusserne Helsingborg ↔ Helsingør | Sista måndag–torsdagsturen 18:30 saknades i båda riktningar. | Den faktiskt lästa [officiella sejlplan-bilden, från 20/3 2026](https://sundbusserne.dk/wp-content/uploads/2026/03/Sejlplan-20260320-50x70-1-pdf.jpg), visar halvtimmestrafik 10:00–18:30 mån–tors, 10:00–20:30 fre–lör och 10:00–17:30 sön. Rättat +8 avgångar per vecka. Pernille/Jeppe-rotationen och cirka 18 min restid stämmer med bilden. |
| Eckerö Linjen | Ankomster i reservschemat var en timme för tidiga åt båda hållen. | [Officiell tidtabell](https://www.eckerolinjen.se/en/timetable): Grisslehamn 10/15/20 → Eckerö 13/18/23; Eckerö 08/13:30/18:30 → Grisslehamn 09/14:30/19:30. Alla tider är lokala; Finland ligger en timme före Sverige. Juluppehåll 24–25/12, inställda morgonturer 1/1 och dockning 7–28/1 är inlagda. |
| Finnlines veckoreserv | Enstaka föråldrade ankomster på Malmö–Travemünde. | [Officiell ruttsida](https://www.finnlines.com/sv/rutter/malmo-travemunde/): Malmö tis/ons/tors 10:00 anländer 19:15; fredag 10:00 anländer 21:00. Travemünde lördag 03:00 anländer Malmö 12:00. Även [Kapellskär–Nådendal](https://www.finnlines.com/sv/rutter/kapellskar-langnas-nadendal/) och [Malmö–Świnoujście](https://www.finnlines.com/sv/rutter/malmo-swinoujscie/) är kontrollerade mot aktuella officiella tabeller. |

## Kontroll av fungerande datainsamling

Avgränsat API-stickprov med faktisk scraper, begärt 21–28 oktober 2026. Vissa officiella källor returnerar ett eget datumfönster; siffrorna är mottagna rader före projektets datumfiltrering och sammanslagning, inte slutligt antal publicerade rader.

| Källa | Mottagna rader / riktningar | Status och observation |
|---|---:|---|
| [DFDS timetable API](https://www.dfds.com/api/timetable) | 71 / 14 | Fungerar med rutt- och datumparametrar. Samtliga registrerade DFDS-riktningar gav data i stickprovet. |
| [Tallink CMS timetable API](https://cms-web-api-nx.tallink.com/api/seaweb/timetables) | 64 / 6 | Fungerar med parametrar; svar sträckte sig till 3/11 trots begäran till 28/10. |
| [Stena Freight LiveView](https://stenalinefreight.com/timetable/) | 181 / 10 | Fungerar, även Nynäshamn–Ventspils i båda riktningar. |
| [Molslinjen officiell katalog](https://new.api.molslinjen.dk/api/v1/ai/markup/data-catalog?language=da&line=2&routeId=SVE7) | 54 / 4 | Fungerar för Bornholmslinjen och Øresundslinjen. Katalogen ger kommande avgångar 21–22/10, inte hela publiceringsfönstret. Tidigare veckoreserv måste därför kunna finnas på andra datum. |
| [Polferries datumtabeller](https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html) | 1 318 / 8 | Alla fyra ruttpar och 32 månadstabeller fungerar efter parserrättningen. Publicerade månadstabeller oktober–januari; sista faktiska tur i stickprovet 11/1. Tomma senare datum får inte fyllas med gissningar. |
| [Finnlines GraphQL](https://dm3xyy44wbeivgqmeymvmw22be.appsync-api.eu-central-1.amazonaws.com/graphql) | 0 / 0 | Blockerat: HTTP 403 `WAFForbiddenException`. Aktuell offentligt laddad bokningsklient använder samma endpoint och klientkonfiguration som scrapern; ingen ändrad endpoint har bekräftats. Verifierad veckoreserv behövs. |

## Länkar och begränsningar

- Vanlig läsning av 22 unika registrerade källadresser gav HTTP 200 för de officiella vanliga webbsidorna och alla fyra kontrollerade TT-Line-PDF:er. Viking Lines två ruttsidor och TT-Lines live-tidtabell gav 403/Cloudflare. Det betyder **åtkomstblockering**, inte bekräftat borttagen sida.
- API:er behöver metod, parametrar och ibland publika klienthuvuden. Ett ensamt GET till API-basadressen är inget giltigt friskhetstest; riktiga scraper-anrop användes ovan.
- Äldre veckounderlag kan innehålla `laevagraafik.ee`. Nätfel där är dokumenterade av länkkontrollen. En källhänvisning ska inte bytas till en ny sida enbart för att den nya länken fungerar; underlagets tider måste då också verifieras. Aktuella exakta DFDS- och Tallink-rader har officiella API-källor.
- Color Line Strömstad–Sandefjord har fortsatt status **endast källänk**, inte tidtabellsimport. [Officiell tidtabellssida](https://www.colorline.se/tidtabeller) svarade 200. Ingen gissad import har lagts till.
- Sundbussernes [fartplan](https://sundbusserne.dk/fartplan/) och den aktuella tidtabellsbilden är nu båda innehållsgranskade 2026-10-21. Samtliga avgångsklockslag och fartygsrotationer jämfördes: 132 avgångar per riktning och vecka efter rättningen. Källbilden anger cirka 18 min restid; ankomst är därför fortsatt en beräkning, inte en separat publicerad exakt ankomsttid.
- Finnlines, Viking Line och TT-Line har kvar begränsningar för maskinell åtkomst. En fungerande reservtabell ska vara märkt som sådan och bör granskas när den officiella sidan eller dess giltighetsperiod ändras.
- Wasaline och Eckerö är här verifierade periodbundna veckounderlag; automatiska datumkällor saknas för dessa två. Wasalines importerade period slutar 25/3 2027 för att inte extrapolera över påskundantag; Eckerö-underlaget slutar 31/3 2027 för ny granskning före senare helgundantag. TT-Lines 2026-reserv extrapoleras inte till 2027.

## Verifiering

- Sex automatiska parserregressioner för Polferries passerade: tvåsiffriga sektioner, oktober/januari, nya rutter/fartyg, giltig tom månad, nätfel/felaktigt format samt trunkerad rad.
- Datumspecifika stickprov för Wasaline och Eckerö bekräftar korrekta lokala tider, periodskiften och tom trafik 24/12 samt Eckerös dockning 7/1.
- Samtliga 31 då tillgängliga projektregressioner passerade 22:43. Den slutliga sammanställda uppdateringens kvalitetsgrind rapporteras separat i projektloggen.
- Maskinellt underlag för API-stickprovet: `source-api-checks-2026-10-21.json`. Löpande kontroller och driftsstatus är separata från denna historiska revisionsfil.

### Slutförd bildkontroll: Sundbusserne

Den officiella sidan länkar vid kontrolltillfället samma bild `Sejlplan-20260320-50x70-1-pdf.jpg`. Bilden laddades och lästes visuellt. Kontroll per riktning: mån–tors 18 avgångar/dag (10:00–18:30), fre–lör 22 (10:00–20:30), sön 16 (10:00–17:30). Helsingborg börjar med Pernille 10:00 och växlar till Jeppe 10:30; Helsingør börjar med Jeppe 10:00 och Pernille 10:30. Alla rader följer denna rotation. Den tidigare jämförelsen som enbart noterade HTTP 200 är härmed kompletterad med faktisk innehållskontroll och ovanstående rättning.
