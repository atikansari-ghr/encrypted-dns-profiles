import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "android-private-dns.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="bash is required to run the Android helper script",
)


@pytest.fixture
def fake_adb(tmp_path):
    """Put a stub adb on PATH that logs its arguments.

    The stub is stateful: it remembers what was written by a
    "settings put global <key> <value>" call and echoes that value back
    for the matching "settings get global <key>" call. A real device
    behaves the same way, and the script's --set verification step relies
    on reading back what it just wrote, so a stub that always returned a
    fixed string would make that verification fail for any provider other
    than the one whose hostname happened to match the fixed string.
    """
    log = tmp_path / "adb.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    stub = tmp_path / "adb"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{log}"\n'
        'if [ "$1" = "devices" ]; then echo "List of devices attached"; '
        'echo "emulator-5554\tdevice"; fi\n'
        f'if [ "$1" = "shell" ] && [ "$2" = "settings" ] && [ "$3" = "put" ]; then echo "$6" > "{state_dir}/$5"; fi\n'
        f'if [ "$1" = "shell" ] && [ "$2" = "settings" ] && [ "$3" = "get" ]; then '
        f'if [ -f "{state_dir}/$5" ]; then cat "{state_dir}/$5"; else echo "dns.adguard-dns.com"; fi; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub.parent, log


def run(args, path_dir=None):
    env = dict(os.environ)
    if path_dir:
        env["PATH"] = f"{path_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


def test_help_exits_zero():
    result = run(["--help"])
    assert result.returncode == 0
    assert "--set" in result.stdout


def test_list_shows_every_catalogue_hostname():
    result = run(["--list"])
    assert result.returncode == 0
    assert "dns.adguard-dns.com" in result.stdout
    assert "family.adguard-dns.com" in result.stdout
    assert result.stdout.count("adguard") >= 2


def test_set_writes_both_adb_settings(fake_adb):
    path_dir, log = fake_adb
    result = run(["--set", "adguard-family"], path_dir)
    assert result.returncode == 0
    logged = log.read_text(encoding="utf-8")
    assert "private_dns_mode hostname" in logged
    assert "private_dns_specifier family.adguard-dns.com" in logged


def test_set_rejects_an_unknown_slug(fake_adb):
    path_dir, _ = fake_adb
    result = run(["--set", "not-a-provider"], path_dir)
    assert result.returncode != 0
    assert "not-a-provider" in result.stdout + result.stderr


def test_off_sets_mode_to_off(fake_adb):
    path_dir, log = fake_adb
    assert run(["--off"], path_dir).returncode == 0
    assert "private_dns_mode off" in log.read_text(encoding="utf-8")


def test_fails_cleanly_when_adb_is_absent(tmp_path):
    env = dict(os.environ)
    env["PATH"] = str(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--status"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )
    assert result.returncode != 0
    assert "adb" in (result.stdout + result.stderr).lower()
