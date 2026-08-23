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
