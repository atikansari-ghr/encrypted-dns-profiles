# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-08-22

### Added
- Eighteen encrypted DNS configuration profiles covering nine provider variants
  in DoH and DoT: AdGuard (Default, Family), Mullvad Adblock, ControlD Free
  (Ads, Family), Cloudflare (Security, Family) and CleanBrowsing (Family, Security).
- GitHub Pages install site with per-profile QR codes.
- Android Private DNS guide and `scripts/android-private-dns.sh` adb helper.
- Profile generation from `providers.toml` with deterministic UUIDv5 payload IDs.
- CI drift detection, structural validation, and a weekly endpoint liveness check.
