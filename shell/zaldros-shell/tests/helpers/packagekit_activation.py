# SPDX-License-Identifier: GPL-3.0-or-later
"""Private-bus activation target. Never connects to a host/system bus."""
import os
from pathlib import Path
import sys
import time

backend, directory, mode = sys.argv[1:]
sys.path.insert(0, backend)
from zaldros_backend.testing import MockSystem
from zaldros_backend.wire import Message
from zaldros_backend.connection import Connection
from zaldros_backend.service import ObjectServer

directory = Path(directory)
(directory / str(os.getpid())).write_text("started")
if mode == "fail-start":
    raise SystemExit(23)
if mode == "slow-start":
    time.sleep(0.35)
address = os.environ["DBUS_STARTER_ADDRESS"]
mock = MockSystem(address)
replacement = None
try:
    # Export first, then synchronously acquire the name. Requests queued by activation
    # may arrive during RequestName: production Connection must retain them for process().
    connection = Connection.connect(address)
    mock.servers["org.freedesktop.PackageKit"] = ObjectServer(connection)
    mock._connections.append(connection)
    mock.add_packagekit(updates=2)
    server = mock.service("org.freedesktop.PackageKit")
    manager = server.objects["/org/freedesktop/PackageKit"]["org.freedesktop.PackageKit"]
    transaction = server.objects["/org/freedesktop/PackageKit/Transaction/1"][
        "org.freedesktop.PackageKit.Transaction"]
    original_refresh = transaction.methods["RefreshCache"].handler
    def refresh(force):
        with (directory / "calls.log").open("a") as handle:
            handle.write("RefreshCache\n")
        return original_refresh(force)
    transaction.methods["RefreshCache"].handler = refresh
    original_create = manager.methods["CreateTransaction"].handler
    def create():
        global replacement
        if mode == "replace-before-reply" and replacement is None:
            server.connection.call(Message(destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus", interface="org.freedesktop.DBus", member="ReleaseName",
                signature="s", body=["org.freedesktop.PackageKit"]))
            replacement = MockSystem(address)
            replacement.add_packagekit(updates=99)
        return original_create()
    manager.methods["CreateTransaction"].handler = create
    assert server.request_name("org.freedesktop.PackageKit")
    (directory / "ready").write_text(server.connection.unique_name)
    while not server.connection.closed:
        mock.process(0.005)
        if replacement is not None:
            replacement.process(0.005)
finally:
    mock.close()
    if replacement is not None:
        replacement.close()
