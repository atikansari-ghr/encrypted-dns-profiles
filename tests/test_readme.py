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
