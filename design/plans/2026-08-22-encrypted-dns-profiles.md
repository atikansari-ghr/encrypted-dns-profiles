# Encrypted DNS Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public repository of installable encrypted DNS configuration profiles — AdGuard ad-blocking and family protection plus four curated alternatives — served from a GitHub Pages install site, with an Android Private DNS guide and CI that detects dead provider endpoints.

**Architecture:** One `providers.toml` catalogue is the single source of truth. A dependency-free Python package reads it and emits 18 `.mobileconfig` plists into `docs/profiles/`, with payload UUIDs derived via UUIDv5 so regeneration is byte-identical and CI can fail on drift. GitHub Pages publishes `docs/` as both the install site and the browsable profile source.

**Tech Stack:** Python 3.11+ (stdlib `tomllib`, `plistlib`, `uuid`, `ipaddress`), pytest, `segno` for QR generation (build-time only), hand-written HTML/CSS/SVG, GitHub Actions, bash.

**Spec:** `design/specs/2026-08-22-encrypted-dns-profiles-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Deviation from spec §5.1:** the catalogue is `providers.toml`, not `providers.yaml`. Python 3.11+ reads TOML with stdlib `tomllib`, so `dnsprofiles/` and `generate_profiles.py` have **zero third-party dependencies**. Only `make_qr.py` needs `segno`, and it is build-time only.
- **Package layout addition to spec §4:** a root-level `dnsprofiles/` package holds the logic; `scripts/*.py` are thin CLIs over it. Tests live in `tests/`.
- Platform floor: **iOS/iPadOS 14+, macOS 11+**. Android **9+** for Private DNS.
- `PayloadOrganization` is exactly `Atik Ansari` on every profile.
- `PayloadRemovalDisallowed` is `false`. No `OnDemandRules`. No `ProhibitDisablement`.
- `PayloadIdentifier` format: `com.atikansari.dns.<slug>-<doh|dot>`.
- Pages base URL: `https://atikansari-ghr.github.io/encrypted-dns-profiles`
- Regenerating profiles with no catalogue change MUST produce byte-identical files.
- The Pages site makes **zero external requests** — no CDN, no web fonts, no analytics.
- `LICENSE` is MIT, `Copyright (c) 2026 Atik Ansari`.
- Commits credit Atik Ansari alone: **no `Co-Authored-By` trailers, no "Generated with" notices** in commits, PR bodies, README, or any published file.
- `linkedin/` is **never committed** and must never be added to the repository `.gitignore`.
- The nine slugs in spec §4.1 are frozen; changing one alters its UUID and breaks replace-on-reinstall.

---

### Task 1: Repository foundation

Scaffolding, licence, line-ending policy, and a green test run to build on.

**Files:**
- Create: `.gitattributes`, `.gitignore`, `LICENSE`, `CHANGELOG.md`, `pytest.ini`, `requirements-dev.txt`, `dnsprofiles/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `dnsprofiles` package and a working `pytest` invocation for all later tasks.

- [ ] **Step 1: Rename the GitHub repository and update the remote**

```bash
gh repo rename encrypted-dns-profiles --repo atikansari-ghr/md-toolbox --yes
git remote set-url origin https://github.com/atikansari-ghr/encrypted-dns-profiles.git
git remote -v
```

Expected: both fetch and push URLs show `encrypted-dns-profiles`. GitHub redirects the old URL, so the earlier commit is unaffected.

- [ ] **Step 2: Write `.gitattributes`**

Line endings matter here: profiles are byte-compared by the CI drift check, so a CRLF checkout on Windows would fail CI while passing on Linux runners.

```gitattributes
* text=auto eol=lf

*.mobileconfig text eol=lf
*.py          text eol=lf
*.sh          text eol=lf
*.toml        text eol=lf
*.md          text eol=lf
*.html        text eol=lf
*.svg         text eol=lf
*.yml         text eol=lf

*.png binary
```

- [ ] **Step 3: Write `.gitignore`**

Note the absence of a `linkedin/` entry — that folder is excluded machine-wide via `~/.gitignore_global`, and adding it here would leave a visible trace.

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/

.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Write `LICENSE`**

Standard MIT text with exactly this copyright line:

```
Copyright (c) 2026 Atik Ansari
```

- [ ] **Step 5: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding.
```

- [ ] **Step 6: Write `pytest.ini` and `requirements-dev.txt`**

`pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

`requirements-dev.txt`:

```
pytest>=8.0
segno>=1.6
```

- [ ] **Step 7: Create the package and a smoke test**

`dnsprofiles/__init__.py`:

```python
"""Generation and validation of encrypted DNS configuration profiles."""

__version__ = "0.1.0"
```

`tests/__init__.py`: empty file.

`tests/test_smoke.py`:

```python
import dnsprofiles


def test_package_imports():
    assert dnsprofiles.__version__ == "0.1.0"
```

- [ ] **Step 8: Run the tests**

Run: `python -m pytest`
Expected: PASS, 1 passed.

- [ ] **Step 9: Commit**

```bash
git add .gitattributes .gitignore LICENSE CHANGELOG.md pytest.ini requirements-dev.txt dnsprofiles tests
git commit -m "Add repository scaffolding, MIT licence and test harness"
```

---

### Task 2: Provider catalogue and loader

**Files:**
- Create: `providers.toml`, `dnsprofiles/catalog.py`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ProfileSpec` frozen dataclass with fields `slug: str`, `provider: str`, `variant: str`, `display_name: str`, `blocks: str`, `description: str`, `homepage: str`, `doh_url: str`, `dot_hostname: str`, `addresses: tuple[str, ...]`
  - `load_catalog(path: Path) -> tuple[ProfileSpec, ...]`
  - `CatalogError(Exception)`
  - `DEFAULT_CATALOG_PATH: Path` pointing at the repo-root `providers.toml`

- [ ] **Step 1: Write the failing tests**

`tests/test_catalog.py`:

```python
import pytest

from dnsprofiles.catalog import (
    CatalogError,
    DEFAULT_CATALOG_PATH,
    ProfileSpec,
    load_catalog,
)

VALID = """
[[profiles]]
slug = "adguard-default"
provider = "AdGuard"
variant = "Default"
display_name = "AdGuard DNS - Ad Blocking"
blocks = "Ads and trackers"
description = "Blocks ads and tracking domains."
homepage = "https://adguard-dns.io/"
doh_url = "https://dns.adguard-dns.com/dns-query"
dot_hostname = "dns.adguard-dns.com"
addresses = ["94.140.14.14", "94.140.15.15"]
"""


def write(tmp_path, text):
    path = tmp_path / "providers.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_a_valid_entry(tmp_path):
    specs = load_catalog(write(tmp_path, VALID))
    assert len(specs) == 1
    assert specs[0] == ProfileSpec(
        slug="adguard-default",
        provider="AdGuard",
        variant="Default",
        display_name="AdGuard DNS - Ad Blocking",
        blocks="Ads and trackers",
        description="Blocks ads and tracking domains.",
        homepage="https://adguard-dns.io/",
        doh_url="https://dns.adguard-dns.com/dns-query",
        dot_hostname="dns.adguard-dns.com",
        addresses=("94.140.14.14", "94.140.15.15"),
    )


def test_rejects_duplicate_slugs(tmp_path):
    with pytest.raises(CatalogError, match="duplicate slug"):
        load_catalog(write(tmp_path, VALID + VALID))


def test_rejects_malformed_slug(tmp_path):
    bad = VALID.replace('slug = "adguard-default"', 'slug = "AdGuard_Default"')
    with pytest.raises(CatalogError, match="slug"):
        load_catalog(write(tmp_path, bad))


def test_rejects_missing_field(tmp_path):
    bad = VALID.replace('homepage = "https://adguard-dns.io/"\n', "")
    with pytest.raises(CatalogError, match="homepage"):
        load_catalog(write(tmp_path, bad))


def test_rejects_non_https_doh_url(tmp_path):
    bad = VALID.replace("https://dns.adguard-dns.com", "http://dns.adguard-dns.com")
    with pytest.raises(CatalogError, match="https"):
        load_catalog(write(tmp_path, bad))


def test_rejects_invalid_ip_address(tmp_path):
    bad = VALID.replace('"94.140.14.14"', '"not-an-ip"')
    with pytest.raises(CatalogError, match="address"):
        load_catalog(write(tmp_path, bad))


def test_rejects_empty_addresses(tmp_path):
    bad = VALID.replace('addresses = ["94.140.14.14", "94.140.15.15"]', "addresses = []")
    with pytest.raises(CatalogError, match="address"):
        load_catalog(write(tmp_path, bad))


def test_real_catalogue_has_nine_unique_entries():
    specs = load_catalog(DEFAULT_CATALOG_PATH)
    assert len(specs) == 9
    assert len({s.slug for s in specs}) == 9
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dnsprofiles.catalog'`

- [ ] **Step 3: Write `dnsprofiles/catalog.py`**

```python
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
```

- [ ] **Step 4: Write `providers.toml` with all nine entries**

Values are copied verbatim from spec §3 — every endpoint there was live-tested. IPv6 addresses are deliberately omitted until confirmed against provider documentation (spec §16.2); the schema accepts them whenever they are added.

```toml
# Provider catalogue - the single source of truth for every generated profile.
# Add a provider by appending a [[profiles]] block and running:
#   python scripts/generate_profiles.py
#
# Slugs are frozen once released: a slug change alters the derived payload UUID
# and breaks replace-on-reinstall for anyone who already installed the profile.

[[profiles]]
slug = "adguard-default"
provider = "AdGuard"
variant = "Default"
display_name = "AdGuard DNS - Ad Blocking"
blocks = "Ads and trackers"
description = "Blocks advertising and tracking domains across every app on the device. Operated by AdGuard Software Limited. The public resolver does not log queries."
homepage = "https://adguard-dns.io/"
doh_url = "https://dns.adguard-dns.com/dns-query"
dot_hostname = "dns.adguard-dns.com"
addresses = ["94.140.14.14", "94.140.15.15"]

[[profiles]]
slug = "adguard-family"
provider = "AdGuard"
variant = "Family Protection"
display_name = "AdGuard DNS - Family Protection"
blocks = "Ads, trackers, adult content, and enforces safe search"
description = "Everything the ad-blocking profile blocks, plus adult content, and enforces safe search on major search engines. Operated by AdGuard Software Limited."
homepage = "https://adguard-dns.io/"
doh_url = "https://family.adguard-dns.com/dns-query"
dot_hostname = "family.adguard-dns.com"
addresses = ["94.140.14.15", "94.140.15.16"]

[[profiles]]
slug = "mullvad-adblock"
provider = "Mullvad"
variant = "Adblock"
display_name = "Mullvad DNS - Adblock"
blocks = "Ads and trackers"
description = "Blocks advertising and tracking domains. Operated by Mullvad VPN AB in Sweden, with a published no-logging policy. Free to use without a Mullvad account."
homepage = "https://mullvad.net/en/help/dns-over-https-and-dns-over-tls"
doh_url = "https://adblock.dns.mullvad.net/dns-query"
dot_hostname = "adblock.dns.mullvad.net"
addresses = ["194.242.2.3"]

[[profiles]]
slug = "controld-ads"
provider = "ControlD"
variant = "Free - Ads"
display_name = "ControlD Free - Ad Blocking"
blocks = "Ads, trackers and malware"
description = "Blocks advertising, tracking and malware domains. Operated by Windscribe under the ControlD brand. This is the free tier and needs no account."
homepage = "https://controld.com/free-dns"
doh_url = "https://freedns.controld.com/p2"
dot_hostname = "p2.freedns.controld.com"
addresses = ["76.76.2.11"]

[[profiles]]
slug = "controld-family"
provider = "ControlD"
variant = "Free - Family"
display_name = "ControlD Free - Family"
blocks = "Ads, trackers, malware and adult content"
description = "Everything the ControlD ad-blocking profile blocks, plus adult content. Operated by Windscribe under the ControlD brand. Free tier, no account required."
homepage = "https://controld.com/free-dns"
doh_url = "https://freedns.controld.com/family"
dot_hostname = "family.freedns.controld.com"
addresses = ["76.76.2.11"]

[[profiles]]
slug = "cloudflare-security"
provider = "Cloudflare"
variant = "Security"
display_name = "Cloudflare - Security"
blocks = "Malware only - does not block ads"
description = "Blocks known malware domains. Operated by Cloudflare. This profile does NOT block advertising or trackers - choose an AdGuard, Mullvad or ControlD profile for that."
homepage = "https://one.one.one.one/family/"
doh_url = "https://security.cloudflare-dns.com/dns-query"
dot_hostname = "security.cloudflare-dns.com"
addresses = ["1.1.1.2", "1.0.0.2"]

[[profiles]]
slug = "cloudflare-family"
provider = "Cloudflare"
variant = "Family"
display_name = "Cloudflare - Family"
blocks = "Malware and adult content - does not block ads"
description = "Blocks known malware and adult content. Operated by Cloudflare. This profile does NOT block advertising or trackers - choose an AdGuard or ControlD family profile if you want both."
homepage = "https://one.one.one.one/family/"
doh_url = "https://family.cloudflare-dns.com/dns-query"
dot_hostname = "family.cloudflare-dns.com"
addresses = ["1.1.1.3", "1.0.0.3"]

[[profiles]]
slug = "cleanbrowsing-family"
provider = "CleanBrowsing"
variant = "Family Filter"
display_name = "CleanBrowsing - Family Filter"
blocks = "Adult content, and enforces safe search"
description = "Blocks adult content and enforces safe search on major search engines. Operated by CleanBrowsing. Does not block advertising."
homepage = "https://cleanbrowsing.org/filters/"
doh_url = "https://doh.cleanbrowsing.org/doh/family-filter/"
dot_hostname = "family-filter-dns.cleanbrowsing.org"
addresses = ["185.228.168.168", "185.228.169.168"]

[[profiles]]
slug = "cleanbrowsing-security"
provider = "CleanBrowsing"
variant = "Security Filter"
display_name = "CleanBrowsing - Security Filter"
blocks = "Malware and phishing - does not block ads"
description = "Blocks malware and phishing domains. Operated by CleanBrowsing. Does not block advertising or adult content."
homepage = "https://cleanbrowsing.org/filters/"
doh_url = "https://doh.cleanbrowsing.org/doh/security-filter/"
dot_hostname = "security-filter-dns.cleanbrowsing.org"
addresses = ["185.228.168.9", "185.228.169.9"]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_catalog.py -v`
Expected: PASS, 8 passed.

- [ ] **Step 6: Commit**

```bash
git add providers.toml dnsprofiles/catalog.py tests/test_catalog.py
git commit -m "Add provider catalogue with nine verified DNS variants"
```

---

### Task 3: Profile construction

The payload builder, with the determinism guarantees the CI drift check depends on.

**Files:**
- Create: `dnsprofiles/profile.py`
- Test: `tests/test_profile.py`

**Interfaces:**
- Consumes: `ProfileSpec` from `dnsprofiles.catalog`.
- Produces:
  - `PAGES_BASE: str`, `IDENTIFIER_PREFIX: str`
  - `PROTOCOLS: tuple[str, ...]` equal to `("doh", "dot")`
  - `profile_filename(slug: str, protocol: str) -> str`
  - `profile_url(slug: str, protocol: str) -> str`
  - `build_profile(spec: ProfileSpec, protocol: str) -> dict`
  - `to_plist_bytes(profile: dict) -> bytes`

- [ ] **Step 1: Write the failing tests**

`tests/test_profile.py`:

```python
import plistlib
import uuid

import pytest

from dnsprofiles.catalog import ProfileSpec
from dnsprofiles.profile import (
    PAGES_BASE,
    PROTOCOLS,
    build_profile,
    profile_filename,
    profile_url,
    to_plist_bytes,
)

SPEC = ProfileSpec(
    slug="adguard-family",
    provider="AdGuard",
    variant="Family Protection",
    display_name="AdGuard DNS - Family Protection",
    blocks="Ads, trackers and adult content",
    description="Blocks ads, trackers and adult content.",
    homepage="https://adguard-dns.io/",
    doh_url="https://family.adguard-dns.com/dns-query",
    dot_hostname="family.adguard-dns.com",
    addresses=("94.140.14.15", "94.140.15.16"),
)


def test_protocols_are_doh_and_dot():
    assert PROTOCOLS == ("doh", "dot")


def test_filename_and_url():
    assert profile_filename("adguard-family", "doh") == "adguard-family-doh.mobileconfig"
    assert profile_url("adguard-family", "doh") == (
        f"{PAGES_BASE}/profiles/adguard-family-doh.mobileconfig"
    )


def test_doh_payload_uses_server_url_and_https_protocol():
    settings = build_profile(SPEC, "doh")["PayloadContent"][0]["DNSSettings"]
    assert settings["DNSProtocol"] == "HTTPS"
    assert settings["ServerURL"] == "https://family.adguard-dns.com/dns-query"
    assert settings["ServerAddresses"] == ["94.140.14.15", "94.140.15.16"]
    assert "ServerName" not in settings


def test_dot_payload_uses_server_name_and_tls_protocol():
    settings = build_profile(SPEC, "dot")["PayloadContent"][0]["DNSSettings"]
    assert settings["DNSProtocol"] == "TLS"
    assert settings["ServerName"] == "family.adguard-dns.com"
    assert settings["ServerAddresses"] == ["94.140.14.15", "94.140.15.16"]
    assert "ServerURL" not in settings


def test_top_level_keys_match_the_spec():
    profile = build_profile(SPEC, "doh")
    assert profile["PayloadType"] == "Configuration"
    assert profile["PayloadVersion"] == 1
    assert profile["PayloadOrganization"] == "Atik Ansari"
    assert profile["PayloadRemovalDisallowed"] is False
    assert profile["PayloadIdentifier"] == "com.atikansari.dns.adguard-family-doh"
    assert profile["PayloadDisplayName"] == "AdGuard DNS - Family Protection (DoH)"
    assert "OnDemandRules" not in profile
    assert "ProhibitDisablement" not in profile


def test_inner_payload_identity():
    payload = build_profile(SPEC, "dot")["PayloadContent"][0]
    assert payload["PayloadType"] == "com.apple.dnsSettings.managed"
    assert payload["PayloadIdentifier"] == "com.atikansari.dns.adguard-family-dot.settings"
    assert payload["PayloadVersion"] == 1


def test_uuid_is_uuid5_of_the_canonical_url():
    profile = build_profile(SPEC, "doh")
    expected = str(
        uuid.uuid5(uuid.NAMESPACE_URL, profile_url("adguard-family", "doh"))
    ).upper()
    assert profile["PayloadUUID"] == expected


def test_outer_and_inner_uuids_differ():
    profile = build_profile(SPEC, "doh")
    assert profile["PayloadUUID"] != profile["PayloadContent"][0]["PayloadUUID"]


def test_generation_is_deterministic():
    assert to_plist_bytes(build_profile(SPEC, "doh")) == to_plist_bytes(
        build_profile(SPEC, "doh")
    )


def test_output_is_a_parseable_plist():
    parsed = plistlib.loads(to_plist_bytes(build_profile(SPEC, "doh")))
    assert parsed["PayloadIdentifier"] == "com.atikansari.dns.adguard-family-doh"


def test_unknown_protocol_is_rejected():
    with pytest.raises(ValueError, match="protocol"):
        build_profile(SPEC, "quic")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_profile.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dnsprofiles.profile'`

- [ ] **Step 3: Write `dnsprofiles/profile.py`**

```python
"""Construction of Apple configuration profiles from catalogue entries."""

from __future__ import annotations

import plistlib
import uuid

from dnsprofiles.catalog import ProfileSpec

PAGES_BASE = "https://atikansari-ghr.github.io/encrypted-dns-profiles"
IDENTIFIER_PREFIX = "com.atikansari.dns"
ORGANIZATION = "Atik Ansari"

PROTOCOLS = ("doh", "dot")

_PROTOCOL_LABELS = {"doh": "DoH", "dot": "DoT"}


def profile_filename(slug: str, protocol: str) -> str:
    return f"{slug}-{protocol}.mobileconfig"


def profile_url(slug: str, protocol: str) -> str:
    return f"{PAGES_BASE}/profiles/{profile_filename(slug, protocol)}"


def _identifier(slug: str, protocol: str) -> str:
    return f"{IDENTIFIER_PREFIX}.{slug}-{protocol}"


def _uuid_for(url: str) -> str:
    """Derive a stable UUIDv5 so regeneration is byte-identical."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url)).upper()


def _dns_settings(spec: ProfileSpec, protocol: str) -> dict:
    settings: dict = {"ServerAddresses": list(spec.addresses)}
    if protocol == "doh":
        settings["DNSProtocol"] = "HTTPS"
        settings["ServerURL"] = spec.doh_url
    else:
        settings["DNSProtocol"] = "TLS"
        settings["ServerName"] = spec.dot_hostname
    return settings


def build_profile(spec: ProfileSpec, protocol: str) -> dict:
    """Build the profile dictionary for one catalogue entry and protocol."""
    if protocol not in PROTOCOLS:
        raise ValueError(f"unknown protocol '{protocol}'; expected one of {PROTOCOLS}")

    label = _PROTOCOL_LABELS[protocol]
    identifier = _identifier(spec.slug, protocol)
    url = profile_url(spec.slug, protocol)
    display_name = f"{spec.display_name} ({label})"

    description = (
        f"{spec.description}\n\n"
        f"Blocks: {spec.blocks}.\n"
        f"Transport: {'DNS-over-HTTPS' if protocol == 'doh' else 'DNS-over-TLS'}.\n"
        f"Provider: {spec.homepage}"
    )

    return {
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": identifier,
        "PayloadUUID": _uuid_for(url),
        "PayloadDisplayName": display_name,
        "PayloadDescription": description,
        "PayloadOrganization": ORGANIZATION,
        "PayloadRemovalDisallowed": False,
        "PayloadContent": [
            {
                "PayloadType": "com.apple.dnsSettings.managed",
                "PayloadVersion": 1,
                "PayloadIdentifier": f"{identifier}.settings",
                "PayloadUUID": _uuid_for(f"{url}#settings"),
                "PayloadDisplayName": display_name,
                "PayloadOrganization": ORGANIZATION,
                "DNSSettings": _dns_settings(spec, protocol),
            }
        ],
    }


def to_plist_bytes(profile: dict) -> bytes:
    """Serialise a profile to XML plist bytes, deterministically."""
    return plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_profile.py -v`
Expected: PASS, 11 passed.

- [ ] **Step 5: Commit**

```bash
git add dnsprofiles/profile.py tests/test_profile.py
git commit -m "Add deterministic configuration profile builder"
```

---

### Task 4: Generator CLI and the eighteen profiles

**Files:**
- Create: `scripts/generate_profiles.py`, `dnsprofiles/generate.py`
- Create (generated): `docs/profiles/*.mobileconfig` — 18 files
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `load_catalog`, `build_profile`, `to_plist_bytes`, `profile_filename`, `PROTOCOLS`.
- Produces: `generate_all(catalog_path: Path, output_dir: Path) -> list[Path]`, returning written paths sorted by filename.

- [ ] **Step 1: Write the failing tests**

`tests/test_generate.py`:

```python
import plistlib
from pathlib import Path

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog
from dnsprofiles.generate import generate_all

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "profiles"


def test_generates_two_files_per_catalogue_entry(tmp_path):
    written = generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    assert len(written) == 2 * len(load_catalog(DEFAULT_CATALOG_PATH))
    assert len(written) == 18


def test_every_written_file_parses_as_a_plist(tmp_path):
    for path in generate_all(DEFAULT_CATALOG_PATH, tmp_path):
        parsed = plistlib.loads(path.read_bytes())
        assert parsed["PayloadType"] == "Configuration"


def test_regeneration_is_byte_identical(tmp_path):
    first = {p.name: p.read_bytes() for p in generate_all(DEFAULT_CATALOG_PATH, tmp_path)}
    second = {p.name: p.read_bytes() for p in generate_all(DEFAULT_CATALOG_PATH, tmp_path)}
    assert first == second


def test_committed_profiles_match_a_fresh_generation(tmp_path):
    """The repository must never drift from the catalogue."""
    fresh = {p.name: p.read_bytes() for p in generate_all(DEFAULT_CATALOG_PATH, tmp_path)}
    committed = {p.name: p.read_bytes() for p in OUTPUT.glob("*.mobileconfig")}
    assert committed == fresh


def test_removes_profiles_no_longer_in_the_catalogue(tmp_path):
    stale = tmp_path / "gone-doh.mobileconfig"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"stale")
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    assert not stale.exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dnsprofiles.generate'`

- [ ] **Step 3: Write `dnsprofiles/generate.py`**

Stale-file removal matters: without it, renaming a slug leaves an orphaned profile being served from Pages forever.

```python
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
```

- [ ] **Step 4: Write the CLI `scripts/generate_profiles.py`**

```python
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
```

- [ ] **Step 5: Generate the profiles**

Run: `python scripts/generate_profiles.py`
Expected: 18 paths printed, ending `18 profiles written to docs\profiles`

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_generate.py -v`
Expected: PASS, 5 passed.

- [ ] **Step 7: Verify determinism against git**

Run: `python scripts/generate_profiles.py && git status --porcelain docs/profiles`
Expected: after `git add`, no further modifications appear on a second run. Empty output means regeneration is byte-stable.

- [ ] **Step 8: Commit**

```bash
git add dnsprofiles/generate.py scripts/generate_profiles.py tests/test_generate.py docs/profiles
git commit -m "Generate eighteen DoH and DoT profiles from the catalogue"
```

---

### Task 5: Offline schema validation

**Files:**
- Create: `dnsprofiles/validate.py`, `scripts/validate_profiles.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `load_catalog`, `profile_filename`, `PROTOCOLS`.
- Produces: `validate_directory(catalog_path: Path, profile_dir: Path) -> list[str]` returning human-readable problems; empty list means valid.

- [ ] **Step 1: Write the failing tests**

`tests/test_validate.py`:

```python
import plistlib
from pathlib import Path

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH
from dnsprofiles.generate import generate_all
from dnsprofiles.validate import validate_directory

PROFILES = Path(__file__).resolve().parent.parent / "docs" / "profiles"


def test_the_shipped_profiles_are_valid():
    assert validate_directory(DEFAULT_CATALOG_PATH, PROFILES) == []


def test_detects_a_missing_file(tmp_path):
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    (tmp_path / "adguard-default-doh.mobileconfig").unlink()
    problems = validate_directory(DEFAULT_CATALOG_PATH, tmp_path)
    assert any("adguard-default-doh" in p and "missing" in p for p in problems)


def test_detects_a_bad_dns_protocol(tmp_path):
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    path = tmp_path / "adguard-default-doh.mobileconfig"
    data = plistlib.loads(path.read_bytes())
    data["PayloadContent"][0]["DNSSettings"]["DNSProtocol"] = "QUIC"
    path.write_bytes(plistlib.dumps(data))
    assert any("DNSProtocol" in p for p in validate_directory(DEFAULT_CATALOG_PATH, tmp_path))


def test_detects_protocol_and_endpoint_key_mismatch(tmp_path):
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    path = tmp_path / "adguard-default-doh.mobileconfig"
    data = plistlib.loads(path.read_bytes())
    settings = data["PayloadContent"][0]["DNSSettings"]
    del settings["ServerURL"]
    settings["ServerName"] = "dns.adguard-dns.com"
    path.write_bytes(plistlib.dumps(data))
    assert any("ServerURL" in p for p in validate_directory(DEFAULT_CATALOG_PATH, tmp_path))


def test_detects_removal_disallowed_set_true(tmp_path):
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    path = tmp_path / "adguard-default-doh.mobileconfig"
    data = plistlib.loads(path.read_bytes())
    data["PayloadRemovalDisallowed"] = True
    path.write_bytes(plistlib.dumps(data))
    assert any("PayloadRemovalDisallowed" in p for p in validate_directory(DEFAULT_CATALOG_PATH, tmp_path))


def test_detects_duplicate_identifiers(tmp_path):
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    path = tmp_path / "adguard-family-doh.mobileconfig"
    data = plistlib.loads(path.read_bytes())
    data["PayloadIdentifier"] = "com.atikansari.dns.adguard-default-doh"
    path.write_bytes(plistlib.dumps(data))
    assert any("duplicate" in p.lower() for p in validate_directory(DEFAULT_CATALOG_PATH, tmp_path))


def test_detects_an_unexpected_extra_file(tmp_path):
    generate_all(DEFAULT_CATALOG_PATH, tmp_path)
    (tmp_path / "rogue-doh.mobileconfig").write_bytes(b"<plist></plist>")
    assert any("rogue-doh" in p for p in validate_directory(DEFAULT_CATALOG_PATH, tmp_path))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dnsprofiles.validate'`

- [ ] **Step 3: Write `dnsprofiles/validate.py`**

```python
"""Offline structural validation of generated profiles."""

from __future__ import annotations

import plistlib
import uuid
from pathlib import Path

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog
from dnsprofiles.profile import PROTOCOLS, profile_filename

_ENDPOINT_KEY = {"HTTPS": "ServerURL", "TLS": "ServerName"}
_EXPECTED_DNS_PROTOCOL = {"doh": "HTTPS", "dot": "TLS"}


def _check_uuid(value: object, label: str, problems: list[str]) -> None:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError):
        problems.append(f"{label}: malformed UUID {value!r}")


def validate_directory(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    profile_dir: Path = Path("docs/profiles"),
) -> list[str]:
    """Return a list of problems; an empty list means the directory is valid."""
    profile_dir = Path(profile_dir)
    problems: list[str] = []
    identifiers: dict[str, str] = {}
    expected_names: set[str] = set()

    for spec in load_catalog(catalog_path):
        for protocol in PROTOCOLS:
            name = profile_filename(spec.slug, protocol)
            expected_names.add(name)
            path = profile_dir / name

            if not path.exists():
                problems.append(f"{name}: missing")
                continue

            try:
                data = plistlib.loads(path.read_bytes())
            except Exception as exc:
                problems.append(f"{name}: unparseable plist ({exc})")
                continue

            if data.get("PayloadType") != "Configuration":
                problems.append(f"{name}: PayloadType must be 'Configuration'")
            if data.get("PayloadOrganization") != "Atik Ansari":
                problems.append(f"{name}: PayloadOrganization must be 'Atik Ansari'")
            if data.get("PayloadRemovalDisallowed") is not False:
                problems.append(f"{name}: PayloadRemovalDisallowed must be false")
            for forbidden in ("OnDemandRules", "ProhibitDisablement"):
                if forbidden in data:
                    problems.append(f"{name}: must not set {forbidden}")

            identifier = data.get("PayloadIdentifier", "")
            if identifier in identifiers:
                problems.append(
                    f"{name}: duplicate PayloadIdentifier, also used by {identifiers[identifier]}"
                )
            identifiers[identifier] = name
            _check_uuid(data.get("PayloadUUID"), name, problems)

            content = data.get("PayloadContent") or []
            if len(content) != 1:
                problems.append(f"{name}: expected exactly one payload")
                continue

            payload = content[0]
            if payload.get("PayloadType") != "com.apple.dnsSettings.managed":
                problems.append(f"{name}: inner PayloadType must be com.apple.dnsSettings.managed")
            _check_uuid(payload.get("PayloadUUID"), f"{name} payload", problems)

            settings = payload.get("DNSSettings") or {}
            dns_protocol = settings.get("DNSProtocol")
            if dns_protocol != _EXPECTED_DNS_PROTOCOL[protocol]:
                problems.append(
                    f"{name}: DNSProtocol is {dns_protocol!r}, "
                    f"expected {_EXPECTED_DNS_PROTOCOL[protocol]!r}"
                )
                continue

            required = _ENDPOINT_KEY[dns_protocol]
            forbidden = _ENDPOINT_KEY["TLS" if dns_protocol == "HTTPS" else "HTTPS"]
            if not settings.get(required):
                problems.append(f"{name}: {dns_protocol} profile must set {required}")
            if forbidden in settings:
                problems.append(f"{name}: {dns_protocol} profile must not set {forbidden}")
            if not settings.get("ServerAddresses"):
                problems.append(f"{name}: ServerAddresses must not be empty")

    for found in sorted(profile_dir.glob("*.mobileconfig")):
        if found.name not in expected_names:
            problems.append(f"{found.name}: not named by the catalogue")

    return problems
```

- [ ] **Step 4: Write the CLI `scripts/validate_profiles.py`**

```python
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
```

- [ ] **Step 5: Run the tests and the CLI**

Run: `python -m pytest tests/test_validate.py -v && python scripts/validate_profiles.py`
Expected: PASS, 7 passed, then `All profiles valid.`

- [ ] **Step 6: Commit**

```bash
git add dnsprofiles/validate.py scripts/validate_profiles.py tests/test_validate.py
git commit -m "Add offline schema validation for generated profiles"
```

---

### Task 6: Endpoint liveness checking

The check that would have caught dns0.eu. Network calls are isolated behind two injectable probe functions so the unit tests never touch the network.

**Files:**
- Create: `dnsprofiles/liveness.py`, `scripts/check_endpoints.py`
- Test: `tests/test_liveness.py`

**Interfaces:**
- Consumes: `load_catalog`, `ProfileSpec`.
- Produces:
  - `RFC8484_QUERY: str` — base64url DNS query for `www.example.com A`
  - `probe_doh(url: str, timeout: float = 10.0) -> tuple[bool, str]`
  - `probe_dot(hostname: str, timeout: float = 10.0) -> tuple[bool, str]`
  - `check_all(specs, doh_probe=probe_doh, dot_probe=probe_dot) -> list[tuple[str, bool, str]]` returning `(label, ok, detail)`

- [ ] **Step 1: Write the failing tests**

`tests/test_liveness.py`:

```python
from dnsprofiles.catalog import ProfileSpec
from dnsprofiles.liveness import RFC8484_QUERY, check_all

SPEC = ProfileSpec(
    slug="adguard-default",
    provider="AdGuard",
    variant="Default",
    display_name="AdGuard DNS - Ad Blocking",
    blocks="Ads and trackers",
    description="Blocks ads.",
    homepage="https://adguard-dns.io/",
    doh_url="https://dns.adguard-dns.com/dns-query",
    dot_hostname="dns.adguard-dns.com",
    addresses=("94.140.14.14",),
)


def ok_probe(target, timeout=10.0):
    return True, "200"


def fail_probe(target, timeout=10.0):
    return False, "NXDOMAIN"


def test_query_is_the_rfc8484_test_vector():
    assert RFC8484_QUERY == "AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB"


def test_checks_both_protocols_per_spec():
    results = check_all([SPEC], doh_probe=ok_probe, dot_probe=ok_probe)
    assert len(results) == 2
    assert [label for label, _, _ in results] == [
        "adguard-default (DoH)",
        "adguard-default (DoT)",
    ]
    assert all(ok for _, ok, _ in results)


def test_reports_failures_with_detail():
    results = check_all([SPEC], doh_probe=fail_probe, dot_probe=ok_probe)
    doh, dot = results
    assert doh[1] is False and doh[2] == "NXDOMAIN"
    assert dot[1] is True


def test_probes_receive_the_right_targets():
    seen = {}

    def record_doh(target, timeout=10.0):
        seen["doh"] = target
        return True, "200"

    def record_dot(target, timeout=10.0):
        seen["dot"] = target
        return True, "handshake ok"

    check_all([SPEC], doh_probe=record_doh, dot_probe=record_dot)
    assert seen["doh"] == "https://dns.adguard-dns.com/dns-query"
    assert seen["dot"] == "dns.adguard-dns.com"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_liveness.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dnsprofiles.liveness'`

- [ ] **Step 3: Write `dnsprofiles/liveness.py`**

```python
"""Live checks that provider endpoints still answer."""

from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable

from dnsprofiles.catalog import ProfileSpec

# RFC 8484 test vector: a DNS query for www.example.com A, base64url encoded.
RFC8484_QUERY = "AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB"

DOT_PORT = 853

Probe = Callable[..., tuple[bool, str]]


def probe_doh(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Send an RFC 8484 GET query and report whether the resolver answered."""
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}dns={RFC8484_QUERY}",
        headers={"accept": "application/dns-message"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.status != 200:
                return False, f"HTTP {response.status}"
            if not body:
                return False, "HTTP 200 with empty body"
            return True, f"HTTP 200, {len(body)} bytes"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def probe_dot(hostname: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Complete a TLS handshake on port 853 and verify the certificate."""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, DOT_PORT), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=hostname) as tls:
                return True, f"TLS {tls.version()}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def check_all(
    specs: Iterable[ProfileSpec],
    doh_probe: Probe = probe_doh,
    dot_probe: Probe = probe_dot,
) -> list[tuple[str, bool, str]]:
    """Probe every endpoint, returning (label, ok, detail) in catalogue order."""
    results: list[tuple[str, bool, str]] = []
    for spec in specs:
        ok, detail = doh_probe(spec.doh_url)
        results.append((f"{spec.slug} (DoH)", ok, detail))
        ok, detail = dot_probe(spec.dot_hostname)
        results.append((f"{spec.slug} (DoT)", ok, detail))
    return results
```

- [ ] **Step 4: Write the CLI `scripts/check_endpoints.py`**

```python
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
```

- [ ] **Step 5: Run the unit tests**

Run: `python -m pytest tests/test_liveness.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 6: Run the real check and record the result**

Run: `python scripts/check_endpoints.py`
Expected on this development machine: AdGuard, Cloudflare, ControlD and CleanBrowsing report PASS; **Mullvad reports FAIL** because this network filters it (spec §2.3). That is expected locally and must pass in CI. Do not "fix" a Mullvad failure here — confirm it in CI first.

- [ ] **Step 7: Commit**

```bash
git add dnsprofiles/liveness.py scripts/check_endpoints.py tests/test_liveness.py
git commit -m "Add DoH and DoT endpoint liveness checks"
```

---

### Task 7: Continuous integration

**Files:**
- Create: `.github/workflows/validate.yml`, `.github/workflows/endpoints.yml`, `.github/workflows/pages.yml`, `.github/FUNDING.yml`

**Interfaces:**
- Consumes: `scripts/generate_profiles.py`, `scripts/validate_profiles.py`, `scripts/check_endpoints.py`, `python -m pytest`.
- Produces: workflow names `validate` and `endpoints` for README badge URLs.

- [ ] **Step 1: Write `.github/workflows/validate.yml`**

Liveness deliberately lives in a separate workflow: a provider outage must not turn every pull request red.

```yaml
name: validate

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install test dependencies
        run: python -m pip install --upgrade pip pytest

      - name: Run unit tests
        run: python -m pytest -v

      - name: Regenerate profiles
        run: python scripts/generate_profiles.py

      - name: Fail if the committed profiles drifted from the catalogue
        run: |
          if ! git diff --exit-code --stat docs/profiles; then
            echo "::error::docs/profiles is out of date. Run: python scripts/generate_profiles.py"
            exit 1
          fi

      - name: Validate profile structure
        run: python scripts/validate_profiles.py
```

- [ ] **Step 2: Write `.github/workflows/endpoints.yml`**

```yaml
name: endpoints

on:
  schedule:
    - cron: '17 6 * * 1'
  workflow_dispatch:

jobs:
  liveness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Probe every provider endpoint
        run: python scripts/check_endpoints.py
```

- [ ] **Step 3: Write `.github/workflows/pages.yml`**

```yaml
name: pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Write `.github/FUNDING.yml`**

```yaml
ko_fi: atikansari
```

- [ ] **Step 5: Verify the workflow files parse**

Run: `python -c "import json,sys; [print(p) for p in __import__('pathlib').Path('.github/workflows').glob('*.yml')]"`
Expected: three paths listed. Full YAML linting happens on GitHub at push time.

- [ ] **Step 6: Commit**

```bash
git add .github
git commit -m "Add validation, endpoint liveness and Pages workflows"
```

---

### Task 8: Illustrative SVG mockups

Four hand-drawn SVGs in the flat style of the existing `terminal.svg` / `telegram.svg`.

**Files:**
- Create: `docs/screenshots/ios-install.svg`, `docs/screenshots/ios-dns-selector.svg`, `docs/screenshots/android-private-dns.svg`, `docs/screenshots/provider-comparison.svg`

**Interfaces:**
- Consumes: nothing.
- Produces: four SVG paths referenced by `README.md` (Task 11) and `docs/index.html` (Task 10).

Full SVG source is not reproduced here because each file is several hundred lines of coordinates; the acceptance criteria below are the contract, and each file is written directly by the implementer.

- [ ] **Step 1: Draw `ios-install.svg`**

Three iPhone frames side by side, each roughly 300×620 within a single viewBox:

1. Safari showing the install page with a "Download AdGuard — Ad Blocking (DoH)" button and the iOS download confirmation sheet.
2. Settings root with a **Profile Downloaded** row highlighted near the top.
3. The Install Profile screen showing title "AdGuard DNS — Ad Blocking (DoH)", `Signed: Not Signed` **rendered in red**, a Description line, and an Install button.

Requirements: no external fonts — use `font-family="-apple-system, Helvetica, Arial, sans-serif"`; no raster images; no `<script>`; a `<title>` element for accessibility.

- [ ] **Step 2: Draw `ios-dns-selector.svg`**

One iPhone frame showing Settings → General → VPN & Device Management → DNS with four installed profiles listed and a checkmark against "AdGuard DNS — Ad Blocking (DoH)". This is the image that teaches readers they can install several profiles and switch between them.

- [ ] **Step 3: Draw `android-private-dns.svg`**

One Android frame showing the Private DNS dialog: three radio options (Off / Automatic / Private DNS provider hostname) with the third selected and `dns.adguard-dns.com` typed into the field, plus Cancel and Save buttons.

- [ ] **Step 4: Draw `provider-comparison.svg`**

A table graphic with one row per provider variant and columns Ads / Trackers / Malware / Adult, using filled and hollow marks. It must visibly show that the two Cloudflare rows are **empty in the Ads column** — that contrast is the point of the graphic.

- [ ] **Step 5: Verify every SVG is well-formed and self-contained**

```bash
python - <<'PY'
import pathlib, re, xml.etree.ElementTree as ET
for p in sorted(pathlib.Path("docs/screenshots").glob("*.svg")):
    ET.parse(p)
    text = p.read_text(encoding="utf-8")
    assert "<script" not in text, f"{p}: contains a script"
    assert not re.search(r'(href|src)\s*=\s*"https?://', text), f"{p}: external reference"
    print(f"OK  {p.name}  ({len(text)} bytes)")
PY
```

Expected: four `OK` lines, no assertion errors.

- [ ] **Step 6: Commit**

```bash
git add docs/screenshots
git commit -m "Add illustrative SVG mockups for iOS and Android setup"
```

---

### Task 9: QR codes and social preview image

**Files:**
- Create: `scripts/make_qr.py`, `docs/qr/*.svg` (18 files), `docs/social-preview.png`
- Test: `tests/test_qr.py`

**Interfaces:**
- Consumes: `load_catalog`, `profile_url`, `PROTOCOLS`.
- Produces: `generate_qr_codes(catalog_path: Path, output_dir: Path) -> list[Path]`, one SVG per profile named `<slug>-<protocol>.svg`.

- [ ] **Step 1: Install the build-time dependency**

Run: `python -m pip install segno`
Expected: `Successfully installed segno-...`

- [ ] **Step 2: Write the failing test**

`tests/test_qr.py`:

```python
import pytest

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH

segno = pytest.importorskip("segno")

from scripts.make_qr import generate_qr_codes  # noqa: E402


def test_generates_one_qr_per_profile(tmp_path):
    written = generate_qr_codes(DEFAULT_CATALOG_PATH, tmp_path)
    assert len(written) == 18
    assert (tmp_path / "adguard-default-doh.svg").exists()


def test_qr_encodes_the_canonical_pages_url(tmp_path):
    generate_qr_codes(DEFAULT_CATALOG_PATH, tmp_path)
    text = (tmp_path / "adguard-default-doh.svg").read_text(encoding="utf-8")
    assert text.lstrip().startswith("<?xml") or text.lstrip().startswith("<svg")
    assert "<script" not in text
```

- [ ] **Step 3: Add `tests/conftest.py` so `scripts` is importable**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

Also create an empty `scripts/__init__.py` so `from scripts.make_qr import ...` resolves.

- [ ] **Step 4: Run the test to verify it fails**

Run: `python -m pytest tests/test_qr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.make_qr'`

- [ ] **Step 5: Write `scripts/make_qr.py`**

```python
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
            segno.make(profile_url(spec.slug, protocol), error="m").save(
                str(path), kind="svg", scale=4, border=2, dark="#111111", light=None
            )
            written.append(path)
    return sorted(written, key=lambda path: path.name)


if __name__ == "__main__":
    paths = generate_qr_codes()
    print(f"{len(paths)} QR codes written")
```

- [ ] **Step 6: Generate and test**

Run: `python scripts/make_qr.py && python -m pytest tests/test_qr.py -v`
Expected: `18 QR codes written`, then PASS, 2 passed.

- [ ] **Step 7: Compose and capture `docs/social-preview.png`**

Write a temporary `docs/_social.html` sized exactly 1280×640: project name, the strapline "Encrypted DNS profiles for iOS, iPadOS, macOS and Android", the AdGuard-led provider logotype row as plain text, and a muted background. Open it in the browser tool at viewport 1280×640, screenshot it, save as `docs/social-preview.png`, then delete `docs/_social.html`.

Verify the dimensions:

```bash
python - <<'PY'
import struct, pathlib
data = pathlib.Path("docs/social-preview.png").read_bytes()
assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
width, height = struct.unpack(">II", data[16:24])
print(f"{width}x{height}")
assert (width, height) == (1280, 640), f"expected 1280x640, got {width}x{height}"
PY
```

Expected: `1280x640`

- [ ] **Step 8: Commit**

```bash
git add scripts/__init__.py scripts/make_qr.py tests/conftest.py tests/test_qr.py docs/qr docs/social-preview.png
git commit -m "Add QR codes for every profile and the social preview image"
```

---

### Task 10: The Pages install site

**Files:**
- Create: `docs/index.html`
- Test: `tests/test_site.py`

**Interfaces:**
- Consumes: `docs/profiles/*.mobileconfig`, `docs/qr/*.svg`, `docs/screenshots/*.svg`, `load_catalog`.
- Produces: the published install site. Hand-written and committed, not generated — but the test below keeps it honest against the catalogue.

- [ ] **Step 1: Write the failing test**

`tests/test_site.py`:

```python
import re
from pathlib import Path

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog
from dnsprofiles.profile import PROTOCOLS, profile_filename

INDEX = Path(__file__).resolve().parent.parent / "docs" / "index.html"


def test_links_to_every_profile():
    html = INDEX.read_text(encoding="utf-8")
    for spec in load_catalog(DEFAULT_CATALOG_PATH):
        for protocol in PROTOCOLS:
            assert f"profiles/{profile_filename(spec.slug, protocol)}" in html


def test_makes_no_external_requests():
    html = INDEX.read_text(encoding="utf-8")
    external = re.findall(r'(?:href|src)\s*=\s*["\'](https?://[^"\']+)', html)
    offsite = [
        url
        for url in external
        if not url.startswith("https://github.com/atikansari-ghr/")
    ]
    assert offsite == [], f"external assets or links found: {offsite}"


def test_names_every_android_dot_hostname():
    html = INDEX.read_text(encoding="utf-8")
    for spec in load_catalog(DEFAULT_CATALOG_PATH):
        assert spec.dot_hostname in html


def test_explains_the_unsigned_warning():
    html = INDEX.read_text(encoding="utf-8").lower()
    assert "not signed" in html
```

Note: the external-link test permits links back to the project's own GitHub repository, since the site must link to its source. Provider homepages are rendered as plain text rather than anchors to keep the rule absolute and the test simple.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_site.py -v`
Expected: FAIL — `FileNotFoundError: docs/index.html`

- [ ] **Step 3: Write `docs/index.html`**

One self-contained file. All CSS in a single `<style>` block, the only JavaScript being a short inline clipboard handler for the Android hostnames. Required structure:

1. `<header>` — project name, one-line description, link to the GitHub repository.
2. **What this does** — a DNS profile changes which resolver the device uses; it is not a VPN; it applies to every app.
3. **Choose a profile** — nine cards, one per catalogue entry, each containing: provider and variant name, the `blocks` line verbatim from the catalogue, an operator line, a DoH install button (primary), a DoT install button (secondary), the DoT hostname with a **Copy** button for Android, and the DoH QR code inline via `<img src="qr/<slug>-doh.svg">`. The two Cloudflare cards must carry a visible "does not block ads" note.
4. **Install on iPhone or iPad** — numbered steps with `screenshots/ios-install.svg`, including a callout explaining that "Not Signed" is expected and why, and a note that switching between installed profiles happens under Settings → General → VPN & Device Management.
5. **Install on Android** — Private DNS steps for stock Android and Samsung stated separately, DoT-only and Android 9+ called out.
6. **Install on macOS** — System Settings → General → Device Management.
7. **Check it is working** — visit a provider test page, confirm ads disappear, and re-check Settings.
8. **FAQ** — is this a VPN, does it cost anything, does it slow browsing, how to remove a profile, what happens on a network that blocks DoH.
9. `<footer>` — MIT, Atik Ansari, repository link.

Styling constraints: `<meta name="viewport" content="width=device-width, initial-scale=1">`; system font stack only; CSS custom properties for colour with a `@media (prefers-color-scheme: dark)` block; mobile-first layout with cards in a responsive grid; no external requests of any kind.

The copy button handler, inline at the end of `<body>`:

```html
<script>
  document.querySelectorAll('[data-copy]').forEach(function (button) {
    button.addEventListener('click', function () {
      navigator.clipboard.writeText(button.dataset.copy).then(function () {
        var original = button.textContent;
        button.textContent = 'Copied';
        setTimeout(function () { button.textContent = original; }, 1500);
      });
    });
  });
</script>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_site.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 5: Review the rendered page**

Serve locally and open it in the browser tool at both mobile and desktop widths, in light and dark colour schemes:

```bash
python -m http.server 8000 --directory docs
```

Confirm: cards reflow without horizontal scrolling at 375px; dark mode is readable; every QR image loads; no console errors; the network panel shows zero third-party requests.

- [ ] **Step 6: Commit**

```bash
git add docs/index.html tests/test_site.py
git commit -m "Add the GitHub Pages install site"
```

---

### Task 11: Android Private DNS helper script

**Files:**
- Create: `scripts/android-private-dns.sh`
- Test: `tests/test_android_script.py`

**Interfaces:**
- Consumes: `providers.toml` (parsed with `grep`/`sed`, so the script stays dependency-free).
- Produces: a CLI with `--list`, `--set <slug>`, `--status`, `--off`, `--help`, resolving `adb` from `PATH`.

- [ ] **Step 1: Write the failing tests**

Tests drive the script through a stub `adb` placed on `PATH`, which records its arguments — no device and no real `adb` needed.

`tests/test_android_script.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "android-private-dns.sh"

pytestmark = pytest.mark.skipif(
    not Path("/usr/bin/bash").exists() and not Path("/bin/bash").exists(),
    reason="bash is required to run the Android helper script",
)


@pytest.fixture
def fake_adb(tmp_path):
    """Put a stub adb on PATH that logs its arguments."""
    log = tmp_path / "adb.log"
    stub = tmp_path / "adb"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{log}"\n'
        'if [ "$1" = "devices" ]; then echo "List of devices attached"; '
        'echo "emulator-5554\tdevice"; fi\n'
        'if [ "$3" = "get" ]; then echo "dns.adguard-dns.com"; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub.parent, log


def run(args, path_dir=None):
    env = dict(os.environ)
    if path_dir:
        env["PATH"] = f"{path_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


def test_help_exits_zero():
    result = run(["--help"])
    assert result.returncode == 0
    assert "--set" in result.stdout


def test_list_shows_every_catalogue_hostname():
    result = run(["--list"])
    assert result.returncode == 0
    assert "dns.adguard-dns.com" in result.stdout
    assert "family.adguard-dns.com" in result.stdout
    assert result.stdout.count("adguard") >= 2


def test_set_writes_both_adb_settings(fake_adb):
    path_dir, log = fake_adb
    result = run(["--set", "adguard-family"], path_dir)
    assert result.returncode == 0
    logged = log.read_text(encoding="utf-8")
    assert "private_dns_mode hostname" in logged
    assert "private_dns_specifier family.adguard-dns.com" in logged


def test_set_rejects_an_unknown_slug(fake_adb):
    path_dir, _ = fake_adb
    result = run(["--set", "not-a-provider"], path_dir)
    assert result.returncode != 0
    assert "not-a-provider" in result.stdout + result.stderr


def test_off_sets_mode_to_off(fake_adb):
    path_dir, log = fake_adb
    assert run(["--off"], path_dir).returncode == 0
    assert "private_dns_mode off" in log.read_text(encoding="utf-8")


def test_fails_cleanly_when_adb_is_absent(tmp_path):
    env = dict(os.environ)
    env["PATH"] = str(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--status"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )
    assert result.returncode != 0
    assert "adb" in (result.stdout + result.stderr).lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_android_script.py -v`
Expected: FAIL — the script does not exist.

- [ ] **Step 3: Write `scripts/android-private-dns.sh`**

```bash
#!/usr/bin/env bash
#
# Set Android Private DNS (DNS-over-TLS) over adb.
#
# Android has no equivalent of an Apple .mobileconfig. Private DNS is the only
# no-root, no-app path, it is DNS-over-TLS only, and it needs Android 9 or later.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CATALOG="${SCRIPT_DIR}/../providers.toml"

usage() {
  cat <<'USAGE'
Usage: android-private-dns.sh [option]

  --list            List available providers and their DoT hostnames
  --set <slug>      Enable Private DNS with that provider
  --status          Show the current Private DNS setting on the device
  --off             Disable Private DNS
  --help            Show this message

Requires adb on PATH, USB debugging enabled, and Android 9 or later.
Example:
  ./scripts/android-private-dns.sh --set adguard-family
USAGE
}

# Emit "slug<TAB>hostname" for every catalogue entry.
catalogue() {
  awk '
    /^slug *=/        { gsub(/.*= *"|"/, ""); slug = $0 }
    /^dot_hostname *=/ { gsub(/.*= *"|"/, ""); if (slug != "") { print slug "\t" $0; slug = "" } }
  ' "$CATALOG"
}

hostname_for() {
  catalogue | awk -F'\t' -v want="$1" '$1 == want { print $2; found = 1 } END { exit !found }'
}

require_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "Error: adb not found on PATH." >&2
    echo "Install Android platform-tools: https://developer.android.com/tools/releases/platform-tools" >&2
    exit 1
  fi
}

cmd_list() {
  printf '%-26s %s\n' "PROVIDER" "DoT HOSTNAME"
  catalogue | while IFS=$'\t' read -r slug host; do
    printf '%-26s %s\n' "$slug" "$host"
  done
}

cmd_set() {
  local slug="${1:-}"
  if [ -z "$slug" ]; then
    echo "Error: --set requires a provider slug. Run --list to see them." >&2
    exit 2
  fi

  local host
  if ! host="$(hostname_for "$slug")"; then
    echo "Error: unknown provider '$slug'. Run --list to see available providers." >&2
    exit 2
  fi

  require_adb
  adb shell settings put global private_dns_mode hostname
  adb shell settings put global private_dns_specifier "$host"

  local applied
  applied="$(adb shell settings get global private_dns_specifier | tr -d '\r')"
  if [ "$applied" != "$host" ]; then
    echo "Error: device reports '$applied' but expected '$host'." >&2
    exit 1
  fi
  echo "Private DNS set to $host ($slug)."
}

cmd_status() {
  require_adb
  local mode specifier
  mode="$(adb shell settings get global private_dns_mode | tr -d '\r')"
  specifier="$(adb shell settings get global private_dns_specifier | tr -d '\r')"
  echo "mode:      ${mode}"
  echo "hostname:  ${specifier}"
}

cmd_off() {
  require_adb
  adb shell settings put global private_dns_mode off
  echo "Private DNS disabled."
}

case "${1:---help}" in
  --list)   cmd_list ;;
  --set)    cmd_set "${2:-}" ;;
  --status) cmd_status ;;
  --off)    cmd_off ;;
  --help|-h) usage ;;
  *)
    echo "Error: unknown option '$1'" >&2
    usage >&2
    exit 2
    ;;
esac
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_android_script.py -v`
Expected: PASS, 6 passed.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests pass across every file written so far.

- [ ] **Step 6: Commit**

```bash
git add scripts/android-private-dns.sh tests/test_android_script.py
git commit -m "Add adb helper for setting Android Private DNS"
```

---

### Task 12: README and changelog

**Files:**
- Create: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_readme.py`

**Interfaces:**
- Consumes: everything built so far.
- Produces: the repository's front page.

- [ ] **Step 1: Write the failing test**

`tests/test_readme.py`:

```python
from pathlib import Path

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH, load_catalog

README = Path(__file__).resolve().parent.parent / "README.md"


def test_documents_every_provider():
    text = README.read_text(encoding="utf-8")
    for spec in load_catalog(DEFAULT_CATALOG_PATH):
        assert spec.display_name in text, f"{spec.slug} missing from README"
        assert spec.dot_hostname in text, f"{spec.slug} DoT hostname missing"


def test_has_no_generated_by_attribution():
    text = README.read_text(encoding="utf-8").lower()
    assert "co-authored-by" not in text
    assert "generated with" not in text


def test_documents_adding_a_provider():
    text = README.read_text(encoding="utf-8")
    assert "providers.toml" in text
    assert "scripts/generate_profiles.py" in text


def test_states_the_platform_floor():
    text = README.read_text(encoding="utf-8")
    assert "iOS 14" in text
    assert "Android 9" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_readme.py -v`
Expected: FAIL — README.md currently holds only the stub content.

- [ ] **Step 3: Write `README.md`**

Follow the section order in spec §10. Required content:

- Title `# Encrypted DNS Profiles`, then badges:

```markdown
[![validate](https://github.com/atikansari-ghr/encrypted-dns-profiles/actions/workflows/validate.yml/badge.svg)](https://github.com/atikansari-ghr/encrypted-dns-profiles/actions/workflows/validate.yml)
[![endpoints](https://github.com/atikansari-ghr/encrypted-dns-profiles/actions/workflows/endpoints.yml/badge.svg)](https://github.com/atikansari-ghr/encrypted-dns-profiles/actions/workflows/endpoints.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
```

- Pitch paragraph naming AdGuard first, stating that a profile installs in under a minute and applies to every app, and that this is not a VPN.
- Screenshots section embedding all four SVGs with descriptive alt text and the italic note *"Illustrative mockups, not real screenshots."*
- **What each provider blocks** — the full table from spec §3, with the Cloudflare rows saying "does not block ads" in bold.
- **Install on iPhone or iPad** — numbered steps, the install-page link, and an explicit paragraph on the red "Not Signed" label: what it means, why signing is not done, and that the profile source is readable at `docs/profiles/`.
- **Install on Android** — Private DNS steps for stock and Samsung, the hostname table, the DoT-only and Android 9+ limits, and the `--set` example:

```bash
./scripts/android-private-dns.sh --set adguard-family
```

- **Install on macOS** — macOS 11+, System Settings → General → Device Management.
- **All profiles** — a table of all 18 with install links to the Pages URLs.
- **Check it is working**.
- **Add a provider** — the exact four-step loop:

```bash
# 1. Append a [[profiles]] block to providers.toml
# 2. Regenerate
python scripts/generate_profiles.py
# 3. Validate structure and endpoints
python scripts/validate_profiles.py
python scripts/check_endpoints.py
# 4. Run the tests, then open a pull request
python -m pytest
```

  State that slugs are frozen once released because the payload UUID derives from the filename.
- **Troubleshooting** — Safari shows XML instead of downloading; the profile installs but DNS does not change; a network blocks DoH so switch to DoT or vice versa; a VPN overrides the DNS profile; how to remove a profile.
- **Security notes** — a DNS provider sees every domain you resolve; profiles are unsigned and readable; bootstrap IPs are included; the site makes no external requests; no telemetry.
- **Support** — the Ko-fi badge, matching the existing project.
- **Author** — `**Atik Ansari** — [github.com/atikansari-ghr](https://github.com/atikansari-ghr)`
- **License** — `[MIT](LICENSE)`

- [ ] **Step 4: Update `CHANGELOG.md`**

```markdown
## [1.0.0] - 2026-08-22

### Added
- Eighteen encrypted DNS configuration profiles covering nine provider variants
  in DoH and DoT: AdGuard (Default, Family), Mullvad Adblock, ControlD Free
  (Ads, Family), Cloudflare (Security, Family) and CleanBrowsing (Family, Security).
- GitHub Pages install site with per-profile QR codes.
- Android Private DNS guide and `scripts/android-private-dns.sh` adb helper.
- Profile generation from `providers.toml` with deterministic UUIDv5 payload IDs.
- CI drift detection, structural validation, and a weekly endpoint liveness check.
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_readme.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 6: Commit**

```bash
git add README.md CHANGELOG.md tests/test_readme.py
git commit -m "Add README and changelog for the first release"
```

---

### Task 13: Publish, verify live behaviour, and repository metadata

The one task that cannot be verified locally: whether GitHub Pages serves `.mobileconfig` as a download. Spec §16.1 records this as an unverified assumption, and this task settles it.

**Files:**
- Modify: `README.md`, `docs/index.html` (only if the fallback proves necessary)

- [ ] **Step 1: Push everything**

```bash
git push -u origin main
```

- [ ] **Step 2: Enable GitHub Pages from Actions**

```bash
gh api -X POST repos/atikansari-ghr/encrypted-dns-profiles/pages -f build_type=workflow || \
gh api -X PUT repos/atikansari-ghr/encrypted-dns-profiles/pages -f build_type=workflow
gh run list --workflow=pages.yml --limit 1
```

Expected: the `pages` workflow completes successfully.

- [ ] **Step 3: Verify the served MIME type — the decisive check**

```bash
curl -sIL "https://atikansari-ghr.github.io/encrypted-dns-profiles/profiles/adguard-default-doh.mobileconfig" | grep -iE "^(HTTP|content-type|content-disposition)"
```

Expected: `HTTP/2 200` with a `Content-Type` that is **not** `text/plain` — `application/octet-stream` or `application/x-apple-aspen-config` both give the correct Safari behaviour.

**If it returns `text/plain`:** the assumption in spec §16.1 has failed. Do not silently ship a broken install flow. Add a prominent note to both `README.md` and `docs/index.html` telling iOS users to tap **Share → Save to Files**, then open the file from the Files app, and record the outcome in `CHANGELOG.md`.

- [ ] **Step 4: Confirm the site renders and profiles download**

```bash
curl -sL -o /dev/null -w '%{http_code} %{size_download}\n' "https://atikansari-ghr.github.io/encrypted-dns-profiles/"
python - <<'PY'
import urllib.request, plistlib
url = "https://atikansari-ghr.github.io/encrypted-dns-profiles/profiles/adguard-family-dot.mobileconfig"
data = urllib.request.urlopen(url, timeout=20).read()
profile = plistlib.loads(data)
settings = profile["PayloadContent"][0]["DNSSettings"]
print(profile["PayloadDisplayName"], "|", settings["DNSProtocol"], "|", settings["ServerName"])
PY
```

Expected: `200` with a non-zero size, then `AdGuard DNS - Family Protection (DoT) | TLS | family.adguard-dns.com`

- [ ] **Step 5: Confirm the liveness workflow passes in CI, including Mullvad**

```bash
gh workflow run endpoints.yml
gh run watch
```

Expected: 18/18 endpoints healthy. Mullvad passes here even though it fails on the development machine (spec §2.3). If Mullvad fails in CI too, the provider genuinely has a problem — treat it the way dns0.eu was treated.

- [ ] **Step 6: Set repository metadata**

```bash
gh repo edit atikansari-ghr/encrypted-dns-profiles \
  --description "Ready-to-install encrypted DNS profiles for iOS, iPadOS and macOS - AdGuard ad blocking and family protection, plus Mullvad, ControlD, Cloudflare and CleanBrowsing - with an Android Private DNS guide" \
  --homepage "https://atikansari-ghr.github.io/encrypted-dns-profiles" \
  --add-topic dns --add-topic doh --add-topic dot --add-topic adguard \
  --add-topic ios --add-topic mobileconfig --add-topic android \
  --add-topic private-dns --add-topic adblock --add-topic privacy
```

The social preview image must be uploaded by hand — GitHub exposes no API for it. Repository → Settings → General → Social preview → upload `docs/social-preview.png`.

- [ ] **Step 7: Tag the release**

```bash
git tag -a v1.0.0 -m "First release: eighteen encrypted DNS profiles"
git push origin v1.0.0
gh release create v1.0.0 --title "v1.0.0" --notes-file - <<'NOTES'
Eighteen encrypted DNS configuration profiles across nine provider variants,
in DoH and DoT, plus an Android Private DNS guide.

Install page: https://atikansari-ghr.github.io/encrypted-dns-profiles
NOTES
```

- [ ] **Step 8: Commit any fallback documentation**

Only if Step 3 required it:

```bash
git add README.md docs/index.html CHANGELOG.md
git commit -m "Document the Files app fallback for profile downloads"
git push
```

---

### Task 14: LinkedIn draft

**Files:**
- Create: `linkedin/2026-08-22-encrypted-dns-profiles.md` — **never committed**

- [ ] **Step 1: Confirm the folder is excluded before writing anything into it**

```bash
mkdir -p linkedin && touch linkedin/.probe
git check-ignore -v linkedin/.probe; rm linkedin/.probe
```

Expected: a line naming `~/.gitignore_global` as the source of the ignore rule. **If it prints nothing, stop** — the folder is not excluded. Report this rather than writing a draft that could be committed, and do not add `linkedin/` to the repository `.gitignore`.

- [ ] **Step 2: Write the draft**

Open on the dns0.eu discovery: while assembling a curated list of public DNS providers, the resolver hostnames for one of them returned NXDOMAIN — the service had quietly stopped existing while its website stayed up. Ordinary users would have had no way to tell; their device would just fail to resolve.

Then the consequence: the repository now probes every provider endpoint on a weekly schedule, so a provider going dark shows up as a failed build rather than a stranger's broken phone.

Close with what shipped — profiles for iOS, iPadOS and macOS covering ad blocking and family protection, an Android Private DNS guide, and a link to the install page.

Constraints: first person, no hashtag pile, no emoji rows, no "excited to announce", concrete numbers over adjectives. Include a suggested image (`docs/social-preview.png` or `provider-comparison.svg`) and an alt-text line for accessibility.

- [ ] **Step 3: Verify the draft is untracked**

```bash
git status --porcelain
```

Expected: no `linkedin/` entry appears in the output.

---

## Self-Review

**Spec coverage:** §1 Tasks 1–13 · §2.1 Task 13 Step 3 · §2.2 Task 2 (dns0.eu absent, ControlD present) · §2.3 Task 6 Step 6 and Task 13 Step 5 · §2.4 Tasks 11–12 · §3 Task 2 · §4 Tasks 1, 4 · §4.1 Task 4 · §5 Tasks 2–4 · §6 Task 3 · §7 Task 10 · §8 Task 11 · §9 Task 12 · §10 Task 12 · §11 Tasks 8–9 · §12 Task 14 · §13 Task 7 · §14 Tasks 1, 13 · §15 Tasks 10, 12 · §16 Task 13 (assumption 1), Task 2 (assumption 2), Task 9 (assumption 3), Task 12 (assumption 4) · §17 verified across Tasks 4, 12, 13.

**Type consistency:** `ProfileSpec` field names are identical in Tasks 2, 3, 6 and 11. `generate_all`, `validate_directory`, `check_all`, `generate_qr_codes` keep one signature throughout. `profile_filename` and `profile_url` are defined once in Task 3 and reused unchanged in Tasks 4, 5, 9 and 10. `PROTOCOLS` is `("doh", "dot")` everywhere, and the `doh`/`dot` filename suffixes match the `HTTPS`/`TLS` `DNSProtocol` values through the single `_EXPECTED_DNS_PROTOCOL` mapping in Task 5.

**Known deviation from spec:** the catalogue is TOML rather than YAML, recorded in Global Constraints with its rationale.

**Deliberate omission:** Task 8 (SVG mockups) and Task 10 (`index.html`) state acceptance criteria and verification commands rather than several hundred lines of literal SVG path data and HTML markup. Both tasks carry automated tests that fail until the required content exists, so the contract is enforced rather than assumed.
