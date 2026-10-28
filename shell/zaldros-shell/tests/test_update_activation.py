# SPDX-License-Identifier: GPL-3.0-or-later
"""Real dbus-daemon service-file activation; the child is a test PackageKit."""
import os
from pathlib import Path
import shlex
import signal
import sys
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QGuiApplication

import zaldros_backend
from zaldros_backend import Bus, Connection
from zaldros_backend.testing import SessionDaemon
from zaldros_backend.updates import UpdatesFacet
from zaldros_backend.wire import Message
from zaldros_shell.updatecheck import UpdateCheck

NAME = "org.freedesktop.PackageKit"
HELPER = Path(__file__).with_name("helpers") / "packagekit_activation.py"
pytestmark = pytest.mark.skipif(not SessionDaemon.available(), reason="dbus-daemon missing")


@pytest.fixture
def qt_app():
    return QGuiApplication.instance() or QGuiApplication([])


def until(predicate, seconds=3):
    if predicate():
        return
    loop, poll, deadline = QEventLoop(), QTimer(), QTimer()
    poll.timeout.connect(lambda: loop.quit() if predicate() else None)
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    poll.start(5)
    deadline.start(round(seconds * 1000))
    loop.exec()
    poll.stop()
    deadline.stop()
    assert predicate()


@pytest.fixture
def activation(tmp_path, qt_app):
    services, processes = tmp_path / "service files", tmp_path / "processes"
    services.mkdir()
    processes.mkdir()
    checks = []
    with SessionDaemon(str(services)) as daemon:
        observer = Connection.connect(daemon.address)
        def register(mode="success"):
            command = shlex.join([sys.executable, str(HELPER),
                str(Path(zaldros_backend.__file__).resolve().parent.parent), str(processes), mode])
            (services / (NAME + ".service")).write_text(
                f"[D-BUS Service]\nName={NAME}\nExec={command}\n")
            # Let the daemon consume the directory notification before a query.
            until(lambda: NAME in observer.call(Message(destination='org.freedesktop.DBus',
                path='/org/freedesktop/DBus', interface='org.freedesktop.DBus',
                member='ListActivatableNames')).body[0])
        def check(timeout=2):
            obj = UpdateCheck(lambda: Bus(connection=Connection.connect(daemon.address)), timeout)
            checks.append(obj)
            return obj
        try:
            yield SimpleNamespace(register=register, check=check, observer=observer,
                                  address=daemon.address, processes=processes)
        finally:
            for obj in checks:
                obj.cancel()
                until(lambda: not obj.busy)
            for path in processes.iterdir():
                if path.name.isdigit():
                    try:
                        os.kill(int(path.name), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            observer.close()


def test_inactive_installed_service_is_activated_and_read_back(activation):
    activation.register()
    assert not activation.observer.name_has_owner(NAME)
    obj = activation.check()
    obj.start()
    until(lambda: not obj.busy)
    assert obj.status == "succeeded" and obj.reading.value == 2
    assert activation.observer.name_has_owner(NAME)
    assert (activation.processes / "calls.log").read_text().splitlines() == ["RefreshCache"]


@pytest.mark.parametrize("mode", [None, "fail-start"])
def test_missing_or_failed_activation_reports_failure_not_zero(activation, mode):
    if mode:
        activation.register(mode)
    obj = activation.check()
    obj.start()
    until(lambda: not obj.busy)
    assert obj.status == "failed" and obj.reading is None
    assert not obj.control_state("updates.available").available


@pytest.mark.parametrize("stop", ["deadline", "cancel"])
def test_activation_keeps_deadline_or_cancellation_and_can_retry(activation, stop):
    activation.register("slow-start")
    obj = activation.check(timeout=0.1 if stop == "deadline" else 2)
    obj.start()
    if stop == "cancel":
        until(lambda: any(p.name.isdigit() for p in activation.processes.iterdir()))
        obj.cancel()
    until(lambda: not obj.busy)
    assert obj.status == ("timed_out" if stop == "deadline" else "cancelled")
    assert obj.reading is None
    until(lambda: activation.observer.name_has_owner(NAME))
    obj.timeout = 2
    assert obj.start()
    until(lambda: not obj.busy)
    assert obj.status == "succeeded" and obj.reading.value == 2
    assert len([p for p in activation.processes.iterdir() if p.name.isdigit()]) == 1
    assert (activation.processes / "calls.log").read_text().splitlines() == ["RefreshCache"]


def test_service_exit_then_new_check_activates_a_new_process(activation):
    activation.register()
    obj = activation.check()
    for attempt in range(2):
        assert obj.start()
        until(lambda: not obj.busy)
        assert obj.status == "succeeded" and obj.reading.value == 2
        if attempt == 0:
            pid = next(int(p.name) for p in activation.processes.iterdir() if p.name.isdigit())
            os.kill(pid, signal.SIGTERM)
            until(lambda: not activation.observer.name_has_owner(NAME))
    assert len([p for p in activation.processes.iterdir() if p.name.isdigit()]) == 2


def test_owner_replacement_before_create_reply_never_reports_success(activation):
    activation.register("replace-before-reply")
    # Start the service explicitly to reproduce the pre-existing ownership race
    # independently of the inactive-service activation defect.
    activation.observer.call(Message(destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus", member="StartServiceByName", signature="su", body=[NAME,0]))
    bus = Bus(connection=Connection.connect(activation.address))
    try:
        result = UpdatesFacet(bus).refresh(timeout=1)
        assert not result.ok
        assert not (activation.processes / "calls.log").exists()
    finally:
        bus.close()
