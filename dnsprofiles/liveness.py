"""Live checks that provider endpoints still answer."""

from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable

from dnsprofiles.catalog import ProfileSpec

# RFC 8484 test vector: a DNS query for www.example.com A, base64url encoded.
RFC8484_QUERY = "AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB"

DOT_PORT = 853

Probe = Callable[..., tuple[bool, str]]


def probe_doh(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Send an RFC 8484 GET query and report whether the resolver answered."""
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}dns={RFC8484_QUERY}",
        headers={"accept": "application/dns-message"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.status != 200:
                return False, f"HTTP {response.status}"
            if not body:
                return False, "HTTP 200 with empty body"
            if len(body) < 12:
                return False, f"HTTP 200 with truncated DNS response ({len(body)} bytes, need >=12)"
            if body[0:2] != b"\x00\x00":
                return False, f"HTTP 200 but response transaction ID is {body[0:2].hex()}, not 0000"
            if not (body[2] & 0x80):
                return False, "HTTP 200 but response is a query, not a response (QR bit not set)"
            content_type = response.headers.get("Content-Type")
            media_type = content_type.split(";", 1)[0].strip() if content_type else content_type
            if media_type and media_type != "application/dns-message":
                return False, f"HTTP 200 but Content-Type is {content_type}, not application/dns-message"
            return True, f"HTTP 200, {len(body)} bytes"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def probe_dot(hostname: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Complete a TLS handshake on port 853 and verify the certificate."""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, DOT_PORT), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=hostname) as tls:
                return True, f"TLS {tls.version()}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def check_all(
    specs: Iterable[ProfileSpec],
    doh_probe: Probe = probe_doh,
    dot_probe: Probe = probe_dot,
) -> list[tuple[str, bool, str]]:
    """Probe every endpoint, returning (label, ok, detail) in catalogue order."""
    results: list[tuple[str, bool, str]] = []
    for spec in specs:
        ok, detail = doh_probe(spec.doh_url)
        results.append((f"{spec.slug} (DoH)", ok, detail))
        ok, detail = dot_probe(spec.dot_hostname)
        results.append((f"{spec.slug} (DoT)", ok, detail))
    return results
