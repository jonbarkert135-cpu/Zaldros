# SPDX-License-Identifier: GPL-3.0-or-later
"""Re-run the bundled QtDBus candidate probe using the shell Python environment."""
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtDBus import (QDBusArgument, QDBusConnection, QDBusMessage,
                           QDBusPendingCallWatcher, QDBusUnixFileDescriptor)
from zaldros_backend.service import Interface
from zaldros_backend.testing import MockSystem, SessionDaemon

app = QCoreApplication([])
ready, stop = threading.Event(), threading.Event()
ticks, results = [], {}
with SessionDaemon() as daemon:
    def serve():
        mock = MockSystem(daemon.address)
        try:
            mock.add_upower()
            iface = Interface("org.zaldros.SlowProbe")
            iface.add_method("Slow", "", "s", lambda: (time.sleep(0.45) or "late"))
            mock.service("org.zaldros.SlowProbe").add("/org/zaldros/SlowProbe", iface)
            ready.set()
            while not stop.is_set():
                mock.process(0.005)
        finally:
            mock.close()
    thread = threading.Thread(target=serve)
    thread.start()
    assert ready.wait(2)
    connection = QDBusConnection.connectToBus(daemon.address, "zaldros-qtdbus-probe")
    assert connection.isConnected()
    message = QDBusMessage.createMethodCall("org.freedesktop.UPower",
        "/org/freedesktop/UPower/devices/DisplayDevice", "org.freedesktop.DBus.Properties", "GetAll")
    message.setArguments(["org.freedesktop.UPower.Device"])
    slow = QDBusMessage.createMethodCall("org.zaldros.SlowProbe", "/org/zaldros/SlowProbe",
                                        "org.zaldros.SlowProbe", "Slow")
    watches = [QDBusPendingCallWatcher(connection.asyncCall(message, 250)),
               QDBusPendingCallWatcher(connection.asyncCall(slow, 250))]
    def record(index, watcher):
        reply = watcher.reply()
        arguments = reply.arguments()
        converted = [value.asVariant() if isinstance(value, QDBusArgument) else value
                     for value in arguments]
        results[str(index)] = {"signature": reply.signature(), "error": reply.errorMessage(),
            "argument_types": [type(value).__name__ for value in arguments],
            "converted_types": [type(value).__name__ for value in converted],
            "native_dictionary": bool(converted and isinstance(converted[0], dict))}
    for index, watcher in enumerate(watches):
        watcher.finished.connect(lambda watcher, index=index: record(index, watcher))
    heartbeat, guard = QTimer(), QTimer()
    heartbeat.setTimerType(Qt.TimerType.PreciseTimer)
    heartbeat.timeout.connect(lambda: ticks.append(time.monotonic()))
    heartbeat.start(5)
    guard.setSingleShot(True)
    guard.timeout.connect(app.quit)
    guard.start(700)
    try:
        app.exec()
    finally:
        heartbeat.stop()
        QDBusConnection.disconnectFromBus("zaldros-qtdbus-probe")
        stop.set()
        thread.join(2)
        assert not thread.is_alive()
read_fd, write_fd = os.pipe()
descriptor = QDBusUnixFileDescriptor(read_fd)
os.close(read_fd)
os.close(write_fd)
results.update(pyside=importlib.metadata.version("PySide6-Essentials"),
    license_metadata=importlib.metadata.metadata("PySide6-Essentials").get("License"),
    unix_fd_wrapper_valid=descriptor.isValid(), unix_fd_bus_roundtrip="UNRUN",
    ui_latency_ms=round(max(b-a for a,b in zip(ticks,ticks[1:]))*1000,3),
    scope="bundled QtDBus probe; automatic GetAll conversion and one async timeout only")
assert results["0"]["signature"] == "a{sv}" and results["1"]["error"]
print(json.dumps(results, indent=2))
