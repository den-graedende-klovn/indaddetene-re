# Ind ad det ene øre

Otorhinolaryngologisk AI-genereret podcastserie: korte dialoger om øre-næse-hals-emner til togturen.

**Feed til podcast-appen:** https://den-graedende-klovn.github.io/indaddetene-re/feed.xml

## Sådan virker det

1. Claude lægger et manuskript i `manuskripter/`.
2. GitHub Actions (`.github/workflows/lav-afsnit.yml`) laver lyden med den valgte talemotor og opdaterer `feed.xml`.
3. GitHub Pages udgiver feed og lydfiler, og podcast-appen henter nye afsnit.

| Mappe eller fil | Indhold |
|---|---|
| `manuskripter/` | Et manuskript pr. afsnit. Slet filen for at fjerne afsnittet. Ret filen for at lave afsnittet om. |
| `afsnit/` | De færdige MP3-filer (laves automatisk). |
| `motor/` | Koden. |
| `indstillinger.json` | Titel, stemmer, pauser og indstillinger for talemotorerne. |
| `status.json` | Resultat af seneste kørsel, inklusive tidsforbrug og fejl. |

## Talemotorer

- `roest`: Røst v3 fra CoRal-projektet (dansk, open source), kører på processoren. Stemmerne Mic og Nic.
- `edge`: Microsofts danske neurale stemmer via edge-tts. Hurtig, gratis, uofficiel adgang.
- `test`: Toner i stedet for tale, kun til afprøvning.
