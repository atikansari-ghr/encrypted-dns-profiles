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
