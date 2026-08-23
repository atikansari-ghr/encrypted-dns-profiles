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
