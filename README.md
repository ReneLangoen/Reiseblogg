# Thea og Renés reiseblogg

Kildekode for [theaogrene.no](https://theaogrene.no) — en statisk reiseblogg bygget med
[Jekyll](https://jekyllrb.com/), med ukentlige innlegg, et interaktivt kart over ruten og et
bildegalleri. Publiseres via GitHub Pages på egendefinert domene (se `CNAME`).

## Kom i gang lokalt

Krever Ruby og Bundler (`gem install bundler`).

```bash
bundle install
./scripts/serve-local.sh   # http://127.0.0.1:4000, med live reload
```

Kun bygging, uten server:

```bash
./scripts/build-local.sh   # bygger til _site/
```

Begge kjører med `_config_dev.yml` i tillegg til `_config.yml`, som fjerner `baseurl` lokalt.

## Struktur

```
_posts/         Ukentlige innlegg (Markdown + frontmatter)
_data/map.yml   Lokasjoner og ruter som driver kartsiden
_includes/      Delte HTML-fragmenter (header, footer)
_layouts/       Sidemaler
assets/         CSS/JS og delte bilder
pictures/       Bilder til innlegg, én mappe per uke (week-1, week-2, ...)
scripts/        Vedlikeholdsverktøy for innhold/kartdata (ikke del av nettstedet)
_private/       Lokale, ikke-versjonerte data og skript (holdes utenfor git og bygget)
```

`scripts/` og `cache/` er lagt til i `exclude:` i `_config.yml` og havner derfor aldri i
`_site/` eller på det publiserte nettstedet.

## Legge til et nytt ukesinnlegg

1. Opprett `_posts/YYYY-MM-DD-uke_N_sted.md` etter mønsteret i eksisterende innlegg.
2. Legg bilder i `pictures/week-N/` og referer til dem som `/pictures/week-N/bilde.jpg`.
3. Legg til lokasjon og rute i `_data/map.yml`, se under.

## Kartdata (`_data/map.yml`)

`map.md` leser `site.data.map` og tegner kartet klient-side.

- `locations`: `id`, `label`, `lat`, `lng`, valgfritt `country`. `ghost: true` registrerer et
  sted i statistikken uten å vise det som markør på kartet.
- `routes`: `from`/`to` (location-id), `mode` (`Fly`, `Bil`, `Tog`, ...) og `distance_km`.

Legg til lokasjoner/ruter med riktig format via:

```bash
./scripts/add_location.py "Oslo" "Norway"   # geokoder automatisk og legger til
./scripts/add_location.py --list            # list lagrede lokasjoner
```

Skriptet spør interaktivt om en rute fra forrige lokasjon, inkludert mellomstopp
(`ghost`-lokasjoner). Sett gjerne `NOMINATIM_EMAIL` i miljøet før bruk, slik at
geokodingsoppslag mot OpenStreetMap Nominatim identifiserer seg riktig.

`scripts/compute_route_distances.py` fyller inn manglende `distance_km` på eksisterende
ruter. `scripts/compute_train_distance.py` estimerer togavstand via OSM-jernbanedata
(krever `osmnx`).

## Nyhetsbrev

Påmeldingsskjemaet i footeren sender til en ekstern endpoint. Synkronisering mot
abonnentlisten er et lokalt verktøy som ikke er en del av dette repoet — se
`_private/README.md`.

## Feilsøking

- Ugyldig `_data/map.yml`: sjekk at `lat`/`lng` er tall og at YAML-strukturen er gyldig.
- 403/429 fra Nominatim: sett `NOMINATIM_EMAIL` og unngå hyppige forespørsler.
- Liquid-feil ved bygg: `bundle exec jekyll build --trace` gir full stacktrace.


