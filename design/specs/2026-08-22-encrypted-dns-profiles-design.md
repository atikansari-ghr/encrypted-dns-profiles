# Encrypted DNS Profiles — Design

**Date:** 2026-08-22
**Status:** Approved for implementation planning
**Repository:** `atikansari-ghr/encrypted-dns-profiles` (renamed from `md-toolbox`)

## 1. Overview

A repository of ready-to-install encrypted DNS configuration profiles for Apple
devices, plus an equivalent setup guide for Android. The headline use case is
AdGuard Public DNS in two flavours — ad blocking and family protection — with a
curated set of alternative providers alongside it.

Users download a `.mobileconfig` file from a GitHub Pages site and install it on
iOS, iPadOS or macOS. Android users follow a Private DNS guide, optionally
driven by an `adb` helper script.

### Goals

- Two AdGuard profiles (ad blocking, family protection) installable in under a minute.
- Encrypted transport by default — DNS-over-HTTPS and DNS-over-TLS, never plaintext.
- A curated alternative-provider catalogue with honest documentation of what each one blocks.
- An Android path that works without root, without an app, on Android 9+.
- Adding a new provider is a small, documented change to one file.
- Dead or changed provider endpoints are detected automatically, not by user reports.

### Non-goals

- Competing on catalogue size with `paulmillr/encrypted-dns` (~100 profiles). This
  project competes on curation, documentation honesty and install experience.
- Providers requiring an account or a per-user endpoint (NextDNS, paid ControlD tiers).
- A companion Android application.
- Code-signed profiles (see §15).

## 2. Background and verified constraints

The following were established empirically during design, not assumed.

### 2.1 raw.githubusercontent.com cannot serve installable profiles

```
$ curl -sIL .../adguard-default-https.mobileconfig
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
```

Safari renders `text/plain` inline, so a raw link shows the user XML rather than
offering to install it. This is the reason for the GitHub Pages site (§7) — Pages
serves unknown extensions as a download, producing the correct
Safari → "Profile Downloaded" → Settings flow.

**Implementation must verify** the real `Content-Type` returned by Pages for
`.mobileconfig` once the site is live, and add a documented fallback
("Share → Save to Files → open from Files") if it serves inline.

### 2.2 dns0.eu is defunct

`zero.dns0.eu` and `kids.dns0.eu` both return **NXDOMAIN** (Status=3) from a
public resolver, while the marketing apex `dns0.eu` still resolves. A DoH service
whose documented endpoints do not exist in DNS is not running. dns0.eu was
dropped from the catalogue and replaced with ControlD Free, which supplies both
an ad-blocking and a family endpoint from one operator.

This finding is the direct motivation for the scheduled liveness check in §13.

### 2.3 The development network filters some providers

`mullvad.net` and `adblock.dns.mullvad.net` fail locally (connection reset /
no-resolve) but resolve correctly through a public resolver to `194.242.2.3`.
Mullvad is alive and ships; it simply cannot be tested from the development
machine. GitHub Actions runners are not subject to this filtering and will
validate all nine variants.

### 2.4 Platform capabilities

- iOS/iPadOS 14+ and macOS 11+ support the `com.apple.dnsSettings.managed`
  payload with a `DNSProtocol` of `HTTPS` or `TLS`. Below these versions, no profile.
- Since iOS 12.2 Safari never auto-installs a profile. Download then manual
  install from Settings is the only flow; documentation must reflect this.
- Multiple DNS profiles may be installed simultaneously; the user selects the
  active one. This is a feature to document, not a conflict to avoid.
- Android has **no** installable profile format. Android 9+ Private DNS accepts a
  DoT hostname only — no DoH, no per-network rules, system-wide including cellular.

## 3. Provider catalogue

Nine variants. Every DoH endpoint returned HTTP 200 to an RFC 8484 query during
design, except Mullvad which was confirmed by public resolution (§2.3).

