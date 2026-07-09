#!/usr/bin/env python3
"""
Interactive add-location helper for _data/map.yml.
Only interactive mode is supported: run `./scripts/add_location.py` and follow prompts.
Supports inserting ordered ghost intermediates between the previous location and
the newly added main location; routes and distances will be computed and written
after the user confirms the planned sequence.
"""
import sys
import os
import urllib.parse
import urllib.request
import json
import re
from pathlib import Path
import urllib.error

NOMINATIM = "https://nominatim.openstreetmap.org/search"
CONTACT_EMAIL = os.environ.get("NOMINATIM_EMAIL") or os.environ.get("EMAIL") or "rene015@live.no"
HEADERS = {
    "User-Agent": f"add_location/1.0 ({CONTACT_EMAIL})",
    "From": CONTACT_EMAIL,
}


def geocode(query: str):
    params = {"q": query, "format": "json", "limit": 1}
    url = NOMINATIM + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"HTTP error from geocoding service: {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"Error contacting geocoding service: {e}")
        return None
    arr = json.loads(data)
    if not arr:
        return None
    return arr[0]


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return s.strip("-")


def format_block(label: str, lat: str, lon: str, country: str = None, ghost: bool = False):
    id_ = slugify(label)
    try:
        latf = float(lat)
        lonf = float(lon)
        lat_s = f"{latf:.4f}"
        lon_s = f"{lonf:.4f}"
    except Exception:
        lat_s = lat
        lon_s = lon
    parts = [
        f"  - id: {id_}\n",
        f"    label: {label}\n",
    ]
    if country:
        parts.append(f"    country: {country}\n")
    if ghost:
        parts.append(f"    ghost: true\n")
    parts.extend([
        f"    lat: {lat_s}\n",
        f"    lng: {lon_s}\n",
    ])
    # ensure a blank line after each generated location block
    return "".join(parts) + "\n"


def append_to_map(block: str, force: bool = False):
    p = Path("_data/map.yml")
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("locations:\n\n", encoding="utf-8")
    text = p.read_text(encoding="utf-8")
    block = block.rstrip() + "\n\n"
    m_id = re.search(r"id:\s*([a-z0-9-]+)", block)
    if not m_id:
        print("Could not determine id from generated block.")
        return False
    id_ = m_id.group(1)
    exists = re.search(r"^\s*-\s*id:\s*" + re.escape(id_) + r"\b", text, flags=re.M)
    if exists and not force:
        print(f"Entry with id '{id_}' already exists in _data/map.yml. Use --force to replace.")
        return False
    backup = p.with_name(p.name + ".bak")
    backup.write_text(text, encoding="utf-8")
    if exists and force:
        m = re.search(r"^\s*-\s*id:\s*" + re.escape(id_) + r"\b", text, flags=re.M)
        start = m.start()
        next_entry = re.search(r"\n\s*-\s*id:\s*", text[m.end():])
        if next_entry:
            end = m.end() + next_entry.start()
        else:
            routes = re.search(r"^routes:\s*", text, flags=re.M)
            end = routes.start() if routes else len(text)
        new_text = text[:start] + block + text[end:]
    else:
        routes = re.search(r"^routes:\s*", text, flags=re.M)
        if routes:
            idx = routes.start()
            new_text = text[:idx] + block + text[idx:]
        else:
            new_text = text + block if text.endswith("\n") else text + "\n" + block
    p.write_text(new_text, encoding="utf-8")
    return True


def get_last_location_id() -> str | None:
    p = Path("_data/map.yml")
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    ids = re.findall(r"^\s*-\s*id:\s*([a-z0-9-]+)", text, flags=re.M)
    return ids[-1] if ids else None


