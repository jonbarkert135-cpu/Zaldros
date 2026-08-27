# ADR-0014 — One Zaldros backend layer, spoken over our own D-Bus client

Date: 2026-08-28
Status: accepted

## Context

The shell had no system layer. Each surface reached for whatever was nearest:

| what | how it was read | where |
| --- | --- | --- |
| battery | `/sys/class/power_supply/BAT*/capacity` | `system.py` |
| backlight | `/sys/class/backlight/*/brightness` | `system.py` |
| network | `/sys/class/net/*/operstate` | `system.py` |
| volume | `wpctl get-volume`, parsed as text | `system.py` |
| bluetooth | `ls /sys/class/bluetooth` | `system.py` |
| keyboard | `gdbus call` + `localectl status`, parsed as text | `system.py` |
| CPU / memory | `/proc/stat`, `/proc/meminfo` | `backend.py`, `hostinfo.py` (two copies) |

Four consequences, all of them measurable rather than aesthetic:

1. **Nothing updated.** `SystemState` took one snapshot at construction and never took another.
   The tray showed the battery level from the moment the shell started, forever.
2. **The clock polled at 1 Hz** to move a display that shows `HH:MM`, and dragged two /proc reads
   and a full binding re-evaluation along with every tick.
3. **Every panel invented its own vocabulary** for "there is nothing to show".
4. **Nothing could be controlled.** Every quick-settings tile was a picture. There was no way to
   turn Wi-Fi off, mount a USB stick, connect a headset or change the brightness, because none of
   the reading paths had a writing path.

## Decision

One layer, `backend/zaldros_backend`, between the UI and the system:

```
Zaldros UI  ->  Zaldros Backend  ->  systemd · logind · NetworkManager · BlueZ · UPower
                                     udisks2 · polkit · PipeWire · KWin · KScreen
```

* **One facet per domain** (`power`, `network`, `bluetooth`, `audio`, `storage`, `display`,
  `services`, `session`, `notifications`, `auth`, `hardware`), reached through one
  `ZaldrosBackend`. A panel calls `backend.power.battery()`; it never learns that the answer comes
  from UPower's composite `DisplayDevice`.
* **One honesty contract** (`Reading`): a value, whether it is real, why it is not, and the source
  it came from. The wordings live in one file, so two panels cannot phrase the same absence
  differently.
* **Event-driven.** Every facet subscribes to the signals its service already emits; the facade
  coalesces the burst; the UI is told once. A `QSocketNotifier` on the bus socket means an idle
  desktop adds zero wakeups.
* **No Qt below `qtbridge.py`**, so the backend is usable from a tool, a test or a service.

### Why our own D-Bus client instead of a library

Measured, not assumed: PySide6's QtDBus **cannot decode `a{sv}`**. `QDBusArgument.asVariant()`
returns a null converter (`pointerToPython(): SbkConverter is null for VoidPtr`), so every property
dictionary and every variant reply comes back as `None` — and a property dictionary is what UPower,
NetworkManager, BlueZ, udisks2 and systemd all answer with.

`python3-dbus`, `PyGObject` and vendored `jeepney` were all rejected for the same reason: each has
to be installed by the CI workflow, and the GitHub App that pushes this repository has no
`workflows` permission, so a dependency we cannot install is a test suite we cannot run.

`wire.py` + `connection.py` implement the specification against the standard library alone: no
dependency, no packaging risk, and the shell keeps a client it can debug. `service.py` is the same
protocol in the other direction, which Zaldros needs anyway to *be*
`org.freedesktop.Notifications` — in Windows the notification centre is part of the shell, not a
separate daemon.

### Which interface per domain, and why

| domain | interface | note |
| --- | --- | --- |
| battery, AC, lid | `org.freedesktop.UPower` | the composite `DisplayDevice`, as GNOME and Plasma read it |
| sleep, shutdown, session | `org.freedesktop.login1` | `Can*` returns a string; `challenge` is still an offer |
| services | `org.freedesktop.systemd1` | both managers — system *and* user |
| network | `org.freedesktop.NetworkManager` | one `path_namespace` match rule for the whole tree |
| bluetooth | `org.bluez` via `ObjectManager` | BlueZ has no "list devices": the tree is the inventory |
| storage | `org.freedesktop.UDisks2` | mounting a stick without root is a polkit action a user holds |
| privilege | `org.freedesktop.PolicyKit1` | asked *before* drawing a control, never after the click |
| brightness | `org.kde.ScreenBrightness`, then PowerDevil, then sysfs **read-only** | writing sysfs needs root and races PowerDevil |
| outputs | `kscreen-doctor -j` | output management is a Wayland protocol, not D-Bus |
| audio | `wpctl` / `pactl` | **PipeWire is not on D-Bus**; mixer control is libwireplumber or a tool |

The last row is the one exception to "no shelling out", and it is marked as such in every reading
it produces (`source: "wpctl"`).

## Consequences

* The tray updates. Quick-settings tiles do something. Storage, services, outputs, notifications
  and polkit are reachable for the first time.
* A machine with no D-Bus loses nothing: the sysfs readers survive as fallbacks, in the same
  wording, so the layer could not take a reading away — only add sources.
* One more package to install (`build/iso/build-iso.sh` copies it next to `zaldros_shell`;
  `tests/test_flat_layout.py` boots the shell from exactly that copy set and would have caught it).
* We own a D-Bus implementation. It is fuzzed round-trip and exercised against a real
  `dbus-daemon` with mock UPower / NetworkManager / BlueZ / udisks2 / logind / systemd services,
  each on its own connection — an arrangement that already caught a real routing bug (a udisks2
  signal waking the BlueZ handler, because a signal's sender is the unique name and not the
  well-known one).
* Not done here, and not claimed: `org.zaldros.Backend1` is not published yet, so Sheets and
  Settings still import the package rather than calling the shell; the notification *server* is
  implemented and tested but not yet claimed at runtime; nothing in this ADR has been observed on
  real hardware — the first evidence will be an ISO boot report.
