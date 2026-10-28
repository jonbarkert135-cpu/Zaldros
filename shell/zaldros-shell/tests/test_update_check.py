# SPDX-License-Identifier: GPL-3.0-or-later
"""UI/model → worker → real private D-Bus → PackageKit-shaped test service."""
import threading
import time
from types import SimpleNamespace

import pytest
from PySide6.QtTest import QTest
from PySide6.QtCore import QEventLoop, QTimer

from zaldros_backend import Bus, Connection, DBusError
from zaldros_backend.reading import Reading
from zaldros_backend.testing import MockSystem, SessionDaemon, offline_backend
from zaldros_backend.wire import Message, SIGNAL
from zaldros_shell.model import SettingsControls, SettingsTree
from zaldros_shell.settingscontrols import Registry
from zaldros_shell.updatecheck import UpdateCheck

pytestmark = pytest.mark.skipif(not SessionDaemon.available(), reason="dbus-daemon missing")


def wait_for(predicate, timeout=2):
    if predicate():
        return
    # Run a real Qt loop in the test. Repeated QTest.qWait calls can starve Python
    # workers of the GIL; the production Qt loop itself releases it while waiting.
    loop = QEventLoop()
    poll, guard = QTimer(), QTimer()
    poll.timeout.connect(lambda: loop.quit() if predicate() else None)
    guard.setSingleShot(True)
    guard.timeout.connect(loop.quit)
    poll.start(5)
    guard.start(round(timeout * 1000))
    loop.exec()
    poll.stop()
    guard.stop()
    assert predicate()


@pytest.fixture
def rig(qt_app):
    with SessionDaemon() as daemon:
        stop, ready, called = threading.Event(), threading.Event(), threading.Event()
        config = SimpleNamespace(mode="success", calls=[], worker_ids=[], errors=[], create_delay=0)
        def serve():
            mock = MockSystem(daemon.address)
            try:
                mock.add_packagekit(updates=2)
                server = mock.service("org.freedesktop.PackageKit")
                transaction = server.objects["/org/freedesktop/PackageKit/Transaction/1"][
                    "org.freedesktop.PackageKit.Transaction"]
                manager = server.objects["/org/freedesktop/PackageKit"]["org.freedesktop.PackageKit"]
                create_original = manager.methods["CreateTransaction"].handler
                def create_transaction():
                    time.sleep(config.create_delay)
                    return create_original()
                manager.methods["CreateTransaction"].handler = create_transaction
                original = transaction.methods["RefreshCache"].handler
                def refresh(force):
                    mode = config.mode
                    config.calls.append("RefreshCache")
                    called.set()
                    if mode == "hang":
                        time.sleep(0.4)
                    if mode == "delay":
                        time.sleep(0.08)
                    if mode == "silent":
                        return
                    if mode == "denied":
                        raise RuntimeError("Permission denied")
                    if mode == "vanish":
                        server.connection.close()
                        return
                    original(force)
                transaction.methods["RefreshCache"].handler = refresh
                ready.set()
                while not stop.is_set():
                    mock.process(0.005)
            except DBusError:
                if config.mode != "vanish":
                    config.errors.append("unexpected service connection failure")
            finally:
                mock.close()
        server_thread = threading.Thread(target=serve)
        server_thread.start()
        assert ready.wait(2)
        checks = []
        def create(timeout=0.8):
            def factory():
                config.worker_ids.append(threading.get_ident())
                return Bus(connection=Connection.connect(daemon.address, timeout=0.5), timeout=0.5)
            check = UpdateCheck(factory, timeout)
            checks.append(check)
            return check
        try:
            yield SimpleNamespace(create=create, config=config, called=called, address=daemon.address)
        finally:
            for check in checks:
                check.cancel()
                wait_for(lambda: not check.busy)
            stop.set()
            server_thread.join(2)
            assert not server_thread.is_alive()
            assert not config.errors