| Provider | Variant | Blocks | DoH endpoint | DoT hostname | Bootstrap IPs |
|---|---|---|---|---|---|
| AdGuard | Default | Ads + trackers | `https://dns.adguard-dns.com/dns-query` | `dns.adguard-dns.com` | 94.140.14.14, 94.140.15.15 |
| AdGuard | Family | Ads + trackers + adult + safe search | `https://family.adguard-dns.com/dns-query` | `family.adguard-dns.com` | 94.140.14.15, 94.140.15.16 |
| Mullvad | Adblock | Ads + trackers, no logging | `https://adblock.dns.mullvad.net/dns-query` | `adblock.dns.mullvad.net` | 194.242.2.3 |
| ControlD | Free ads | Ads + trackers + malware | `https://freedns.controld.com/p2` | `p2.freedns.controld.com` | 76.76.2.11 |
| ControlD | Family | Ads + trackers + malware + adult | `https://freedns.controld.com/family` | `family.freedns.controld.com` | 76.76.2.11 |
| Cloudflare | Security | Malware only — **not ads** | `https://security.cloudflare-dns.com/dns-query` | `security.cloudflare-dns.com` | 1.1.1.2, 1.0.0.2 |
| Cloudflare | Family | Malware + adult — **not ads** | `https://family.cloudflare-dns.com/dns-query` | `family.cloudflare-dns.com` | 1.1.1.3, 1.0.0.3 |
| CleanBrowsing | Family | Adult + safe search | `https://doh.cleanbrowsing.org/doh/family-filter/` | `family-filter-dns.cleanbrowsing.org` | 185.228.168.168, 185.228.169.168 |
| CleanBrowsing | Security | Malware + phishing | `https://doh.cleanbrowsing.org/doh/security-filter/` | `security-filter-dns.cleanbrowsing.org` | 185.228.168.9, 185.228.169.9 |

IPv6 bootstrap addresses are to be added per provider where published;
implementation must confirm each against provider documentation before shipping.

The "Blocks" column is a documentation feature. Stating that Cloudflare for
Families does not block ads corrects the most common misconception in this space.

**9 variants × 2 protocols = 18 profiles.**

## 4. Repository structure

