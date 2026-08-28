"""Every Linux service name, object path, interface and enumeration Zaldros speaks to.

One file, so that "which D-Bus name does the battery live on" has exactly one answer and the UI
never learns any of them. Each block cites the primary source it was read from and the date, so a
future run can tell a fact from a memory.

Ubuntu 26.04 ships: systemd 259.5, bluez 5.85, udisks2 2.10.91, upower 1.91.1, pipewire 1.6.2
[ubuntu-26.04-desktop-amd64.manifest, 2026-08-27].
"""

from __future__ import annotations

# --------------------------------------------------------------------------------------------
# Standard interfaces (D-Bus Specification, fetched 2026-08-27)
# --------------------------------------------------------------------------------------------
PROPERTIES = "org.freedesktop.DBus.Properties"
INTROSPECTABLE = "org.freedesktop.DBus.Introspectable"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
PEER = "org.freedesktop.DBus.Peer"


# --------------------------------------------------------------------------------------------
# UPower — batteries, AC, lid  (https://upower.freedesktop.org/docs/, fetched 2026-08-27)
# --------------------------------------------------------------------------------------------
class UPower:
    SERVICE = "org.freedesktop.UPower"
    PATH = "/org/freedesktop/UPower"
    IFACE = "org.freedesktop.UPower"
    DEVICE_IFACE = "org.freedesktop.UPower.Device"
    DEVICE_NAMESPACE = "/org/freedesktop/UPower/devices"
    # Manager: EnumerateDevices() -> ao, GetDisplayDevice() -> o, GetCriticalAction() -> s
    # Manager properties: DaemonVersion s, OnBattery b, LidIsClosed b, LidIsPresent b
    # Signals: DeviceAdded(o), DeviceRemoved(o)
    DISPLAY_DEVICE = "/org/freedesktop/UPower/devices/DisplayDevice"

    # Device.Type
    TYPE = {0: "unknown", 1: "line-power", 2: "battery", 3: "ups", 4: "monitor", 5: "mouse",
            6: "keyboard", 7: "pda", 8: "phone", 9: "media-player", 10: "tablet",
            11: "computer", 12: "gaming-input", 13: "pen", 14: "touchpad", 15: "modem",
            16: "network", 17: "headset", 18: "speakers", 19: "headphones", 20: "video",
            21: "other-audio", 22: "remote-control", 23: "printer", 24: "scanner",
            25: "camera", 26: "wearable", 27: "toy", 28: "bluetooth-generic"}
    # Device.State
    STATE = {0: "unknown", 1: "charging", 2: "discharging", 3: "empty", 4: "fully-charged",
             5: "pending-charge", 6: "pending-discharge"}
    # Device.WarningLevel
    WARNING = {0: "unknown", 1: "none", 2: "discharging", 3: "low", 4: "critical", 5: "action"}


# --------------------------------------------------------------------------------------------
# systemd-logind — the session, sleep and shutdown
# (https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.login1.html)
# --------------------------------------------------------------------------------------------
class Login1:
    SERVICE = "org.freedesktop.login1"
    PATH = "/org/freedesktop/login1"
    MANAGER = "org.freedesktop.login1.Manager"
    SESSION = "org.freedesktop.login1.Session"
    SEAT = "org.freedesktop.login1.Seat"
    SELF_SESSION = "/org/freedesktop/login1/session/self"
    # Manager: PowerOff(b), Reboot(b), Suspend(b), Hibernate(b), HybridSleep(b),
    #          SuspendThenHibernate(b), CanPowerOff() -> s, CanReboot() -> s, CanSuspend() -> s,
    #          CanHibernate() -> s, LockSession(s), Inhibit(ssss) -> h
    #          Signals: PrepareForSleep(b), PrepareForShutdown(b)
    # A Can* reply is a string: "yes", "no", "na", "challenge".
    CAN_YES = ("yes", "challenge")


