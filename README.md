# Rivers first, cities after

An interactive world map of the ancient world's major rivers and the
civilizations that grew up along them — 33 river systems and 79 cities and
cultures, from the Supe valley in Peru to the Yellow River bend, spanning
10,000 BCE to 1600 CE.

**Live map: https://USERNAME.github.io/REPO/**

Water is drawn as the brightest thing on the page, because that is the
argument the map is making. A timeline along the bottom sweeps from 10,000 BCE
forward, lighting each city as it is founded and dimming it when it ends —
stop at 2534 BCE and you get the Bronze Age world exactly: Mesopotamia, Egypt,
the Indus, and Caral on the Peruvian coast, all lit at once.

## What's here

- Hover a river or a city for an infobox; click either to zoom in and read more.
- Cities are sized by significance: capital or metropolis, city or ceremonial
  centre, village or minor site.
- City cards pull a photograph and a one-line description from Wikipedia, and
  link out to the article.
- A **Modern cities** toggle adds 74 present-day cities on the same water —
  Cairo, Baghdad, Xi'an, Chongqing, Lima, Manaus, New Orleans — so you can see
  `LUOYANG ○ ● Erlitou` and `XI'AN ○ ● Banpo` sitting side by side.
- Dry channels, such as the Ghaggar–Hakra that the Harappans built on, are
  drawn as broken lines.

## Running it

Double-click `index.html`. That is the whole procedure.

The map is one self-contained file: markup, styles, logic and data, with no
build step, no dependencies, no server and no external scripts. Save it
anywhere and it works, including offline — the only things fetched from the
network are the two web fonts (which fall back to Palatino and a system
monospace) and the photographs on the city cards.

## Layout

```
index.html            the entire map
scripts/validate.mjs  checks the data (runs in CI)
scripts/build_geo.py  rebuilds the coastlines and river courses
```

Inside `index.html`, the data sits in labelled blocks near the bottom, above the
code:

```html
<script data-block="SITES">    the 79 ancient cities and cultures
<script data-block="RIVERS">   the 33 river systems
<script data-block="MODERN">   modern cities on the same rivers
<script data-block="IMG">      manual image overrides
<script data-block="GEO">      GENERATED geometry — do not hand-edit
```

Search the file for `data-block="SITES"` and you are where the interesting
edits happen. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

Sites, corrections, better images and missing rivers are all welcome. The short
version:

```sh
# edit the SITES block in index.html, reload the page, then
node scripts/validate.mjs
```

Node is only needed for that check, and CI runs it for you anyway — a pull
request that just edits the data is perfectly welcome without it.

Open a pull request. CI runs the same validator. Dates and population
estimates need a source in the PR description.

## Sources and licensing

- Code: [MIT](LICENSE).
- The site and river records (the SITES, RIVERS, MODERN and IMG blocks):
  [CC BY 4.0](LICENSE-DATA).
- Coastlines, lakes and river centrelines: [Natural
  Earth](https://www.naturalearthdata.com/), public domain. Smaller rivers that
  Natural Earth omits are hand-digitised in `scripts/build_geo.py`; those
  courses are approximate — good enough to show the relationship between a city
  and its water, not accurate enough to measure.
- Photographs are loaded live from Wikipedia and Wikimedia Commons and are **not**
  redistributed here. Each remains under its own licence; the card links to the
  source article.
- Population figures are published estimates, marked `est.`, and contested ones
  say so. Dates for long-lived cities are the span the map shows, not a claim
  about precise founding years.

## Known limitations

- The Peruvian coastal valleys, the Tiber, the Karkheh, the Ghaggar–Hakra and a
  few others are schematic courses, as noted above.
- Coastlines are simplified for file size and look blocky at the deepest zoom.
- Xianyang & Haojing has no image on Wikipedia; its card says so.