```
encrypted-dns-profiles/
├── providers.yaml                   # single source of truth
├── scripts/
│   ├── generate_profiles.py         # providers.yaml -> .mobileconfig
│   ├── validate_profiles.py         # schema + liveness checks
│   ├── make_qr.py                   # QR codes as SVG
│   └── android-private-dns.sh       # adb helper
├── docs/                            # GitHub Pages root
│   ├── index.html
│   ├── profiles/*.mobileconfig      # 18 generated, committed
│   ├── qr/*.svg
│   ├── screenshots/*.svg
│   └── social-preview.png
├── design/
│   ├── plans/                       # implementation plans
│   └── specs/                       # design docs
├── .github/workflows/validate.yml
├── .github/workflows/pages.yml
├── .github/FUNDING.yml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

Profiles live under `docs/profiles/` rather than a root `profiles/` directory.
Pages serves from `docs/`, so this yields one canonical path that is
simultaneously the install URL and the GitHub-browsable source. There is no copy
step and therefore no opportunity for the served file to drift from the reviewed file.

Planning documents — this spec and the implementation plan — live under
`design/` at the repository root, outside `docs/`, so Pages never publishes
them. That is a deliberate separation between the published install site and
internal project history, not an attempt at secrecy: the repository is public
either way, and nothing about `design/` needs hiding — it simply has no reason
to be served as part of the site.

### 4.1 Generated filenames

The eighteen generated profiles, named `<slug>-<doh|dot>.mobileconfig`:

| Slug | DoH file | DoT file |
|---|---|---|
| `adguard-default` | `adguard-default-doh.mobileconfig` | `adguard-default-dot.mobileconfig` |
| `adguard-family` | `adguard-family-doh.mobileconfig` | `adguard-family-dot.mobileconfig` |
| `mullvad-adblock` | `mullvad-adblock-doh.mobileconfig` | `mullvad-adblock-dot.mobileconfig` |
| `controld-ads` | `controld-ads-doh.mobileconfig` | `controld-ads-dot.mobileconfig` |
| `controld-family` | `controld-family-doh.mobileconfig` | `controld-family-dot.mobileconfig` |
| `cloudflare-security` | `cloudflare-security-doh.mobileconfig` | `cloudflare-security-dot.mobileconfig` |
| `cloudflare-family` | `cloudflare-family-doh.mobileconfig` | `cloudflare-family-dot.mobileconfig` |
| `cleanbrowsing-family` | `cleanbrowsing-family-doh.mobileconfig` | `cleanbrowsing-family-dot.mobileconfig` |
| `cleanbrowsing-security` | `cleanbrowsing-security-doh.mobileconfig` | `cleanbrowsing-security-dot.mobileconfig` |

These filenames are the public install URLs and are load-bearing: per §5.3 a slug
change alters the derived UUID and breaks the replace-on-reinstall behaviour, so
the table above is frozen once released.

## 5. Generation

### 5.1 providers.yaml

One entry per variant. Illustrative shape:

```yaml
profiles:
  - slug: adguard-default
    provider: AdGuard
    variant: Default
    display_name: AdGuard DNS — Ad Blocking
    blocks: Ads and trackers
    description: >
      Blocks ads and tracking domains network-wide. Operated by AdGuard
      Software Limited (Cyprus). No query logging on the public resolver.
    homepage: https://adguard-dns.io/
    doh_url: https://dns.adguard-dns.com/dns-query
    dot_hostname: dns.adguard-dns.com
    addresses: [94.140.14.14, 94.140.15.15]
