# Instruktioner til Claude

Dette repository er Mathias' private studiepodcast "Ind ad det ene øre". Brugeren er læge i hoveduddannelse i øre-næse-hals. Et afsnit laves ved at lægge et manuskript i `manuskripter/` og pushe til `main`. Resten sker automatisk i GitHub Actions.

## Lav et afsnit

1. Skriv manuskriptet ud fra den gennemgang, der allerede er lavet i chatten. Tilføj ingen nye fakta, tal eller doser.
2. Gem det som `manuskripter/ÅÅÅÅ-MM-DD-kort-emne.txt` (små bogstaver, bindestreger, ingen æøå i filnavnet).
3. `git add`, `git commit -m "Afsnit: <emne>"`, `git fetch origin main && git rebase origin/main`, `git push origin HEAD:main`.
4. Følg kørslen, til trinnet "Lav afsnit" er i gang: `curl -s "https://api.github.com/repos/den-graedende-klovn/indaddetene-re/actions/runs?per_page=3"` og `.../actions/runs/<id>/jobs`. Logfiler kan ikke hentes herfra.
5. Fortæl brugeren, at afsnittet er på vej, og hvornår det cirka er klar. Beregn tiden ud fra `beregning_pr_lydminut` i `status.json` (cirka 12 minutter pr. lydminut på GitHubs maskiner i oktober 2026, så 5 minutters afsnit tager cirka en time og 10 minutters cirka to timer) plus cirka 3 minutters opstart. Vent kun på hele kørslen, hvis brugeren beder om det. GitHub mailer brugeren, hvis en kørsel fejler.
6. Hvis en kørsel fejler: `git pull` og læs `fejl` i `status.json`.

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
- Længde: 5 minutter, medmindre brugeren angiver andet (fx "podcast 10min"). Længden gælder selve gennemgangen. Quizzen til sidst kommer oveni (se nedenfor). Regn med cirka 130 ord pr. minut inklusive pauser: 5 minutter er cirka 650 ord, 10 minutter cirka 1300 ord. Målt på afsnittet om persisterende postural-perceptuel svimmelhed: 650 ord gav 5 minutter og 21 sekunder.
- Ved længere afsnit uddybes differentialdiagnostik, udredning og faldgruber, ikke indledningen.
- Hvis gennemgangen ikke rækker til den ønskede længde, må stof fra gennemgangens egne kilder bruges, men ingen påstande uden kilde. Rækker det stadig ikke, så gør afsnittet kortere og sig det til brugeren.
- Afsnit over cirka 25 minutter når ikke at blive færdige inden for GitHubs grænse på seks timer. Del dem i to manuskripter (fx "del 1" og "del 2").
- Ingen akronymer eller forkortelser. Skriv alt ud: "computertomografi", "ultralyd", "human papillomavirus".
- Tal skrives med bogstaver: "fireoghalvtreds år", "tre uger". Ingen procenttegn, skråstreger, parenteser, punktopstillinger eller symboler.
- Latinske termer må gerne bruges, men kun når de er nødvendige, og gerne med den danske betegnelse ved siden af.
- Korte sætninger, højst cirka 25 ord. Røst-motoren deler ved punktum.
- Ingen doser i lyden.
- Struktur: åbning med case, kernen (anamnese, fund, udredning, behandling), faldgruber, quiz, kort opsummering.
- Undgå tankestreger.

## Quiz til sidst

Brugeren sætter stor pris på quizzen. Den må ikke tage tid fra resten af afsnittet.

- Quizzen ligger samlet efter faldgruberne og før opsummeringen. Den tæller ikke med i den ønskede længde, men kommer oveni.
- Antal: seks spørgsmål ved 5 minutter, otte ved 10 minutter og derover. Brugeren kan angive et andet antal (fx "podcast 10min 10 spørgsmål"). Højst tolv.
- Bland faktuelle spørgsmål, korte kliniske caser ("en kvinde på syvogtres år med ...") og ræsonnementsspørgsmål (næste skridt, hvad ændrer håndteringen). Spørgsmålene skal dække hele afsnittet, ikke kun slutningen.
- Værten stiller spørgsmålet. Derefter `[pause 5]`, eller `[pause 8]` efter caser og ræsonnementsspørgsmål. Eksperten svarer kort og giver én sætning om hvorfor.
- Hvert spørgsmål med svar er cirka 25 til 40 ord og fylder cirka 20 til 30 sekunder med pausen.
- Spørgsmål og svar må kun bygge på stof, der er gennemgået i afsnittet.

## Teknik

- `motor/lav_afsnit.py` laver det, der mangler. Lokal afprøvning uden netadgang: `python motor/lav_afsnit.py --motor test`. Nulstil bagefter med `git checkout -- . && git clean -fd afsnit`.
- Røst-modellen: `CoRal-project/roest-v3-chatterbox-500m` via `chatterbox-tts==0.1.7`, torch 2.6.0 CPU. Stemmereferencer: `audio_samples/00_mic_*` og `00_nic_*` fra modellens repository.
- Feedet har `itunes:block`, så det ikke optræder i podcastkataloger.
