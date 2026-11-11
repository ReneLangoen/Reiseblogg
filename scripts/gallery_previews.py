#!/usr/bin/env python3
"""Generate gallery previews without modifying the original images."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PREVIEW_ROOT = REPOSITORY_ROOT / "gallery-previews"
IMAGE_EXTENSIONS = {".gif", ".heic", ".heif", ".jpeg", ".jpg", ".png", ".webp"}
MAX_DIMENSION = 960
JPEG_QUALITY = 90


def ensure_preview(source: Path, *, force: bool = False) -> bool:
    """Create or refresh a preview; return whether it was generated."""
    relative_source = source.resolve().relative_to(REPOSITORY_ROOT)
    preview = PREVIEW_ROOT / relative_source
    preview = preview.with_name(preview.name + ".jpg")
    if not force and preview.is_file() and preview.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        return False
    if not shutil.which("sips"):
        raise RuntimeError("Generating gallery previews requires macOS and the sips command")

    preview.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".jpg", dir=preview.parent, delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        subprocess.run(
            [
                "sips", "-s", "format", "jpeg", "-s", "formatOptions",
                str(JPEG_QUALITY), "-Z", str(MAX_DIMENSION),
                str(source), "--out", str(temp_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        temp_path.replace(preview)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"sips failed for {source}: {error.stderr.strip()}") from error
    finally:
        temp_path.unlink(missing_ok=True)
    return True


def generate_folder(folder: Path, *, force: bool = False) -> tuple[int, int]:
    if not folder.is_dir():
        raise ValueError(f"Photo folder does not exist: {folder}")
    generated = total = 0
    for source in sorted(folder.iterdir()):
        if source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS:
            total += 1
            try:
                generated += ensure_preview(source, force=force)
            except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
                raise RuntimeError(f"Could not generate preview for {source}: {error}") from error
    return generated, total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", type=Path, nargs="+", help="Photo folders to process")
    parser.add_argument("--force", action="store_true", help="Regenerate existing previews")
    args = parser.parse_args()
    for folder in args.folders:
        generated, total = generate_folder(folder, force=args.force)
        print(f"{folder}: generated {generated} of {total} previews")


if __name__ == "__main__":
    main()
