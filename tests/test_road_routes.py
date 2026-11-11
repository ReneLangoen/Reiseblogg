import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import add_location
import cache_road_routes


class RoadRoutesTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        old_cwd = Path.cwd()
        os.chdir(self.temporary.name)
        self.addCleanup(os.chdir, old_cwd)
        Path("_data").mkdir()
        Path("_data/map.yml").write_text(
            "locations:\n"
            "  - id: a\n    lat: 1.0\n    lng: 2.0\n"
            "  - id: b\n    lat: 3.0\n    lng: 4.0\n"
            "routes:\n", encoding="utf-8"
        )
        self.paths = Path("_data/route_paths.yml")
        self.paths.write_text("a-b:\n  - [9, 9]\n  - [8, 8]\n", encoding="utf-8")
        self.path_patch = patch.object(add_location, "PATHS_FILE", self.paths)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        add_location._ROAD_PATH_CACHE.clear()
        self.addCleanup(add_location._ROAD_PATH_CACHE.clear)

    def test_osrm_geometry_and_distance(self):
        response = {"code": "Ok", "routes": [{"distance": 12345, "geometry": {"coordinates": [[2, 1], [4, 3]]}}]}
        with patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
            distance, coords = add_location.road_route((1, 2), (3, 4))
        self.assertEqual(distance, 12.345)
        self.assertEqual(coords, [(1.0, 2.0), (3.0, 4.0)])

    def test_prompt_calculation_and_append_save_directional_road_path(self):
        with patch.object(add_location, "road_route", return_value=(12.3, [(1, 2), (3, 4)])) as fetch:
            distance = add_location.compute_route_distance("a", "b", "Buss")
            self.assertTrue(add_location.append_route("a", "b", "Buss", distance_km=distance, calculate_distance=False))
            self.assertEqual(fetch.call_count, 1)
        paths = yaml.safe_load(self.paths.read_text())
        self.assertEqual(paths["road--a-b"], [[1, 2], [3, 4]])
        self.assertEqual(paths["a-b"], [[9, 9], [8, 8]])
        self.assertEqual(yaml.safe_load(Path("_data/map.yml").read_text())["routes"][0]["distance_km"], 12.3)

    def test_automatic_calculation_and_manual_distance(self):
        with patch.object(add_location, "road_route", return_value=(12.3, [(1, 2), (3, 4)])) as fetch:
            self.assertTrue(add_location.append_route("a", "b", "Bil"))
            add_location._ROAD_PATH_CACHE.clear()
            self.assertTrue(add_location.append_route("b", "a", "Bil", distance_km=15, calculate_distance=False))
            self.assertEqual(fetch.call_count, 2)
        paths = yaml.safe_load(self.paths.read_text())
        self.assertIn("road--a-b", paths)
        self.assertIn("road--b-a", paths)
        self.assertEqual(yaml.safe_load(Path("_data/map.yml").read_text())["routes"][1]["distance_km"], 15)

    def test_backfill_is_incremental_and_preserves_distances(self):
        map_path = Path("_data/map.yml")
        original = map_path.read_text() + "  - from: a\n    to: b\n    mode: Bil\n    distance_km: 99\n"
        map_path.write_text(original)
        with patch.object(add_location, "road_route", return_value=(12.3, [(1, 2), (3, 4)])) as fetch, \
             patch.object(sys, "argv", ["cache_road_routes.py", "--delay", "0"]):
            self.assertEqual(cache_road_routes.main(), 0)
            self.assertEqual(cache_road_routes.main(), 0)
            self.assertEqual(fetch.call_count, 1)
        self.assertEqual(map_path.read_text(), original)
        self.assertIn("road--a-b", yaml.safe_load(self.paths.read_text()))

    def test_backfill_reports_failed_routes(self):
        with Path("_data/map.yml").open("a") as file:
            file.write("  - from: a\n    to: b\n    mode: Buss\n")
        with patch.object(add_location, "road_route", side_effect=ValueError("NoRoute")), \
             patch.object(sys, "argv", ["cache_road_routes.py", "--delay", "0"]), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(cache_road_routes.main(), 1)
        self.assertIn("NoRoute", errors.getvalue())
        self.assertNotIn("road--a-b", yaml.safe_load(self.paths.read_text()))


if __name__ == "__main__":
    unittest.main()
