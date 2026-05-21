# Ombyggnadsarkitektur för färjetidtabeller

## Syfte

Detta dokument beskriver målarkitekturen för ombyggnaden av tidtabellssystemet.
Målet är att sidan ska visa så aktuell och korrekt information som möjligt utan
gissningar, med tydlig källprioritering, automatisk uppdatering och separat
bevakning av trafikinformation.

## Implementerat läge 2026-05-21

- `farjor_data.json` innehåller nu `avgangsinstanser` för hela publiceringsfönstret
  `idag - 1 månad` till `idag + 3 månader`.
- `index.html` renderar `avgangsinstanser` först och använder veckoschema som fallback
  via backend-materialisering i stället för som primär frontendkälla.
- Timvis dynamisk uppdatering och daglig backfill är uppdelade i egna workflows.
- Dynamiska källor kan bära källmärkning och statuskommentarer hela vägen fram till
  info-rutan per avgång.
- Kvarvarande större gap gäller separat collector för externa trafikmeddelandesidor,
  Viking Lines blockerade server-side-källa och full separering av `Polferries`/`Unity Line`.

## Problem i nuvarande modell

- Veckoschema är fortfarande primär modell och renderas först i frontend.
- Exakta datumrader läggs ovanpå i efterhand i stället för att vara källsanning.
- Små tidsskillnader mellan veckodata och dagsdata kan skapa dubbla rader.
- Uppdatering av dynamiska källor sker för sällan för att räknas som aktuell.
- Trafikmeddelanden och avvikelser hämtas inte som egen datakälla.
- Browser-side livehämtning ger inte ett enhetligt serverförberett resultat.

## Målprinciper

- Exakta datumkällor vinner alltid över veckoschema när de finns.
- Veckoschema används bara som fallback för rutter utan bättre källa.
- All datainhämtning ska vara automatisk och reproducerbar.
- Varje avgång ska kunna spåras till källa, uppdateringstid och källtyp.
- Trafikinformation ska kunna knytas till rederi, rutt och vid behov specifik avgång.
- All visning ska begränsas till 1 månad bakåt och 3 månader framåt.

## Föreslagen datamodell

### 1. `source_registry`

Regelverk per rederi och rutt:

- primär källa
- fallback-källa
- källtyp: `live`, `date_table`, `weekly_schedule`, `static_interval`
- uppdateringsfrekvens
- om trafikinformationskälla finns
- om rederiet ska slås ihop under annat visningsnamn i UI

### 2. `static_schedule`

Basdata för rutter där ingen bättre datumkälla finns.

- rederi
- rutt
- veckomönster eller intervalltext
- källa
- giltighetsperiod

### 3. `date_schedule`

Primär operativ datamodell för visning.

- service_id
- display_operator
- source_operator
- route_id
- departure_port
- arrival_port
- departure_date
- departure_time
- arrival_date
- arrival_time
- vessel
- source_type
- source_url
- fetched_at
- confidence

### 4. `traffic_notices`

Separat lager för avvikelser och kommentarer.

- notice_id
- operator
- display_operator
- route_id
- severity
- title
- message
- valid_from
- valid_to
- source_url
- fetched_at
- affected_departures

## Föreslagen källhierarki

1. Live-/dagkälla från rederiet
2. Officiell statisk dagtabell med exakta datum
3. Veckoschema som fallback
4. Ingen rad alls om ingen verifierbar källa finns

## Uppdateringsmodell

För konkret workflow-uppdelning, bridge-läge och rekommenderade cron-tider, se
`automation-kormodell.md`.

### Dynamiska tidtabeller

- körs varje timme
- bygger `date_schedule`
- behåller 1 månad bakåt
- materialiserar högst 3 månader framåt

### Trafikinformation

- körs minst en gång per dygn
- körs separat från tidtabellshämtning
- skapar kommentarsunderlag för info-rutan

### Statiska tabeller

- verifieras veckovis
- uppdateras bara när källan ändras

## UI-principer

- Rader från live-/datumkälla märks upp tydligt.
- Rader från fallback/veckoschema märks upp mindre starkt.
- Trafikändringar visas i info-rutan som kommentar för berörd avgång.
- Ett sammanslaget visningsnamn får inte dölja att flera källor hämtas i bakgrunden.

## Särskilt om Polsca

- `display_operator` ska vara `Polsca`.
- `source_operator` ska kunna vara `Polferries` eller `Unity Line`.
- Tidtabeller och trafikmeddelanden ska hämtas separat per källa.
- Sammanfogning sker först i normaliseringslagret före visning.

## Föreslagna genomförandefaser

### Fas 1

- dokumentera källhierarki per rederi
- skapa ny målstruktur för datafiler
- besluta vilka rutter som ska vara datuminstans-baserade direkt

### Fas 2

- bygga ny generering av `date_schedule`
- bygga ny normalisering för `source_registry`
- ändra frontend att rendera datuminstanser först

### Fas 3

- lägga till `traffic_notices`
- märka upp livekällor i UI
- lägga till dubbel bevakning för Polsca

### Fas 4

- städa bort gammal veckologik som inte längre behövs
- flytta kvarvarande statik till tydliga fallback-spår
- förenkla frontendens specialfall
