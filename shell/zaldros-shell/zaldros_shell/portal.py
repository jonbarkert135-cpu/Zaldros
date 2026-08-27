"""xdg-desktop-portal ScreenCast — how the recorder gets legal access to the screen.

On Wayland no application may simply read the framebuffer; the compositor hands out a PipeWire
node through `org.freedesktop.portal.ScreenCast`, and the user approves it once. That handshake
is four D-Bus calls with a response signal after each, which is why it lives in its own file:

    CreateSession → SelectSources → Start → OpenPipeWireRemote

The result is a PipeWire node id and a file descriptor, which `capture.recording_command` turns
into an ffmpeg command. If the portal is not running, `session()` returns a `PortalError` with the
reason, and the game bar prints that sentence instead of pretending to record.
"""

from __future__ import annotations

from dataclasses import dataclass

BUS_NAME = "org.freedesktop.portal.Desktop"
OBJECT_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
REQUEST = "org.freedesktop.portal.Request"

# SelectSources options, as the portal spec defines them.
SOURCE_MONITOR = 1          # types: 1 monitor, 2 window, 4 virtual
CURSOR_EMBEDDED = 2         # cursor_mode: 1 hidden, 2 embedded, 4 metadata


@dataclass
class PortalError(Exception):
    """Why we could not get a screen cast. Shown to the user verbatim."""

    reason: str

    def __str__(self) -> str:                              # pragma: no cover - trivial
        return self.reason


@dataclass
class Cast:
    """A live screen cast: the PipeWire node to read and the fd that keeps it open."""

    node: int
    fd: int
    session: str


def _handle_token(counter: list[int]) -> str:
    counter[0] += 1
    return f"zaldros{counter[0]}"


def session(timeout_ms: int = 30000):
    """Run the handshake and return a `Cast`. Raises `PortalError` with the reason if it fails.

    Imported lazily so the module can be read (and tested) on a machine without QtDBus.
    """
    try:
        from PySide6.QtCore import QEventLoop, QTimer, QVariant  # noqa: F401
        from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusReply
    except ImportError as exc:                                   # noqa: BLE001 — reported
        raise PortalError(f"QtDBus недоступен: {exc}") from exc

    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        raise PortalError("Нет сессионной шины D-Bus — портал захвата экрана недоступен")
    iface = QDBusInterface(BUS_NAME, OBJECT_PATH, SCREENCAST, bus)
    if not iface.isValid():
        raise PortalError("xdg-desktop-portal не запущен: записывать экран нечем")

    counter = [0]
    loop = QEventLoop()
    state: dict = {}

    def wait_for(reply_path: str, step: str):
        """Every portal call answers later, on the Response signal of its Request object."""
        state.pop("response", None)

        def on_response(code, results):
            state["response"] = (int(code), dict(results))
            loop.quit()

        bus.connect(BUS_NAME, reply_path, REQUEST, "Response", on_response)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(timeout_ms)
        loop.exec()
        bus.disconnect(BUS_NAME, reply_path, REQUEST, "Response", on_response)
        if "response" not in state:
            raise PortalError(f"Портал не ответил на шаге {step}")
        code, results = state["response"]
        if code != 0:
            raise PortalError(f"Запись отменена на шаге {step} (код {code})")
        return results

    reply = iface.call("CreateSession", {"session_handle_token": _handle_token(counter),
                                         "handle_token": _handle_token(counter)})
    path = QDBusReply(reply).value()
    if not path:
        raise PortalError("Портал не создал сессию захвата экрана")
    results = wait_for(str(path), "CreateSession")
    handle = results.get("session_handle")
    if not handle:
        raise PortalError("Портал не вернул дескриптор сессии")

    reply = iface.call("SelectSources", handle,
                       {"types": SOURCE_MONITOR, "multiple": False,
                        "cursor_mode": CURSOR_EMBEDDED,
                        "handle_token": _handle_token(counter)})
    wait_for(str(QDBusReply(reply).value()), "SelectSources")

    reply = iface.call("Start", handle, "", {"handle_token": _handle_token(counter)})
    results = wait_for(str(QDBusReply(reply).value()), "Start")
    streams = results.get("streams") or []
    if not streams:
        raise PortalError("Пользователь не выбрал экран для записи")
    node = int(streams[0][0])

    reply = iface.call("OpenPipeWireRemote", handle, {})
    fd = QDBusReply(reply).value()
    try:
        fd = int(fd.fileDescriptor())
    except AttributeError:
        fd = int(fd)
    if fd < 0:
        raise PortalError("Портал не отдал дескриптор PipeWire")
    return Cast(node=node, fd=fd, session=str(handle))
