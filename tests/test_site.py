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


ALLOWED_EXTERNAL_PREFIXES = (
    "https://github.com/atikansari-ghr/",
    "https://dnsleaktest.com/",
    "https://adblock-tester.com/",
    "https://ko-fi.com/atikansari",
)


def test_external_links_are_a_closed_allowlist():
    """No external href/src beyond the project repo, the two verification
    tools, and the author's own Ko-fi link, all deliberately reviewed. The
    speed-test provider URLs live inside the inline script as JS string
    literals, not HTML attributes, so this regex does not and should not see
    them; test_speed_test_matches_the_catalogue below covers those instead.
    """
    html = INDEX.read_text(encoding="utf-8")
    external = re.findall(r'(?:href|src)\s*=\s*["\'](https?://[^"\']+)', html)
    offsite = [url for url in external if not url.startswith(ALLOWED_EXTERNAL_PREFIXES)]
    assert offsite == [], f"unapproved external assets or links found: {offsite}"


def test_third_party_verification_links_are_disclosed():
    html = INDEX.read_text(encoding="utf-8")
    assert 'href="https://dnsleaktest.com/"' in html
    assert 'href="https://adblock-tester.com/"' in html
    assert "third-party" in html.lower()


def test_names_every_android_dot_hostname():
    html = INDEX.read_text(encoding="utf-8")
    for spec in load_catalog(DEFAULT_CATALOG_PATH):
        assert spec.dot_hostname in html


def test_explains_the_unsigned_warning():
    html = INDEX.read_text(encoding="utf-8").lower()
    assert "not signed" in html


def test_every_qr_card_can_toggle_between_doh_and_dot():
    html = INDEX.read_text(encoding="utf-8")
    for spec in load_catalog(DEFAULT_CATALOG_PATH):
        assert f'data-slug="{spec.slug}"' in html
        assert f'src="qr/{spec.slug}-doh.svg"' in html
    assert 'data-protocol="doh"' in html
    assert 'data-protocol="dot"' in html
    assert html.count('data-protocol="doh"') == html.count('data-protocol="dot"')


def test_speed_test_matches_the_catalogue():
    html = INDEX.read_text(encoding="utf-8")
    pairs = re.findall(r"slug: '([a-z-]+)'.*?dohUrl: '([^']+)'", html)
    assert len(pairs) == 9
    by_slug = {spec.slug: spec.doh_url for spec in load_catalog(DEFAULT_CATALOG_PATH)}
    for slug, doh_url in pairs:
        assert by_slug[slug] == doh_url, f"{slug}: page has {doh_url!r}, catalogue has {by_slug[slug]!r}"
    assert {slug for slug, _ in pairs} == set(by_slug)


def test_same_provider_variants_sit_side_by_side():
    """The 2-column card grid must not split a provider's own pair across
    rows. Mullvad is the only single-variant provider, so it must trail
    every paired provider rather than sit between two of them.
    """
    html = INDEX.read_text(encoding="utf-8")
    mullvad_index = html.index('data-slug="mullvad-adblock"')
    for spec in load_catalog(DEFAULT_CATALOG_PATH):
        if spec.slug == "mullvad-adblock":
            continue
        other_index = html.index(f'data-slug="{spec.slug}"')
        assert other_index < mullvad_index, f"{spec.slug} card appears after Mullvad's"
