"""The only file in the backend that imports Qt.

It does two things and nothing else:

* watches each bus socket with a `QSocketNotifier`, so the process sleeps until the bus speaks;
* debounces the resulting burst with one single-shot timer before telling the UI.

A `QSocketNotifier` is not a poll. Qt hands the descriptor to the event loop's own `poll()`, the
one it already blocks on, so an idle desktop adds zero wakeups — which is the measurable
difference between this and the 1 Hz QTimer it replaces.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QSocketNotifier, QTimer, Signal

from .facade import DOMAINS, ZaldrosBackend

COALESCE_MS = 120      # long enough to swallow an association burst, short enough to feel instant


class BackendBridge(QObject):
    """Drives a `ZaldrosBackend` from the Qt event loop and re-emits its changes as signals."""

    changed = Signal(str)         # domain name

    def __init__(self, backend: ZaldrosBackend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self._notifiers: list[QSocketNotifier] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(COALESCE_MS)
        self._timer.timeout.connect(self._flush)
        for domain in DOMAINS:
            backend.subscribe(domain, lambda domain=domain: self._mark(domain))
        self.attach()

    def attach(self) -> int:
        """Watch every bus socket that exists. Returns how many are being watched.

        Zero is a normal answer — a session without a system bus is a session where the tray shows
        "служба недоступна", not one where the shell hangs.
        """
        self.detach()
        for bus in (self.backend.system_bus, self.backend.session_bus):
            descriptor = bus.fileno()
            if descriptor is None:
                continue
            notifier = QSocketNotifier(descriptor, QSocketNotifier.Type.Read, self)
            notifier.activated.connect(self._readable)
            self._notifiers.append(notifier)
        return len(self._notifiers)

    def detach(self) -> None:
        for notifier in self._notifiers:
            notifier.setEnabled(False)
            notifier.deleteLater()
        self._notifiers = []

    @property
    def watched_sockets(self) -> int:
        return len(self._notifiers)

    def _readable(self, *_args) -> None:
        self.backend.dispatch()
        if self.backend.pending and not self._timer.isActive():
            self._timer.start()

    def _mark(self, _domain: str) -> None:
        # The facade already collected the domain; this only makes sure a flush is scheduled when
        # something invalidated a domain without a socket having woken us (our own writes).
        if not self._timer.isActive():
            self._timer.start()

    def _flush(self) -> None:
        for domain in self.backend.flush():
            self.changed.emit(domain)

    def refresh_soon(self, domain: str) -> None:
        """After our own write: mark the domain and let the same debounce deliver it."""
        self.backend.invalidate(domain)
        if not self._timer.isActive():
            self._timer.start()
