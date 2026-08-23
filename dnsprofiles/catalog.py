"""Loading and validation of the provider catalogue."""

from __future__ import annotations

import ipaddress
import re
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent / "providers.toml"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class CatalogError(Exception):
    """Raised when the provider catalogue is malformed."""


@dataclass(frozen=True)
class ProfileSpec:
    slug: str
    provider: str
    variant: str
    display_name: str
    blocks: str
    description: str
    homepage: str
    doh_url: str
    dot_hostname: str
    addresses: tuple[str, ...]


_TEXT_FIELDS = (
    "slug",
    "provider",
    "variant",
    "display_name",
    "blocks",
    "description",
    "homepage",
    "doh_url",
    "dot_hostname",
)


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> tuple[ProfileSpec, ...]:
    """Read and validate the catalogue, returning specs in file order."""
    with open(path, "rb") as handle:
        data = tomllib.load(handle)

    entries = data.get("profiles")
    if not entries:
        raise CatalogError(f"{path}: no [[profiles]] entries found")

    known = {f.name for f in fields(ProfileSpec)}
    specs: list[ProfileSpec] = []
    seen: set[str] = set()

    for index, entry in enumerate(entries):
        where = f"{path}: profile #{index + 1}"

        unexpected = set(entry) - known
        if unexpected:
            raise CatalogError(f"{where}: unexpected keys {sorted(unexpected)}")

        for name in _TEXT_FIELDS:
            value = entry.get(name)
            if not isinstance(value, str) or not value.strip():
                raise CatalogError(f"{where}: missing or empty '{name}'")

        slug = entry["slug"]
        if not SLUG_PATTERN.match(slug):
            raise CatalogError(f"{where}: slug '{slug}' must be lowercase kebab-case")
        if slug in seen:
            raise CatalogError(f"{where}: duplicate slug '{slug}'")
        seen.add(slug)

        for name in ("homepage", "doh_url"):
            if not entry[name].startswith("https://"):
                raise CatalogError(f"{where}: '{name}' must use https")

        addresses = entry.get("addresses")
        if not isinstance(addresses, list) or not addresses:
            raise CatalogError(f"{where}: 'addresses' must be a non-empty list")
        for address in addresses:
            try:
                ipaddress.ip_address(address)
            except ValueError as exc:
                raise CatalogError(f"{where}: invalid address '{address}'") from exc

        specs.append(
            ProfileSpec(
                **{name: entry[name] for name in _TEXT_FIELDS},
                addresses=tuple(addresses),
            )
        )

    return tuple(specs)
