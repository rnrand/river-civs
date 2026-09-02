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
    'gila':        ['Gila'],
    'usumacinta':  ['Usumacinta', 'Chixoy'],
    'amazon':      ['Amazonas', 'Marañón', 'Ucayali', 'Negro', 'Madeira', 'Tapajós',
                    'Xingu', 'Japurá'],
    'mamore':      ['Mamoré', 'Guaporé', 'Madre de Dios'],
    'magdalena':   ['Magdalena'],
}

# Natural Earth names are not unique: there is a San Juan in Nicaragua and
# another in Argentina, a Río Negro in Patagonia, a Verde in eastern Mexico, and
# the only Desaguadero in the dataset is the Argentine one, not Titicaca's
# outlet. Every system is therefore clipped to the region it belongs in.
# (lon_min, lon_max, lat_min, lat_max)
BBOX = {
    'nile': (20, 40, -5, 34), 'niger': (-13, 11, 3, 19), 'limpopo': (24, 36, -27, -19),
    'tigriseuph': (35, 50, 28, 41), 'jordan': (34, 37, 30, 34),
    'indus': (64, 80, 21, 37), 'ganges': (74, 93, 19, 33), 'godavari': (71, 85, 13, 23),
    'oxus': (57, 76, 34, 43), 'helmand': (58, 69, 27, 36),
    'huanghe': (94, 123, 31, 43), 'yangtze': (89, 124, 23, 37),
    'hong': (99, 109, 17, 27), 'mekong': (93, 109, 7, 35), 'irrawaddy': (92, 101, 13, 30),
    'danube': (7, 31, 41, 51),
    'mississippi': (-116, -77, 27, 51), 'gila': (-116, -106, 30, 36),
    'usumacinta': (-94, -87, 14, 19),
    'amazon': (-81, -44, -15, 7), 'mamore': (-71, -59, -21, -8),
    'magdalena': (-78, -72, 0, 13),
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
    # San Juan and Animas, the Ancestral Puebloan "Totah" — Natural Earth's
    # "San Juan" features are in Nicaragua and Argentina, not Colorado
    'sanjuan': [[[-107.00, 37.62], [-107.40, 37.35], [-107.75, 37.18], [-108.20, 36.90],
                 [-108.70, 36.80], [-109.20, 37.00], [-109.60, 37.15], [-110.20, 37.25],
                 [-110.45, 37.15]],
                [[-107.80, 37.60], [-107.88, 37.30], [-107.98, 37.00], [-108.02, 36.83],
                 [-108.20, 36.75]]],
    # Desaguadero, Lake Titicaca's outlet to Lake Poopó — the only Desaguadero in
    # Natural Earth is the Argentine river of the same name
    'titicaca': [[[-69.04, -16.56], [-68.85, -16.85], [-68.60, -17.15], [-68.30, -17.45],
                  [-68.00, -17.75], [-67.70, -18.10], [-67.45, -18.45], [-67.20, -18.75],
                  [-67.10, -18.95]]],
    # Yao, draining the Yaojiang valley to Hangzhou Bay — a separate drainage
    # from the Yangtze, despite Hemudu being a "lower Yangtze" culture
    'yao': [[[120.90, 29.85], [121.10, 29.90], [121.35, 29.96], [121.55, 29.95],
             [121.62, 29.92]]],
    # Sabarmati and its Bhogavo tributary, to the Gulf of Khambhat
    'sabarmati': [[[72.90, 24.20], [72.75, 23.60], [72.60, 23.05], [72.55, 22.70],
                   [72.45, 22.35], [72.30, 22.05], [72.25, 21.85]],
                  [[71.95, 22.60], [72.10, 22.55], [72.25, 22.52], [72.35, 22.40],
                   [72.42, 22.25]]],
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
    # Murghab, which waters the Margiana oasis and dies in the Karakum. Not the
    # Amu Darya, but the same Bactria-Margiana world.
    'oxus':    [[[61.20, 35.60], [61.50, 36.20], [61.80, 36.90], [62.00, 37.50],
                 [62.10, 38.00], [62.05, 38.30], [61.95, 38.70]]],
    # Upper Min through Dujiangyan and the Chengdu plain, and the Yazi branch
    # that runs past Sanxingdui
    'yangtze': [[[103.55, 31.75], [103.62, 31.20], [103.70, 30.95], [103.85, 30.70],
                 [104.00, 30.40], [104.05, 30.05], [103.95, 29.75], [103.75, 29.55]],
                [[103.75, 31.10], [104.00, 31.05], [104.20, 31.00], [104.35, 30.85]],
                # Tiaoxi, whose tributaries Liangzhu dammed, into Lake Tai
                [[119.70, 30.30], [119.95, 30.35], [120.05, 30.40], [120.20, 30.60],
                 [120.30, 30.90], [120.25, 31.10], [120.20, 31.15]]],
    # Bolan, down from the pass to the Kachhi plain and the Indus
    'indus':   [[[67.20, 29.90], [67.50, 29.60], [67.72, 29.38], [67.95, 29.10],
                 [68.20, 28.80], [68.50, 28.50], [68.80, 28.20], [68.94, 27.98]]],
    # Lower Amazon and the Pará channel either side of Marajó island
    'amazon':  [[[-51.64, -2.00], [-51.30, -1.70], [-50.90, -1.30], [-50.40, -0.90],
                 [-50.05, -0.60]],
                [[-51.20, -1.60], [-50.60, -1.62], [-49.90, -1.40], [-49.40, -1.20],
                 [-48.60, -1.20]]],
    # Tonlé Sap river from the Mekong to the lake, and the Siem Reap river at Angkor
    'mekong':  [[[105.00, 11.58], [104.85, 11.85], [104.65, 12.10], [104.50, 12.35]],
                [[103.85, 13.60], [103.87, 13.41], [103.90, 13.20], [103.95, 13.05]]],
    # Ramis and Pucará, the lake's main inflow — Pukara sits on this, not on the
    # Desaguadero outlet 215 km south
    'titicaca': [[[-70.62, -14.92], [-70.45, -15.02], [-70.36, -15.11],
                  [-70.22, -15.20], [-70.05, -15.28], [-69.92, -15.35]]],
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
    'pulvar': (53.40, 29.45), 'yao': (121.62, 29.92), 'sabarmati': (72.25, 21.85),
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
    dropped = 0
    for f in fetch('ne_50m_rivers_lake_centerlines.geojson')['features']:
        name = f['properties'].get('name')
        for key, names in SYSTEMS.items():
            if name in names:
                g = f['geometry']
                lines = ([g['coordinates']] if g['type'] == 'LineString'
                         else g['coordinates'])
                for line in lines:
                    box = BBOX.get(key)
                    if box:
                        xs = [c[0] for c in line]; ys = [c[1] for c in line]
                        if (max(xs) < box[0] or min(xs) > box[1] or
                                max(ys) < box[2] or min(ys) > box[3]):
                            dropped += 1          # same name, wrong continent
                            continue
                    seg = round_pts(rdp([(c[0], c[1]) for c in line], 0.025), 3)
                    if len(seg) > 1:
                        rivers.setdefault(key, []).append(seg)
    if dropped:
        print('dropped %d features whose name matched but whose location did not' % dropped)
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
