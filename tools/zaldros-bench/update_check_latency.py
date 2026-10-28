#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure Qt heartbeat gaps while a private PackageKit-shaped service is slow.

This measures one update-check path, not whole Settings startup, VM frame pacing,
RAM or real repository/network performance. Use --backend-root for a frozen baseline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[2]


def measure(mode, backend_root):
    sys.path[:0] = [str(backend_root), str(REPO / "shell/zaldros-shell")]
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication, QTimer, Qt
    from zaldros_backend import Bus, Connection
    from zaldros_backend.testing import MockSystem, SessionDaemon
    from zaldros_backend.updates import UpdatesFacet
    from zaldros_shell.updatecheck import UpdateCheck
    app = QCoreApplication.instance() or QCoreApplication([])
    ready, stop = threading.Event(), threading.Event()
    ticks, result = [], {"mode": mode, "backend_root": str(backend_root)}
    with SessionDaemon() as daemon:
        def serve():
            mock = MockSystem(daemon.address)
            try:
                mock.add_packagekit()
                server = mock.service("org.freedesktop.PackageKit")
                interface = server.objects["/org/freedesktop/PackageKit/Transaction/1"][
                    "org.freedesktop.PackageKit.Transaction"]
                method = interface.methods["RefreshCache"]
                original = method.handler
                method.handler = lambda force: (time.sleep(0.45), original(force))[-1]
                ready.set()
                while not stop.is_set():
                    mock.process(0.005)
            finally:
                mock.close()
        server_thread = threading.Thread(target=serve)
        server_thread.start()
        assert ready.wait(2)
        def factory():
            return Bus(connection=Connection.connect(daemon.address, timeout=0.5))
        check = UpdateCheck(factory, timeout=0.25)
        def invoke():
            if mode == "worker":
                check.start()
            else:
                bus = factory()
                try:
                    outcome = UpdatesFacet(bus).refresh(timeout=0.25)
                    result["call_ok"] = outcome.ok
                finally:
                    bus.close()
        heartbeat, guard = QTimer(), QTimer()
        heartbeat.setTimerType(Qt.TimerType.PreciseTimer)
        heartbeat.timeout.connect(lambda: ticks.append(time.monotonic()))
        guard.setSingleShot(True)
        guard.timeout.connect(app.quit)
        heartbeat.start(5)
        guard.start(750)
        QTimer.singleShot(40, invoke)
        try:
            app.exec()
            assert not check.busy
        finally:
            heartbeat.stop()
            guard.stop()
            check.cancel()
            stop.set()
            server_thread.join(2)
            assert not server_thread.is_alive()
        assert len(ticks) > 2
        result.update(ui_latency_ms=round(max(b-a for a,b in zip(ticks,ticks[1:]))*1000, 3),
                      ticks=len(ticks), heartbeat_ms=5, service_delay_ms=450, deadline_ms=250,
                      operation_status=check.status,
                      scope="private real D-Bus / Qt; test service; one update-check path")
        module = Path(sys.modules["zaldros_backend.updates"].__file__)
        result["metrics"] = {"ui_latency_ms": result["ui_latency_ms"]}
        result.update(loaded_updates_module=str(module),
                      loaded_updates_sha256=hashlib.sha256(module.read_bytes()).hexdigest())
        if mode == "worker":
            assert check.status == "timed_out"
        else:
            assert result["call_ok"] is False
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("synchronous", "worker"), required=True)
    parser.add_argument("--backend-root", type=Path, default=REPO / "backend")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.mode, args.backend_root)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
