#!/usr/bin/env python3
"""Generate every DNS configuration profile from providers.toml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH  # noqa: E402
from dnsprofiles.generate import generate_all  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "docs" / "profiles")
    args = parser.parse_args()

    written = generate_all(args.catalog, args.output)
    for path in written:
        print(path.relative_to(REPO_ROOT))
    print(f"\n{len(written)} profiles written to {args.output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
