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
