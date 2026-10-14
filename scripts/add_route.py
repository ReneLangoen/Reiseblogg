#!/usr/bin/env python3
"""Interactive helper for adding a route between existing map locations."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import add_location


MAP_PATH = Path("_data/map.yml")


def get_locations() -> list[tuple[str, str]]:
    if not MAP_PATH.exists():
        return []
    text = MAP_PATH.read_text(encoding="utf-8")
    locations_match = re.search(r"^locations:\s*", text, flags=re.M)
    routes_match = re.search(r"^routes:\s*", text, flags=re.M)
    if not locations_match:
        return []
    end = routes_match.start() if routes_match else len(text)
    locations_text = text[locations_match.end():end]
    locations = []
    for block in re.findall(r"(^\s*-\s*id:.*?)(?=^\s*-\s*id:|\Z)", locations_text, flags=re.M | re.S):
        id_match = re.search(r"^\s*-\s*id:\s*([a-z0-9-]+)", block, flags=re.M)
        label_match = re.search(r"^\s*label:\s*(.+)$", block, flags=re.M)
        if id_match:
            locations.append((id_match.group(1), label_match.group(1).strip() if label_match else id_match.group(1)))
    return locations


def choose_location(prompt: str, locations: list[tuple[str, str]]) -> str | None:
    valid_ids = {location_id for location_id, _ in locations}
    while True:
        try:
            value = input(prompt).strip().lower()
        except KeyboardInterrupt:
            print()
            return None
        if not value:
            return None
        if value in valid_ids:
            return value
        print("Unknown location. Use one of the listed IDs, or press Enter to cancel.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a route between existing locations")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing files")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip the final confirmation")
    args = parser.parse_args()

    locations = get_locations()
    if not locations:
        print("No locations found in _data/map.yml.")
        return

    print("Existing locations:")
    for location_id, label in locations:
        print(f"- {location_id}: {label}")

    from_id = choose_location("From location ID (or Enter to cancel): ", locations)
    if not from_id:
        print("Cancelled.")
        return
    to_id = choose_location("To location ID (or Enter to cancel): ", locations)
    if not to_id:
        print("Cancelled.")
        return
    if from_id == to_id:
        print("A route must connect two different locations.")
        return

    try:
        mode = input("Transport mode (Fly/Tog/Bil/etc.): ").strip() or "Fly"
    except KeyboardInterrupt:
        print()
        return

    distance_km = add_location.prompt_for_route_distance(from_id, to_id, mode)
    print(f"Planned route: {from_id} -> {to_id} ({mode})")
    if distance_km is None:
        print("No distance will be written.")
    else:
        print(f"Distance: {distance_km:.1f} km")

    if args.yes:
        confirmed = True
    else:
        try:
            confirmed = input("Write this route to _data/map.yml? [y/N]: ").strip().lower() in ("y", "yes")
        except KeyboardInterrupt:
            print()
            confirmed = False
    if not confirmed:
        print("Cancelled — no changes written.")
        return

    add_location.DRY_RUN = args.dry_run
    if add_location.append_route(
        from_id,
        to_id,
        mode,
        distance_km=distance_km,
        calculate_distance=False,
    ):
        print("Route added." if not args.dry_run else "Dry run complete; no changes written.")
    else:
        print("Failed to add route.")


if __name__ == "__main__":
    main()
