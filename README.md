## Reiseblogg — vedlikehold og lokal utvikling

Dette repo er en enkel Jekyll-basert reiseblogg. Denne README-en gir en praktisk guide for hvordan du kjører, utvikler og vedlikeholder nettstedet lokalt, hvordan du legger til kart-punkter og hvordan du bygger/deployer siden.

**For hvem:** denne dokumentasjonen er for deg som oppdaterer bloggen ukentlig og vil holde kartdata og innhold konsistent.

**Rask oversikt**
- Kjør lokalt: `bundle exec jekyll serve --config _config.yml,_config_dev.yml`
- Bygg til `_site/` (lokalt): `bundle exec jekyll build --config _config.yml,_config_dev.yml`
- Hurtigskript: [scripts/serve-local.sh](scripts/serve-local.sh) og [scripts/build-local.sh](scripts/build-local.sh)

Forutsetninger
- Ruby (bruk system Ruby eller rbenv/chruby)
- Bundler: `gem install bundler`
- Kjør: `bundle install` i repo-roten for å installere avhengigheter.

Start lokal utvikling
```bash
bundle install
# Start lokal server (dev config fjerner baseurl):
bundle exec jekyll serve --config _config.yml,_config_dev.yml --watch
```
Åpne: http://127.0.0.1:4000/

Hvis port 4000 er opptatt, legg til `--port 4001`.

Legge til innlegg
Opprett en ny Markdown-fil i `_posts/` med riktig dato + frontmatter. Se eksisterende innlegg for format.

Kartdata (`_data/map.yml`)
- Hovedkilden for kart: [_data/map.yml]( _data/map.yml ) (liste over `locations:` og `routes:`).
- Hver `location` har `id`, `label`, `lat`, `lng` og valgfritt `country`.
- Du kan også markere en lokasjon som skjult ved å sette `ghost: true`. Skjulte (`ghost`) lokasjoner blir ikke vist på kartet, men lagres i `_data/map.yml` og telles i statistikken.

Legge til kartpunkter — CLI
- Raskt verktøy: [scripts/add_location.py](scripts/add_location.py)

Bruk:
```bash
# Interaktivt (standard: append til _data/map.yml):
./scripts/add_location.py

# Non-interaktivt: gi by og land som argumenter
./scripts/add_location.py "Oslo" "Norway"

# Kun skriv ut YAML-blokken (ingen endring):
./scripts/add_location.py "Oslo" "Norway" --no-append

# Tving erstatning av eksisterende entry med samme id:
./scripts/add_location.py "Oslo" "Norway" --append --force

# Skriv ut en liste over lagrede lokasjoner (viser ghost-flag):
./scripts/add_location.py --list
```

Interaktivt: når du legger til en hovedlokasjon vil skriptet nå tilby å legge til en rute fra forrige ukes lokasjon til den nye. Hvis du bekrefter ruteleggelsen får du to valgmuligheter:

- Legg til direkte rute: skriptet legger til den nye hovedlokasjonen i `_data/map.yml` og en enkelt `route` fra forrige til ny lokasjon.
- Legg til med mellomstopp (ghosts): skriptet spør om du vil legge til mellomliggende, skjulte byer i rekkefølge. For hver mellomstopp:
  - Du oppgir `City name` og `Country` (skriptet geokoder automatisk eller lar deg skrive koordinater manuelt ved behov).
  - Lokasjonen blir lagt til i `_data/map.yml` med `ghost: true` (ingen markør vises på kartet), og det blir lagt til en egen `route` for segmentet fra forrige punkt til denne mellomstopp.

Etter at du har lagt inn alle mellomstopp, blir hovedlokasjonen lagt til sist og en siste `route` legges fra siste mellomstopp til hovedlokasjonen. Dermed blir rekkefølgen i `locations:` korrekt (a, b, c, d) og rutene blir separate segmenter (a→b, b→c, c→d).

Kort eksempel (interaktivt):
1. Kjør `./scripts/add_location.py` og angi hovedlokasjon `D`.
2. Når du blir spurt "Add a route from last location 'A' to 'D'?" svar `y`.
3. Velg "Legg til med mellomstopp" og skriv inn `B`, `C` i ønsket rekkefølge.
4. For hvert segment velger du transportmodus (f.eks. `Bil` eller `Fly`).
5. Skriptet legger inn `B` og `C` som `ghost: true`, legger inn segmentene `A->B`, `B->C`, `C->D` og beregner/persisterer `distance_km` for hver.

Ghost-lokaliteter vises ikke som markører på kartet, men inngår i rute-sekvensen og i distanseberegninger.

Miljøvariabler
- `NOMINATIM_EMAIL` — anbefalt å sette (f.eks. `export NOMINATIM_EMAIL="you@example.com"`) slik at Nominatim aksepterer forespørslene. Hvis ikke satt bruker skriptet en standard-e-post som er inkludert i `User-Agent`.

Kartvisning og statikk
- Siden [map.md](map.md) laster `site.data.map` og genererer kartet klient-side.
- `ghost: true`-poster filtreres ut av kartvisningen (ingen markører, ingen ruter som inkluderer ghost-endpoints), men beholdes i `_data/map.yml` slik at de inngår i statistikkberegning og arkiv.
- Statistikkpanelet viser `Antall land`, `Antall byer`, `Distanse <modetype>` og `Total distanse`.

Ruteberegning
- For `Bil`-ruter forsøker klienten å hente kjørerute fra OSRM (`router.project-osrm.org`) hvis ruten ikke har precomputede `points`.
- For flyruter tegnes geodesiske great-circle-linjer. Spesialcase: Bergen→Bangkok tegnes via München.
- Anbefaling: precompute kjøreruter med et script og lag `points` + `distance_km` i `_data/map.yml` for stabilitet (kan implementeres senere).

Vedlikeholdstips
- Når du oppdaterer `_data/map.yml` for en uke:
  - Legg til hoved-lokasjon som nytt element i `locations:` (bruk `scripts/add_location.py` for korrekt formatting).
  - Legg til en `route` fra forrige ukes `id` til ny `id` i `routes:` (skriptet kan gjøre dette interaktivt).
  - Hvis du besøkte flere byer samme uke, legg de som `ghost: true` slik at de ikke vises på kartet men er registrert.
- Hold `country`-feltet oppdatert for bedre estimering av antall land.
- Lag regelmessige backups av `_data/map.yml` — skriptet lager en `.bak` ved endringer.

Commit og deploy
```bash
git add _data/map.yml _posts/ assets/ ...
git commit -m "Uke X: legg til [By], ghost: [By2]"
git push
```

For GitHub Pages: bygg med riktig config som inkluderer `baseurl` hvis brukt:
```bash
bundle exec jekyll build --config _config.yml,_config_gh_pages.yml
```

Feilsøking
- Får du 403/429 fra Nominatim: sett `NOMINATIM_EMAIL` og unngå hyppige automatiske spørringer.
- Hvis Jekyll feiler på Liquid: kjør `bundle exec jekyll build --trace` for stacktrace.
- Når kartet ikke viser forventede punkter: sjekk at `_data/map.yml` er gyldig YAML og at `lat`/`lng` er tall.

Videre forbedringer (valgfritt)
- Legg til et script for å precompute OSRM `points` og `distance_km` for `Bil`-ruter.
- Legg til en administrasjons-side (skrudd av for publikum) som viser `ghost`-lokasjoner.
- Normaliser `country` til ISO-koder hvis du trenger konsistente statistikker.

Kontakt / bidrag
- Åpne en issue eller lag en PR hvis du vil at jeg implementerer precomputing eller adminvisning.

-----
Oppdatert: 2026-07-09


