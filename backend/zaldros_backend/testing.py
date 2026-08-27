"""Mock UPower, NetworkManager, BlueZ, udisks2, logind and systemd, on a real bus.

These are not stubs of our own code: they are D-Bus services with the real names, the real object
paths and the real property names, standing on a real `dbus-daemon`. A facet test therefore
exercises the whole path — marshalling, the socket, the daemon's routing, unmarshalling — and a
mistake in any of it fails the test instead of hiding behind a fake.

Every property value below is shaped like the real thing: UPower's percentage is a double,
NetworkManager's SSID is a byte array, udisks2's device name is a NUL-terminated byte string,
BlueZ's battery is a byte. Those are exactly the details a hand-written fake gets wrong.

Not shipped to a user's machine by accident — it is only imported by tests and by
`tools/zaldros-sysprobe`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from typing import Any

from .bus import Bus
from .connection import Connection
from .service import Interface, ObjectServer
from .wire import Variant


class SessionDaemon:
    """A private `dbus-daemon`, started and stopped by us.

    Used instead of `dbus-run-session` so a test can hold the address and open several
    connections to it — the mock services on one, the backend under test on another, which is how
    the real system is arranged.
    """

    def __init__(self) -> None:
        self.address = ""
        self._process: subprocess.Popen | None = None
        self._directory = ""

    @staticmethod
    def available() -> bool:
        return shutil.which("dbus-daemon") is not None

    def start(self) -> str:
        if not self.available():
            raise RuntimeError("dbus-daemon is not installed")
        self._directory = tempfile.mkdtemp(prefix="zaldros-bus-")
        config = os.path.join(self._directory, "bus.conf")
        socket_path = os.path.join(self._directory, "socket")
        with open(config, "w", encoding="utf-8") as handle:
            handle.write(f"""<!DOCTYPE busconfig PUBLIC
 "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:path={socket_path}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
