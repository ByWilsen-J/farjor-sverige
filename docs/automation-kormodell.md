# Körmodell för automation

## Syfte

Detta dokument beskriver hur automationen bör delas upp under ombyggnaden från
veckoschemabaserad rendering till en modell där exakta datuminstanser och
trafikmeddelanden är separata, uppdaterade dataspår.

## Körspår i målbilden

| Spår | Syfte | Frekvens | Bro i nuvarande repo | Målutdata |
| --- | --- | --- | --- | --- |
| Statisk bas | Hålla verifierade veckoscheman, intervall och rutter som fallback uppdaterade | Vid källändring, plus veckovis kontroll | Excel/JSON-kedjan är fortfarande basen | `static_schedule` eller motsvarande fallback-lager |
| Timvis dynamisk uppdatering | Hämta exakta avgångsinstanser, fartyg, ankomstmeta och statuskommentarer från rederiernas dagskällor | Varje timme | Körs nu via `update-timetables.yml` | `avgangsinstanser` med dynamiska uppdateringar |
| Daglig backfill | Fånga sena justeringar och återbygga hela publiceringsfönstret | Dagligen | Körs nu via `daily-backfill.yml` | Fullt fönster `idag - 1 månad` till `idag + 3 månader` |
| Daglig trafikbevakning | Hämta trafikmeddelanden, inställda avgångar och avvikelseinfo | Minst dagligen | Ingen separat workflow eller collector finns ännu | `traffic_notices` eller motsvarande avvikelselager |

## Rekommenderad körmodell

### 1. Statisk bas

- Statisk bas ska vara fallback, inte primär sanning, för rutter med bättre dagskälla.
- Ingen högfrekvent cron behövs; ändringar ska ske när officiell tidtabell ändras.
- En veckovis kontroll räcker för PDF-, Excel- och intervallbaserade rederier.

Rekommenderad kontrolltid i GitHub Actions (UTC): `20 3 * * 1`

## 2. Timvis dynamisk uppdatering

- Dynamiska rederier ska uppdateras varje timme så att `avgangar_datum` och senare
  `date_schedule` hålls aktuella.
- Körningen ska vara den operativa sanningen för rutter där officiell dagskälla finns.
- Veckoschema används bara när en rutt saknar färsk datumkälla eller när källan är nere.

Rekommenderad körning i GitHub Actions (UTC): `17 * * * *`

### Nuvarande repo

- `.github/workflows/update-timetables.yml` körs timvis (`17 * * * *`).
- Jobbet kör `update_fartyg.py` för ett kort dynamiskt fönster (`today` till `today + 14 dagar`).
- Commit sker bara när `farjor_data.json` faktiskt ändras.

## 3. Daglig backfill

- Backfill ska fånga sena rättningar, försenade publiceringar och poster som kommit in efter att
  timkörningen redan passerat.
- På sikt bör backfill också bygga upp ett bakåtfönster på ungefär 1 månad och säkerställa att
  gårdagens avgångar inte tappas bort när datum rensas.

Rekommenderad körning i GitHub Actions (UTC): `35 2 * * *`

### Nuvarande repo

- `.github/workflows/daily-backfill.yml` körs dagligen (`35 2 * * *`).
- Workflowet räknar själv ut publiceringsfönstret `anchor - 1 month` till `anchor + 3 month`
  och kör `update_fartyg.py` för hela det spannet.
- Backfillen återbygger alltså samma fönster som sidan publicerar, inte bara ett litet dagsglapp.

## 4. Daglig trafikbevakning

- Trafikmeddelanden ska hämtas i ett separat spår från tidtabellsuppdateringen.
- Källor kan vara driftmeddelanden, inställda avgångar, statusfält och särskilda trafikbloggar.
- Resultatet ska inte skrivas in i veckoschemafält, utan lagras som egna notices knutna till
  rederi, rutt och vid behov specifik avgång.

Rekommenderad körning i GitHub Actions (UTC): `50 4 * * *`

### Status i nuvarande repo

- Ingen separat collector eller workflow finns ännu för trafikbevakning.
- Därför ska detta spår dokumenteras nu men implementeras först när en egen importkedja finns.

## Rekommenderad workflow-uppdelning

### Nuvarande läge

- `.github/workflows/update-timetables.yml`
  - timvis dynamic refresh
  - kort operativt dynamiskt fönster
- `.github/workflows/daily-backfill.yml`
  - daglig full backfill
  - återbygger hela publiceringsfönstret

### Nästa uppdelning

- `traffic-monitor.yml`
  - daglig
  - hämtar notices och avvikelser
- `static-schedule-audit.yml`
  - veckovis eller manuell
  - verifierar statisk fallback-data

## Övergångsprinciper

- Introducera inte nya täta scheman i produktion förrän idempotens, commitvolym och rate limits
  har verifierats för respektive källa.
- Timvis dynamik och daglig backfill kan nu leva separat, men `traffic-monitor.yml` bör fortfarande
  införas som eget spår i stället för att blandas in i tidtabellskörningarna.
- Separera trafikbevakning från tidtabellsuppdatering så att ett fel i notices-spåret inte stoppar
  import av datuminstanser.
- Dokumentera i commitmeddelanden och workflow-namn om körningen är timvis eller backfill, så att
  Actions-historiken blir läsbar.
