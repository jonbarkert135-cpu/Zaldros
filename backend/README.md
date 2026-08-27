# Zaldros Backend

One layer between the Zaldros UI and the Linux services under it.

```
Zaldros UI  ->  Zaldros Backend  ->  systemd · logind · NetworkManager · BlueZ · UPower
                                     udisks2 · polkit · PipeWire · KWin · KScreen
```

The UI asks the backend. It does not know that a battery percentage comes from UPower's composite
display device, that a Wi-Fi list is one `AccessPoint` object per radio, or that PipeWire has no
D-Bus interface at all. Design rationale and the alternatives that were rejected:
`docs/state/decisions/ADR-0014-one-backend-layer.md`.

## Using it

```python
from zaldros_backend import ZaldrosBackend

backend = ZaldrosBackend()

battery = backend.power.battery()
if battery.available:
    print(battery.value, "%", battery.detail, "-", battery.get("time_text"))
else:
    print(battery.detail)             # why there is no number, in the user's language

backend.network.set_wifi_enabled(False)
backend.storage.mount("/org/freedesktop/UDisks2/block_devices/sdb1")
backend.notify.notify("Флешка подключена", "ZALDROS готова к работе")

backend.subscribe("power", lambda: print("power changed"))
backend.dispatch()                    # from a socket notifier; never from a timer
backend.flush()                       # coalesced: one call per domain, not per signal
```

Inside Qt, use the bridge instead of calling `dispatch()` yourself:

```python
from zaldros_backend.qtbridge import BackendBridge
bridge = BackendBridge(backend)
bridge.changed.connect(lambda domain: ...)
```

## The two rules

**Nothing is invented.** Every reading is a `Reading`: `available`, `value`, `detail`, `source`.
When a value cannot be measured on this machine, `available` is false and `detail` says why, in
the interface's language. `source` is the D-Bus path, the tool or the sysfs file it came from, so
a number in a screenshot can be traced back to what produced it.

**Nothing polls.** Each facet subscribes to the signals its service already emits, the facade
coalesces the burst, and the UI is told once. What cannot signal is named:

| domain | how it changes | why |
| --- | --- | --- |
| power, network, bluetooth, storage, display, services, session | D-Bus signals | the services emit them |
| audio | on demand | PipeWire is not on D-Bus; mixer control is libwireplumber or `wpctl` |
| clock | one single-shot timer per minute | the taskbar shows `HH:MM` |
| CPU / memory meters | 1 Hz **while a surface that draws them is open** | a meter is only a meter while it is visible |

## Layout

| file | what it is |
| --- | --- |
| `wire.py` | the D-Bus wire format: marshalling, alignment, messages |
| `connection.py` | socket, SASL handshake, calls, match rules, signal delivery |
| `service.py` | the server side — publishing objects, used by the notification server and by the mocks |
| `bus.py` | the non-raising API every facet uses (`Result`) |
| `catalog.py` | every service name, path, interface and enumeration, each with its source |
| `reading.py` | the honesty contract |
| `power` `network` `bluetooth` `audio` `storage` `display` `services` `session` `notifications` `auth` `hardware` | the facets |
| `facade.py` | `ZaldrosBackend` — the single entry point |
| `qtbridge.py` | the only file that imports Qt: socket notifiers plus a debounce |
| `testing.py` | mock services for the tests, on a real `dbus-daemon` |

We implement D-Bus ourselves because PySide6's QtDBus cannot decode `a{sv}`
(`QDBusArgument.asVariant()` returns a null converter), and because a third-party library would
have to be installed by a CI workflow this repository's push token may not edit. Zero
dependencies: the standard library and the specification.

## Tests

They live with the shell's, so CI runs them:

```
cd shell/zaldros-shell
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests -q
```

* `test_backend_wire.py` — the wire format, round-tripped at every alignment offset, plus a fuzz
  pass over property dictionaries.
* `test_backend_bus.py` — a private `dbus-daemon`, real connections, signal routing and
  coalescing.
* `test_backend_facets.py` — each facet against a mock of its own service, with the real property
  names and the real D-Bus types.
* `test_backend_overhead.py` — the guard that keeps the polling gone.

Measurement: `tools/zaldros-bench/backend_overhead.py --seconds 60`.
