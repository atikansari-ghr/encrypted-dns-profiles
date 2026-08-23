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