# --------------------------------------------------------------------------------------------
# systemd — services
# (https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html)
# --------------------------------------------------------------------------------------------
class Systemd:
    SERVICE = "org.freedesktop.systemd1"
    PATH = "/org/freedesktop/systemd1"
    MANAGER = "org.freedesktop.systemd1.Manager"
    UNIT = "org.freedesktop.systemd1.Unit"
    # ListUnits() -> a(ssssssouso), StartUnit(ss) -> o, StopUnit(ss) -> o, RestartUnit(ss) -> o,
    # GetUnit(s) -> o, Subscribe(), Unsubscribe()
    # ListUnits struct: name, description, load_state, active_state, sub_state, followed,
    #                   object_path, job_id, job_type, job_object_path
    LIST_UNITS_SIGNATURE = ("name", "description", "load_state", "active_state", "sub_state",
                            "followed", "path", "job_id", "job_type", "job_path")
    REPLACE = "replace"


# --------------------------------------------------------------------------------------------
# NetworkManager (https://networkmanager.dev/docs/api/latest/, fetched 2026-08-27)
# --------------------------------------------------------------------------------------------
class NetworkManager:
    SERVICE = "org.freedesktop.NetworkManager"
    PATH = "/org/freedesktop/NetworkManager"
    IFACE = "org.freedesktop.NetworkManager"
    DEVICE = "org.freedesktop.NetworkManager.Device"
    WIRELESS = "org.freedesktop.NetworkManager.Device.Wireless"
    WIRED = "org.freedesktop.NetworkManager.Device.Wired"
    ACCESS_POINT = "org.freedesktop.NetworkManager.AccessPoint"
    ACTIVE_CONNECTION = "org.freedesktop.NetworkManager.Connection.Active"
    SETTINGS = "org.freedesktop.NetworkManager.Settings"
    SETTINGS_PATH = "/org/freedesktop/NetworkManager/Settings"
    CONNECTION = "org.freedesktop.NetworkManager.Settings.Connection"
    IP4CONFIG = "org.freedesktop.NetworkManager.IP4Config"
    IP6CONFIG = "org.freedesktop.NetworkManager.IP6Config"
    NAMESPACE = "/org/freedesktop/NetworkManager"

    # NetworkManager.State
    STATE = {0: "unknown", 10: "asleep", 20: "disconnected", 30: "disconnecting",
             40: "connecting", 50: "connected-local", 60: "connected-site", 70: "connected"}
    # NetworkManager.Connectivity
    CONNECTIVITY = {0: "unknown", 1: "none", 2: "portal", 3: "limited", 4: "full"}
    # NM_DEVICE_TYPE — only the kinds a desktop tray cares about are named; the rest stay numeric.
    DEVICE_TYPE = {1: "ethernet", 2: "wifi", 5: "bluetooth", 8: "modem", 13: "bridge",
                   14: "generic", 15: "team", 16: "tun", 29: "wireguard", 30: "wifi-p2p",
                   32: "loopback"}
    # NM_DEVICE_STATE
    DEVICE_STATE = {0: "unknown", 10: "unmanaged", 20: "unavailable", 30: "disconnected",
                    40: "prepare", 50: "config", 60: "need-auth", 70: "ip-config",
                    80: "ip-check", 90: "secondaries", 100: "activated", 110: "deactivating",
                    120: "failed"}
    # NM_802_11_AP_SEC / flags: bit 0 of AccessPoint.Flags is PRIVACY (the padlock).
    AP_FLAG_PRIVACY = 0x1
    # NM_METERED
    METERED = {0: "unknown", 1: "yes", 2: "no", 3: "guess-yes", 4: "guess-no"}


# --------------------------------------------------------------------------------------------
# BlueZ (https://github.com/bluez/bluez/blob/master/doc/, fetched 2026-08-27)
# --------------------------------------------------------------------------------------------
class BlueZ:
    SERVICE = "org.bluez"
    ROOT = "/"
    NAMESPACE = "/org/bluez"
    ADAPTER = "org.bluez.Adapter1"
    DEVICE = "org.bluez.Device1"
    BATTERY = "org.bluez.Battery1"
    # Adapter1: StartDiscovery(), StopDiscovery(), RemoveDevice(o)
    #   properties Address s, Name s, Alias s, Powered b, Discoverable b, Pairable b, Discovering b
    # Device1: Connect(), Disconnect(), Pair()
    #   properties Address s, Name s, Alias s, Icon s, Paired b, Bonded b, Connected b,
    #              Trusted b, Blocked b, RSSI n, Adapter o
    # Battery1: Percentage y


