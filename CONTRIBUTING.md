# Contributing

Thanks for wanting to add to the map. The whole thing is one file: open
`index.html` in an editor, change the data near the bottom, reload it in a
browser, open a pull request. There is nothing to install and nothing to build.

The data sits in labelled blocks — search for `data-block="SITES"` and you are
in the right place.

```sh
node scripts/validate.mjs      # optional; CI runs it on your pull request
```

## Adding a city or culture

One record in the `SITES` block of `index.html`, kept to two lines: facts, then
description.

```js
 {n:'Babylon',c:'Babylonia',r:'tigriseuph',lo:44.42,la:32.54,f:-2300,t:-140,w:'Babylon',
  g:['law code','Ishtar Gate','base-60 maths'],role:'Capital of Babylonia',ti:1,pop:'est. 150,000',
  d:'Astride the Euphrates: Hammurabi\u2019s law code, Nebuchadnezzar\u2019s glazed gate, and the mathematics that gave us 60 minutes in an hour.'},
```

| field  | required | meaning |
|--------|----------|---------|
| `n`    | yes | Site name as it appears on the map. Must be unique. |
| `c`    | yes | Culture, people or polity — *Sumer*, *Mississippian culture*. |
| `r`    | yes | River system id, a key from the `RIVERS` block. |
| `lo`   | yes | Longitude, decimal degrees, negative west. |
| `la`   | yes | Latitude, decimal degrees, negative south. |
| `f`    | yes | First year of the span shown. Negative is BCE; no year zero in the data, use -1 or 1. |
| `t`    | yes | Last year of the span. Must be greater than `f`. Both must sit inside -10000…1600. |
| `w`    | yes | Wikipedia article slug, underscores not spaces (`Huaca_del_Sol`). Check it resolves. |
| `g`    | yes | 2–4 very short tags for the infobox (`'oracle bones'`). |
| `role` | yes | What the place *was*, in a few words: `Capital of Babylonia`, `Fishing town`, `Unexcavated Indus-scale mound`. Keep under about 45 characters. |
| `ti`   | yes | Significance tier, which sets the marker: `1` capital or metropolis, `2` city or ceremonial centre, `3` village or minor site. |
| `pop`  | no  | Peak population estimate. Must begin `est. `, and say `(contested)` when it is. Omit rather than guess. |
| `d`    | yes | One or two sentences of why it matters. Aim under 240 characters. Concrete beats grand. |

Guidelines that matter more than the schema:

- **Cite it in the PR.** Dates, population figures and "oldest known" claims all
  need a source in the description of the pull request. Wikipedia is fine as a
  starting point; a paper or excavation report is better.
- **It has to be on the water.** The map's whole claim is the relationship
  between settlement and river. Tikal is in because its reservoir engineering is
  the point; a site that merely happens to be in a river's watershed is not.
- **Don't inflate the tier.** `ti:1` is for capitals of states and genuine
  metropolises. If you are unsure between 1 and 2, it is 2.
- **Write like the existing entries.** Plain, specific, no marketing. "120
  mounds, a plaza the size of 35 football fields, and more people than London
  then held" rather than "an awe-inspiring metropolis".

## Adding a river system

The `RIVERS` block holds the label and metadata:

```js
 nile:{n:'The Nile',hy:'Nile',lo:29.6,la:23.0,rot:-84,mz:1,reg:'Africa'},
```

| field | meaning |
|-------|---------|
| `n`   | Name used in the side list and cards (`The Nile`, `Tigris & Euphrates`). |
| `hy`  | Label drawn on the map. Use the name most readers know — `Yellow River`, not `Huang He`. |
| `alt` | Optional second line, shown when zoomed in: the local or historical name (`Huang He`, `the Sarasvati`). |
| `lo`, `la` | Where the label sits. |
| `rot` | Label rotation in degrees, so it follows the water. |
| `mz`  | Zoom at which the label appears: `1` always, up to about `3` for crowded areas. |
| `reg` | One of Africa, West Asia, Central Asia, South Asia, East Asia, Southeast Asia, Europe, North America, Mesoamerica, South America. |
| `dry` | `1` if the channel no longer flows; it is then drawn broken. |

The **geometry** lives in the generated `GEO` block, one very long line — never
edit it by hand. Add the river to `scripts/build_geo.py` instead:

- If Natural Earth has it, add its feature names to `SYSTEMS`. One river is often
  several features under local names, so list them all (`'Huang'`, `'Tigris'`,
  `'Dicle'`, `'Firat'`).
- If it is too small for the dataset, add waypoints to `HAND`.
- Every system needs an entry in `MOUTHS`, the outlet coordinate. Segments are
  oriented to run toward it so the flow animation always goes downstream — the
  source data is digitised inconsistently and half the segments would otherwise
  animate backwards.

Then rebuild the block and check the result in the browser:

```sh
python3 scripts/build_geo.py     # downloads Natural Earth, rewrites the GEO block
```

That script is the only thing in the project that needs to run, and only when
the map's geometry changes. Adding a city never requires it.

## Images

The map tries, in order: an override from the `IMG` block, the Wikipedia lead
image, the first image in the article's media list. To supply or replace one:

```js
window.IMG = {
  'Sechín Alto': ['File:Sechín Archaeological site - relief (warrior).jpg',
                  'Carved warrior at neighbouring Cerro Sechín'],
  'Paithan': 'File:Coin of Satkarni.jpg',
  'Some Site': false,        // show no picture at all
};
```

A Commons `File:` name, a direct URL, or a `[file, caption]` pair. If an image is
not of the site itself, say so in the caption. Run `imageAudit()` in the browser
console to list every site with no image.

## Modern cities

The `MODERN` block, compact form `['Chongqing','yangtze',106.55,29.56]`. These are
for showing that people still live on the same water, so keep them to cities a
reader would recognise, actually on the river in question.

## If an edit breaks the page

The map checks its own data on startup. A stray comma or unbalanced quote makes
the page say which block failed to parse, rather than going blank. `node
scripts/validate.mjs` will point at the same thing with a line of context.

## Reporting a problem instead

If you know a site or a course is wrong but don't want to edit code, open an
issue with what's wrong and a source. That is a genuinely useful contribution —
two of the original Wikipedia slugs were dead and the entire Nile was animating
in both directions until someone noticed.
