#!/usr/bin/env python3
"""Validate the generated profiles against the catalogue. Exits non-zero on problems."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH  # noqa: E402
from dnsprofiles.validate import validate_directory  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    problems = validate_directory(DEFAULT_CATALOG_PATH, REPO_ROOT / "docs" / "profiles")
    if problems:
        print(f"{len(problems)} problem(s) found:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("All profiles valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
