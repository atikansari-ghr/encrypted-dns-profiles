"""Writing the full set of profiles to disk."""

from __future__ import annotations

from pathlib import Path

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog
from dnsprofiles.profile import (
    PROTOCOLS,
    build_profile,
    profile_filename,
    to_plist_bytes,
)


def generate_all(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    output_dir: Path = Path("docs/profiles"),
) -> list[Path]:
    """Generate every profile, removing any file the catalogue no longer names."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for spec in load_catalog(catalog_path):
        for protocol in PROTOCOLS:
            path = output_dir / profile_filename(spec.slug, protocol)
            path.write_bytes(to_plist_bytes(build_profile(spec, protocol)))
            written.append(path)

    expected = {path.name for path in written}
    for existing in output_dir.glob("*.mobileconfig"):
        if existing.name not in expected:
            existing.unlink()

    return sorted(written, key=lambda path: path.name)
