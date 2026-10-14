# Instruktioner til Claude

Dette repository er Mathias' private studiepodcast "Ind ad det ene øre". Brugeren er læge i hoveduddannelse i øre-næse-hals. Et afsnit laves ved at lægge et manuskript i `manuskripter/` og pushe til `main`. Resten sker automatisk i GitHub Actions.

## Lav et afsnit

1. Skriv manuskriptet ud fra den gennemgang, der allerede er lavet i chatten. Tilføj ingen nye fakta, tal eller doser.
2. Gem det som `manuskripter/ÅÅÅÅ-MM-DD-kort-emne.txt` (små bogstaver, bindestreger, ingen æøå i filnavnet).
3. `git add`, `git commit -m "Afsnit: <emne>"`, `git fetch origin main && git rebase origin/main`, `git push origin HEAD:main`.
4. Følg kørslen: `curl -s https://api.github.com/repos/den-graedende-klovn/indaddetene-re/actions/runs?per_page=3`. Når den er færdig: `git pull` og læs `status.json` (tidsforbrug, fejl).
5. Fortæl brugeren, at afsnittet er på vej, og hvornår det cirka er klar. Røst er langsom på GitHubs maskiner, se `status.json` for seneste tidsforbrug pr. lydminut.

Ret et afsnit: ret manuskriptet og push. Det får et nyt fingeraftryk og laves om.
Fjern et afsnit: slet manuskriptet og push.

## Manuskriptformat

```
titel: Knude på halsen hos voksne
beskrivelse: En til to sætninger, der vises i podcast-appen.
motor: roest
kilder:
- Titel, udgiver eller tidsskrift, årstal, link
---
VÆRT: ...
EKSPERT: ...
[pause 5]
```

- `motor` er valgfri (standard i `indstillinger.json`). Flere motorer adskilles med komma og giver et afsnit pr. motor.
- Roller: `VÆRT` (reservelæge, spørger, opsummerer, stiller lytterspørgsmål) og `EKSPERT` (overlæge, forklarer). Stemmerne er sat i `indstillinger.json`.
- `[pause N]` indsætter N sekunders stilhed, bruges efter lytterspørgsmål.

## Skriv til øret (vigtigt for talesyntesen)

- Dialog, ikke monolog. Værten har cirka en fjerdedel af ordene. Ingen tom snak eller overdreven begejstring.
- Længde: cirka 700 til 800 ord giver cirka 5 minutter.
- Ingen akronymer eller forkortelser. Skriv alt ud: "computertomografi", "ultralyd", "human papillomavirus".
- Tal skrives med bogstaver: "fireoghalvtreds år", "tre uger". Ingen procenttegn, skråstreger, parenteser, punktopstillinger eller symboler.
- Latinske termer må gerne bruges, men kun når de er nødvendige, og gerne med den danske betegnelse ved siden af.
- Korte sætninger, højst cirka 25 ord. Røst-motoren deler ved punktum.
- Ingen doser i lyden.
- Struktur: åbning med case, kernen (anamnese, fund, udredning, behandling), faldgruber, to til tre lytterspørgsmål med `[pause 5]` og svar, kort opsummering.
- Undgå tankestreger.

## Teknik

- `motor/lav_afsnit.py` laver det, der mangler. Lokal afprøvning uden netadgang: `python motor/lav_afsnit.py --motor test`. Nulstil bagefter med `git checkout -- . && git clean -fd afsnit`.
- Røst-modellen: `CoRal-project/roest-v3-chatterbox-500m` via `chatterbox-tts==0.1.7`, torch 2.6.0 CPU. Stemmereferencer: `audio_samples/00_mic_*` og `00_nic_*` fra modellens repository.
- Feedet har `itunes:block`, så det ikke optræder i podcastkataloger.
