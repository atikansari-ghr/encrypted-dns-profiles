# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Each install-site card now visually separates its iOS/iPadOS/macOS
  controls from its Android controls, with a divider and platform labels,
  instead of leaving the reader to work out which button does what on
  which platform.
- A second QR code per card, specifically for Android: since Android has
  no file to install, it encodes a link back to this site anchored to
  that exact card (`#<slug>`) rather than a `.mobileconfig` link, so
  scanning it lands on the hostname and Copy button instead of a file
  Android can't open. `dnsprofiles/profile.py` gained `card_url()` for
  this; `scripts/make_qr.py` now generates 24 QR codes (16 install + 8
  Android) instead of 16.

### Removed
- Mullvad Adblock. Several networks reset the connection to Mullvad's
  resolver and to mullvad.net itself outright, so a profile pointing at it
  can leave a device unable to resolve anything at all until the profile is
  removed. The remaining eight profiles (four providers, two variants each)
  were all confirmed reachable. `scripts/make_qr.py` was also fixed to
  delete a provider's QR codes when it is removed from the catalogue,
  matching the behaviour `dnsprofiles/generate.py` already had for
  `.mobileconfig` files — this repository's own removal is what surfaced
  the gap.

## [1.0.0] - 2026-08-22

### Added
- Eighteen encrypted DNS configuration profiles covering nine provider variants
  in DoH and DoT: AdGuard (Default, Family), Mullvad Adblock, ControlD Free
  (Ads, Family), Cloudflare (Security, Family) and CleanBrowsing (Family, Security).
- GitHub Pages install site with per-profile QR codes.
- Android Private DNS guide and `scripts/android-private-dns.sh` adb helper.
- Profile generation from `providers.toml` with deterministic UUIDv5 payload IDs.
- CI drift detection, structural validation, and a weekly endpoint liveness check.

### Known limitations
- Bootstrap addresses are IPv4-only for every provider in this release. IPv6
  addresses were planned (see the design spec) but are not yet confirmed
  per-provider against official documentation, so they are omitted rather than
  guessed. They will be added once confirmed.

[Unreleased]: https://github.com/atikansari-ghr/encrypted-dns-profiles/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/atikansari-ghr/encrypted-dns-profiles/releases/tag/v1.0.0
