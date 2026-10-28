# SPDX-License-Identifier: GPL-3.0-or-later
"""One bounded update check, with a private bus owned exclusively by its worker.

Stopping observation cannot undo a PackageKit metadata refresh already accepted by
the daemon. No installer or package upgrade is started here.
"""
from __future__ import annotations

import math
import threading
import time

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot

from zaldros_backend.bus import Bus
from zaldros_backend.updates import UpdatesFacet
from .settingscontrols import ACTION, INFO, State


class UpdateCheck(QObject):
    changed = Signal()
    _completed = Signal(int, object)

    def __init__(self, bus_factory=None, timeout: float = 240.0):
        super().__init__()
        self._bus_factory = bus_factory or (lambda: Bus(timeout=2.0))
        self.timeout = timeout
        self.status = "idle"
        self.error = ""
        self.error_code = ""
        self.reading = None
        self.busy = False
        self._generation = 0
        self._stop = threading.Event()
        self._deadline = 0.0
        self._thread = None
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._expired)
        self._completed.connect(self._receive, Qt.ConnectionType.QueuedConnection)

    @property
    def detail(self):
        return {"idle": self.tr("Not checked"), "running": self.tr("Checking for updates…"),
                "succeeded": self.tr("Check completed"),
                "failed": self.tr("Update check failed"),
                "cancelled": self.tr("Waiting stopped"),
                "timed_out": self.tr("Update check timed out")}[self.status]

    @property
    def message(self):
        if self.status == "cancelled":
            return self.tr("Stopped waiting; the service may still finish refreshing metadata")
        return self.detail + (": " + self.error if self.error else "")

    def control_state(self, control_id):
        if control_id == "updates.check":
            return State(ACTION, True, None, self.detail, not self.busy,
                         self.error, [], "PackageKit")
        if control_id == "updates.available":
            reading = self.reading
            if self.status == "succeeded" and reading is not None and reading.available:
                return State(INFO, True, reading.value, reading.detail, False, "", [], reading.source)
            return State(INFO, False, None, "", False, self.detail, [], "PackageKit")
        return None

    def start(self):
        if self.busy:
            return False  # one worker at a time; no unbounded queue after repeated clicks
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 86400:
            raise ValueError("update-check timeout must be between zero and one day")
        self._generation += 1
        generation = self._generation
        stop = self._stop = threading.Event()
        deadline = self._deadline = time.monotonic() + self.timeout
        self.status, self.error, self.error_code = "running", "", ""
        self.reading = None
        self.busy = True
        self._timer.start(max(1, math.ceil(self.timeout * 1000)))
        self._thread = threading.Thread(target=self._work, args=(generation, stop, deadline),
                                        name="zaldros-update-check", daemon=True)
        try:
            self._thread.start()
        except RuntimeError as exc:
            self._timer.stop()
            self._thread = None
            self.busy, self.status = False, "failed"
            self.error, self.error_code = str(exc), "worker_error"
            self.changed.emit()
            return False
        self.changed.emit()
        return True

    def _work(self, generation, stop, deadline):
        bus = None
        result = ("failed", None, "", "service_error")
        try:
            # Factory, connection, calls, subscriptions and close all run here.
            bus = self._bus_factory()
            facet = UpdatesFacet(bus)
            cancelled = lambda: stop.is_set() or time.monotonic() >= deadline
            refreshed = facet.refresh(max(0.001, deadline - time.monotonic()), cancelled)
            if not refreshed.ok:
                result = ("failed", None, refreshed.error, "service_error")
            elif not cancelled():
                reading = facet.updates(max(0.001, deadline - time.monotonic()), cancelled)
                result = (("succeeded", reading, "", "") if reading.available else
                          ("failed", None, reading.detail, "service_error"))
        except Exception as exc:
            result = ("failed", None, str(exc), "worker_error")
        finally:
            if bus is not None:
                bus.close()
            self._completed.emit(generation, result)

    @Slot(int, object)
    def _receive(self, generation, result):
        if generation != self._generation:
            return  # queued late results cannot overwrite a newer operation
        self.busy = False
        self._thread = None
        if self.status == "running":
            if time.monotonic() >= self._deadline:
                self.status, self.error_code = "timed_out", "deadline"
            else:
                self.status, self.reading, self.error, self.error_code = result
        self._timer.stop()
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self.status == "running":
            self._stop.set()
            self.status, self.error_code = "cancelled", "cancelled"
            self._timer.stop()
            self.changed.emit()

    @Slot()
    def _expired(self):
        remaining = self._deadline - time.monotonic()
        if remaining > 0:
            self._timer.start(max(1, math.ceil(remaining * 1000)))
        elif self.status == "running":
            self._stop.set()
            self.status, self.error_code = "timed_out", "deadline"
            self.changed.emit()
