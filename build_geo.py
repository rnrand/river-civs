#!/usr/bin/env python3
"""Rebuild the GEO data block inside index.html from Natural Earth.

    python3 scripts/build_geo.py

Downloads Natural Earth coastlines, lakes and river centrelines, simplifies
them, adds the small rivers that global datasets omit, orients every river
segment downstream, and rewrites the GEO block in index.html in place.

Natural Earth is public domain. Nothing here needs an API key.
"""
import json, math, os, re, sys, urllib.request

NE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/'
CACHE = os.path.join(os.path.dirname(__file__), '.cache')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'index.html')      # the GEO block inside it

# Natural Earth splits one river into many features under local names.
SYSTEMS = {
    'nile':        ['Nile', 'Damietta Branch', 'Rosetta Branch', 'El Bahr el Abyad',
                    'Bahr el Jebel', 'Bahr el  Zeraf', 'El Bahr el Azraq', 'Abay',
                    'Atbara', 'Setit', 'Albert Nile', 'Victoria Nile'],
    'tigriseuph':  ['Tigris', 'Dicle', 'Euphrates', 'Firat', 'Al Furat', 'Shatt al Arab'],
    'jordan':      ['Jordan'],
    'indus':       ['Indus', 'Chenab', 'Sutlej', 'Shiquan'],
    'ganges':      ['Ganges', 'Yamuna'],
    'oxus':        ['Amu  Darya', 'Amu Darya', 'Panj', 'Pamir'],
    'helmand':     ['Helmand'],
    'huanghe':     ['Huang'],
    'yangtze':     ['Yangtze', 'Chang Jiang', 'Jinsha', 'Tongtian', 'Tuotuo', 'Min'],
    'hong':        ['Hong'],
    'mekong':      ['Mekong', 'Lancang'],
    'irrawaddy':   ['Ayeyarwady', 'Irrawaddy Delta', 'Nmai'],
    'danube':      ['Danube', 'Donau', 'Tisza', 'Bratul Sulina'],
    'niger':       ['Niger', 'Benue'],
    'limpopo':     ['Limpopo'],
    'godavari':    ['Godävari', 'Krishna'],
    'mississippi': ['Mississippi', 'Ohio', 'Missouri', 'Illinois'],
    'gila':        ['Gila', 'Verde'],
    'sanjuan':     ['San Juan'],
    'usumacinta':  ['Usumacinta', 'Chixoy'],
    'amazon':      ['Amazonas', 'Marañón', 'Ucayali', 'Negro', 'Madeira', 'Tapajós',
                    'Xingu', 'Japurá'],
    'mamore':      ['Mamoré', 'Guaporé', 'Madre de Dios'],
    'magdalena':   ['Magdalena'],
    'titicaca':    ['Desaguadero'],
}

