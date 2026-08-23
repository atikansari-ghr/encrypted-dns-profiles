#!/usr/bin/env bash
#
# Set Android Private DNS (DNS-over-TLS) over adb.
#
# Android has no equivalent of an Apple .mobileconfig. Private DNS is the only
# no-root, no-app path, it is DNS-over-TLS only, and it needs Android 9 or later.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CATALOG="${SCRIPT_DIR}/../providers.toml"

usage() {
  cat <<'USAGE'
Usage: android-private-dns.sh [option]

  --list            List available providers and their DoT hostnames
  --set <slug>      Enable Private DNS with that provider
  --status          Show the current Private DNS setting on the device
  --off             Disable Private DNS
  --help            Show this message

Requires adb on PATH, USB debugging enabled, and Android 9 or later.
Example:
  ./scripts/android-private-dns.sh --set adguard-family
USAGE
}

# Emit "slug<TAB>hostname" for every catalogue entry.
catalogue() {
  awk '
    /^slug *=/        { gsub(/.*= *"|"/, ""); slug = $0 }
    /^dot_hostname *=/ { gsub(/.*= *"|"/, ""); if (slug != "") { print slug "\t" $0; slug = "" } }
  ' "$CATALOG"
}

hostname_for() {
  catalogue | awk -F'\t' -v want="$1" '$1 == want { print $2; found = 1 } END { exit !found }'
}

require_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "Error: adb not found on PATH." >&2
    echo "Install Android platform-tools: https://developer.android.com/tools/releases/platform-tools" >&2
    exit 1
  fi
}

cmd_list() {
  printf '%-26s %s\n' "PROVIDER" "DoT HOSTNAME"
  catalogue | while IFS=$'\t' read -r slug host; do
    printf '%-26s %s\n' "$slug" "$host"
  done
}

cmd_set() {
  local slug="${1:-}"
  if [ -z "$slug" ]; then
    echo "Error: --set requires a provider slug. Run --list to see them." >&2
    exit 2
  fi

  local host
  if ! host="$(hostname_for "$slug")"; then
    echo "Error: unknown provider '$slug'. Run --list to see available providers." >&2
    exit 2
  fi

  require_adb
  adb shell settings put global private_dns_mode hostname
  adb shell settings put global private_dns_specifier "$host"

  local applied
  applied="$(adb shell settings get global private_dns_specifier | tr -d '\r')"
  if [ "$applied" != "$host" ]; then
    echo "Error: device reports '$applied' but expected '$host'." >&2
    exit 1
  fi
  echo "Private DNS set to $host ($slug)."
}

cmd_status() {
  require_adb
  local mode specifier
  mode="$(adb shell settings get global private_dns_mode | tr -d '\r')"
  specifier="$(adb shell settings get global private_dns_specifier | tr -d '\r')"
  echo "mode:      ${mode}"
  echo "hostname:  ${specifier}"
}

cmd_off() {
  require_adb
  adb shell settings put global private_dns_mode off
  echo "Private DNS disabled."
}

case "${1:---help}" in
  --list)   cmd_list ;;
  --set)    cmd_set "${2:-}" ;;
  --status) cmd_status ;;
  --off)    cmd_off ;;
  --help|-h) usage ;;
  *)
    echo "Error: unknown option '$1'" >&2
    usage >&2
    exit 2
    ;;
esac