def test_actual_model_action_runs_in_worker_and_reads_packages_after_finished(rig):
    check = rig.create()
    registry = Registry(backend=offline_backend(), state_provider=check.control_state)
    controls = SettingsControls(registry=registry, update_check=check)
    before = controls.state("updates.available")
    assert not before["available"] and before["value"] is None
    assert controls.activate("updates.check")["kind"] == "action"
    assert check.busy and not controls.state("updates.check")["writable"]
    assert not check.start()  # no repeated-click queue
    wait_for(lambda: not check.busy)
    assert check.status == "succeeded" and check.error_code == ""
    state = controls.state("updates.available")
    assert state["available"] and state["value"] == 2
    assert rig.config.calls == ["RefreshCache"]
    assert rig.config.worker_ids and set(rig.config.worker_ids) != {threading.get_ident()}


@pytest.mark.parametrize("mode,expected", [("denied", "failed"), ("vanish", "failed"),
                                           ("silent", "timed_out"), ("hang", "timed_out")])
def test_failure_timeout_or_daemon_loss_never_becomes_zero_updates(rig, mode, expected):
    check = rig.create(timeout=0.15)
    rig.config.mode = mode
    assert check.start()
    wait_for(lambda: not check.busy)
    assert check.status == expected
    assert check.error_code in ("service_error", "deadline")
    state = check.control_state("updates.available")
    assert not state.available and state.value is None and state.reason


def test_stop_waiting_does_not_claim_remote_rollback_and_late_result_cannot_win(rig):
    check = rig.create()
    rig.config.mode = "hang"
    check.start()
    wait_for(rig.called.is_set)
    check.cancel()
    assert check.status == "cancelled" and check.error_code == "cancelled"
    assert "may still finish" in check.message
    wait_for(lambda: not check.busy)
    assert check.status == "cancelled" and check.reading is None
    old_generation = check._generation
    rig.config.mode = "success"
    assert check.start()
    # Simulate an already queued completion from the previous generation.
    check._receive(old_generation, ("succeeded", Reading.measured(99, "old", "test"), "", ""))
    assert check.busy and check.status == "running" and check.reading is None
    wait_for(lambda: not check.busy)
    assert check.status == "succeeded" and check.reading.value == 2


def test_foreign_finished_signal_cannot_complete_the_transaction(rig):
    check = rig.create(timeout=0.15)
    rig.config.mode = "silent"
    check.start()
    wait_for(rig.called.is_set)
    connection = Connection.connect(rig.address)
    try:
        connection.send(Message(type=SIGNAL, path="/org/freedesktop/PackageKit/Transaction/1",
            interface="org.freedesktop.PackageKit.Transaction", member="Finished",
            signature="uu", body=[1, 0]))
        connection.list_names()
        QTest.qWait(25)
        assert check.status == "running"
        wait_for(lambda: not check.busy)
        assert check.status == "timed_out" and check.reading is None
    finally:
        connection.close()


def test_update_notifications_refresh_only_cached_rows_not_other_services(rig):
    check = rig.create()
    registry = Registry(backend=offline_backend(), state_provider=check.control_state)
    controls = SettingsControls(registry=registry, update_check=check)
    pages = {"update": {"id": "update", "title": "Updates", "parent": "", "entries": [
        {"control": "updates.available", "value": "old", "writable": False},
        {"control": "updates.check", "value": "old", "writable": True}]}}
    tree = SettingsTree(pages=pages, controls=controls)
    original = registry.state
    def guarded(control_id):
        assert control_id.startswith("updates.")
        return original(control_id)
    registry.state = guarded
    controls.activate("updates.check")
    wait_for(lambda: not check.busy)
    assert tree.page("update")["entries"][0]["value"] == check.reading.detail
    assert tree.page("update")["entries"][1]["writable"]


def test_state_reads_and_registry_build_do_not_create_a_worker_or_touch_update_service(rig):
    check = rig.create()
    registry = Registry(backend=offline_backend(), state_provider=check.control_state)
    for _ in range(3):
        assert registry.state("updates.available").value is None
        assert registry.state("updates.check").writable
    assert not rig.config.worker_ids and not rig.config.calls