# Rivers too small for the 50m dataset, digitised from known site coordinates.
# Approximate courses: good enough to show city-and-water, not for measurement.
HAND = {
    'tiber': [[[12.05, 43.72], [12.32, 43.28], [12.52, 42.66], [12.66, 42.42],
               [12.48, 42.02], [12.34, 41.86], [12.23, 41.74]]],
    'karun': [[[47.45, 34.35], [47.90, 33.40], [48.15, 32.75], [48.32, 32.20],
               [48.05, 31.75], [47.92, 31.55]],
              [[50.55, 32.60], [49.85, 32.20], [49.20, 31.85], [48.75, 31.05],
               [48.55, 30.45]]],
    'ghaggar': [[[77.10, 30.78], [76.62, 30.62], [76.28, 30.30], [75.86, 30.14],
                 [75.42, 29.96], [74.98, 29.82], [74.60, 29.56], [74.18, 29.44],
                 [73.76, 29.20], [73.32, 29.04], [72.90, 28.76], [72.50, 28.50],
                 [72.06, 28.20], [71.62, 27.96], [71.16, 27.74], [70.72, 27.40],
                 [70.34, 27.06]]],
    'coatza': [[[-94.95, 17.05], [-94.82, 17.45], [-94.62, 17.80], [-94.45, 18.14]],
               [[-93.05, 16.35], [-92.92, 17.05], [-93.02, 17.55], [-93.22, 17.95],
                [-92.72, 18.48]]],
    'norteChico': [[[-76.98, -10.73], [-77.28, -10.83], [-77.52, -10.87], [-77.74, -10.80]],
                   [[-77.05, -10.55], [-77.38, -10.63], [-77.62, -10.68], [-77.79, -10.68]],
                   [[-77.12, -10.35], [-77.45, -10.42], [-77.72, -10.44]]],
    'casma': [[[-77.92, -9.42], [-78.12, -9.44], [-78.28, -9.47], [-78.40, -9.47]]],
    'mocheChicama': [[[-78.35, -8.02], [-78.62, -8.08], [-78.85, -8.12], [-79.04, -8.14]],
                     [[-78.55, -7.66], [-78.88, -7.72], [-79.12, -7.72], [-79.34, -7.69]]],
    'rimacLurin': [[[-76.42, -11.86], [-76.72, -11.94], [-76.98, -12.02], [-77.15, -12.06]],
                   [[-76.50, -12.10], [-76.72, -12.16], [-76.90, -12.22], [-76.96, -12.26]]],
    'urubamba': [[[-71.18, -14.52], [-71.42, -14.10], [-71.68, -13.82], [-72.10, -13.40],
                  [-72.42, -13.20], [-72.58, -12.90], [-72.90, -12.35], [-73.10, -11.80]]],
    # San Juan Teotihuacan, canalised through the city grid, down to Lake Texcoco
    'sanjuanteo': [[[-98.76, 19.73], [-98.81, 19.71], [-98.845, 19.692], [-98.89, 19.66],
                    [-98.94, 19.62], [-98.99, 19.58], [-99.03, 19.55]]],
    # Mosna and Huachecsa, meeting at Chavín, on to the Puchka and the Marañón
    'mosna': [[[-77.12, -9.78], [-77.15, -9.68], [-77.177, -9.60], [-77.19, -9.48],
               [-77.20, -9.36], [-77.13, -9.24], [-77.02, -9.14], [-76.90, -9.06]],
              [[-77.27, -9.55], [-77.22, -9.58], [-77.18, -9.594]]],
    # Atoyac, draining the Valley of Oaxaca to the Pacific
    'atoyac': [[[-96.62, 17.22], [-96.72, 17.08], [-96.80, 16.95], [-96.92, 16.78],
                [-97.06, 16.62], [-97.24, 16.46], [-97.45, 16.28], [-97.62, 16.10],
                [-97.72, 15.99]]],
    # Río Grande de Nasca and the Nazca, which run underground for much of the year
    'nasca': [[[-74.50, -14.45], [-74.72, -14.60], [-74.90, -14.72], [-75.05, -14.82],
               [-75.18, -14.92], [-75.30, -15.02], [-75.38, -15.08]],
              [[-74.85, -14.82], [-74.94, -14.83], [-75.05, -14.83], [-75.14, -14.83],
               [-75.22, -14.91]]],
    # Musi, with Palembang at the head of its delta
    'musi': [[[103.20, -3.62], [103.65, -3.45], [104.10, -3.25], [104.50, -3.08],
              [104.78, -2.98], [104.95, -2.70], [105.10, -2.42], [105.22, -2.25]]],
    # Çarşamba, which ends in the closed Konya basin rather than the sea
    'carsamba': [[[32.30, 37.15], [32.45, 37.32], [32.60, 37.46], [32.72, 37.56],
                  [32.83, 37.66], [32.90, 37.80], [32.97, 37.93]]],
    # Pulvar and Kor, past Persepolis to Lake Bakhtegan
    'pulvar': [[[53.22, 30.30], [53.10, 30.18], [52.99, 30.06], [52.92, 29.96],
                [52.89, 29.87], [52.90, 29.76]],
               [[52.60, 29.90], [52.80, 29.78], [52.95, 29.68], [53.15, 29.55],
                [53.40, 29.45]]],
}
# Tributaries appended to an existing system.
EXTRA = {
    'huanghe': [[[110.30, 34.55], [109.60, 34.62], [108.85, 34.32], [108.05, 34.32],
                 [107.20, 34.42], [106.35, 34.62], [105.70, 34.80]]],           # Wei
    'gila':    [[[-110.50, 33.72], [-111.05, 33.62], [-111.60, 33.52],
                 [-112.05, 33.42], [-112.35, 33.34]]],                          # Salt
}
# Outlet of each system. Every segment is oriented to run toward it, so the
# flow animation always travels downstream regardless of how the source data
# happened to be digitised.
MOUTHS = {
    'nile': (31.0, 31.5), 'niger': (6.4, 4.3), 'limpopo': (35.4, -25.2),
    'tigriseuph': (48.6, 29.9), 'jordan': (35.5, 31.5), 'karun': (48.5, 30.0),
    'indus': (67.4, 24.0), 'ghaggar': (70.3, 27.1), 'ganges': (89.5, 22.2),
    'godavari': (82.3, 16.9), 'oxus': (59.0, 44.5), 'helmand': (61.3, 31.2),
    'huanghe': (119.0, 37.8), 'yangtze': (121.8, 31.4), 'hong': (106.7, 20.3),
    'mekong': (106.6, 9.5), 'irrawaddy': (94.8, 15.9), 'danube': (29.7, 45.2),
    'tiber': (12.23, 41.74), 'mississippi': (-89.2, 29.1), 'gila': (-114.5, 32.7),
    'sanjuan': (-110.4, 37.2), 'usumacinta': (-92.6, 18.6), 'coatza': (-93.5, 18.4),
    'norteChico': (-77.8, -10.7), 'casma': (-78.42, -9.47),
    'mocheChicama': (-79.2, -8.0), 'rimacLurin': (-77.1, -12.1),
    'titicaca': (-67.1, -18.9), 'urubamba': (-73.1, -11.8), 'amazon': (-50.0, -0.2),
    'mamore': (-65.4, -11.0), 'magdalena': (-74.85, 11.1),
    'sanjuanteo': (-99.03, 19.55), 'mosna': (-76.90, -9.06), 'atoyac': (-97.72, 15.99),
    'nasca': (-75.38, -15.08), 'musi': (105.22, -2.25), 'carsamba': (32.97, 37.93),
    'pulvar': (53.40, 29.45),
}
LAKES = {'Lake Chad', 'Lago Titicaca', 'Tonlé Sap', 'Lake Urmia', 'Tai Hu', 'Poyang Hu',
         'Lake Van', 'Sea of Galilee', 'Lake Nasser', 'Lake Superior', 'Lake Michigan',
         'Lake Huron', 'Lake Erie', 'Lake Ontario', 'Lake Victoria', 'Lake Tanganyika',
         'Lake Malawi', 'Lake Nyasa', 'Caspian Sea', 'South Aral Sea', 'North Aral Sea',
         'Great Salt Lake', 'Lake Balkhash', 'Lake Baikal', 'Dead Sea', 'Lake Winnipeg',
         'Lake Ladoga'}


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print('downloading', name)
        req = urllib.request.Request(NE + name, headers={'User-Agent': 'rivers-map/1.0'})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, 'wb') as f:
            f.write(r.read())
    return json.load(open(path))


