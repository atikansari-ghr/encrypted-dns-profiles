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
