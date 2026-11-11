import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import add_photos
import gallery_previews


@unittest.skipUnless(shutil.which("sips"), "requires macOS sips")
class GalleryPreviewsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.folder = self.root / "pictures" / "week-1"
        self.folder.mkdir(parents=True)
        self.source = self.folder / "photo with spaces.jpeg"
        shutil.copyfile(ROOT / "pictures" / "week-7" / "Busan_i_sikte.jpeg", self.source)
        self.preview = self.root / "gallery-previews" / "pictures" / "week-1" / "photo with spaces.jpeg.jpg"
        self.root_patch = patch.object(gallery_previews, "REPOSITORY_ROOT", self.root)
        self.preview_patch = patch.object(gallery_previews, "PREVIEW_ROOT", self.root / "gallery-previews")
        self.root_patch.start()
        self.preview_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.preview_patch.stop)

    def test_preview_is_small_cached_and_refreshable(self):
        original = self.source.read_bytes()
        self.assertTrue(gallery_previews.ensure_preview(self.source))
        self.assertTrue(self.preview.is_file())
        self.assertEqual(self.source.read_bytes(), original)
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(self.preview)],
            check=True, capture_output=True, text=True,
        )
        dimensions = [
            int(line.split(":")[-1])
            for line in result.stdout.splitlines()
            if "pixelWidth:" in line or "pixelHeight:" in line
        ]
        self.assertEqual(len(dimensions), 2)
        self.assertLessEqual(max(dimensions), gallery_previews.MAX_DIMENSION)
        self.assertFalse(gallery_previews.ensure_preview(self.source))
        self.assertTrue(gallery_previews.ensure_preview(self.source, force=True))
        newer = self.preview.stat().st_mtime_ns + 1_000_000_000
        os.utime(self.source, ns=(newer, newer))
        self.assertTrue(gallery_previews.ensure_preview(self.source))

    def test_import_generates_previews_for_new_and_existing_photos(self):
        post = self.root / "post.md"
        post.write_text('---\ntitle: Test\n---\nBody\n', encoding="utf-8")
        with patch.object(add_photos, "REPOSITORY_ROOT", self.root), \
             patch.object(add_photos, "capture_datetime", return_value=None):
            self.assertEqual(add_photos.update_images(post, self.folder, "Oslo", "Norway")[0], 1)
            self.assertTrue(self.preview.is_file())
            self.assertIn("/pictures/week-1/photo%20with%20spaces.jpeg", post.read_text())
            self.preview.unlink()
            before = post.read_text()
            self.assertEqual(add_photos.update_images(post, self.folder, "Oslo", "Norway")[0], 0)
            self.assertTrue(self.preview.is_file())
            self.assertEqual(post.read_text(), before)

    def test_conversion_failure_is_reported_without_changing_post(self):
        post = self.root / "post.md"
        original_post = '---\ntitle: Test\n---\nBody\n'
        post.write_text(original_post, encoding="utf-8")
        failure = subprocess.CalledProcessError(1, ["sips"], stderr="invalid image")
        with patch.object(add_photos, "REPOSITORY_ROOT", self.root), \
             patch.object(add_photos, "capture_datetime", return_value=None), \
             patch.object(gallery_previews.subprocess, "run", side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, "invalid image"):
                add_photos.update_images(post, self.folder, "Oslo", "Norway")
        self.assertEqual(post.read_text(), original_post)
        self.assertFalse(self.preview.exists())
        self.assertEqual(list(self.preview.parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
