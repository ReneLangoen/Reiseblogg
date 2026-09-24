#!/usr/bin/env python3
"""Add image files from a folder to a post's YAML front matter."""
import argparse
from datetime import datetime
import re
import shutil
import subprocess
import unicodedata
from urllib.parse import quote
from pathlib import Path
from typing import Optional

import yaml


IMAGE_EXTENSIONS = {
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".png",
    ".webp",
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "image"


def yaml_value(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def image_block(images: list[dict[str, str]]) -> str:
    lines = ["images:"]
    for index, image in enumerate(images):
        lines.extend(
            [
                f"  - id: {image['id']}",
                f"    src: {yaml_value(image['src'])}",
                f"    caption: {yaml_value(image.get('caption', ''))}",
                f"    city: {yaml_value(image['city'])}",
                f"    country: {yaml_value(image['country'])}",
            ]
        )
        if index < len(images) - 1:
            lines.append("")
    return "\n".join(lines) + "\n"


def parse_front_matter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Post must start with YAML front matter delimited by ---")
    return match.group(1), text[match.end() :]


def capture_datetime(path: Path) -> Optional[datetime]:
    if not shutil.which("exiftool"):
        raise RuntimeError("exiftool is required to sort photos by capture time")
    result = subprocess.run(
        ["exiftool", "-s3", "-DateTimeOriginal", "-CreateDate", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for value in result.stdout.splitlines():
        try:
            return datetime.strptime(value.strip()[:19], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
    return None


def update_images(post: Path, folder: Path, city: str, country: str) -> tuple[int, bool]:
    text = post.read_text(encoding="utf-8")
    front_matter, body = parse_front_matter(text)
    metadata = yaml.safe_load(front_matter) or {}
    images = metadata.get("images") or []
    if not isinstance(images, list):
        raise ValueError("The post's images field must be a YAML list")

    existing_sources = {image.get("src") for image in images if isinstance(image, dict)}
    existing_ids = {image.get("id") for image in images if isinstance(image, dict)}
    capture_times = {}
    added = []
    for path in sorted(
        folder.iterdir(),
        key=lambda item: (
            (capture_datetime(item) or datetime.min)
            if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
            else datetime.min,
            item.name.casefold(),
        ),
        reverse=True,
    ):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        source = "/" + quote(path.resolve().relative_to(Path.cwd().resolve()).as_posix(), safe="/:@-._~")
        capture_times[source] = capture_datetime(path) or datetime.min
        if source in existing_sources:
            continue

        image_id = slugify(path.stem)
        if image_id in existing_ids:
            suffix = 2
            while f"{image_id}-{suffix}" in existing_ids:
                suffix += 1
            image_id = f"{image_id}-{suffix}"
        added.append(
            {
                "id": image_id,
                "src": source,
                "caption": "",
                "city": city,
                "country": country,
            }
        )
        existing_ids.add(image_id)

    images.extend(added)
    images.sort(
        key=lambda image: (
            capture_times.get(image.get("src"), datetime.min),
            image.get("src") or "",
        ),
        reverse=True,
    )
    new_images = image_block(images)
    images_match = re.search(
        r"^images:\n(?:^[ \t]+.*\n|^\s*\n)*?(?=^[^ \t\n].*:|\Z)",
        front_matter,
        flags=re.MULTILINE,
    )
    if images_match:
        new_front_matter = front_matter[: images_match.start()] + new_images + front_matter[images_match.end() :]
    else:
        new_front_matter = front_matter.rstrip() + "\n" + new_images + "\n"

    new_text = "---\n" + new_front_matter.rstrip() + "\n---\n" + body
    if new_text != text:
        post.write_text(new_text, encoding="utf-8")
    return len(added), any(path["src"].lower().endswith((".heic", ".heif")) for path in added)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post", type=Path, nargs="?", help="Markdown post to update")
    parser.add_argument("folder", type=Path, nargs="?", help="Folder containing the photos")
    parser.add_argument("city", nargs="?", help="City stored on each new photo")
    parser.add_argument("country", nargs="?", help="Country stored on each new photo")
    args = parser.parse_args()

    if not all((args.post, args.folder, args.city, args.country)):
        print("Add photos to a post")
        args.post = Path(input("Post path: ").strip())
        args.folder = Path(input("Photo folder: ").strip())
        args.city = input("City: ").strip()
        args.country = input("Country: ").strip()

    if not args.post.is_file():
        parser.error(f"Post does not exist: {args.post}")
    if not args.folder.is_dir():
        parser.error(f"Photo folder does not exist: {args.folder}")

    added, has_heic = update_images(args.post, args.folder, args.city, args.country)
    if added:
        print(f"Added {added} photo(s) to {args.post}")
    else:
        print("No new photos to add")
    if has_heic:
        print("Warning: HEIC files were added; browser support is not universal.")


if __name__ == "__main__":
    main()