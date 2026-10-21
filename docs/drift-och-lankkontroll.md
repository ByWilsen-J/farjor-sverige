# Regelbunden felsökning och säkra automatiska uppdateringar

## Körschema

| Jobb | Schema (UTC) | Uppgift |
|---|---|---|
| `update-timetables.yml` | Varje timme, minut 17 | Hämta dynamiska avgångar, bevara säkra reservkällor och granska före publicering. |
| `daily-backfill.yml` | Dagligen 02:35 | Återbygg hela publiceringsfönstret och granska före publicering. |
| `site-health.yml` | Dagligen 05:45 | Kontrollera alla käll-/sidlänkar, den publicerade startsidan och dess data/äldre adress, datafärskhet, rutttäckning, Python/JavaScript och regressioner. Försök återhämta data vid fel. |

GitHub kan senarelägga schemakörningar. 05:45 UTC motsvarar 06:45 svensk vintertid / 07:45 svensk sommartid. Ankardatum och datumgränser räknas i Europe/Stockholm, även före UTC-dygnsskiftet. Månadsskiften använder samma datumfunktion som generatorn och klämmer månadens sista dag korrekt. Alla jobb som skriver data delar samma kö så att timjobbet och backfill inte skriver över varandras filer. Pull requests kör dessutom kontroller utan automatiska reparationer eller push och jämför inte med den ännu ej uppdaterade publicerade webbplatsen.

## Vad uppdateras automatiskt?

- Timjobbet och återhämtningsförsöket använder befintliga officiella importkedjor. Nya tider konstrueras aldrig av länkkontrollen.
- Hämtningen utgår från hela publiceringsfönstret (en månad bakåt, tre framåt). En källa kan publicera en kortare period; då måste verifierad reservdata täcka återstående datum. Inställningen `FERRY_DYNAMIC_FORWARD_DAYS` styr inte längre fönstret.
- En 301/308-redirect kan ersätta en exakt käll-/sidlänk när slutadressen har samma värdnamn/port, HTTPS, oförändrade parametrar och rätt innehållstyp samt har verifierats med ett andra GET-anrop. Generella startsidor, inloggning, fel-/captcha-sidor, API-adresser, signerade/tokenbaserade URL:er och domänbyten ändras inte automatiskt.
- Automatisk länkrättning gäller exakta URL-fält i JSON och citerade URL:er på HTML-sidor. Scraperkod och ruttregistret kräver granskning vid URL-byte; en återkommande gammal URL i registret dokumenteras därför fortfarande i rapporten.
- Bekräftade 404/410 efter två försök utlöser ett nytt datahämtningsförsök men ingen gissad ersättningslänk. Kvarstående fel markeras som misslyckat GitHub-jobb.

## Vad stoppar publicering?

`check_route_coverage.py` kontrollerar aktiva rutter, riktningar, primär-/reservkällor och datumtäckning. `check_site_health.py` stoppar data äldre än 48 timmar, ogiltigt/utgånget publiceringsfönster, avsaknad av kommande data, total scraperförlust, totalt bortfall för en rutt som tidigare haft någon avgång och tapp på mer än hälften av en rutts avgångar jämfört med senast publicerad data för samma kommande 14 dagar (när baslinjen har minst 10 avgångar). Ett sådant tapp kan vara en riktig säsongsändring och kräver då granskning.

Python-syntax, JavaScript-syntax och regressionstester måste också passera. Ett lyckat HTTP-anrop bevisar bara åtkomst; det garanterar inte att en tidtabell är korrekt eller komplett. Detaljer för varje källa finns i `meta.source_refresh` och i körloggen.

## Rapporter och uppföljning

- [farjelinjer-kallor.md](farjelinjer-kallor.md): läsbar sammanställning per sida och rutt med faktisk käll-URL, importkedja, senaste kontrollförsök, HTTP-resultat och slutadress.
- `source-inventory.json`: samma kopplingar i maskinläsbar form.
- `source-link-checks.json`: beständig kontrollhistorik per URL, senaste riktiga försök och senaste lyckade åtkomst. En ny rapportgenerering skapar aldrig en ny länkkontrollstid.
- Varje körning sparar rapporterna som GitHub Actions-artefakt, även om datan stoppas. Daglig kontroll sparar artefakter i 30 dagar; datajobben i 14 dagar.
- `site-health-checks.json` i artefakten visar verkliga försök mot den publicerade startsidan, den äldre adressen och den publicerade JSON-filen. Den publicerade sidans fel blockerar inte en frisk ny kandidat som kan rätta felet; jobbet visar ändå felet tills en senare kontroll har bekräftat driften efter Pages-publicering.

HTTP 401/403/429, TLS-/nätverksfel och API-endpoints som kräver andra metoder/parametrar markeras som begränsad kontroll, inte som trasiga länkar. Blockerade länkar behöver ändå följas upp om läget kvarstår. Kontrollera GitHub Actions för misslyckade jobb och rapportartefakten för detaljer. Inga separata issues, mejl eller externa meddelanden skickas av denna lösning.

Vid ett stopp: granska källans officiella tidtabell och `meta.source_refresh`, rätta import/länk efter verifiering, kör kontrollerna och starta om relevant jobb manuellt. Behåll senast godkänd publicering tills den nya datan passerar.

## Lokal kontroll

```sh
python3 -m unittest discover -s tests
python3 check_route_coverage.py
python3 check_site_health.py
python3 audit_source_links.py
python3 generate_route_source_report.py
```

Länkaudit behöver nätåtkomst och `requests`; JavaScript-kontrollen behöver Node.js. För explicit säker redirect-rättning: `python3 audit_source_links.py --apply-safe-redirects`, följt av samtliga publiceringskontroller.

## Livekällor ska återställas

Stående användarbeslut 2026-10-21: aktuella officiella live-/datumtabeller prioriteras. Reservscheman upprätthåller visningen medan fortsatt felsökning pågår. Tillgänglig webbplats och fungerande livehämtning följs därför upp separat.

Den dagliga kontrollen granskar nu även `meta.source_refresh` med `check_site_health.py --live-sources-only`. Avstängd, oprövad, misslyckad, ofullständig eller över 26 timmar gammal hämtning hålls öppen i `docs/live-source-status.json`. Rapportens bedömningstid förnyar aldrig själva källans senaste kontrolltid. Avstängd hämtning beskrivs som oprövad, inte som bekräftad blockering.

En sådan punkt utlöser ett nytt försök med befintliga importer även när sidan och reservschemana fungerar. Efteråt kontrolleras källorna igen. Godkänd reservdata kan fortfarande publiceras, men den dagliga felsökningen markeras som misslyckad tills liveproblemen har följts upp. GitHubs vanliga inställningar avgör om misslyckade jobb ger en avisering.

Detta återprovar befintlig kod. Det utvecklar inte automatiskt nya anropsmetoder. Fortsatt utredning ska följa AGENTS.md: jämför tidigare fungerande lösningar, aktuella officiella källor och alternativa fungerande importer; dokumentera nästa försök och verifiera resultaten före publicering.
