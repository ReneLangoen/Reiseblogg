#!/usr/bin/env python3
"""Simple helper to add a subscriber to _data/subscribers.yml locally.

Usage:
  python3 scripts/add_subscriber.py you@example.com

This script validates the email, avoids duplicates, and appends to the YAML list.
It does not commit changes; run `git add`/`git commit` after verifying.
"""
import sys
import re
from pathlib import Path
import yaml

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(e: str) -> bool:
    return bool(EMAIL_RE.match(e))


def main():
    if len(sys.argv) != 2:
        print("Usage: add_subscriber.py you@example.com")
        sys.exit(2)
    email = sys.argv[1].strip().lower()
    if not valid_email(email):
        print("Invalid email address")
        sys.exit(3)

    data_file = Path(__file__).resolve().parents[1] / "_data" / "subscribers.yml"
    if not data_file.exists():
        print(f"Creating new data file: {data_file}")
        data = {"subscribers": [email]}
    else:
        with open(data_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        subs = data.get("subscribers") or []
        if email in subs:
            print("Email already subscribed")
            return
        subs.append(email)
        data["subscribers"] = subs

    with open(data_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    print(f"Added {email} to {data_file}")


if __name__ == "__main__":
    main()
