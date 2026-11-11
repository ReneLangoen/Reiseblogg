from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import add_photos


class PhotoOrderTest(unittest.TestCase):
    def test_import_sorts_existing_and_new_photos_oldest_first(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            folder = root / "pictures" / "week-1"
            folder.mkdir(parents=True)
            post = root / "post.md"
            post.write_text("---\ntitle: Test\n---\nBody\n", encoding="utf-8")
            dates = {
                "middle.jpg": datetime(2026, 1, 2),
                "newest.jpg": datetime(2026, 1, 3),
                "oldest.jpg": datetime(2026, 1, 1),
            }
            for name in ("middle.jpg", "newest.jpg"):
                (folder / name).touch()
            with patch.object(add_photos, "REPOSITORY_ROOT", root), \
                 patch.object(add_photos, "ensure_preview"), \
                 patch.object(add_photos, "capture_datetime", side_effect=lambda path: dates[path.name]):
                add_photos.update_images(post, folder, "Oslo", "Norway")
                (folder / "oldest.jpg").touch()
                add_photos.update_images(post, folder, "Oslo", "Norway")
                front, _ = add_photos.parse_front_matter(post.read_text(encoding="utf-8"))
                images = yaml.safe_load(front)["images"]
                self.assertEqual([image["id"] for image in images], ["oldest", "middle", "newest"])
                self.assertEqual(add_photos.update_images(post, folder, "Oslo", "Norway"), (0, 0, False))

    def test_import_sorts_photos_from_multiple_folders_and_places_unknown_last(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old_folder = root / "pictures" / "old"
            new_folder = root / "pictures" / "new"
            old_folder.mkdir(parents=True)
            new_folder.mkdir(parents=True)
            (old_folder / "early.jpg").touch()
            (new_folder / "late.jpg").touch()
            (new_folder / "unknown.jpg").touch()
            post = root / "post.md"
            post.write_text("---\ntitle: Test\n---\nBody\n", encoding="utf-8")
            dates = {"early.jpg": datetime(2026, 1, 1), "late.jpg": datetime(2026, 1, 3), "unknown.jpg": None}
            with patch.object(add_photos, "REPOSITORY_ROOT", root), \
                 patch.object(add_photos, "ensure_preview"), \
                 patch.object(add_photos, "capture_datetime", side_effect=lambda path: dates[path.name]):
                add_photos.update_images(post, old_folder, "Oslo", "Norway")
                add_photos.update_images(post, new_folder, "Oslo", "Norway")
            front, _ = add_photos.parse_front_matter(post.read_text(encoding="utf-8"))
            self.assertEqual([image["id"] for image in yaml.safe_load(front)["images"]], ["early", "late", "unknown"])


if __name__ == "__main__":
    unittest.main()