def get_location_coords(loc_id: str):
    p = Path("_data/map.yml")
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    # capture the block for this id up to the next id: or routes: or EOF
    m = re.search(r"(^\s*-\s*id:\s*" + re.escape(loc_id) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", text, flags=re.M)
    if not m:
        return None
    block = m.group(1)
    lat_m = re.search(r"lat:\s*([0-9+\-\.]+)", block)
    lng_m = re.search(r"lng:\s*([0-9+\-\.]+)", block)
    if lat_m and lng_m:
        try:
            return float(lat_m.group(1)), float(lng_m.group(1))
        except Exception:
            return None
    return None


def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, atan2, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


def compute_route_distance(from_id: str, to_id: str, mode: str) -> float | None:
    # returns distance in kilometers (float) or None on failure
    coords_a = get_location_coords(from_id)
    coords_b = get_location_coords(to_id)
    if not coords_a or not coords_b:
        return None
    lat1, lon1 = coords_a
    lat2, lon2 = coords_b
    mode_l = (mode or "").lower()
    # special-case Bergen -> Bangkok: route via Munich for non-driving modes
    if from_id == 'bergen' and to_id == 'bangkok' and ('bil' not in mode_l and 'car' not in mode_l):
        munich = (48.1351, 11.5820)
        d1 = haversine(lat1, lon1, munich[0], munich[1])
        d2 = haversine(munich[0], munich[1], lat2, lon2)
        return d1 + d2

    # driving mode: use OSRM
    if 'bil' in mode_l or 'car' in mode_l:
        try:
            url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            req = urllib.request.Request(url, headers={"User-Agent": f"add_location/1.0 ({CONTACT_EMAIL})"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if data and data.get('routes'):
                meters = data['routes'][0].get('distance')
                if meters is not None:
                    return float(meters) / 1000.0
        except Exception as e:
            print(f"OSRM routing failed ({e}), falling back to great-circle distance")

    # default: great-circle distance
    return haversine(lat1, lon1, lat2, lon2)


def append_route(from_id: str, to_id: str, mode: str = "Fly", distance_km: float | None = None) -> bool:
    p = Path("_data/map.yml")
    if not p.exists():
        print("Error: _data/map.yml not found; cannot add route.")
        return False
    text = p.read_text(encoding="utf-8")
    backup = p.with_name(p.name + ".bak")
    backup.write_text(text, encoding="utf-8")
    routes_match = re.search(r"^routes:\s*", text, flags=re.M)
    # include computed distance_km when provided
    # normalize mode display
    mode_str = (mode or "").strip()
    mode_display = mode_str.title() if mode_str else "Annet"

    # compute distance if not provided
    dk_val = None
    if distance_km is not None:
        try:
            dk_val = float(distance_km)
        except Exception:
            dk_val = None
    if dk_val is None:
        # attempt to compute using existing helper
        try:
            dk_val = compute_route_distance(from_id, to_id, mode_str)
        except Exception:
            dk_val = None

    route_block = f"  - from: {from_id}\n    to: {to_id}\n    mode: \"{mode_display}\"\n"
    if dk_val is not None:
        try:
            route_block += f"    distance_km: {round(float(dk_val), 1)}\n"
        except Exception:
            pass
    route_block += "\n"
    if routes_match:
        m_comment = re.search(r"^# .*$", text[routes_match.end():], flags=re.M)
        end_idx = routes_match.end() + m_comment.start() if m_comment else len(text)
        new_text = text[:end_idx] + route_block + text[end_idx:]
    else:
        new_text = text + "routes:\n" + route_block if text.endswith("\n") else text + "\n" + "routes:\n" + route_block
    p.write_text(new_text, encoding="utf-8")
    return True


def list_locations():
    p = Path("_data/map.yml")
    if not p.exists():
        print("_data/map.yml not found.")
        return
    text = p.read_text(encoding="utf-8")
    ids = re.findall(r"^\s*-\s*id:\s*([a-z0-9-]+)", text, flags=re.M)
    labels = re.findall(r"^\s*label:\s*(.+)$", text, flags=re.M)
    ghosts = re.findall(r"^\s*ghost:\s*(true|false)", text, flags=re.M)
    print("Locations in _data/map.yml:")
    for i, idv in enumerate(ids):
        label = labels[i] if i < len(labels) else idv
        ghost = (ghosts[i].lower() == 'true') if i < len(ghosts) else False
        print(f"- {idv}: {label}{' (ghost)' if ghost else ''}")


def interactive_additional_ghosts(append: bool, force: bool):
    # Deprecated: use interactive insertion of intermediates when adding routes.
    return


def interactive_insert_intermediates(prev_id: str | None, new_id: str, append: bool, force: bool, default_mode: str = "Fly", main_block: str | None = None):
    """Interactively add ghost intermediate stops between prev_id and new_id.
    For each added ghost, append it to locations (ghost: true) and append a route
    from the current last node to the ghost with a per-segment transport mode.
    Finally append the route from last intermediate to new_id.
    """
    if not prev_id:
        print("No previous location to link from.")
        return
    try:
        more = input(f"Add intermediate (ghost) stops between '{prev_id}' and '{new_id}'? [y/N]: ").strip().lower()
    except KeyboardInterrupt:
        return
    # If the main location already exists in the file, capture its block so we
    # can re-insert it after the intermediates. Do NOT remove it yet; wait for
    # user confirmation.
    if append:
        p = Path("_data/map.yml")
        txt = p.read_text(encoding='utf-8')
        m_main = re.search(r"(^\s*-\s*id:\s*" + re.escape(new_id) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", txt, flags=re.M)
        if m_main:
            extracted = m_main.group(1)
            if not main_block:
                # normalize extracted main block to ensure a blank line after it
                main_block = extracted.rstrip() + "\n\n"

    current_from = prev_id
    planned_routes = []
    ghost_blocks = []
    ghost_ids = []
    while more in ("y", "yes"):
        try:
            ccity = input("Ghost city name: ").strip()
            ccountry = input("Country: ").strip()
        except KeyboardInterrupt:
            break
        if not ccity or not ccountry:
            print("City and country required; skipping.")
        else:
            cquery = f"{ccity}, {ccountry}"
            cres = geocode(cquery)
            if not cres:
                print(f"Geocoding failed for {cquery}; you may enter coordinates manually or skip.")
                try:
                    lat = input("Enter latitude (or leave blank to skip): ").strip()
                    if not lat:
                        print("Skipping this ghost city.")
                        more = input("Add another ghost city? [y/N]: ").strip().lower()
                        continue
                    lon = input("Enter longitude: ").strip()
                except KeyboardInterrupt:
                    break
                clabel = ccity
                clat = lat
                clng = lon
                ccountry_name = ccountry
            else:
                clabel = ccity
                caddr = cres.get('address', {}) if isinstance(cres, dict) else {}
                ccountry_name = caddr.get('country') or ccountry
                clat = cres.get('lat')
                clng = cres.get('lon')

            # prepare ghost block (do not write locations yet)
            cblock = format_block(clabel, clat, clng, country=ccountry_name, ghost=True)
            new_ghost_id = re.search(r"id:\s*([a-z0-9-]+)", cblock).group(1)
            print("\nPrepared ghost location (will be inserted in order):\n")
            print(cblock)
            # collect ghost for later insertion
            ghost_blocks.append(cblock)
            ghost_ids.append(new_ghost_id)
            # ask mode for segment current_from -> new_ghost_id and record planned route
            try:
                mode = input(f"Transport mode from '{current_from}' to '{new_ghost_id}': ").strip() or default_mode
            except KeyboardInterrupt:
                mode = default_mode
            dist_km = compute_route_distance(current_from, new_ghost_id, mode)
            planned_routes.append((current_from, new_ghost_id, mode, dist_km))
            print(f"Planned route {current_from} -> {new_ghost_id} ({mode})")
            current_from = new_ghost_id

        try:
            more = input("Add another intermediate ghost city? [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            break

    # Always ask for the final leg (from current_from — which may be last ghost — to the new main)
    try:
        mode_last = input(f"Transport mode from '{current_from}' to '{new_id}': ").strip() or default_mode
    except KeyboardInterrupt:
        mode_last = default_mode
    dk = compute_route_distance(current_from, new_id, mode_last)
    planned_routes.append((current_from, new_id, mode_last, dk))

    # show planned sequence and ask for confirmation before writing
    seq_ids = [prev_id] + ghost_ids + [new_id]
    p = Path("_data/map.yml")
    txt = p.read_text(encoding='utf-8')
    labels = {}
    for m in re.finditer(r"^\s*-\s*id:\s*([a-z0-9-]+)[\s\S]*?label:\s*(.+)$", txt, flags=re.M):
        labels[m.group(1)] = m.group(2).strip()
    for i, bid in enumerate(ghost_ids):
        if bid not in labels:
            lb = re.search(r"label:\s*(.+)", ghost_blocks[i])
            if lb: labels[bid] = lb.group(1).strip()
    if new_id not in labels and main_block:
        lb = re.search(r"label:\s*(.+)", main_block)
        if lb: labels[new_id] = lb.group(1).strip()

    seq_display = ' → '.join([f"{sid} ({labels.get(sid, sid)})" for sid in seq_ids])
    try:
        ok = input(f"Planned sequence: {seq_display}\nConfirm write to _data/map.yml? [y/N]: ").strip().lower()
    except KeyboardInterrupt:
        ok = 'n'
    if ok not in ('y', 'yes'):
        print('Aborted — no changes written.')
        return

    # perform insertion: remove any existing instances of ghosts/main and insert in order
    routes_match = re.search(r"^routes:\s*", txt, flags=re.M)
    locs_section = re.search(r"^locations:\s*", txt, flags=re.M)
    if not locs_section:
        print("Could not find locations: section in _data/map.yml; aborting insertion.")
        return
    start_idx = locs_section.end()
    end_idx = routes_match.start() if routes_match else len(txt)
    locs_text = txt[start_idx:end_idx]
    blocks = re.findall(r"(\s*-\s*id:\s*[a-z0-9-]+[\s\S]*?)(?=^\s*-\s*id:|\Z)", locs_text, flags=re.M)
    kept = []
    for b in blocks:
        bid = re.search(r"id:\s*([a-z0-9-]+)", b).group(1)
        if bid in ghost_ids:
            continue
        if main_block and bid == new_id:
            continue
        kept.append(b)
    kept_ids = [re.search(r"id:\s*([a-z0-9-]+)", b).group(1) for b in kept]
    try:
        insert_idx = kept_ids.index(prev_id) + 1
    except ValueError:
        insert_idx = len(kept)
    new_blocks = kept[:insert_idx]
    new_blocks.extend(ghost_blocks)
    if main_block:
        new_blocks.append(main_block)
    new_blocks.extend(kept[insert_idx:])
    new_locs_text = "".join(new_blocks)
    # DEBUG: show internal lists to help track missing ghost insertion
    print(f"DEBUG: found {len(blocks)} existing blocks, kept_ids={kept_ids}, ghost_ids={ghost_ids}, ghost_blocks={len(ghost_blocks)}")
    new_txt = txt[:start_idx] + new_locs_text + txt[end_idx:]
    p.write_text(new_txt, encoding='utf-8')
    print(f"Inserted intermediates and main location into _data/map.yml in order.")

    # append planned routes now
    for fr, to, md, dk in planned_routes:
        if append_route(fr, to, md, distance_km=dk):
            print(f"Wrote route {fr} -> {to} ({md})")
        else:
            print(f"Failed to write route {fr} -> {to} ({md})")
    # post-check: ensure all ghost blocks are present; if any are missing (due to
    # regex edge-cases), insert them sequentially after the previous id.
    txt2 = p.read_text(encoding='utf-8')
    cur_prev = prev_id
    for i, gid in enumerate(ghost_ids):
        if re.search(r"^\s*-\s*id:\s*" + re.escape(gid) + r"\b", txt2, flags=re.M):
            cur_prev = gid
            continue
        # insert this ghost block after cur_prev
        m = re.search(r"(^\s*-\s*id:\s*" + re.escape(cur_prev) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", txt2, flags=re.M)
        if not m:
            # fallback: append before routes section
            routes_match2 = re.search(r"^routes:\s*", txt2, flags=re.M)
            idx = routes_match2.start() if routes_match2 else len(txt2)
            txt2 = txt2[:idx] + ghost_blocks[i] + txt2[idx:]
        else:
            insert_pos = m.end()
            txt2 = txt2[:insert_pos] + ghost_blocks[i] + txt2[insert_pos:]
        cur_prev = gid
    # write back if we made changes
    if txt2 != p.read_text(encoding='utf-8'):
        p.write_text(txt2, encoding='utf-8')


def main():
    # Interactive-only entry point
    append = True
    force = False
    try:
        city = input("City: ").strip()
        country = input("Country: ").strip()
    except KeyboardInterrupt:
        print()
        return
    if not city or not country:
        print("City and country required.")
        return
    query = f"{city}, {country}"

    if not os.environ.get("NOMINATIM_EMAIL") and not os.environ.get("EMAIL"):
        print(f"Using default contact email: {CONTACT_EMAIL}")

    print(f"Querying: {query}")
    res = geocode(query)
    if not res:
        print("No results found (or geocoding failed).")
        try:
            lat = input("Enter latitude (or leave blank to cancel): ").strip()
            if not lat:
                print("Cancelled.")
                return
            lon = input("Enter longitude: ").strip()
            if not lon:
                print("Cancelled.")
                return
        except KeyboardInterrupt:
            print()
            return
        label = city
        block = format_block(label, lat, lon, country=country)
        print("\nAdd this to `_data/map.yml` under `locations:`:\n")
        print(block)
        if append:
            prev_id = get_last_location_id()
            new_id = re.search(r"id:\s*([a-z0-9-]+)", block).group(1)
            try:
                ans = input(f"Add a route from last location '{prev_id}' to '{new_id}'? [y/N]: ").strip().lower()
            except KeyboardInterrupt:
                ans = ""
            if ans in ("y", "yes"):
                mode = input("Transport mode (Fly/Tog/Bil/etc.): ").strip() or "Fly"
                if prev_id:
                    # interactive insertion of intermediates/ghosts + per-segment routes
                    interactive_insert_intermediates(prev_id, new_id, append, force, default_mode=mode, main_block=block)
                else:
                    print("No previous location found to link from.")
            else:
                # user didn't want to add routes/intermediates: append main location now
                ok = append_to_map(block, force=force)
                if ok:
                    print("Appended to _data/map.yml")
                else:
                    print("Failed to append to _data/map.yml")
        return

    display_name = res.get("display_name", f"{city}, {country}")
    lat = res.get("lat")
    lon = res.get("lon")
    label = city
    address = res.get('address', {}) if isinstance(res, dict) else {}
    country_name = address.get('country') or country
    block = format_block(label, lat, lon, country=country_name)
    print("\nAdd this to `_data/map.yml` under `locations:`:\n")
    print(block)

    if append:
        prev_id = get_last_location_id()
        new_id = re.search(r"id:\s*([a-z0-9-]+)", block).group(1)
        # if new_id is same as prev_id, avoid prompting to add a self-route
        if prev_id and new_id and prev_id == new_id:
            print(f"Location '{new_id}' is already the last location; nothing to link.")
            return
        try:
            ans = input(f"Add a route from last location '{prev_id}' to '{new_id}'? [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            ans = ""
        if ans in ("y", "yes"):
            mode = input("Transport mode (Fly/Tog/Bil/etc.): ").strip() or "Fly"
            if prev_id:
                interactive_insert_intermediates(prev_id, new_id, append, force, default_mode=mode, main_block=block)
            else:
                print("No previous location found to link from.")
        else:
            ok = append_to_map(block, force=force)
            if ok:
                print("Appended to _data/map.yml")
            else:
                print("Failed to append to _data/map.yml")


if __name__ == "__main__":
    main()
