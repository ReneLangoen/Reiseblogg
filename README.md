## Reiseblogg (Jekyll)

Dette repo inneholder en enkel Jekyll-basert reiseblogg. Her er raske instruksjoner for å jobbe med den lokalt.

Forutsetninger
- Ruby 2.7+ og `bundler` installert

Kjør lokalt
```bash
bundle install
bundle exec jekyll serve
```

Åpne deretter http://127.0.0.1:4000/ i nettleseren.

Legg til et nytt innlegg
- Lag en ny fil i `_posts/` med formatet `YYYY-MM-DD-slug.md`.
- Eksempel: `2026-07-15-uke_3_bali.md`
- Front matter (minimalt):

```yaml
---
title: "Uke 3: Bali"
description: "Kort beskrivelse"
location: "Bali, Indonesia"
tags: [reisedagbok, uke 3, Indonesia]
week_label: "Uke 3"
image: "/pictures/week-3/beach.jpg"
gallery_images:
	- image: "/pictures/week-3/beach.jpg"
		caption: "Strandliv"
---
```

Bilder
- Legg bilder i `pictures/` og referer til dem i front matter med full sti, f.eks. `/pictures/week-1/photo.jpg`.

Kart og Galleri
- Kartet er tilgjengelig på `/map/`.
- Galleri samler `gallery_images` fra postene.

Diverse
- Jekyll bruker datoen fra filnavnet i `_posts/` som post-datoen. Du trenger ikke et `date:`-felt med mindre du vil overskrive den.
- Kjør `bundle exec jekyll build` for å generere siden i `_site/`.

Hovedfiler
- `_config.yml` — nettstedinnstillinger
- `_layouts/` — sidemaler
- `_includes/` — gjenbrukbare deler
- `_posts/` — innlegg
- `assets/` — CSS og andre statiske filer

Kontakt
- Gi beskjed hvis du vil at jeg skal automatisere bilder, perma-linker eller legge til deploy-oppsett.
