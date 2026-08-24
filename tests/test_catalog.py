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


def test_real_catalogue_has_eight_unique_entries():
    specs = load_catalog(DEFAULT_CATALOG_PATH)
    assert len(specs) == 8
    assert len({s.slug for s in specs}) == 8
