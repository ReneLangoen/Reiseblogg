#!/usr/bin/env python3
"""
Interactive add-location helper for _data/map.yml.
Only interactive mode is supported: run `./scripts/add_location.py` and follow prompts.
Supports inserting ordered ghost intermediates between the previous location and
the newly added main location; routes and distances will be computed and written
after the user confirms the planned sequence.
"""
import os
import argparse
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

# runtime flags
DRY_RUN = False
AUTO_YES = False

def _backup(p: Path, text: str):
    bak = p.with_name(p.name + ".bak")
    bak.write_text(text, encoding='utf-8')
    print(f"Backup written to {bak}")
    return bak


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
    new_is_ghost = bool(re.search(r"ghost:\s*true", block))
    exists = re.search(r"^\s*-\s*id:\s*" + re.escape(id_) + r"\b", text, flags=re.M)
    if exists and not force:
        m_existing = re.search(r"(^\s*-\s*id:\s*" + re.escape(id_) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", text, flags=re.M)
        existing_block = m_existing.group(1) if m_existing else ''
        existing_is_ghost = bool(re.search(r"ghost:\s*true", existing_block))
        new_is_ghost = bool(re.search(r"ghost:\s*true", block))
        # If existing is ghost but new is non-ghost, allow replacement (upgrade)
        if existing_is_ghost and not new_is_ghost:
            print(f"Upgrading existing ghost entry '{id_}' to non-ghost")
            force = True
        # If existing is non-ghost and new is non-ghost, reuse the existing
        # entry instead of inserting a duplicate. In that case, append the
        # upcoming week number to a `weeks` list on the existing block.
        elif (not existing_is_ghost) and (not new_is_ghost):
            # compute next week number as count of current non-ghost locations + 1
            blocks = re.findall(r"(^\s*-\s*id:\s*[a-z0-9-]+[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", text, flags=re.M)
            non_ghost_count = sum(1 for b in blocks if not re.search(r"ghost:\s*true", b))
            week_num = non_ghost_count + 1
            existing = existing_block
            # try inline weeks: [1,2] form
            m_inline = re.search(r"weeks:\s*\[([^\]]*)\]", existing)
            if m_inline:
                nums = [int(n) for n in re.findall(r"\d+", m_inline.group(1))]
                if week_num not in nums:
                    nums.append(week_num)
                    nums = sorted(set(nums))
                    new_inline = f"weeks: [{', '.join(str(n) for n in nums)}]"
                    existing = existing[:m_inline.start()] + new_inline + existing[m_inline.end():]
            else:
                # try block form: weeks:\n      - 3\n      - 5
                m_block = re.search(r"(weeks:\s*(?:\n\s*-\s*\d+\s*)+)", existing)
                if m_block:
                    nums = [int(n) for n in re.findall(r"-\s*(\d+)", m_block.group(0))]
                    if week_num not in nums:
                        nums.append(week_num)
                        nums = sorted(set(nums))
                        # replace with inline form for simplicity
                        indent = re.search(r"^(\s*)weeks:", m_block.group(0))
                        ind = indent.group(1) if indent else '    '
                        new_inline = ind + f"weeks: [{', '.join(str(n) for n in nums)}]\n"
                        existing = existing[:m_block.start()] + new_inline + existing[m_block.end():]
                else:
                    # insert inline weeks after the label line
                    m_label = re.search(r"(label:\s*.+\n)", existing)
                    insert_after = m_label.end() if m_label else 0
                    ins = f"    weeks: [{week_num}]\n"
                    existing = existing[:insert_after] + ins + existing[insert_after:]

            # replace the existing block in the file text
            new_text = text[:m_existing.start(1)] + existing + text[m_existing.end(1):]
            p.write_text(new_text, encoding="utf-8")
            print(f"Reused existing location '{id_}' and recorded week {week_num}.")
            return True
        else:
            print(f"Entry with id '{id_}' already exists in _data/map.yml. Use --force to replace.")
            return False
    _backup(p, text)
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
    # If we added or replaced a non-ghost location, ensure its `weeks` entry
    # includes the current week number.
    try:
        # If the id already existed and was non-ghost, append next week
        if exists and not new_is_ghost and 'existing_block' in locals() and not existing_is_ghost:
            max_w = _get_max_week(p)
            _append_week_to_existing_block(p, id_, max_w + 1)
        else:
            # For newly inserted locations, append next week based on current max
            if not new_is_ghost:
                max_w = _get_max_week(p)
                _append_week_to_existing_block(p, id_, max_w)
    except Exception:
        pass
    return True


def _record_week_for_id(p: Path, id_: str):
    """Ensure the location block for `id_` contains a `weeks:` list
    and append the next week number if not already present.
    """
    text = p.read_text(encoding='utf-8')
    m_existing = re.search(r"(^\s*-\s*id:\s*" + re.escape(id_) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", text, flags=re.M)
    if not m_existing:
        return False
    existing = m_existing.group(1)
    # only operate on non-ghost blocks
    if re.search(r"ghost:\s*true", existing):
        # if it's still ghost, do not record week
        return False
    # compute next week number as count of current non-ghost locations + 1
    blocks = re.findall(r"(^\s*-\s*id:\s*[a-z0-9-]+[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", text, flags=re.M)
    non_ghost_count = sum(1 for b in blocks if not re.search(r"ghost:\s*true", b))
    week_num = non_ghost_count + 1
    # prefer adding week only if not present
    m_inline = re.search(r"weeks:\s*\[([^\]]*)\]", existing)
    if m_inline:
        nums = [int(n) for n in re.findall(r"\d+", m_inline.group(1))]
        if week_num in nums:
            return True
        nums.append(week_num)
        nums = sorted(set(nums))
        new_inline = f"weeks: [{', '.join(str(n) for n in nums)}]"
        new_block = existing[:m_inline.start()] + new_inline + existing[m_inline.end():]
    else:
        m_block = re.search(r"(weeks:\s*(?:\n\s*-\s*\d+\s*)+)", existing)
        if m_block:
            nums = [int(n) for n in re.findall(r"-\s*(\d+)", m_block.group(0))]
            if week_num in nums:
                return True
            nums.append(week_num)
            nums = sorted(set(nums))
            indent = re.search(r"^(\s*)weeks:", m_block.group(0))
            ind = indent.group(1) if indent else '    '
            new_inline = ind + f"weeks: [{', '.join(str(n) for n in nums)}]\n"
            new_block = existing[:m_block.start()] + new_inline + existing[m_block.end():]
        else:
            m_label = re.search(r"(label:\s*.+\n)", existing)
            insert_after = m_label.end() if m_label else 0
            ins = f"    weeks: [{week_num}]\n"
            new_block = existing[:insert_after] + ins + existing[insert_after:]

    new_text = text[:m_existing.start(1)] + new_block + text[m_existing.end(1):]
    p.write_text(new_text, encoding='utf-8')
    return True


def _recompute_weeks(p: Path):
    """Recompute and write `weeks` for all non-ghost locations based on
    their final order in the file. Ensures consistent numbering.
    """
    text = p.read_text(encoding='utf-8')
    locs_m = re.search(r"^locations:\s*", text, flags=re.M)
    if not locs_m:
        return False
    routes_m = re.search(r"^routes:\s*", text, flags=re.M)
    start = locs_m.end()
    end = routes_m.start() if routes_m else len(text)
    locs_text = text[start:end]
    blocks = re.findall(r"(\s*-\s*id:\s*[a-z0-9-]+[\s\S]*?)(?=^\s*-\s*id:|\Z)", locs_text, flags=re.M)

    new_blocks = []
    week_idx = 0
    for b in blocks:
        is_ghost = bool(re.search(r"^\s*ghost:\s*true\b", b, flags=re.M))
        # remove existing weeks entries
        b_clean = re.sub(r"^\s*weeks:\s*\[[^\]]*\]\s*$\n", '', b, flags=re.M)
        b_clean = re.sub(r"^\s*weeks:\s*(?:\n\s*-\s*\d+\s*)+", '', b_clean, flags=re.M)
        if not is_ghost:
            week_idx += 1
            # collect existing week numbers only from explicit `weeks:` entries
            existing_nums = []
            m_inline_old = re.search(r"weeks:\s*\[([^\]]*)\]", b)
            if m_inline_old:
                existing_nums = [int(n) for n in re.findall(r"\d+", m_inline_old.group(1))]
            else:
                m_block_old = re.search(r"weeks:\s*(?:\n\s*-\s*\d+\s*)+", b)
                if m_block_old:
                    existing_nums = [int(n) for n in re.findall(r"-\s*(\d+)", m_block_old.group(0))]
            # keep only existing numbers that are <= current week_idx (discard spurious larger numbers)
            nums = sorted(set([n for n in existing_nums if n>0 and n <= week_idx] + [week_idx]))
            # insert after label line
            m_label = re.search(r"(label:\s*.+\n)", b_clean)
            insert_after = m_label.end() if m_label else 0
            ins = f"    weeks: [{', '.join(str(n) for n in nums)}]\n"
            b_new = b_clean[:insert_after] + ins + b_clean[insert_after:]
        else:
            b_new = b_clean
        new_blocks.append(b_new.rstrip() + "\n\n")

    new_locs_text = ''.join(new_blocks)
    new_text = text[:start] + new_locs_text + text[end:]
    if DRY_RUN:
        print('DRY RUN: would recompute weeks in _data/map.yml (skipped)')
        return True
    p.write_text(new_text, encoding='utf-8')
    return True


def _get_max_week_from_text(text: str) -> int:
    nums = []
    for m in re.finditer(r"weeks:\s*\[([^\]]*)\]", text):
        nums.extend([int(n) for n in re.findall(r"\d+", m.group(1))])
    for m in re.finditer(r"weeks:\s*(?:\n\s*-\s*\d+\s*)+", text):
        nums.extend([int(n) for n in re.findall(r"-\s*(\d+)", m.group(0))])
    return max(nums) if nums else 0


def _get_max_week(p: Path) -> int:
    if not p.exists():
        return 0
    return _get_max_week_from_text(p.read_text(encoding='utf-8'))


def _append_week_to_existing_block(p: Path, id_: str, week: int) -> bool:
    text = p.read_text(encoding='utf-8')
    m_existing = re.search(r"(^\s*-\s*id:\s*" + re.escape(id_) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", text, flags=re.M)
    if not m_existing:
        return False
    existing = m_existing.group(1)
    # do not add week to ghost
    if re.search(r"ghost:\s*true", existing):
        return False
    # check inline form
    m_inline = re.search(r"weeks:\s*\[([^\]]*)\]", existing)
    if m_inline:
        nums = [int(n) for n in re.findall(r"\d+", m_inline.group(1))]
        if week in nums:
            return True
        nums.append(week)
        nums = sorted(set(nums))
        new_inline = f"weeks: [{', '.join(str(n) for n in nums)}]"
        new_block = existing[:m_inline.start()] + new_inline + existing[m_inline.end():]
    else:
        m_block = re.search(r"(weeks:\s*(?:\n\s*-\s*\d+\s*)+)", existing)
        if m_block:
            nums = [int(n) for n in re.findall(r"-\s*(\d+)", m_block.group(0))]
            if week in nums:
                return True
            nums.append(week)
            nums = sorted(set(nums))
            indent = re.search(r"^(\s*)weeks:", m_block.group(0))
            ind = indent.group(1) if indent else '    '
            new_inline = ind + f"weeks: [{', '.join(str(n) for n in nums)}]\n"
            new_block = existing[:m_block.start()] + new_inline + existing[m_block.end():]
        else:
            m_label = re.search(r"(label:\s*.+\n)", existing)
            insert_after = m_label.end() if m_label else 0
            ins = f"    weeks: [{week}]\n"
            new_block = existing[:insert_after] + ins + existing[insert_after:]

    new_text = text[:m_existing.start(1)] + new_block + text[m_existing.end(1):]
    p.write_text(new_text, encoding='utf-8')
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
    _backup(p, text)
    routes_match = re.search(r"^routes:\s*", text, flags=re.M)
    # include computed distance_km when provided
    # normalize mode display
    mode_str = (mode or "").strip()
    mode_display = mode_str.title() if mode_str else "Annet"

    # compute distance (and optionally path) if not provided
    dk_val = None
    route_path = None
    if distance_km is not None:
        try:
            dk_val = float(distance_km)
        except Exception:
            dk_val = None
    if dk_val is None:
        # If transport mode indicates train, attempt OSM-based railway routing
        try:
            mode_low = mode_str.lower()
            if 'tog' in mode_low or 'train' in mode_low:
                try:
                    # lazy import to avoid hard dependency unless needed
                    from scripts.compute_train_distance import compute_distance_and_path
                    coords_a = get_location_coords(from_id)
                    coords_b = get_location_coords(to_id)
                    if coords_a and coords_b:
                        # compute meters and node coords
                        meters, coords = compute_distance_and_path((coords_a[0], coords_a[1]), (coords_b[0], coords_b[1]), padding_deg=0.5)
                        dk_val = meters / 1000.0
                        route_path = coords
                except Exception:
                    # fall back to existing helper below
                    dk_val = None
            if dk_val is None:
                # attempt to compute using existing helper (OSRM or haversine)
                dk_val = compute_route_distance(from_id, to_id, mode_str)
        except Exception:
            dk_val = None

    route_block = f"  - from: {from_id}\n    to: {to_id}\n    mode: \"{mode_display}\"\n"
    if dk_val is not None:
        try:
            route_block += f"    distance_km: {round(float(dk_val), 1)}\n"
        except Exception:
            pass
    # include geometry points if available (map expects `points`)
    if route_path:
        route_block += "    points:\n"
        for lat, lon in route_path:
            route_block += f"      - [{lat:.6f}, {lon:.6f}]\n"
    route_block += "\n"
    if routes_match:
        m_comment = re.search(r"^# .*$", text[routes_match.end():], flags=re.M)
        end_idx = routes_match.end() + m_comment.start() if m_comment else len(text)
        new_text = text[:end_idx] + route_block + text[end_idx:]
    else:
        new_text = text + "routes:\n" + route_block if text.endswith("\n") else text + "\n" + "routes:\n" + route_block
    if DRY_RUN:
        print("DRY RUN: would write updated _data/map.yml (skipped)")
    else:
        if DRY_RUN:
            print("DRY RUN: would write routes to _data/map.yml (skipped)")
        else:
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
    # Removed — kept for compatibility but no-op.
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
    existing_block = None
    existing_is_ghost = False
    if append:
        p = Path("_data/map.yml")
        txt = p.read_text(encoding='utf-8')
        m_main = re.search(r"(^\s*-\s*id:\s*" + re.escape(new_id) + r"\b[\s\S]*?)(?=^\s*-\s*id:|^routes:|\Z)", txt, flags=re.M)
        if m_main:
            existing_block = m_main.group(1)
            existing_is_ghost = bool(re.search(r"ghost:\s*true", existing_block))
            # If a non-ghost already exists, do not re-insert the main block; use
            # the existing non-ghost entry instead. If existing is a ghost and
            # we have a non-ghost main_block, we'll replace/upgrade it below.
            if not existing_is_ghost and main_block:
                main_block = None
            elif existing_is_ghost and not main_block:
                # if existing is ghost and no main_block provided, capture
                # existing block so we can replace it later if needed
                main_block = existing_block.rstrip() + "\n\n"

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

    # If no ghosts were added, use the already-provided default_mode
    if not ghost_ids:
        mode_last = default_mode
        dk = compute_route_distance(current_from, new_id, mode_last)
        planned_routes.append((current_from, new_id, mode_last, dk))
    else:
        # Ask for the final leg mode when there were intermediates
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
    if AUTO_YES:
        ok = 'y'
    else:
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
        # Only remove an existing main block if we're explicitly replacing it
        # (i.e., we have a non-None main_block and either there was no
        # existing block or the existing block was a ghost), or if force is set.
        if bid == new_id:
            if main_block is not None and (existing_block is None or existing_is_ghost or force):
                continue
            # otherwise keep the existing non-ghost main block and do not
            # re-insert the provided main_block later
            if main_block is not None and not (existing_block is None or existing_is_ghost):
                main_block = None
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
    try:
        # append next week for main destination based on pre-write file content
        max_before = _get_max_week_from_text(txt)
        _append_week_to_existing_block(p, new_id, max_before + 1)
    except Exception:
        pass
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
    global DRY_RUN, AUTO_YES
    parser = argparse.ArgumentParser(description='Add a location to _data/map.yml')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing files')
    parser.add_argument('-y', '--yes', action='store_true', help='Automatic yes to prompts')
    args = parser.parse_args()
    DRY_RUN = bool(args.dry_run)
    AUTO_YES = bool(args.yes)

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
            if AUTO_YES:
                ans = 'y'
            else:
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
        if AUTO_YES:
            ans = 'y'
        else:
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
