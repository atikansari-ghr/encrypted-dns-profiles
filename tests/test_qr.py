from pathlib import Path

import pytest

from dnsprofiles.catalog import DEFAULT_CATALOG_PATH

segno = pytest.importorskip("segno")

from scripts.make_qr import generate_qr_codes  # noqa: E402

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "qr"


def test_generates_two_install_qrs_and_one_android_qr_per_profile(tmp_path):
    written = generate_qr_codes(DEFAULT_CATALOG_PATH, tmp_path)
    assert len(written) == 24
    assert (tmp_path / "adguard-default-doh.svg").exists()
    assert (tmp_path / "adguard-default-dot.svg").exists()
    assert (tmp_path / "adguard-default-android.svg").exists()


def test_qr_encodes_the_canonical_pages_url(tmp_path):
    generate_qr_codes(DEFAULT_CATALOG_PATH, tmp_path)
    text = (tmp_path / "adguard-default-doh.svg").read_text(encoding="utf-8")
    assert text.lstrip().startswith("<?xml") or text.lstrip().startswith("<svg")
    assert "<script" not in text


def test_android_qr_differs_from_install_qr(tmp_path):
    """The Android QR encodes a different URL (the card anchor, not the
    profile file), so it must not be byte-identical to either install QR.
    """
    generate_qr_codes(DEFAULT_CATALOG_PATH, tmp_path)
    android = (tmp_path / "adguard-default-android.svg").read_bytes()
    doh = (tmp_path / "adguard-default-doh.svg").read_bytes()
    dot = (tmp_path / "adguard-default-dot.svg").read_bytes()
    assert android != doh
    assert android != dot


def test_committed_qr_codes_match_a_fresh_generation(tmp_path):
    """The repository must never drift from the catalogue."""
    fresh = {p.name: p.read_bytes() for p in generate_qr_codes(DEFAULT_CATALOG_PATH, tmp_path)}
    committed = {p.name: p.read_bytes() for p in OUTPUT.glob("*.svg")}
    assert committed == fresh
