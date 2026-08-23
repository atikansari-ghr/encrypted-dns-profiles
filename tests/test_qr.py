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
