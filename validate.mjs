#!/usr/bin/env node
/* Validate the data files.
 *
 *   node scripts/validate.mjs                 structure only (fast, offline)
 *   node scripts/validate.mjs --check-links   also verify every Wikipedia slug
 *
 * Exits non-zero and prints every problem it finds.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(ROOT, 'index.html'), 'utf8');

/* The data lives in <script data-block="…"> sections inside index.html. */
const win = {};
const blocks = [...html.matchAll(/<script data-block="(\w+)">([\s\S]*?)<\/script>/g)];
if (!blocks.length) {
  console.error('error:   found no <script data-block="…"> sections in index.html');
  process.exit(1);
}
for (const [, name, src] of blocks) {
  try {
    new Function('window', src)(win);
  } catch (e) {
    console.error(`error:   the ${name} data block does not parse: ${e.message}`);
    process.exit(1);
  }
}
const { GEO, CRADLES, SITES, MODERN, IMG } = win;

const errors = [];
const warnings = [];
const bad = (m) => errors.push(m);
const warn = (m) => warnings.push(m);

/* ---------- river systems ---------- */
const RIVER_KEYS = Object.keys(CRADLES);
const REGIONS = ['Africa', 'West Asia', 'Central Asia', 'South Asia', 'East Asia',
                 'Southeast Asia', 'Europe', 'North America', 'Mesoamerica',
                 'South America'];

for (const [key, c] of Object.entries(CRADLES)) {
  for (const field of ['n', 'hy', 'lo', 'la', 'rot', 'mz', 'reg']) {
    if (c[field] === undefined) bad(`river "${key}": missing ${field}`);
  }
  if (!REGIONS.includes(c.reg))
    bad(`river "${key}": region "${c.reg}" is not one of ${REGIONS.join(', ')}`);
  if (Math.abs(c.lo) > 180 || Math.abs(c.la) > 90)
    bad(`river "${key}": label coordinates out of range`);
  if (!GEO.rivers[key])
    bad(`river "${key}": no geometry in the GEO block — add it to scripts/build_geo.py`);
}
for (const key of Object.keys(GEO.rivers)) {
  if (!CRADLES[key]) bad(`the GEO block has geometry for "${key}" with no entry in the RIVERS block`);
}

/* ---------- sites ---------- */
const seen = new Set();
for (const s of SITES) {
  const at = `site "${s.n}"`;
  for (const field of ['n', 'c', 'r', 'lo', 'la', 'f', 't', 'w', 'g', 'role', 'ti', 'd']) {
    if (s[field] === undefined) bad(`${at}: missing ${field}`);
  }
  if (seen.has(s.n)) bad(`${at}: duplicate name`);
  seen.add(s.n);

  if (!RIVER_KEYS.includes(s.r)) bad(`${at}: river "${s.r}" is not in the RIVERS block`);
  if (!(Math.abs(s.lo) <= 180)) bad(`${at}: longitude ${s.lo} out of range`);
  if (!(Math.abs(s.la) <= 90)) bad(`${at}: latitude ${s.la} out of range`);
  if (!(s.f < s.t)) bad(`${at}: start ${s.f} is not before end ${s.t}`);
  if (s.f < -10000 || s.t > 1600)
    bad(`${at}: ${s.f}…${s.t} falls outside the timeline (-10000…1600)`);
  if (![1, 2, 3].includes(s.ti)) bad(`${at}: tier "ti" must be 1, 2 or 3`);
  if (!Array.isArray(s.g) || s.g.length < 2 || s.g.length > 4)
    bad(`${at}: "g" should hold 2–4 short tags`);
  if (s.pop !== undefined && !/^est\. /.test(s.pop))
    bad(`${at}: "pop" must be marked as an estimate, e.g. 'est. 40,000'`);
  if (typeof s.w === 'string' && /\s/.test(s.w))
    bad(`${at}: Wikipedia slug "${s.w}" contains a space — use underscores`);
  if (s.d && s.d.length > 260) warn(`${at}: description is ${s.d.length} chars (aim under 240)`);
  if (typeof s.role === 'string' && s.role.length > 46)
    warn(`${at}: role "${s.role}" is long for the card`);
}

/* every river should carry at least one site */
for (const key of RIVER_KEYS) {
  if (!SITES.some((s) => s.r === key)) bad(`river "${key}" has no sites`);
}

