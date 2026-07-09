#!/usr/bin/env python3
from pathlib import Path
import re
import sys

# import from add_location (compute_route_distance reads coordinates from _data/map.yml)
import importlib.util
add_location_path = Path(__file__).parent / 'add_location.py'
if not add_location_path.exists():
    print('scripts/add_location.py not found')
    sys.exit(1)
spec = importlib.util.spec_from_file_location('add_location', str(add_location_path))
add_location = importlib.util.module_from_spec(spec)
spec.loader.exec_module(add_location)
compute_route_distance = getattr(add_location, 'compute_route_distance')

p = Path('_data/map.yml')
if not p.exists():
    print('_data/map.yml not found')
    sys.exit(1)
text = p.read_text(encoding='utf-8')
routes_match = re.search(r'^routes:\s*', text, flags=re.M)
if not routes_match:
    print('No routes: section found in _data/map.yml')
    sys.exit(0)

routes_text = text[routes_match.end():]
pattern = re.compile(r'(^\s*-\s*from:.*?)(?=^\s*-\s*from:|\Z)', flags=re.M|re.S)
changed = False
new_routes_text = routes_text
for m in pattern.finditer(routes_text):
    block = m.group(1)
    if re.search(r'distance_km:\s*', block):
        continue
    from_m = re.search(r'from:\s*([^\n]+)', block)
    to_m = re.search(r'to:\s*([^\n]+)', block)
    if not from_m or not to_m:
        print('Skipping malformed route block:')
        print(block)
        continue
    from_id = from_m.group(1).strip()
    to_id = to_m.group(1).strip()
    mode_m = re.search(r'mode:\s*(?:"([^"]+)"|([^\n]+))', block)
    mode = (mode_m.group(1) if mode_m and mode_m.group(1) else (mode_m.group(2) if mode_m and mode_m.group(2) else '')).strip() if mode_m else ''
    try:
        dk = compute_route_distance(from_id, to_id, mode)
    except Exception as e:
        print(f'Error computing distance for {from_id} -> {to_id}:', e)
        dk = None
    if dk is None:
        print(f'Could not compute distance for {from_id} -> {to_id}; leaving unchanged.')
        continue
    dk_line = f'    distance_km: {round(float(dk),1)}\n'
    # insert after mode line if present, else after to line
    if mode_m:
        new_block = re.sub(r'(mode:.*\n)', r"\1" + dk_line, block, count=1)
    else:
        new_block = re.sub(r'(to:.*\n)', r"\1" + dk_line, block, count=1)
    new_routes_text = new_routes_text.replace(block, new_block, 1)
    changed = True

if changed:
    backup = p.with_name(p.name + '.bak.auto')
    backup.write_text(text, encoding='utf-8')
    new_text = text[:routes_match.end()] + new_routes_text
    p.write_text(new_text, encoding='utf-8')
    print('Wrote distance_km for routes. Backup saved to', str(backup))
else:
    print('No routes updated; all have distance_km or no computable distance.')