""")
        self._process = subprocess.Popen(
            ["dbus-daemon", f"--config-file={config}", "--nofork", "--print-address"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = self._process.stdout.readline().strip() if self._process.stdout else ""
        if not line:
            self.stop()
            raise RuntimeError("dbus-daemon did not print an address")
        self.address = line
        return self.address

    def stop(self) -> None:
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:      # pragma: no cover - a wedged daemon
                self._process.kill()
            self._process = None
        if self._directory:
            shutil.rmtree(self._directory, ignore_errors=True)
            self._directory = ""

    def __enter__(self) -> "SessionDaemon":
        self.start()
        return self

    def __exit__(self, *_exception: Any) -> None:
        self.stop()


class MockSystem:
    """Every mock service on `address` — each on its own connection, as on a real machine.

    One connection per service is not decoration. Signal match rules are filtered by sender, and a
    signal carries the *unique* name of the connection that sent it; if every mock shared one
    connection, every rule would appear to match every mock and a routing bug would be invisible.
    That is exactly the bug this harness caught.
    """

    def __init__(self, address: str) -> None:
        self.address = address
        self.servers: dict[str, ObjectServer] = {}
        self._connections: list[Connection] = []

    def service(self, name: str) -> ObjectServer:
        """The server that owns `name`, created on its own connection the first time."""
        if name not in self.servers:
            connection = Connection.connect(self.address)
            self._connections.append(connection)
            server = ObjectServer(connection)
            server.request_name(name)
            self.servers[name] = server
        return self.servers[name]

    @property
    def server(self) -> ObjectServer:
        """The first service registered. Convenience for a test that only stood up one."""
        return next(iter(self.servers.values()))

    def close(self) -> None:
        for connection in self._connections:
            connection.close()

    def process(self, timeout: float = 0.0) -> int:
        return sum(server.process(timeout) for server in list(self.servers.values()))

    def pump(self, seconds: float = 0.2) -> int:
        """Answer calls for a while. Tests run this in a thread while the client asks."""
        deadline = time.monotonic() + seconds
        handled = 0
        while time.monotonic() < deadline:
            handled += self.process(0.01)
        return handled

    # -- UPower ------------------------------------------------------------------------------
    def add_upower(self, percentage: float = 87.0, state: int = 2, on_battery: bool = True,
                   time_to_empty: int = 8100) -> None:
        server = self.service("org.freedesktop.UPower")
        manager = Interface("org.freedesktop.UPower", {
            "DaemonVersion": Variant("s", "1.91.1"),
            "OnBattery": Variant("b", on_battery),
            "LidIsClosed": Variant("b", False),
            "LidIsPresent": Variant("b", True)})
        manager.add_method(
            "EnumerateDevices", "", "ao",
            lambda: ["/org/freedesktop/UPower/devices/battery_BAT0",
                     "/org/freedesktop/UPower/devices/mouse_dev_00"])
        manager.add_method("GetDisplayDevice", "", "o",
                           lambda: "/org/freedesktop/UPower/devices/DisplayDevice")
        server.add("/org/freedesktop/UPower", manager)

        for path, kind, model in (("DisplayDevice", 2, ""), ("battery_BAT0", 2, "DELL X7YR1"),
                                  ("mouse_dev_00", 5, "MX Master 3")):
            server.add(f"/org/freedesktop/UPower/devices/{path}", Interface(
                "org.freedesktop.UPower.Device", {
                    "Type": Variant("u", kind),
                    "IsPresent": Variant("b", True),
                    "Percentage": Variant("d", percentage if kind == 2 else 55.0),
                    "State": Variant("u", state),
                    "TimeToEmpty": Variant("x", time_to_empty),
                    "TimeToFull": Variant("x", 0),
                    "EnergyRate": Variant("d", 9.4),
                    "WarningLevel": Variant("u", 1),
                    "IconName": Variant("s", "battery-good-symbolic"),
                    "Model": Variant("s", model),
                    "Vendor": Variant("s", "Zaldros Test"),
                    "NativePath": Variant("s", path)}))

    # -- logind ------------------------------------------------------------------------------
    def add_logind(self, can_suspend: str = "yes", can_hibernate: str = "no") -> None:
        server = self.service("org.freedesktop.login1")
        manager = Interface("org.freedesktop.login1.Manager")
        for method, answer in (("CanPowerOff", "yes"), ("CanReboot", "yes"),
                               ("CanSuspend", can_suspend), ("CanHibernate", can_hibernate),
                               ("CanHybridSleep", "challenge")):
            manager.add_method(method, "", "s", lambda answer=answer: answer)
        self.actions: list[str] = []
        for method in ("PowerOff", "Reboot", "Suspend", "Hibernate"):
            manager.add_method(method, "b", "",
                               lambda _interactive, method=method: self.actions.append(method))
        manager.add_method("LockSessions", "", "",
                           lambda: self.actions.append("LockSessions"))
        server.add("/org/freedesktop/login1", manager)
        server.add("/org/freedesktop/login1/session/self", Interface(
            "org.freedesktop.login1.Session", {
                "Id": Variant("s", "2"), "Type": Variant("s", "wayland"),
                "Active": Variant("b", True), "LockedHint": Variant("b", False),
                "Remote": Variant("b", False), "Desktop": Variant("s", "Zaldros"),
                "Seat": Variant("(so)", ("seat0", "/org/freedesktop/login1/seat/seat0"))}))

    # -- NetworkManager ----------------------------------------------------------------------
    def add_network_manager(self, connected: bool = True, strength: int = 74,
                            wifi_enabled: bool = True) -> None:
        server = self.service("org.freedesktop.NetworkManager")
        device = "/org/freedesktop/NetworkManager/Devices/2"
        active = "/org/freedesktop/NetworkManager/ActiveConnection/1"
        manager = Interface("org.freedesktop.NetworkManager", {
            "State": Variant("u", 70 if connected else 20),
            "Connectivity": Variant("u", 4 if connected else 1),
            "PrimaryConnection": Variant("o", active if connected else "/"),
            "PrimaryConnectionType": Variant("s", "802-11-wireless" if connected else ""),
            "WirelessEnabled": Variant("b", wifi_enabled),
            "WirelessHardwareEnabled": Variant("b", True),
            "NetworkingEnabled": Variant("b", True),
            "Metered": Variant("u", 4),
            "Version": Variant("s", "1.54.0")})
        manager.add_method("GetDevices", "", "ao",
                           lambda: [device, "/org/freedesktop/NetworkManager/Devices/1"])
        manager.add_method("Enable", "b", "", lambda _enable: None)
        server.add("/org/freedesktop/NetworkManager", manager)

        server.add(active, Interface(
            "org.freedesktop.NetworkManager.Connection.Active", {
                "Id": Variant("s", "Zaldros-Guest"), "Type": Variant("s", "802-11-wireless"),
                "State": Variant("u", 2), "Devices": Variant("ao", [device])}))
        server.add(device, Interface("org.freedesktop.NetworkManager.Device", {
            "Interface": Variant("s", "wlan0"), "DeviceType": Variant("u", 2),
            "State": Variant("u", 100), "Driver": Variant("s", "iwlwifi"),
            "HwAddress": Variant("s", "AA:BB:CC:DD:EE:FF"), "Managed": Variant("b", True)}))
        server.add("/org/freedesktop/NetworkManager/Devices/1", Interface(
            "org.freedesktop.NetworkManager.Device", {
                "Interface": Variant("s", "enp3s0"), "DeviceType": Variant("u", 1),
                "State": Variant("u", 30), "Driver": Variant("s", "e1000e"),
                "HwAddress": Variant("s", "11:22:33:44:55:66"), "Managed": Variant("b", True)}))

        wireless = Interface("org.freedesktop.NetworkManager.Device.Wireless", {
            "ActiveAccessPoint": Variant("o", "/org/freedesktop/NetworkManager/AccessPoint/1"),
            "LastScan": Variant("x", 1000)})
        wireless.add_method("GetAllAccessPoints", "", "ao", lambda: [
            "/org/freedesktop/NetworkManager/AccessPoint/1",
            "/org/freedesktop/NetworkManager/AccessPoint/2",
            "/org/freedesktop/NetworkManager/AccessPoint/3"])
        wireless.add_method("RequestScan", "a{sv}", "", lambda _options: None)
        server.add(device, wireless)

        # Two of these share an SSID: a mesh publishes one AccessPoint per radio, and the panel
        # must show one network.
        for path, ssid, ap_strength, flags in (
                ("1", b"Zaldros-Guest", strength, 1),
                ("2", b"Zaldros-Guest", 41, 1),
                ("3", b"\xd0\x9e\xd1\x84\xd0\xb8\xd1\x81", 63, 0)):
            server.add(f"/org/freedesktop/NetworkManager/AccessPoint/{path}", Interface(
                "org.freedesktop.NetworkManager.AccessPoint", {
                    "Ssid": Variant("ay", ssid), "Strength": Variant("y", ap_strength),
                    "Flags": Variant("u", flags), "WpaFlags": Variant("u", 0),
                    "RsnFlags": Variant("u", 0x100 if flags else 0),
                    "Frequency": Variant("u", 5180)}))

    # -- BlueZ -------------------------------------------------------------------------------
    def add_bluez(self, powered: bool = True) -> None:
        server = self.service("org.bluez")
        server.add("/org/bluez/hci0", Interface("org.bluez.Adapter1", {
            "Address": Variant("s", "00:11:22:33:44:55"), "Name": Variant("s", "zaldros"),
            "Alias": Variant("s", "Zaldros"), "Powered": Variant("b", powered),
            "Discoverable": Variant("b", False), "Pairable": Variant("b", True),
            "Discovering": Variant("b", False)}))
        headset = Interface("org.bluez.Device1", {
            "Address": Variant("s", "AA:00:11:22:33:44"), "Name": Variant("s", "WH-1000XM4"),
            "Alias": Variant("s", "WH-1000XM4"), "Icon": Variant("s", "audio-headset"),
            "Paired": Variant("b", True), "Connected": Variant("b", True),
            "Trusted": Variant("b", True), "RSSI": Variant("n", -54),
            "Adapter": Variant("o", "/org/bluez/hci0")})
        headset.add_method("Connect", "", "", lambda: None)
        headset.add_method("Disconnect", "", "", lambda: None)
        server.add("/org/bluez/hci0/dev_AA_00_11_22_33_44", headset)
        server.add("/org/bluez/hci0/dev_AA_00_11_22_33_44",
                        Interface("org.bluez.Battery1", {"Percentage": Variant("y", 65)}))
        server.add("/org/bluez/hci0/dev_BB_00_11_22_33_44", Interface(
            "org.bluez.Device1", {
                "Address": Variant("s", "BB:00:11:22:33:44"),
                "Alias": Variant("s", "Клавиатура"), "Icon": Variant("s", "input-keyboard"),
                "Paired": Variant("b", False), "Connected": Variant("b", False),
                "Trusted": Variant("b", False), "Adapter": Variant("o", "/org/bluez/hci0")}))

    # -- udisks2 -----------------------------------------------------------------------------
    def add_udisks(self, mounted: bool = True) -> None:
        server = self.service("org.freedesktop.UDisks2")
        drive = "/org/freedesktop/UDisks2/drives/Samsung_SSD"
        server.add(drive, Interface("org.freedesktop.UDisks2.Drive", {
            "Vendor": Variant("s", "Samsung"), "Model": Variant("s", "SSD 970 EVO"),
            "Size": Variant("t", 1000204886016), "Removable": Variant("b", False),
            "Ejectable": Variant("b", False), "MediaAvailable": Variant("b", True),
            "ConnectionBus": Variant("s", ""), "Serial": Variant("s", "S4EWNX0")}))
        usb = "/org/freedesktop/UDisks2/drives/Kingston"
        server.add(usb, Interface("org.freedesktop.UDisks2.Drive", {
            "Vendor": Variant("s", "Kingston"), "Model": Variant("s", "DataTraveler"),
            "Size": Variant("t", 32010928128), "Removable": Variant("b", True),
            "Ejectable": Variant("b", True), "MediaAvailable": Variant("b", True),
            "ConnectionBus": Variant("s", "usb"), "Serial": Variant("s", "0014")}))

        for path, device, label, drive_path, system, points in (
                ("sda1", b"/dev/sda1\0", "Windows", drive, True, [b"/\0"] if mounted else []),
                ("sdb1", b"/dev/sdb1\0", "ZALDROS", usb, False, []),
                ("loop0", b"/dev/loop0\0", "snap", drive, False, [b"/snap/core\0"])):
            server.add(f"/org/freedesktop/UDisks2/block_devices/{path}", Interface(
                "org.freedesktop.UDisks2.Block", {
                    "Device": Variant("ay", device), "IdLabel": Variant("s", label),
                    "IdUsage": Variant("s", "filesystem"), "IdType": Variant("s", "ext4"),
                    "IdUUID": Variant("s", f"uuid-{path}"),
                    "Size": Variant("t", 512110190592), "ReadOnly": Variant("b", False),
                    "Drive": Variant("o", drive_path), "HintSystem": Variant("b", system),
                    "HintIgnore": Variant("b", False)}))
            filesystem = Interface("org.freedesktop.UDisks2.Filesystem", {
                "MountPoints": Variant("aay", points), "Size": Variant("t", 512110190592)})
            filesystem.add_method("Mount", "a{sv}", "s", lambda _options: "/media/zaldros/ZALDROS")
            filesystem.add_method("Unmount", "a{sv}", "", lambda _options: None)
            server.add(f"/org/freedesktop/UDisks2/block_devices/{path}", filesystem)

    # -- systemd -----------------------------------------------------------------------------
    def add_systemd(self) -> None:
        server = self.service("org.freedesktop.systemd1")
        manager = Interface("org.freedesktop.systemd1.Manager", {
            "Version": Variant("s", "259.5"), "SystemState": Variant("s", "running")})
        units = [
            ("NetworkManager.service", "Network Manager", "loaded", "active", "running", "",
             "/org/freedesktop/systemd1/unit/NetworkManager_2eservice", 0, "", "/"),
            ("bluetooth.service", "Bluetooth service", "loaded", "active", "running", "",
             "/org/freedesktop/systemd1/unit/bluetooth_2eservice", 0, "", "/"),
            ("zaldros-broken.service", "A unit that failed", "loaded", "failed", "failed", "",
             "/org/freedesktop/systemd1/unit/zaldros_2dbroken_2eservice", 0, "", "/"),
            ("dev-sda1.mount", "Root mount", "loaded", "active", "mounted", "",
             "/org/freedesktop/systemd1/unit/dev_2dsda1_2emount", 0, "", "/")]
        manager.add_method("ListUnits", "", "a(ssssssouso)", lambda: units)
        manager.add_method("Subscribe", "", "", lambda: None)
        self.started: list[str] = []
        for method in ("StartUnit", "StopUnit", "RestartUnit"):
            manager.add_method(
                method, "ss", "o",
                lambda name, _mode, method=method: (
                    self.started.append(f"{method}:{name}") or "/org/freedesktop/systemd1/job/1"))
        manager.add_method("GetUnit", "s", "o",
                           lambda name: f"/org/freedesktop/systemd1/unit/{name.replace('.', '_2e')}")
        server.add("/org/freedesktop/systemd1", manager)
        server.add("/org/freedesktop/systemd1/unit/NetworkManager_2eservice", Interface(
            "org.freedesktop.systemd1.Unit", {
                "Id": Variant("s", "NetworkManager.service"),
                "Description": Variant("s", "Network Manager"),
                "ActiveState": Variant("s", "active"), "SubState": Variant("s", "running"),
                "LoadState": Variant("s", "loaded")}))

    # -- systemd-timedated / systemd-localed ---------------------------------------------------
    def add_timedated(self, timezone: str = "Europe/Moscow", ntp: bool = True) -> None:
        """timedated with working setters: SetTimezone/SetNTP really change the properties, so a
        test can prove the round trip instead of only that a call was made."""
        server = self.service("org.freedesktop.timedate1")
        iface = Interface("org.freedesktop.timedate1", {
            "Timezone": Variant("s", timezone), "LocalRTC": Variant("b", False),
            "CanNTP": Variant("b", True), "NTP": Variant("b", ntp),
            "NTPSynchronized": Variant("b", ntp), "TimeUSec": Variant("t", 1770000000000000),
            "RTCTimeUSec": Variant("t", 1770000000000000)})
        path = "/org/freedesktop/timedate1"

        def set_timezone(zone, _interactive):
            server.set_property(path, "org.freedesktop.timedate1", "Timezone", Variant("s", zone))

        def set_ntp(enabled, _interactive):
            for name in ("NTP", "NTPSynchronized"):
                server.set_property(path, "org.freedesktop.timedate1", name,
                                    Variant("b", bool(enabled)))

        def set_local_rtc(local, _adjust, _interactive):
            server.set_property(path, "org.freedesktop.timedate1", "LocalRTC",
                                Variant("b", bool(local)))

        iface.add_method("SetTimezone", "sb", "", set_timezone)
        iface.add_method("SetNTP", "bb", "", set_ntp)
        iface.add_method("SetLocalRTC", "bbb", "", set_local_rtc)
        iface.add_method("ListTimezones", "", "as",
                         lambda: ["Europe/Moscow", "Europe/Berlin", "Asia/Jerusalem", "UTC"])
        server.add(path, iface)

    def add_localed(self, lang: str = "ru_RU.UTF-8", layout: str = "us,ru") -> None:
        server = self.service("org.freedesktop.locale1")
        path = "/org/freedesktop/locale1"
        iface = Interface("org.freedesktop.locale1", {
            "Locale": Variant("as", [f"LANG={lang}"]), "X11Layout": Variant("s", layout),
            "X11Model": Variant("s", "pc105"), "X11Variant": Variant("s", ""),
            "X11Options": Variant("s", "grp:alt_shift_toggle"),
            "VConsoleKeymap": Variant("s", "us"),
            "VConsoleKeymapToggle": Variant("s", "")})

        def set_locale(values, _interactive):
            server.set_property(path, "org.freedesktop.locale1", "Locale",
                                Variant("as", [str(value) for value in values]))

        def set_x11(layout, model, variant, options, _convert, _interactive):
            for name, value in (("X11Layout", layout), ("X11Model", model),
                                ("X11Variant", variant), ("X11Options", options)):
                server.set_property(path, "org.freedesktop.locale1", name, Variant("s", value))

        iface.add_method("SetLocale", "asb", "", set_locale)
        iface.add_method("SetX11Keyboard", "ssssbb", "", set_x11)
        server.add(path, iface)

    # -- KWin input devices ---------------------------------------------------------------------
    def add_kwin_input(self) -> None:
        """A mouse and a touchpad, with the same property names KWin publishes."""
        server = self.service("org.kde.KWin")
        manager = Interface("org.kde.KWin.InputDeviceManager",
                            {"devicesSysNames": Variant("as", ["event3", "event5"])})
        server.add("/org/kde/KWin/InputDevice", manager)
        server.add("/org/kde/KWin/InputDevice/event3", Interface("org.kde.KWin.InputDevice", {
            "name": Variant("s", "Logitech MX Master 3"), "sysName": Variant("s", "event3"),
            "keyboard": Variant("b", False), "pointer": Variant("b", True),
            "touchpad": Variant("b", False), "touch": Variant("b", False),
            "tabletTool": Variant("b", False),
            "enabled": Variant("b", True), "supportsDisableEvents": Variant("b", False),
            "leftHanded": Variant("b", False), "supportsLeftHanded": Variant("b", True),
            "naturalScroll": Variant("b", False), "supportsNaturalScroll": Variant("b", True),
            "middleEmulation": Variant("b", False), "supportsMiddleEmulation": Variant("b", True),
            "pointerAcceleration": Variant("d", 0.0),
            "supportsPointerAcceleration": Variant("b", True)}))
        server.add("/org/kde/KWin/InputDevice/event5", Interface("org.kde.KWin.InputDevice", {
            "name": Variant("s", "SynPS/2 Synaptics TouchPad"), "sysName": Variant("s", "event5"),
            "keyboard": Variant("b", False), "pointer": Variant("b", True),
            "touchpad": Variant("b", True), "touch": Variant("b", False),
            "tabletTool": Variant("b", False),
            "enabled": Variant("b", True), "supportsDisableEvents": Variant("b", True),
            "tapToClick": Variant("b", False), "tapAndDrag": Variant("b", True),
            "disableWhileTyping": Variant("b", True),
            "supportsDisableWhileTyping": Variant("b", True),
            "naturalScroll": Variant("b", True), "supportsNaturalScroll": Variant("b", True),
            "pointerAcceleration": Variant("d", 0.2),
            "supportsPointerAcceleration": Variant("b", True)}))

    # -- accountsservice --------------------------------------------------------------------------
    def add_accounts(self, user: str = "zaldros", admin: bool = True) -> None:
        server = self.service("org.freedesktop.Accounts")
        manager = Interface("org.freedesktop.Accounts", {
            "DaemonVersion": Variant("s", "23.13.9"),
            "HasMultipleUsers": Variant("b", True)})
        users = {user: "/org/freedesktop/Accounts/User1000",
                 "guest": "/org/freedesktop/Accounts/User1001"}
        manager.add_method("ListCachedUsers", "", "ao", lambda: list(users.values()))
        manager.add_method("FindUserByName", "s", "o",
                           lambda name: users.get(name, "/org/freedesktop/Accounts/UserNone"))
        server.add("/org/freedesktop/Accounts", manager)
        for path, name, uid, is_admin in ((users[user], user, 1000, admin),
                                          (users["guest"], "guest", 1001, False)):
            iface = Interface("org.freedesktop.Accounts.User", {
                "Uid": Variant("t", uid), "UserName": Variant("s", name),
                "RealName": Variant("s", name.title()),
                "AccountType": Variant("i", 1 if is_admin else 0),
                "HomeDirectory": Variant("s", f"/home/{name}"),
                "Shell": Variant("s", "/bin/bash"), "Locked": Variant("b", False),
                "AutomaticLogin": Variant("b", False), "SystemAccount": Variant("b", False)})
            for method, signature, property_name, kind in (
                    ("SetAutomaticLogin", "b", "AutomaticLogin", "b"),
                    ("SetLocked", "b", "Locked", "b"),
                    ("SetAccountType", "i", "AccountType", "i"),
                    ("SetRealName", "s", "RealName", "s")):
                iface.add_method(
                    method, signature, "",
                    lambda value, path=path, property_name=property_name, kind=kind:
                        server.set_property(path, "org.freedesktop.Accounts.User", property_name,
                                            Variant(kind, value)))
            server.add(path, iface)

    # -- xdg-desktop-portal permission store -------------------------------------------------------
    def add_permission_store(self) -> None:
        server = self.service("org.freedesktop.impl.portal.PermissionStore")
        tables: dict[tuple[str, str], dict[str, list[str]]] = {
            ("devices", "camera"): {"org.chromium.Chromium": ["yes"], "im.riot.Riot": ["no"]},
            ("devices", "microphone"): {"org.chromium.Chromium": ["yes"]},
            ("location", "location"): {}}
        iface = Interface("org.freedesktop.impl.portal.PermissionStore")
        iface.add_method("Lookup", "ss", "a{sas}v",
                         lambda table, entry: (dict(tables.get((table, entry), {})),
                                               Variant("s", "")))
        iface.add_method("GetPermission", "sss", "as",
                         lambda table, entry, app: tables.get((table, entry), {}).get(app, []))
        iface.add_method(
            "SetPermission", "sbssas", "",
            lambda table, _create, entry, app, permissions: tables.setdefault(
                (table, entry), {}).__setitem__(app, [str(value) for value in permissions]))
        iface.add_method("List", "s", "as",
                         lambda table: [entry for (name, entry) in tables if name == table])
        server.add("/org/freedesktop/impl/portal/PermissionStore", iface)

    # -- PackageKit ---------------------------------------------------------------------------------
    def add_packagekit(self, updates: int = 2) -> None:
        """The daemon plus a transaction that answers with Package signals and Finished, which is
        the shape the real one has and the reason UpdatesFacet pumps the bus."""
        server = self.service("org.freedesktop.PackageKit")
        path = "/org/freedesktop/PackageKit/Transaction/1"
        daemon = Interface("org.freedesktop.PackageKit", {
            "VersionMajor": Variant("u", 1), "VersionMinor": Variant("u", 3),
            "VersionMicro": Variant("u", 0), "BackendName": Variant("s", "aptcc"),
            "DistroId": Variant("s", "ubuntu;26.04;x86_64"),
            "NetworkState": Variant("u", 2), "Locked": Variant("b", False)})
        daemon.add_method("CreateTransaction", "", "o", lambda: path)
        server.add("/org/freedesktop/PackageKit", daemon)

        transaction = Interface("org.freedesktop.PackageKit.Transaction",
                                {"Percentage": Variant("u", 0)})

        def get_updates(_filter):
            for index in range(updates):
                server.emit_signal(path, "org.freedesktop.PackageKit.Transaction", "Package",
                                   "uss", [8 if index == 0 else 9,
                                           f"zaldros-package{index};1.{index};amd64;ubuntu",
                                           f"Package {index}"])
            server.emit_signal(path, "org.freedesktop.PackageKit.Transaction", "Finished", "uu",
                               [1, 42])

        transaction.add_method("GetUpdates", "t", "", get_updates)
        transaction.add_method(
            "RefreshCache", "b", "",
            lambda _force: server.emit_signal(path, "org.freedesktop.PackageKit.Transaction",
                                              "Finished", "uu", [1, 7]))
        server.add(path, transaction)

    def add_all(self) -> None:
        self.add_upower()
        self.add_logind()
        self.add_network_manager()
        self.add_bluez()
        self.add_udisks()
        self.add_systemd()
        self.add_timedated()
        self.add_localed()
        self.add_kwin_input()
        self.add_accounts()
        self.add_permission_store()
        self.add_packagekit()


def offline_backend():
    """A backend whose buses can never connect — a machine where nothing is running.

    Used by tests that must prove the *absence* path: every reading unavailable, every control
    disabled with a reason, and not one invented value. Faster and more honest than skipping.
    """
    from .facade import ZaldrosBackend
    system, session = Bus("system"), Bus("session")
    for bus in (system, session):
        bus._failure = "offline test bus"          # noqa: SLF001 - this module is the test rig
        bus._next_attempt = float("inf")           # noqa: SLF001 - never retry the connection
    return ZaldrosBackend(system_bus=system, session_bus=session)


def backend_on(address: str):
    """A `ZaldrosBackend` whose both buses point at `address`. Used by the facet tests."""
    from .facade import ZaldrosBackend
    system = Bus("system", connection=Connection.connect(address))
    session = Bus("session", connection=Connection.connect(address))
    return ZaldrosBackend(system_bus=system, session_bus=session)