```

### 5.2 generate_profiles.py

Reads `providers.yaml` and emits two files per entry
(`<slug>-doh.mobileconfig`, `<slug>-dot.mobileconfig`) into `docs/profiles/`
using the standard library `plistlib`. No template engine, no XML string building.

**Determinism is a hard requirement.** Regenerating without a YAML change must
produce byte-identical output, otherwise the CI drift check (§13) is meaningless.
This requires:

- `PayloadUUID` derived as UUIDv5 over a fixed namespace and the profile's
  canonical Pages URL — never `uuid4()`.
- No timestamps, no environment-dependent values, and no output that depends on
  dictionary iteration order.

### 5.3 Identity and upgrade behaviour

- `PayloadIdentifier`: `com.atikansari.dns.<slug>-<doh|dot>`
- `PayloadUUID`: `uuid5(NAMESPACE_URL, "https://atikansari-ghr.github.io/encrypted-dns-profiles/profiles/<slug>-<proto>.mobileconfig")`
- The inner DNS payload takes its own stable identifier and UUID, suffixed `.settings`.

Because identifier and UUID are stable across regenerations, a user installing an
updated profile **replaces** their existing installation rather than accumulating
duplicates. Changing a slug is therefore a breaking change and must be treated as
one in `CHANGELOG.md`.

## 6. Profile anatomy

A Configuration payload wrapping a single `com.apple.dnsSettings.managed` payload.
The DoH and DoT variants differ in exactly three keys:

| Key | DoH | DoT |
|---|---|---|
| `DNSSettings.DNSProtocol` | `HTTPS` | `TLS` |
| endpoint key | `ServerURL` | `ServerName` |
| `DNSSettings.ServerAddresses` | bootstrap IPs | bootstrap IPs |

`ServerAddresses` is optional in Apple's schema but is included deliberately.
Without bootstrap addresses the device must resolve the DoH/DoT hostname using
whatever resolver it currently has, so a hostile or broken network can prevent the
profile from ever engaging.

Fixed top-level keys:

| Key | Value |
|---|---|
| `PayloadType` | `Configuration` |
| `PayloadVersion` | `1` |
| `PayloadOrganization` | `Atik Ansari` |
| `PayloadDisplayName` | e.g. `AdGuard DNS — Family Protection (DoH)` |
| `PayloadDescription` | What it blocks, who operates it, logging policy |
| `PayloadRemovalDisallowed` | `false` |

`PayloadRemovalDisallowed` is false by deliberate choice: a profile downloaded
from the internet must always be removable by the person who installed it.
No `OnDemandRules` — the setting applies on Wi-Fi and cellular alike, which is
what "block ads on my phone" means to a user. No `ProhibitDisablement`, which
requires supervision and is inapplicable to unmanaged personal devices.

## 7. GitHub Pages install site

A single hand-written `index.html` published from `docs/`.

**Hard constraint: zero external requests.** No CDN, no web fonts, no analytics,
no third-party anything. All CSS and JS inline, all images local SVG. A project
whose subject is DNS privacy cannot credibly load third-party assets, and a
technical audience will check.

Page structure:

1. What this is and what it does to your device
2. Provider cards — plain-language "blocks" line, DoH and DoT install buttons, QR code
3. iOS / iPadOS install steps, including the "Not Signed" warning explained
4. Android Private DNS steps with tap-to-copy hostnames
5. macOS install steps
6. How to verify it is working
7. FAQ and troubleshooting

Light and dark themes, mobile-first layout — most visitors arrive on the phone
they are about to configure.

QR codes are generated as SVG at build time and encode each profile's canonical
Pages URL, so a reader on a laptop can point their phone at the screen and land
directly on the download.

## 8. Android

Private DNS (Android 9+) accepts a DoT hostname and is the only no-app, no-root path.

Documentation covers stock Android (**Network & internet → Private DNS**) and
Samsung One UI (**Connections → More connection settings → Private DNS**)
separately; that divergence causes most user confusion.

`scripts/android-private-dns.sh` wraps the non-interactive equivalent:

```bash
adb shell settings put global private_dns_mode hostname
adb shell settings put global private_dns_specifier dns.adguard-dns.com
```

with provider selection by name, a `--list` flag, and read-back verification.
Intended for configuring several devices at once.

Limits stated explicitly in the documentation rather than glossed over:

- DoT only — the DoH profiles have no Android equivalent.
- Android 9+ only; older versions are pointed at a third-party app.
- System-wide and all-or-nothing; no per-network exceptions.

## 9. macOS

The same `.mobileconfig` files install on macOS 11+ via
System Settings → General → Device Management. Documented as a README section
and a Pages section. No additional files.

## 10. README

Follows the established house structure from `Cloudflare-DDNS-Telegram`:

1. Title, badge row (CI · MIT · Pages)
2. Pitch paragraph
3. Screenshots (SVG)
4. What each provider blocks — the comparison table from §3
5. iOS quick start
6. Android quick start
7. macOS
8. Full profile index with install links
9. How to verify it is working
10. **How to add a provider** — a `providers.yaml` edit plus one command
11. Troubleshooting
12. Security notes
13. Support (Ko-fi)
14. Author — Atik Ansari
15. License — MIT

Section 10 is the deliverable form of the "how do we add other ad-block servers"
requirement: a working contribution path rather than prose advice.

## 11. Images

Five assets, hand-drawn in the flat illustrative style of the existing
`terminal.svg` / `telegram.svg`:

| File | Content |
|---|---|
| `ios-install.svg` | Three panels: Safari download → Settings "Profile Downloaded" → install screen showing the red "Not Signed" label |
| `ios-dns-selector.svg` | Settings → General → VPN & DNS with several profiles installed, one active |
| `android-private-dns.svg` | The Private DNS dialog with a hostname entered |
| `provider-comparison.svg` | The blocks-what matrix as a graphic |
| `social-preview.png` | 1280×640 for the GitHub social preview and the LinkedIn card |

All illustrative, using documentation values — consistent with the existing
projects' "illustrative output using demo values" convention.

The PNG is composed as HTML and captured at exactly 1280×640 in a headless
browser, avoiding an ImageMagick or Cairo dependency on Windows.

## 12. LinkedIn

Draft in `linkedin/`, which is **never committed** per standing instruction.
Implementation must confirm `~/.gitignore_global` covers the folder before writing
into it, and must not add a `linkedin/` entry to the repository `.gitignore`.

Angle: the dns0.eu discovery (§2.2) as the hook — nearly shipping profiles
pointing at a service that had quietly died — leading into why the repository
validates provider endpoints on a schedule. A real engineering story rather than
a launch announcement, and it motivates the project's main technical decision.

## 13. CI and validation

`.github/workflows/validate.yml`, on push, pull request, and a weekly schedule:

1. **Drift check** — regenerate from `providers.yaml`, then `git diff --exit-code`.
   Guarantees the YAML and the shipped profiles cannot silently disagree.
2. **Schema check** — parse each profile with `plistlib`; assert required keys are
   present, `DNSProtocol` is `HTTPS` or `TLS`, the endpoint key matches the
   protocol, UUIDs are well formed, and identifiers are unique.
3. **Liveness check** — an RFC 8484 query against every DoH endpoint and a TLS
   handshake on port 853 against every DoT hostname.

Step 3 is the check that would have caught dns0.eu before a user did. Running it
weekly converts a provider going dark from a bug report into a failed build.
GitHub runners are unaffected by the development network's filtering (§2.3) and
will genuinely exercise all nine variants.

`.github/workflows/pages.yml` deploys `docs/`.

## 14. Release and repository metadata

- Rename `md-toolbox` → `encrypted-dns-profiles`; update the local git remote afterwards.
- Repository description naming AdGuard explicitly for search.
- Topics: `dns`, `doh`, `dot`, `adguard`, `ios`, `mobileconfig`, `android`,
  `private-dns`, `adblock`, `privacy`.
- Social preview image uploaded.
- `CHANGELOG.md` with semantic version tags; slug changes flagged as breaking.
- `LICENSE`: MIT, `Copyright (c) 2026 Atik Ansari`.
- Commits credit Atik Ansari alone; no co-author trailers, no generated-with notices.

## 15. Security and trust

**Profiles ship unsigned.** iOS displays "Not Signed" in red on the install screen.
Proper signing requires a paid Apple Developer certificate; a self-signed
certificate produces the same warning and buys nothing. Rather than hide this, the
README and install page explain what the warning means and encourage users to read
the profile's XML — which is plain text, short, and browsable on GitHub at the same
path it is served from (§4).

Further trust measures:

- A DNS profile can see every domain the device resolves. Documentation states
  each provider's operator, jurisdiction and logging policy.
- Bootstrap IP addresses are included so the profile does not depend on the
  network's existing resolver to start working.
- No external requests from the Pages site (§7).
- No telemetry of any kind in the repository or the site.

## 16. Assumptions

Recorded so they can be challenged during implementation:

1. GitHub Pages serves `.mobileconfig` as a download rather than inline. **To be
   verified once live**; a documented fallback ships if it does not.
2. IPv6 bootstrap addresses will be confirmed per provider against official
   documentation before shipping.
3. `segno` (pure Python) is acceptable as the QR generation dependency; it runs in
   CI and locally at build time, never for end users.
4. Verification links referenced in the README (for example a DNS filter test page)
   will be checked live before being published.

## 17. Success criteria

- A user with an iPhone can go from the README to a working AdGuard ad-blocking
  profile in under a minute, without needing to understand DoH.
- An Android 9+ user can reach the same outcome via Private DNS without an app.
- Adding a tenth provider variant requires editing one file and running one command.
- A provider endpoint going dark produces a failed weekly build within seven days.
- `git status` is clean immediately after regenerating every profile.
