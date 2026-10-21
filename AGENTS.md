# Projektets stående arbetsregler

Läs project-log.md först. Uppdatera loggen vid betydande ändringar och bevara tidigare beslut som historik. Håll arbetsfiler organiserade; arkivera ersatt eller osäkert material i archive/ i stället för att radera.

## Prioritera aktuella officiella tidtabeller

Användarbeslut 2026-10-21: Live- och datumtabeller ska användas i största möjliga mån. Blockerade anrop ska aktivt felsökas och alternativa fungerande lösningar eftersträvas även om ett reservschema håller sidan igång.

- Prioritera verifierad aktuell officiell datumkälla framför verifierat veckoschema. Reservscheman är tillfällig driftkontinuitet och avslutar inte arbetet med att återställa en avsedd livekälla.
- Vid bortfall: jämför med senaste fungerande implementation/körning; skilj certifikatfel, serverns nekande, ändrad adress/metod, parserfel och avstängd kod. Dokumentera vad som faktiskt provats, miljö, tid och resultat.
- Undersök officiell webbplats/bokningsklient, offentliga datumtabeller och alternativa normala anropsvägar. Verifiera resultatets tider, datum, fartyg och riktningar innan ny import publiceras.
- Ett avstängt anrop är oprövat i den körningen. Ett 403-svar visar att just anropet nekades; det bevisar inte att alla andra lösningar är uttömda.
- Blockerade eller otillräckligt verifierade livekällor ska stå kvar som öppna, prioriterade felsökningspunkter i projektloggen. Avsluta dem först när en aktuell fungerande hämtning är verifierad, eller när användaren beslutat att permanent använda annat underlag.
- Automatiken kan återprova befintliga importer och rapportera kvarstående problem. Nya anropsmetoder behöver utredas, testas och verifieras; rapportera inte att sådan utveckling sker automatiskt om endast befintliga anrop återprovas.

Dagens prioriterade livearbete: återverifiera Viking Line (API avstängt i senaste fullkörningen), återställ TT-Line (tidigare TLS-lösning räcker inte för nuvarande nekade anrop), återställ Finnlines (WAFForbiddenException).
