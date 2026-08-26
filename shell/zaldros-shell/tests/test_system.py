"""Tests for the system readouts. The contract under test is the honesty rule: unknown values must
come back as unavailable, never as a plausible-looking number."""
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from zaldros_shell import system


def test_battery_reads_a_real_sysfs_layout(tmp_path: Path):
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "capacity").write_text("87\n")
    (bat / "status").write_text("Discharging\n")
    reading = system.battery(str(tmp_path))
    assert reading.available and reading.value == 87 and reading.detail == "Discharging"


def test_missing_battery_is_reported_as_unavailable(tmp_path: Path):
    reading = system.battery(str(tmp_path))
    assert not reading.available and reading.value is None and reading.detail


def test_absent_sysfs_path_does_not_raise():
    assert system.battery("/no/such/path").available is False


def test_backlight_is_a_percentage_of_the_maximum(tmp_path: Path):
    device = tmp_path / "intel_backlight"
    device.mkdir()
    (device / "brightness").write_text("300")
    (device / "max_brightness").write_text("1200")
    assert system.backlight(str(tmp_path)).value == 25


def test_network_reports_only_interfaces_that_are_up(tmp_path: Path):
    down, up = tmp_path / "eth0", tmp_path / "wlan0"
    down.mkdir(); up.mkdir()
    (down / "operstate").write_text("down")
    (up / "operstate").write_text("up")
    (up / "wireless").mkdir()
    reading = system.network(str(tmp_path))
    assert reading.available and "wlan0" in reading.detail and "Wi-Fi" in reading.detail


def test_no_link_is_reported_honestly(tmp_path: Path):
    (tmp_path / "eth0").mkdir()
    (tmp_path / "eth0" / "operstate").write_text("down")
    assert system.network(str(tmp_path)).available is False


def test_volume_without_an_audio_server_is_unavailable_not_zero():
    reading = system.volume()
    assert reading.available or reading.value is None


def test_snapshot_covers_every_quick_setting():
    snapshot = system.snapshot()
    assert set(snapshot) == {"battery", "brightness", "network", "volume", "bluetooth",
                             "keyboard"}
    for reading in snapshot.values():
        assert reading.available or reading.value is None


def test_unset_keymap_never_reaches_the_tray():
    """Run #29 in the booted ISO showed "(UN" in the tray: localectl had answered "(unset)" and
    the badge was the first three characters of it."""
    def runner(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="   VC Keymap: (unset)\n  X11 Layout: (unset)\n")

    with mock.patch.object(system.shutil, "which", return_value="/usr/bin/localectl"), \
         mock.patch.dict(system.os.environ, {"LANG": "ru_RU.UTF-8"}, clear=False):
        reading = system.keyboard_layout(runner=runner)
    assert reading.available, "LANG still tells us the layout"
    assert reading.detail == "РУС", f"expected the Windows-style badge, got {reading.detail!r}"


def test_layout_badges_follow_windows_and_never_invent_a_name():
    assert system.layout_badge("ru") == "РУС"
    assert system.layout_badge("us") == "ENG"
    assert system.layout_badge("ru,us") == "РУС", "the active layout is the first one"
    assert system.layout_badge("xy") == "XY", "an unknown layout keeps its own code"


LAYOUT_LIST = "([('us', 'English (US)', 'us'), ('ru', 'Russian', 'ru')],)\n"


def _kwin_runner(current="(uint32 1,)", calls=None):
    def runner(args, **_kwargs):
        if calls is not None:
            calls.append(args)
        method = args[args.index("--method") + 1]
        if method.endswith("getLayoutsList"):
            return SimpleNamespace(returncode=0, stdout=LAYOUT_LIST)
        if method.endswith("getLayout"):
            return SimpleNamespace(returncode=0, stdout=current)
        return SimpleNamespace(returncode=0, stdout="()\n")
    return runner


def test_the_badge_follows_kwin_because_kwin_owns_the_keyboard():
    """localectl only knows what the image was configured with; after the user switches layout,
    KWin is the only process that knows which one is active."""
    with mock.patch.object(system.shutil, "which", return_value="/usr/bin/gdbus"):
        reading = system.keyboard_layout(runner=_kwin_runner())
    assert reading.available and reading.source == "kwin"
    assert reading.detail == "РУС", "index 1 of us,ru is Russian"


def test_switching_asks_kwin_for_the_next_layout_and_wraps_around():
    calls = []
    with mock.patch.object(system.shutil, "which", return_value="/usr/bin/gdbus"):
        assert system.switch_layout(runner=_kwin_runner(current="(uint32 1,)", calls=calls))
    setters = [c for c in calls if c[c.index("--method") + 1].endswith("setLayout")]
    assert setters, "the switch must go through KWin"
    assert setters[0][-1] == "uint32 0", "after the last layout it wraps to the first"


def test_without_kwin_the_badge_falls_back_instead_of_disappearing():
    def dead(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="")

    with mock.patch.object(system.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
         mock.patch.dict(system.os.environ, {"LANG": "ru_RU.UTF-8"}, clear=False):
        reading = system.keyboard_layout(runner=dead)
    assert reading.available and reading.detail == "РУС" and reading.source != "kwin"