def rdp(pts, eps):
    """Ramer-Douglas-Peucker simplification."""
    if len(pts) < 3:
        return pts
    def dist(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1)
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
    a, b, idx, dmax = pts[0], pts[-1], 0, 0
    for i in range(1, len(pts) - 1):
        d = dist(pts[i], a, b)
        if d > dmax:
            idx, dmax = i, d
    if dmax > eps:
        return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [a, b]


def round_pts(pts, n):
    out = []
    for x, y in pts:
        p = [round(x, n), round(y, n)]
        if not out or out[-1] != p:
            out.append(p)
    return out


def build_land():
    rings = []
    for f in fetch('ne_50m_land.geojson')['features']:
        g = f['geometry']
        raw = ([g['coordinates'][0]] if g['type'] == 'Polygon'
               else [poly[0] for poly in g['coordinates']])
        for ring in raw:
            ring = [(x, y) for x, y in ring]
            if all(y < -58 for _, y in ring):      # drop Antarctica
                continue
            r = rdp(ring, 0.07)
            if len(r) < 4:
                continue
            area = abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]
                           for i in range(len(r) - 1))) / 2
            if area < 0.35:                        # drop specks
                continue
            rings.append(round_pts(r, 2))
    rings.sort(key=lambda r: -len(r))
    return rings


