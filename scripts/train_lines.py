#!/usr/bin/env python3
"""Route trains along named lines using OSM data (standard library only).

Line definitions live in scripts/train_lines.json:
  {"narita-tokyo": [{"line": "Keisei|京成", "from": "Narita", "to": "Nippori"}], ...}
`line` is a regex matched against the OSM route relation's name tags; `from`/`to`
are station names (English or Japanese). A reversed key (to-from) reuses the route backwards.
"""
import heapq
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS_URLS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
LINES_FILE = Path(__file__).with_name("train_lines.json")
HEADERS = {"User-Agent": "reiseblogg/1.0 (personal travel blog)"}
JAPAN_BBOX = "24,122,46,146"


def _haversine_m(a, b):
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _overpass(query, retries=3):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for attempt in range(retries):
        for url in OVERPASS_URLS:
            try:
                req = urllib.request.Request(url, data=data, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=240) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                last = e
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass request failed: {last}")


def _escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _find_stations(name, bbox=JAPAN_BBOX):
    n = _escape(name)
    pat = f"^{n}( Station| 駅)?$"
    q = (
        f'[out:json][timeout:60];nwr["railway"~"^(station|halt)$"]'
        f'["name:en"~"{pat}",i]({bbox});out center;'
        f'nwr["railway"~"^(station|halt)$"]["name"~"{pat}",i]({bbox});out center;'
    )
    out = []
    for e in _overpass(q).get("elements", []):
        c = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        out.append(c)
    return out


def _line_graph(line_regex, bbox):
    """Return (adjacency, node coords) from every way in matching route relations."""
    rx = _escape(line_regex)
    q = (
        f'[out:json][timeout:180];'
        f'relation["route"~"^(train|railway)$"]["name"~"{rx}",i]({bbox})->.r;'
        f'way(r.r)->.w;.w out geom;'
    )
    adj, coords = {}, {}
    for e in _overpass(q).get("elements", []):
        if e.get("type") != "way":
            continue
        ids, geom = e.get("nodes", []), e.get("geometry", [])
        if len(ids) != len(geom):
            continue
        for nid, g in zip(ids, geom):
            if g:
                coords[nid] = (g["lat"], g["lon"])
        for a, b in zip(ids[:-1], ids[1:]):
            if a in coords and b in coords:
                w = _haversine_m(coords[a], coords[b])
                adj.setdefault(a, []).append((b, w))
                adj.setdefault(b, []).append((a, w))
    return adj, coords


def _nearest_node(coords, point):
    best, best_d = None, float("inf")
    for nid, c in coords.items():
        d = _haversine_m(c, point)
        if d < best_d:
            best, best_d = nid, d
    return best, best_d


def _dijkstra(adj, src, dst):
    dist, prev = {src: 0.0}, {}
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == dst:
            break
        if d > dist.get(u, float("inf")):
            continue
        for v, w in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    if dst not in dist:
        return None, None
    path, cur = [dst], dst
    while cur != src:
        cur = prev[cur]
        path.append(cur)
    return dist[dst], path[::-1]


def compute_leg(line_regex, from_station, to_station):
    """Shortest track path on the named line(s) between two stations."""
    starts = _find_stations(from_station)
    ends = _find_stations(to_station)
    if not starts:
        raise RuntimeError(f'Station not found: "{from_station}"')
    if not ends:
        raise RuntimeError(f'Station not found: "{to_station}"')
    pts = starts + ends
    pad = 0.15
    bbox = (
        f"{min(p[0] for p in pts) - pad},{min(p[1] for p in pts) - pad},"
        f"{max(p[0] for p in pts) + pad},{max(p[1] for p in pts) + pad}"
    )
    adj, coords = _line_graph(line_regex, bbox)
    if not coords:
        raise RuntimeError(f'No track found for line "{line_regex}"')

    def snap(cands):
        return min((_nearest_node(coords, c) + (c,) for c in cands), key=lambda t: t[1])

    s_node, s_d, _ = snap(starts)
    e_node, e_d, _ = snap(ends)
    if s_d > 1500 or e_d > 1500:
        raise RuntimeError(
            f'Stations are not on line "{line_regex}" '
            f'({from_station}: {s_d:.0f} m, {to_station}: {e_d:.0f} m from track)'
        )
    dist, path = _dijkstra(adj, s_node, e_node)
    if path is None:
        raise RuntimeError(f'No connected track on "{line_regex}" from {from_station} to {to_station}')
    return dist, [coords[n] for n in path]


def load_lines():
    if LINES_FILE.exists():
        return json.loads(LINES_FILE.read_text(encoding="utf-8"))
    return {}


def save_lines(lines):
    LINES_FILE.write_text(json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_legs(from_id, to_id):
    """Return the leg list for a route, reversing a stored to-from route if needed."""
    lines = load_lines()
    if f"{from_id}-{to_id}" in lines:
        return lines[f"{from_id}-{to_id}"]
    rev = lines.get(f"{to_id}-{from_id}")
    if rev:
        return [{"line": leg["line"], "from": leg["to"], "to": leg["from"]} for leg in reversed(rev)]
    return None


def parse_legs(text):
    """Parse 'Keisei: Narita > Nippori; Joban: Nippori > Kashiwa' into legs."""
    legs = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        line, _, stations = part.partition(":")
        a, _, b = stations.partition(">")
        if not (line.strip() and a.strip() and b.strip()):
            raise ValueError(f'Cannot parse "{part}" (expected "Line: From > To")')
        legs.append({"line": line.strip(), "from": a.strip(), "to": b.strip()})
    return legs


def compute_route(legs):
    """Chain the legs; returns (meters, [(lat, lon), ...])."""
    total, coords = 0.0, []
    for leg in legs:
        d, c = compute_leg(leg["line"], leg["from"], leg["to"])
        total += d
        coords.extend(c if not coords else c[1:])
    return total, coords


def train_route(from_id, to_id, origin=None, dest=None):
    """(meters, coords) using named lines when defined, else whole-network OSM routing."""
    legs = get_legs(from_id, to_id)
    if not legs and sys.stdin.isatty():
        print(f"No train lines stored for {from_id} -> {to_id}.")
        print('Enter lines as "Line: From > To; Line: From > To" (e.g. "Keisei: Narita > Nippori").')
        text = input("Train lines (Enter for slow automatic routing): ").strip()
        if text:
            legs = parse_legs(text)
            lines = load_lines()
            lines[f"{from_id}-{to_id}"] = legs
            save_lines(lines)
    if legs:
        return compute_route(legs)
    from compute_train_distance import compute_distance_and_path
    return compute_distance_and_path(origin, dest, padding_deg=0.5)


if __name__ == "__main__":
    route = sys.argv[1] if len(sys.argv) > 1 else "narita-tokyo"
    a, _, b = route.partition("-")
    legs = get_legs(a, b)
    t = time.time()
    meters, pts = compute_route(legs)
    print(f"{route}: {meters / 1000:.1f} km, {len(pts)} points, {time.time() - t:.1f} s")
