#!/usr/bin/env python3
"""Save missing car and bus route geometry for the static map."""

import argparse
from pathlib import Path
import subprocess
import sys
import time

import yaml

import add_location


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between OSRM requests (default: 1)")
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be non-negative")

    data = yaml.safe_load(Path("_data/map.yml").read_text(encoding="utf-8"))
    paths = yaml.safe_load(add_location.PATHS_FILE.read_text(encoding="utf-8")) or {}
    locations = {}
    for location in data["locations"]:
        if location["id"] not in locations or (locations[location["id"]].get("ghost") and not location.get("ghost")):
            locations[location["id"]] = location

    failures = 0
    requested = 0
    for route in data["routes"]:
        if not add_location._is_road_mode(route.get("mode", "")) or route.get("points"):
            continue
        from_id, to_id = route["from"], route["to"]
        key = f"road--{from_id}-{to_id}"
        if key in paths:
            continue
        if requested:
            time.sleep(args.delay)
        requested += 1
        try:
            origin, destination = locations[from_id], locations[to_id]
            distance, coords = add_location.road_route(
                (origin["lat"], origin["lng"]), (destination["lat"], destination["lng"])
            )
            add_location.save_route_path(from_id, to_id, coords, road=True)
            paths[key] = True
            print(f"Saved {from_id} -> {to_id} ({distance:.1f} km from OSRM)")
        except (KeyError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            failures += 1
            print(f"Failed {from_id} -> {to_id}: {error}", file=sys.stderr)
    print(f"Requested {requested} routes; {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
