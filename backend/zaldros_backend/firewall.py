"""The firewall.

Two implementations exist on the machines Zaldros can run on and they are nothing alike:

* **ufw** — what Ubuntu ships. A CLI over nftables with *no* D-Bus API and no polkit action of its
  own, so the state is read from `/etc/ufw/ufw.conf` (the file `ufw enable` itself rewrites) plus
  the unit state from systemd, and a change is made by running `ufw` through `pkexec`. That means
  a password prompt, which is exactly what turning a firewall off should cost.
* **firewalld** — has a real bus API and its own polkit actions. When it is running it wins,
  because then ufw is not the thing holding the rules.

If neither is installed the facet says so. It never reports "off" for "not installed": those are
different facts and a user who is told the wrong one makes the wrong decision.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .bus import Bus, Result
from .catalog import Firewall
from .reading import Reading

NOT_INSTALLED = "брандмауэр не установлен"
UFW = "ufw"
PKEXEC = "pkexec"


class FirewallFacet:
    def __init__(self, system_bus: Bus, conf_path: str = Firewall.UFW_CONF,
                 runner=subprocess.run, which=shutil.which) -> None:
        self._bus = system_bus
        self._conf = Path(conf_path)
        self._run = runner
        self._which = which

    # -- reading -----------------------------------------------------------------------------
    def status(self) -> Reading:
        firewalld = self._firewalld_status()
        if firewalld is not None:
            return firewalld
        ufw = self._ufw_status()
        if ufw is not None:
            return ufw
        return Reading.missing(NOT_INSTALLED, Firewall.UFW_CONF)

    def _firewalld_status(self) -> Reading | None:
        if not self._bus.has_service(Firewall.FIREWALLD_SERVICE):
            return None
        state = self._bus.get(Firewall.FIREWALLD_SERVICE, Firewall.FIREWALLD_PATH,
                              Firewall.FIREWALLD_IFACE, "state")
        running = state.ok and str(state.value).upper() == "RUNNING"
        zone = self._bus.call_one(Firewall.FIREWALLD_SERVICE, Firewall.FIREWALLD_PATH,
                                  Firewall.FIREWALLD_IFACE, "getDefaultZone")
        return Reading.measured(None, "включён" if running else "выключен",
                                Firewall.FIREWALLD_SERVICE, enabled=running, backend="firewalld",
                                writable=True, zone=str(zone.value) if zone.ok else "")

    def _ufw_status(self) -> Reading | None:
        try:
            text = self._conf.read_text(encoding="utf-8")
        except OSError:
            return None
        enabled = False
        for line in text.splitlines():
            key, _, value = line.strip().partition("=")
            if key.strip().upper() == "ENABLED":
                enabled = value.strip().strip('"').lower() in ("yes", "true", "1")
        writable = bool(self._which(UFW) and self._which(PKEXEC))
        return Reading.measured(None, "включён" if enabled else "выключен", str(self._conf),
                                enabled=enabled, backend="ufw", writable=writable,
                                zone="")

    # -- writing -----------------------------------------------------------------------------
    def set_enabled(self, enabled: bool) -> Result:
        current = self.status()
        if not current.available:
            return Result.bad(NOT_INSTALLED, current.source)
        if current.get("backend") == "firewalld":
            # firewalld is a systemd unit; enabling the *panic* mode is not the same thing, so the
            # unit is what gets started and stopped, through systemd's own polkit action.
            from .catalog import Systemd
            method = "StartUnit" if enabled else "StopUnit"
            return self._bus.call(Systemd.SERVICE, Systemd.PATH, Systemd.MANAGER, method, "ss",
                                  ["firewalld.service", Systemd.REPLACE], timeout=30.0)
        if not current.get("writable"):
            return Result.bad(f"{UFW} or {PKEXEC} is missing", str(self._conf))
        return self._pkexec_ufw("enable" if enabled else "disable")

    def _pkexec_ufw(self, argument: str) -> Result:
        try:
            done = self._run([PKEXEC, UFW, argument], capture_output=True, text=True,
                             timeout=120.0)
        except (OSError, subprocess.SubprocessError) as exc:
            return Result.bad(str(exc), UFW)
        if done.returncode != 0:
            return Result.bad((done.stderr or done.stdout or "").strip() or "pkexec refused", UFW)
        return Result.good(True, UFW)
