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


def card_url(slug: str) -> str:
    """The install site's own page, anchored to one profile's card."""
    return f"{PAGES_BASE}/#{slug}"


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
