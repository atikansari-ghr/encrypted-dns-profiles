#!/usr/bin/env python3
"""Probe every provider endpoint. Exits non-zero if any endpoint fails."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog  # noqa: E402
from dnsprofiles.liveness import check_all  # noqa: E402


def main() -> int:
    results = check_all(load_catalog(DEFAULT_CATALOG_PATH))
    failures = 0
    for label, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label:<34} {detail}")
        if not ok:
            failures += 1
    print(f"\n{len(results) - failures}/{len(results)} endpoints healthy")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
