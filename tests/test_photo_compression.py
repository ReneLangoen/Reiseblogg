from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import add_photos


class PhotoCompressionTest(unittest.TestCase):
    def test_compresses_large_jpeg_and_preserves_capture_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            photo = folder / "photo.jpg"
            exif = Image.Exif()
            exif[36867] = "2026:11:15 10:00:00"
            Image.new("RGB", (3000, 1500), "blue").save(
                photo, quality=100, exif=exif
            )
            photo.chmod(0o640)
            original_size = photo.stat().st_size

            count, bytes_saved = add_photos.compress_jpeg_photos(folder)

            self.assertEqual(count, 1)
            self.assertGreater(bytes_saved, 0)
            self.assertLess(photo.stat().st_size, original_size)
            self.assertEqual(stat.S_IMODE(photo.stat().st_mode), 0o640)
            with Image.open(photo) as compressed:
                self.assertEqual(compressed.size, (1920, 960))
                self.assertEqual(
                    compressed.getexif().get(36867),
                    "2026:11:15 10:00:00",
                )

    def test_keeps_original_when_compression_would_increase_size(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            photo = folder / "photo.jpg"
            Image.new("RGB", (20, 20), "blue").save(photo, quality=60)
            original = photo.read_bytes()

            def write_larger(_image, destination, **_options):
                Path(destination).write_bytes(b"x" * (len(original) + 1))

            with patch.object(Image.Image, "save", autospec=True, side_effect=write_larger):
                result = add_photos.compress_jpeg_photos(folder)

            self.assertEqual(result, (0, 0))
            self.assertEqual(photo.read_bytes(), original)

    def test_cli_compresses_jpegs_before_adding_them_to_the_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            folder = root / "pictures" / "week-1"
            folder.mkdir(parents=True)
            photo = folder / "photo.jpg"
            Image.new("RGB", (3000, 1500), "blue").save(photo, quality=100)
            post = root / "post.md"
            post.write_text("---\ntitle: Test\n---\nBody\n", encoding="utf-8")
            argv = [
                "add_photos.py",
                str(post),
                str(folder),
                "Oslo",
                "Norway",
            ]

            with patch.object(sys, "argv", argv), \
                 patch.object(add_photos, "REPOSITORY_ROOT", root), \
                 patch.object(add_photos, "capture_datetime", return_value=None):
                add_photos.main()

            with Image.open(photo) as compressed:
                self.assertEqual(compressed.size, (1920, 960))
            front_matter, _ = add_photos.parse_front_matter(
                post.read_text(encoding="utf-8")
            )
            self.assertEqual(yaml.safe_load(front_matter)["images"][0]["id"], "photo")


if __name__ == "__main__":
    unittest.main()
