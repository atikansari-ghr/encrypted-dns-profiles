#!/usr/bin/env python3
"""Generate one QR code per profile, encoding its canonical Pages URL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import segno  # noqa: E402

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog  # noqa: E402
from dnsprofiles.profile import PROTOCOLS, profile_url  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def generate_qr_codes(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    output_dir: Path = REPO_ROOT / "docs" / "qr",
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for spec in load_catalog(catalog_path):
        for protocol in PROTOCOLS:
            path = output_dir / f"{spec.slug}-{protocol}.svg"
            # Pass an open binary handle rather than a path string: segno's
            # save() opens paths in text mode, which on Windows rewrites LF
            # to CRLF and breaks byte-identical regeneration.
            with open(path, "wb") as handle:
                segno.make(profile_url(spec.slug, protocol), error="m").save(
                    handle, kind="svg", scale=4, border=2, dark="#111111", light=None
                )
            written.append(path)

    expected = {path.name for path in written}
    for existing in output_dir.glob("*.svg"):
        if existing.name not in expected:
            existing.unlink()

    return sorted(written, key=lambda path: path.name)


if __name__ == "__main__":
    paths = generate_qr_codes()
    print(f"{len(paths)} QR codes written")
