#!/usr/bin/env python3
"""Generate QR codes: one per profile (install link, iOS/iPadOS/macOS) and
one per catalogue entry (anchor link back to its own card, for Android,
where there is no file to install)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import segno  # noqa: E402

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog  # noqa: E402
from dnsprofiles.profile import PROTOCOLS, card_url, profile_url  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_qr(url: str, path: Path) -> None:
    # Pass an open binary handle rather than a path string: segno's save()
    # opens paths in text mode, which on Windows rewrites LF to CRLF and
    # breaks byte-identical regeneration.
    with open(path, "wb") as handle:
        segno.make(url, error="m").save(
            handle, kind="svg", scale=4, border=2, dark="#111111", light=None
        )


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
            _write_qr(profile_url(spec.slug, protocol), path)
            written.append(path)

        android_path = output_dir / f"{spec.slug}-android.svg"
        _write_qr(card_url(spec.slug), android_path)
        written.append(android_path)

    expected = {path.name for path in written}
    for existing in output_dir.glob("*.svg"):
        if existing.name not in expected:
            existing.unlink()

    return sorted(written, key=lambda path: path.name)


if __name__ == "__main__":
    paths = generate_qr_codes()
    print(f"{len(paths)} QR codes written")