# --------------------------------------------------------------------------------------------
# udisks2 (https://storaged.org/doc/udisks2-api/latest/, fetched 2026-08-27)
# --------------------------------------------------------------------------------------------
class UDisks2:
    SERVICE = "org.freedesktop.UDisks2"
    PATH = "/org/freedesktop/UDisks2"
    NAMESPACE = "/org/freedesktop/UDisks2"
    MANAGER = "org.freedesktop.UDisks2.Manager"
    DRIVE = "org.freedesktop.UDisks2.Drive"
    BLOCK = "org.freedesktop.UDisks2.Block"
    FILESYSTEM = "org.freedesktop.UDisks2.Filesystem"
    PARTITION = "org.freedesktop.UDisks2.Partition"
    # Filesystem: Mount(a{sv}) -> s, Unmount(a{sv}); property MountPoints aay
    # Block: properties Device ay, IdLabel s, IdType s, IdUUID s, Size t, ReadOnly b,
    #        Drive o, HintSystem b, HintIgnore b
    # Drive: Eject(a{sv}), PowerOff(a{sv}); properties Vendor s, Model s, Size t,
    #        Removable b, Ejectable b, MediaAvailable b, ConnectionBus s


# --------------------------------------------------------------------------------------------
# polkit (https://polkit.pages.freedesktop.org/polkit/, fetched 2026-08-27)
# --------------------------------------------------------------------------------------------
class Polkit:
    SERVICE = "org.freedesktop.PolicyKit1"
    PATH = "/org/freedesktop/PolicyKit1/Authority"
    AUTHORITY = "org.freedesktop.PolicyKit1.Authority"
    # CheckAuthorization(subject:(sa{sv}), action_id:s, details:a{ss}, flags:u,
    #                    cancellation_id:s) -> (bba{ss})
    # flags: 1 = ALLOW_USER_INTERACTION
    ALLOW_USER_INTERACTION = 1


# --------------------------------------------------------------------------------------------
# Desktop notifications (https://specifications.freedesktop.org/notification/latest/)
# --------------------------------------------------------------------------------------------
class Notifications:
    SERVICE = "org.freedesktop.Notifications"
    PATH = "/org/freedesktop/Notifications"
    IFACE = "org.freedesktop.Notifications"
    # Notify(susssasa{sv}i) -> u, CloseNotification(u), GetCapabilities() -> as,
    # GetServerInformation() -> ssss; signals NotificationClosed(uu), ActionInvoked(us)
    URGENCY_LOW, URGENCY_NORMAL, URGENCY_CRITICAL = 0, 1, 2
    CLOSED_REASON = {1: "expired", 2: "dismissed", 3: "closed-by-call", 4: "undefined"}


# --------------------------------------------------------------------------------------------
# Display brightness — KDE, because PowerDevil owns the backlight on a Plasma/KWin session.
# Writing /sys/class/backlight directly needs root or a udev rule and races PowerDevil's own
# state [KDE Discuss + powerdevil sources, 2026-08-27].
# --------------------------------------------------------------------------------------------
class ScreenBrightness:
    SERVICE = "org.kde.ScreenBrightness"                 # Plasma 6.5+
    PATH = "/org/kde/ScreenBrightness"
    IFACE = "org.kde.ScreenBrightness"
    DISPLAY = "org.kde.ScreenBrightness.Display"
    # /org/kde/ScreenBrightness -> DisplaysDBusNames as
    # per display: Brightness i, MaxBrightness i, SetBrightness(i value, u flags)


class PowerDevil:
    SERVICE = "org.kde.Solid.PowerManagement"            # legacy, still present in Plasma 6
    BRIGHTNESS_PATH = "/org/kde/Solid/PowerManagement/Actions/BrightnessControl"
    BRIGHTNESS_IFACE = "org.kde.Solid.PowerManagement.Actions.BrightnessControl"
    # brightness() -> i, brightnessMax() -> i, setBrightness(i), setBrightnessSilent(i)
    # signal brightnessChanged(i). brightnessMax is a normalised scale, not raw sysfs.