/* ---------- modern cities ---------- */
for (const m of MODERN) {
  const [n, r, lo, la] = m.length ? m : [m.n, m.r, m.lo, m.la];
  if (!n || !r) { bad(`modern city ${JSON.stringify(m)}: needs [name, river, lon, lat]`); continue; }
  if (!RIVER_KEYS.includes(r)) bad(`modern city "${n}": river "${r}" is not in the RIVERS block`);
  if (!(Math.abs(lo) <= 180 && Math.abs(la) <= 90))
    bad(`modern city "${n}": coordinates out of range`);
}

/* ---------- image overrides ---------- */
for (const [name, v] of Object.entries(IMG)) {
  if (!seen.has(name))
    bad(`image override "${name}" matches no site name in the SITES block`);
  const val = Array.isArray(v) ? v[0] : v;
  if (v !== false && !(typeof val === 'string' && val.length))
    bad(`image override "${name}": expected a URL, a 'File:…' name, an [url, caption] pair, or false`);
}

/* ---------- optional: do the Wikipedia slugs resolve? ---------- */
if (process.argv.includes('--check-links')) {
  const UA = { 'User-Agent': 'rivers-map-validate/1.0 (github.com/rnrand/river-civs)' };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  /* Wikipedia throttles bursts. Retry on 429 and 5xx, and never fail the build
     over rate limiting — only a real 404 means the data is wrong. */
  async function api(url, tries = 4) {
    for (let i = 0; i < tries; i++) {
      const r = await fetch(url, { headers: UA });
      if (r.status !== 429 && r.status < 500) return r;
      await sleep(1000 * Math.pow(2, i));
    }
    return null;
  }

  const API = 'https://en.wikipedia.org/api/rest_v1/page/summary/';
  let noImage = 0;
  for (const s of SITES) {
    const url = API + encodeURIComponent(s.w) + '?redirect=true';
    try {
      const r = await api(url);
      if (!r) { warn(`site "${s.n}": rate limited, "${s.w}" not checked`); continue; }
      if (r.status === 404) { bad(`site "${s.n}": Wikipedia article "${s.w}" does not exist`); continue; }
      if (!r.ok) { warn(`site "${s.n}": "${s.w}" returned ${r.status}`); continue; }
      const j = await r.json();
      if (j.type === 'disambiguation')
        warn(`site "${s.n}": slug "${s.w}" is a disambiguation page`);
      if (!j.thumbnail) noImage++;
    } catch (e) {
      warn(`site "${s.n}": could not check "${s.w}" (${e.message})`);
    }
    await sleep(250);
  }
  console.log(`${noImage} of ${SITES.length} sites have no lead image on Wikipedia ` +
              `(the map falls back to the article's media list, then the IMG block).`);

  /* Do the hand-picked images in the IMG block still exist? */
  const FILE_API = 'https://en.wikipedia.org/w/api.php?action=query&format=json' +
                   '&prop=imageinfo&iiprop=url|size&titles=';
  for (const [site, v] of Object.entries(IMG)) {
    if (v === false) continue;
    const val = Array.isArray(v) ? v[0] : v;
    if (/^https?:/i.test(val)) {
      warn(`image override "${site}": direct URL, not checked (${val})`);
      continue;
    }
    const title = 'File:' + String(val).replace(/^\s*(File|Image)\s*:\s*/i, '');
    try {
      const r = await api(FILE_API + encodeURIComponent(title));
      if (!r || !r.ok) { warn(`image override "${site}": ${title} not checked`); continue; }
      const j = await r.json();
      const page = Object.values(j.query.pages)[0];
      if (!page.imageinfo) bad(`image override "${site}": ${title} does not exist`);
      else if (page.imageinfo[0].width < 500)
        warn(`image override "${site}": ${title} is only ${page.imageinfo[0].width}px wide`);
    } catch (e) {
      warn(`image override "${site}": could not check ${title} (${e.message})`);
    }
    await sleep(250);
  }
}

/* ---------- report ---------- */
for (const w of warnings) console.warn('warning: ' + w);
for (const e of errors) console.error('error:   ' + e);
console.log(`\n${SITES.length} sites, ${RIVER_KEYS.length} river systems, ` +
            `${MODERN.length} modern cities, ${Object.keys(IMG).length} image overrides`);
if (errors.length) {
  console.error(`\n${errors.length} error(s).`);
  process.exit(1);
}
console.log(warnings.length ? `${warnings.length} warning(s), no errors.` : 'All checks passed.');
