#!/usr/bin/env python3
"""Compute approximate train distance between two points using OSM railway ways.

Usage examples:
  python scripts/compute_train_distance.py --orig-lat 35.6895 --orig-lon 139.6917 --dest-lat 34.6937 --dest-lon 135.5023
  python scripts/compute_train_distance.py --orig "Tokyo Station" --dest "Osaka Station" --geocode

Dependencies: osmnx, networkx, requests
Install: pip install osmnx networkx requests
"""
import argparse
import sys
import math
import requests

def geocode(name, email=None):
    url = 'https://nominatim.openstreetmap.org/search'
    headers = {'User-Agent': f'compute_train_distance/1.0 ({email or "anonymous"})'}
    params = {'q': name, 'format': 'json', 'limit': 1}
    r = requests.get(url, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f'No geocode result for "{name}"')
    return float(data[0]['lat']), float(data[0]['lon'])

def compute_distance_m(origin, dest, padding_deg=0.5):
    # delegate to the richer function that also returns path coordinates
    dist_m, _coords = compute_distance_and_path(origin, dest, padding_deg=padding_deg)
    return dist_m


def compute_distance_and_path(origin, dest, padding_deg=0.5):
    # lazy import to allow graceful error if osmnx isn't installed
    import osmnx as ox
    import networkx as nx

    olat, olon = origin
    dlat, dlon = dest

    north = max(olat, dlat) + padding_deg
    south = min(olat, dlat) - padding_deg
    east = max(olon, dlon) + padding_deg
    west = min(olon, dlon) - padding_deg

    # Fetch railway ways only
    custom_filter = '["railway"~"rail|light_rail|subway|tram"]'
    bbox = (north, south, east, west)
    G = ox.graph_from_bbox(bbox, network_type='all', simplify=True, custom_filter=custom_filter)

    # If graph is empty, raise
    if len(G.nodes) == 0:
        raise RuntimeError('No railway data found in bbox; try increasing padding or check coverage')

    # nearest nodes on the railway graph
    orig_node = ox.distance.nearest_nodes(G, X=olon, Y=olat)
    dest_node = ox.distance.nearest_nodes(G, X=dlon, Y=dlat)

    # ensure undirected weighted graph for length
    Hu = nx.Graph()
    for u, v, data in G.edges(data=True):
        length = data.get('length', None)
        if length is None:
            # fallback: compute great-circle distance between nodes
            uxy = (G.nodes[u].get('y'), G.nodes[u].get('x'))
            vxy = (G.nodes[v].get('y'), G.nodes[v].get('x'))
            length = haversine_m(uxy, vxy)
        # add edge (undirected)
        if Hu.has_edge(u, v):
            # keep smallest weight
            Hu[u][v]['weight'] = min(Hu[u][v]['weight'], length)
        else:
            Hu.add_edge(u, v, weight=length)

    if not nx.has_path(Hu, orig_node, dest_node):
        raise RuntimeError('No path found between points on railway subgraph')

    path = nx.shortest_path(Hu, source=orig_node, target=dest_node, weight='weight')
    distance_m = sum(Hu[u][v]['weight'] for u, v in zip(path[:-1], path[1:]))

    # extract node coordinates from original graph G (y=lat, x=lon)
    coords = []
    for n in path:
        node = G.nodes.get(n, {})
        lat = node.get('y')
        lon = node.get('x')
        if lat is None or lon is None:
            # fallback to 0,0 if missing (shouldn't happen)
            coords.append((0.0, 0.0))
        else:
            coords.append((lat, lon))

    return distance_m, coords

    olat, olon = origin
    dlat, dlon = dest

    north = max(olat, dlat) + padding_deg
    south = min(olat, dlat) - padding_deg
    east = max(olon, dlon) + padding_deg
    west = min(olon, dlon) - padding_deg

    # Fetch railway ways only
    custom_filter = '["railway"~"rail|light_rail|subway|tram"]'
    bbox = (north, south, east, west)
    G = ox.graph_from_bbox(bbox, network_type='all', simplify=True, custom_filter=custom_filter)

    # If graph is empty, raise
    if len(G.nodes) == 0:
        raise RuntimeError('No railway data found in bbox; try increasing padding or check coverage')

    # nearest nodes on the railway graph
    orig_node = ox.distance.nearest_nodes(G, X=olon, Y=olat)
    dest_node = ox.distance.nearest_nodes(G, X=dlon, Y=dlat)

    # ensure undirected weighted graph for length
    Hu = nx.Graph()
    for u, v, data in G.edges(data=True):
        length = data.get('length', None)
        if length is None:
            # fallback: compute great-circle distance between nodes
            uxy = (G.nodes[u].get('y'), G.nodes[u].get('x'))
            vxy = (G.nodes[v].get('y'), G.nodes[v].get('x'))
            length = haversine_m(uxy, vxy)
        # add edge (undirected)
        if Hu.has_edge(u, v):
            # keep smallest weight
            Hu[u][v]['weight'] = min(Hu[u][v]['weight'], length)
        else:
            Hu.add_edge(u, v, weight=length)

    if not nx.has_path(Hu, orig_node, dest_node):
        raise RuntimeError('No path found between points on railway subgraph')

    path = nx.shortest_path(Hu, source=orig_node, target=dest_node, weight='weight')
    distance_m = sum(Hu[u][v]['weight'] for u, v in zip(path[:-1], path[1:]))
    return distance_m

def haversine_m(a, b):
    # a, b = (lat, lon)
    R = 6371000.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    hav = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(hav))

def parse_args():
    p = argparse.ArgumentParser(description='Compute approximate train distance via OSM railway network')
    group_o = p.add_mutually_exclusive_group(required=True)
    group_o.add_argument('--orig', help='Origin place name (requires --geocode)')
    group_o.add_argument('--orig-latlon', nargs=2, metavar=('LAT','LON'), type=float, help='Origin coordinates')
    group_d = p.add_mutually_exclusive_group(required=True)
    group_d.add_argument('--dest', help='Destination place name (requires --geocode)')
    group_d.add_argument('--dest-latlon', nargs=2, metavar=('LAT','LON'), type=float, help='Destination coordinates')
    p.add_argument('--geocode', action='store_true', help='Geocode place names using Nominatim')
    p.add_argument('--padding', type=float, default=0.5, help='Degrees padding around bbox (default 0.5)')
    p.add_argument('--email', help='Contact email for Nominatim User-Agent (recommended)')
    return p.parse_args()

def main():
    args = parse_args()

    try:
        if args.geocode:
            if args.orig:
                orig = geocode(args.orig, email=args.email)
            else:
                orig = tuple(args.orig_latlon)
            if args.dest:
                dest = geocode(args.dest, email=args.email)
            else:
                dest = tuple(args.dest_latlon)
        else:
            if args.orig:
                print('Error: --orig requires --geocode to resolve names', file=sys.stderr); sys.exit(2)
            orig = tuple(args.orig_latlon)
            dest = tuple(args.dest_latlon)

        print(f'Computing railway distance between {orig} and {dest} (padding={args.padding})...')
        dist_m = compute_distance_m(orig, dest, padding_deg=args.padding)
        print(f'Approximate train distance: {dist_m/1000:.2f} km')
    except Exception as e:
        print('Error:', e, file=sys.stderr)
        sys.exit(3)

if __name__ == '__main__':
    main()