class KWinKeyboard:
    """KWin owns the keyboard layout on Wayland; localectl only knows what the image was built
    with. Verified against kwin v6.6.0 src/keyboard_layout.cpp."""

    SERVICE = "org.kde.keyboard"
    PATH = "/Layouts"
    IFACE = "org.kde.KeyboardLayouts"
    # getLayoutsList() -> a(sss) (short, display, long), getLayout() -> u, setLayout(u) -> b
    # signal layoutChanged(u)


# --------------------------------------------------------------------------------------------
# Audio — PipeWire has no D-Bus control surface.
# WirePlumber exposes mixer control through its own libwireplumber/Lua API and the `wpctl` tool;
# there is no `org.freedesktop.PipeWire` volume interface to call [WirePlumber 0.5 docs,
# 2026-08-27]. So this is the one facet that shells out, and it says so.
# --------------------------------------------------------------------------------------------
class Audio:
    WPCTL = "wpctl"
    PACTL = "pactl"
    DEFAULT_SINK = "@DEFAULT_AUDIO_SINK@"
    DEFAULT_SOURCE = "@DEFAULT_AUDIO_SOURCE@"


# --------------------------------------------------------------------------------------------
# systemd-timedated — clock, timezone, NTP
# (https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.timedate1.html,
#  fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class TimeDate1:
    SERVICE = "org.freedesktop.timedate1"
    PATH = "/org/freedesktop/timedate1"
    IFACE = "org.freedesktop.timedate1"
    # readonly: Timezone s, LocalRTC b, CanNTP b, NTP b, NTPSynchronized b, TimeUSec t,
    #           RTCTimeUSec t
    # SetTime(xbb), SetTimezone(sb), SetLocalRTC(bbb), SetNTP(bb), ListTimezones() -> as
    # Every setter's last argument is `interactive`: true lets polkit ask the user for a password
    # instead of failing outright, which is what a Settings page wants.


# --------------------------------------------------------------------------------------------
# systemd-localed — system language and X11/Wayland keyboard defaults
# (https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.locale1.html,
#  fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class Locale1:
    SERVICE = "org.freedesktop.locale1"
    PATH = "/org/freedesktop/locale1"
    IFACE = "org.freedesktop.locale1"
    # readonly: Locale as ("LANG=ru_RU.UTF-8", ...), X11Layout s, X11Model s, X11Variant s,
    #           X11Options s, VConsoleKeymap s, VConsoleKeymapToggle s
    # SetLocale(asb), SetVConsoleKeyboard(ssbb), SetX11Keyboard(ssssbb)
    # SetX11Keyboard only sets the *default*; the running Wayland session's layout belongs to
    # KWin (see KWinKeyboard), so the two are written together, never one instead of the other.


# --------------------------------------------------------------------------------------------
# KWin input devices — mouse, touchpad, keyboards, live on the running compositor
# (KDE/kwin src/backends/libinput/connection.cpp + device.h, fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class KWinInput:
    SERVICE = "org.kde.KWin"
    MANAGER_PATH = "/org/kde/KWin/InputDevice"
    MANAGER = "org.kde.KWin.InputDeviceManager"          # property devicesSysNames as
    DEVICE = "org.kde.KWin.InputDevice"                  # /org/kde/KWin/InputDevice/<sysName>
    # Writable device properties used by Settings, each paired with a `supports*` flag that says
    # whether this hardware has it at all: enabled b, leftHanded b, naturalScroll b,
    # tapToClick b, disableWhileTyping b, middleEmulation b, pointerAcceleration d,
    # scrollFactor d. Read-only kind flags: keyboard b, pointer b, touchpad b, touch b.
    KINDS = ("keyboard", "pointer", "touchpad", "touch", "tabletTool")


# --------------------------------------------------------------------------------------------
# accountsservice — the other people who can log in
# (accountsservice data/org.freedesktop.Accounts{,.User}.xml, fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class Accounts:
    SERVICE = "org.freedesktop.Accounts"
    PATH = "/org/freedesktop/Accounts"
    IFACE = "org.freedesktop.Accounts"
    USER = "org.freedesktop.Accounts.User"
    # Manager: ListCachedUsers() -> ao, FindUserByName(s) -> o, CreateUser(ssi) -> o,
    #          DeleteUser(xb); properties HasMultipleUsers b, AutomaticLoginUsers ao
    # User: properties Uid t, UserName s, RealName s, AccountType i (0 standard, 1 admin),
    #       HomeDirectory s, Shell s, Locked b, AutomaticLogin b, SystemAccount b
    #       methods SetRealName(s), SetAccountType(i), SetLocked(b), SetAutomaticLogin(b)
    ACCOUNT_TYPE = {0: "обычная", 1: "администратор"}


