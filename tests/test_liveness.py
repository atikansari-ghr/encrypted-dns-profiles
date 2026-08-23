from dnsprofiles.catalog import ProfileSpec
from dnsprofiles.liveness import RFC8484_QUERY, check_all

SPEC = ProfileSpec(
    slug="adguard-default",
    provider="AdGuard",
    variant="Default",
    display_name="AdGuard DNS - Ad Blocking",
    blocks="Ads and trackers",
    description="Blocks ads.",
    homepage="https://adguard-dns.io/",
    doh_url="https://dns.adguard-dns.com/dns-query",
    dot_hostname="dns.adguard-dns.com",
    addresses=("94.140.14.14",),
)


def ok_probe(target, timeout=10.0):
    return True, "200"


def fail_probe(target, timeout=10.0):
    return False, "NXDOMAIN"


def test_query_is_the_rfc8484_test_vector():
    assert RFC8484_QUERY == "AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB"


def test_checks_both_protocols_per_spec():
    results = check_all([SPEC], doh_probe=ok_probe, dot_probe=ok_probe)
    assert len(results) == 2
    assert [label for label, _, _ in results] == [
        "adguard-default (DoH)",
        "adguard-default (DoT)",
    ]
    assert all(ok for _, ok, _ in results)


def test_reports_failures_with_detail():
    results = check_all([SPEC], doh_probe=fail_probe, dot_probe=ok_probe)
    doh, dot = results
    assert doh[1] is False and doh[2] == "NXDOMAIN"
    assert dot[1] is True


def test_probes_receive_the_right_targets():
    seen = {}

    def record_doh(target, timeout=10.0):
        seen["doh"] = target
        return True, "200"

    def record_dot(target, timeout=10.0):
        seen["dot"] = target
        return True, "handshake ok"

    check_all([SPEC], doh_probe=record_doh, dot_probe=record_dot)
    assert seen["doh"] == "https://dns.adguard-dns.com/dns-query"
    assert seen["dot"] == "dns.adguard-dns.com"


# Direct unit tests for probe_doh and probe_dot
from unittest import mock
from dnsprofiles.liveness import probe_doh, probe_dot


def test_probe_doh_accepts_wellformed_dns_response():
    """probe_doh should accept a valid DNS response body."""
    # A minimal valid DNS response: transaction ID 0000, QR bit set (response), 65 bytes total
    valid_dns = b"\x00\x00\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = valid_dns

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is True
        assert "65 bytes" in detail


def test_probe_doh_rejects_html_error_page_with_200():
    """probe_doh should reject an HTML error page even if it has DNS structure."""
    # HTML error page with correct DNS structure but wrong Content-Type (captive portal scenario)
    # This has the DNS packet structure but is served as HTML
    valid_structure = b"\x00\x00\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.read.return_value = valid_structure

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "text/html" in detail


def test_probe_doh_rejects_empty_body():
    """probe_doh should reject an empty response body."""
    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = b""

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "empty body" in detail


def test_probe_doh_rejects_truncated_response():
    """probe_doh should reject a response body shorter than 12 bytes."""
    truncated = b"\x00\x00\x84\x00"  # Only 4 bytes, needs 12+

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = truncated

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "truncated" in detail
        assert "4 bytes" in detail


def test_probe_doh_rejects_wrong_transaction_id():
    """probe_doh should reject a response with wrong transaction ID."""
    # Valid structure but wrong transaction ID (should be 0000)
    wrong_txid = b"\x12\x34\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = wrong_txid

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "transaction ID" in detail


def test_probe_doh_rejects_query_instead_of_response():
    """probe_doh should reject a query packet (QR bit not set)."""
    # Same structure but QR bit not set (0x04 instead of 0x84)
    query_packet = b"\x00\x00\x04\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = query_packet

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "QR bit" in detail


def test_probe_doh_rejects_wrong_content_type():
    """probe_doh should reject a response with wrong Content-Type header."""
    valid_dns = b"\x00\x00\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.read.return_value = valid_dns

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "application/json" in detail


def test_probe_doh_accepts_missing_content_type():
    """probe_doh should accept a response with no Content-Type header."""
    valid_dns = b"\x00\x00\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}  # No Content-Type
    mock_response.read.return_value = valid_dns

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is True


def test_probe_doh_rejects_non_200_status():
    """probe_doh should reject non-200 HTTP status codes."""
    mock_response = mock.Mock()
    mock_response.status = 500
    mock_response.headers = {}
    mock_response.read.return_value = b"Server Error"

    with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=mock.Mock(return_value=mock_response), __exit__=mock.Mock(return_value=None))):
        ok, detail = probe_doh("https://example.com/dns-query")
        assert ok is False
        assert "500" in detail


def test_probe_doh_appends_query_separator_question_mark():
    """probe_doh should use ? when URL has no query string."""
    valid_dns = b"\x00\x00\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = valid_dns

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = mock.Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = mock.Mock(return_value=None)
        probe_doh("https://example.com/dns-query")
        called_url = mock_urlopen.call_args[0][0].full_url
        assert called_url == f"https://example.com/dns-query?dns={RFC8484_QUERY}"


def test_probe_doh_appends_query_separator_ampersand():
    """probe_doh should use & when URL already has query string."""
    valid_dns = b"\x00\x00\x84\x00\x00\x01\x00\x01\x00\x00\x00\x00" + b"X" * 53

    mock_response = mock.Mock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.read.return_value = valid_dns

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = mock.Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = mock.Mock(return_value=None)
        probe_doh("https://example.com/dns-query?foo=bar")
        called_url = mock_urlopen.call_args[0][0].full_url
        assert called_url == f"https://example.com/dns-query?foo=bar&dns={RFC8484_QUERY}"


def test_probe_dot_reports_connection_failure():
    """probe_dot should report failure when socket.create_connection raises."""
    import socket as socket_module

    with mock.patch("socket.create_connection", side_effect=socket_module.gaierror("Name resolution failed")):
        ok, detail = probe_dot("nonexistent.invalid")
        assert ok is False
        assert "gaierror" in detail or "Name resolution" in detail