def build_lakes():
    out = []
    for f in fetch('ne_50m_lakes.geojson')['features']:
        name = f['properties'].get('name')
        if name not in LAKES:
            continue
        g = f['geometry']
        raw = ([g['coordinates'][0]] if g['type'] == 'Polygon'
               else [poly[0] for poly in g['coordinates']])
        for ring in raw:
            r = round_pts(rdp([(x, y) for x, y in ring], 0.02), 3)
            if len(r) > 3:
                out.append({'n': name, 'p': r})
    return out


def build_rivers():
    rivers = {}
    for f in fetch('ne_50m_rivers_lake_centerlines.geojson')['features']:
        name = f['properties'].get('name')
        for key, names in SYSTEMS.items():
            if name in names:
                g = f['geometry']
                lines = ([g['coordinates']] if g['type'] == 'LineString'
                         else g['coordinates'])
                for line in lines:
                    seg = round_pts(rdp([(c[0], c[1]) for c in line], 0.025), 3)
                    if len(seg) > 1:
                        rivers.setdefault(key, []).append(seg)
    missing = [k for k in SYSTEMS if k not in rivers]
    if missing:
        sys.exit('Natural Earth returned nothing for: ' + ', '.join(missing))
    for key, segs in HAND.items():
        rivers[key] = [list(map(list, s)) for s in segs]
    for key, segs in EXTRA.items():
        rivers[key] += [list(map(list, s)) for s in segs]

    if set(rivers) != set(MOUTHS):
        sys.exit('MOUTHS and river systems disagree: '
                 + str(set(rivers) ^ set(MOUTHS)))
    flipped = 0
    for key, segs in rivers.items():
        mx, my = MOUTHS[key]
        near = lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2
        for i, seg in enumerate(segs):
            if near(seg[0]) < near(seg[-1]):
                segs[i] = seg[::-1]
                flipped += 1
    print('oriented downstream: %d segments reversed' % flipped)
    return rivers


def main():
    land, lakes, rivers = build_land(), build_lakes(), build_rivers()
    print('land rings %d (%d points) | lakes %d | river systems %d (%d points)' % (
        len(land), sum(len(r) for r in land), len(lakes), len(rivers),
        sum(len(s) for v in rivers.values() for s in v)))
    payload = 'window.GEO = ' + json.dumps(
        {'land': land, 'lakes': lakes, 'rivers': rivers}, separators=(',', ':')) + ';'

    html = open(OUT, encoding='utf-8').read()
    pattern = re.compile(r'(<script data-block="GEO">\n)(.*?)(\n</script>)', re.S)
    if not pattern.search(html):
        sys.exit('Could not find the <script data-block="GEO"> block in index.html')
    html = pattern.sub(lambda m: m.group(1) + payload.replace('\\', '\\\\') + m.group(3), html, count=1)
    open(OUT, 'w', encoding='utf-8').write(html)
    print('rewrote the GEO block in index.html (%.0f KB of geometry)' % (len(payload) / 1024))


if __name__ == '__main__':
    main()