def test_gui_heartbeat_continues_during_a_slow_service_reply(rig):
    rig.config.mode = "hang"
    check = rig.create(timeout=0.15)
    ticks = [time.monotonic()]
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()
    try:
        check.start()
        wait_for(lambda: not check.busy)
    finally:
        timer.stop()
    assert check.status == "timed_out"
    assert len(ticks) > 5
    assert max(b-a for a,b in zip(ticks,ticks[1:])) < 0.1


def test_backend_uses_one_deadline_for_create_start_and_finished(rig):
    from zaldros_backend.updates import UpdatesFacet
    rig.config.create_delay = 0.08
    rig.config.mode = "delay"
    bus = Bus(connection=Connection.connect(rig.address))
    try:
        started = time.monotonic()
        outcome = UpdatesFacet(bus).refresh(timeout=0.12)
        elapsed = time.monotonic() - started
        assert not outcome.ok
        assert elapsed < 0.22
    finally:
        bus.close()


def test_real_qml_click_starts_check_and_keyboard_can_stop_waiting(rig, qt_app, tmp_path):
    from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
    from PySide6.QtQuick import QQuickView
    from zaldros_shell.app import ASSETS, QML_DIR
    from zaldros_shell.icons import IconProvider
    from zaldros_shell import settingspages
    check = rig.create()
    rig.config.mode = "hang"
    registry = Registry(backend=offline_backend(), state_provider=check.control_state)
    controls = SettingsControls(registry=registry, update_check=check)
    entries = [settingspages.control_entry(registry, key, key) for key in
               ("updates.available", "updates.check")]
    pages = settingspages.to_variant({"update": settingspages.Page("update", "Updates", "sync", "", entries)})
    tree = SettingsTree(pages=pages, controls=controls)
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    view.engine().addImageProvider("zaldrosicon", IconProvider(ASSETS / "icons/fluent"))
    view.engine().rootContext().setContextProperty("settingsControls", controls)
    view.setInitialProperties({"tree": tree, "stack": ["update"]})
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "apps/Settings.qml")))
    assert view.status() == QQuickView.Status.Ready, view.errors()
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(1200, 760)
    view.show()
    assert QTest.qWaitForWindowExposed(view)
    def find_visual(item, name):
        if item.objectName() == name:
            return item
        for child in item.childItems():
            found = find_visual(child, name)
            if found is not None:
                return found
        return None
    try:
        root = view.rootObject()
        wait_for(lambda: find_visual(root, "updates.check") is not None)
        card = find_visual(root, "updates.check")
        point = card.mapToScene(QPointF(20, card.height()/2))
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(round(point.x()), round(point.y())))
        assert check.busy, {"width": card.width(), "position": point,
                            "disabled": card.property("disabled"), "visible": card.isVisible()}
        wait_for(rig.called.is_set)
        stop_button = find_visual(root, "stopUpdateCheck")
        assert stop_button.property("enabled")
        stop_button.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Space)
        assert check.status == "cancelled"
        wait_for(lambda: not check.busy)
        assert not controls.state("updates.available")["available"]
        view.grabWindow().save(str(tmp_path / "update-check-cancelled.png"))
    finally:
        view.close()
        view.deleteLater()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 1e20])
def test_invalid_deadline_does_not_start_worker(timeout):
    check = UpdateCheck(timeout=timeout)
    with pytest.raises(ValueError):
        check.start()
    assert not check.busy


def test_worker_start_failure_is_reported_without_a_stuck_busy_state(qt_app, monkeypatch):
    def fail_start(_thread):
        raise RuntimeError("worker unavailable")
    monkeypatch.setattr(threading.Thread, "start", fail_start)
    check = UpdateCheck()
    assert not check.start()
    assert not check.busy and check.status == "failed" and check.error_code == "worker_error"
    assert not check.control_state("updates.available").available