# --------------------------------------------------------------------------------------------
# xdg-desktop-portal permission store — which applications may use the camera, the microphone
# and the location. (xdg-desktop-portal data/org.freedesktop.impl.portal.PermissionStore.xml and
# src/device.c, src/location.c at 1.18.4, fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class PermissionStore:
    SERVICE = "org.freedesktop.impl.portal.PermissionStore"
    PATH = "/org/freedesktop/impl/portal/PermissionStore"
    IFACE = "org.freedesktop.impl.portal.PermissionStore"
    # Lookup(ss) -> (a{sas} permissions, v data), List(s) -> as,
    # SetPermission(s table, b create, s id, s app, as permissions),
    # GetPermission(sss) -> as, DeletePermission(sss)
    DEVICES_TABLE = "devices"                 # ids: "camera", "microphone", "speakers"
    LOCATION_TABLE = "location"
    LOCATION_ID = "location"
    YES, NO, ASK = "yes", "no", "ask"


# --------------------------------------------------------------------------------------------
# PackageKit — updates, whatever the distribution's package manager is underneath
# (PackageKit src/org.freedesktop.PackageKit{,.Transaction}.xml, fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class PackageKit:
    SERVICE = "org.freedesktop.PackageKit"
    PATH = "/org/freedesktop/PackageKit"
    IFACE = "org.freedesktop.PackageKit"
    TRANSACTION = "org.freedesktop.PackageKit.Transaction"
    # Daemon: CreateTransaction() -> o; properties BackendName s, DistroId s, NetworkState u
    # Transaction: GetUpdates(t filter), RefreshCache(b force);
    #   signals Package(u info, s package_id, s summary), Finished(u exit, u runtime),
    #           ErrorCode(u code, s details)
    FILTER_NONE = 1                            # PK_FILTER_ENUM_NONE
    EXIT = {1: "success", 2: "failed", 4: "cancelled", 5: "key-required", 6: "eula-required",
            11: "need-untrusted"}
    # PkInfoEnum values a "what will be updated" list cares about.
    INFO = {8: "security", 9: "normal", 10: "blocked", 11: "download", 12: "installing",
            2: "available", 1: "installed", 4: "low", 5: "enhancement", 6: "bugfix",
            7: "important"}


# --------------------------------------------------------------------------------------------
# Firewalls. Ubuntu ships ufw (a CLI over nftables, no D-Bus); firewalld does have a bus API and
# is what a Fedora-shaped machine runs. Both are read here, neither is invented.
# (ufw 0.36 /etc/ufw/ufw.conf; firewalld D-Bus API docs, fetched 2026-08-28)
# --------------------------------------------------------------------------------------------
class Firewall:
    FIREWALLD_SERVICE = "org.fedoraproject.FirewallD1"
    FIREWALLD_PATH = "/org/fedoraproject/FirewallD1"
    FIREWALLD_IFACE = "org.fedoraproject.FirewallD1"
    UFW_CONF = "/etc/ufw/ufw.conf"              # ENABLED=yes|no, written by `ufw enable`
    UFW_UNIT = "ufw.service"


# --------------------------------------------------------------------------------------------
# power-profiles-daemon (https://gitlab.freedesktop.org/upower/power-profiles-daemon, 2026-08-28)
# The bus name moved from net.hadess.PowerProfiles to org.freedesktop.UPower.PowerProfiles in
# 0.20; the old name is kept as an alias because Ubuntu 26.04 still ships both activation files.
# --------------------------------------------------------------------------------------------
class PowerProfiles:
    SERVICE = "org.freedesktop.UPower.PowerProfiles"
    PATH = "/org/freedesktop/UPower/PowerProfiles"
    IFACE = "org.freedesktop.UPower.PowerProfiles"
    LEGACY_SERVICE = "net.hadess.PowerProfiles"
    NAMES = {"power-saver": "Экономия энергии", "balanced": "Сбалансированный",
             "performance": "Максимальная производительность"}
