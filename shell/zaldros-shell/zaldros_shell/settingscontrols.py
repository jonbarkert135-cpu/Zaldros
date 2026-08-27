"""Every Settings control that really changes something, in one registry.

A row in Settings used to be a picture of a control. This file is the other half: for each control
id there is a `read()` that asks the system what the state *is*, and a `write()` that asks the
system to change it. The UI does nothing else — it never stores a value of its own, and after a
write it re-reads, so what is drawn is what the machine answered, not what the click intended.

    click ──► Control.write ──► zaldros_backend ──► the Linux service
                                       │
    row ◄── Control.read ◄─────────────┘   (re-read after every write)

Four kinds cover the whole page tree:

* `switch` — an on/off row.
* `choice` — a value with a list of options; Settings opens a nested page of them. Sliders are
  modelled as a choice over discrete steps rather than a new widget, so brightness, volume and
  pointer speed write real values today instead of waiting for a slider component.
* `action` — a row that does something once (check for updates, restart the network).
* `info` — a reading with no control behind it. It is *listed here anyway*, so that "this row is
  read-only" is a recorded fact rather than an omission.

Every state carries `available`, `writable` and a `reason`. A control that cannot work on this
machine says why, in the interface's language, and Settings shows the reason where the value would
be. Nothing here ever invents a plausible default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import prefs, system

SWITCH, CHOICE, ACTION, INFO = "switch", "choice", "action", "info"

NO_HARDWARE = "устройство не найдено"
NO_SERVICE = "служба недоступна"
READ_ONLY = "только чтение"


@dataclass(frozen=True)
class State:
    """What one control is right now."""

    kind: str
    available: bool = False
    value: Any = None
    detail: str = ""
    writable: bool = False
    reason: str = ""
    choices: list[dict] = field(default_factory=list)
    source: str = ""

    def as_variant(self) -> dict:
        return {"kind": self.kind, "available": self.available, "value": self.value,
                "detail": self.detail, "writable": self.writable, "reason": self.reason,
                "choices": list(self.choices), "source": self.source}


@dataclass(frozen=True)
class Control:
    id: str
    kind: str
    title: str
    reader: Callable[[], State]
    writer: Callable[[Any], tuple[bool, str]] | None = None

    def read(self) -> State:
        try:
            return self.reader()
        except Exception as exc:                     # noqa: BLE001 - a dead row, never a crash
            return State(self.kind, False, None, "", False, f"ошибка чтения: {exc}")

    def write(self, value: Any) -> tuple[bool, str]:
        if self.writer is None:
            return False, READ_ONLY
        try:
            return self.writer(value)
        except Exception as exc:                     # noqa: BLE001
            return False, f"ошибка записи: {exc}"


def _ok(result) -> tuple[bool, str]:
    """Turn a backend `Result` into the pair the UI needs."""
    if getattr(result, "ok", False):
        return True, ""
    return False, getattr(result, "error", "") or NO_SERVICE


def _percent_choices(values=(0, 20, 40, 60, 80, 100)) -> list[dict]:
    return [{"id": str(value), "title": f"{value} %"} for value in values]


class Registry:
    """All controls, built against one backend. Rebuilt cheaply; holds no state of its own."""

    def __init__(self, backend=None, home: Path | None = None) -> None:
        self._backend = backend if backend is not None else system.backend()
        self._home = home
        self._controls: dict[str, Control] = {}
        self._build()

    # -- public API ----------------------------------------------------------------------------
    def __contains__(self, control_id: str) -> bool:
        return control_id in self._controls

    def get(self, control_id: str) -> Control | None:
        return self._controls.get(control_id)

    def ids(self) -> list[str]:
        return sorted(self._controls)

    def state(self, control_id: str) -> State:
        control = self._controls.get(control_id)
        if control is None:
            return State(INFO, False, None, "", False, "нет такого параметра")
        return control.read()

    def set(self, control_id: str, value: Any) -> State:
        """Write, then read back. The returned state is the machine's answer, not the request."""
        control = self._controls.get(control_id)
        if control is None:
            return State(INFO, False, None, "", False, "нет такого параметра")
        ok, error = control.write(value)
        state = control.read()
        if ok:
            return state
        return State(state.kind, state.available, state.value, state.detail, state.writable,
                     error or state.reason, state.choices, state.source)

    def toggle(self, control_id: str) -> State:
        state = self.state(control_id)
        if state.kind != SWITCH or not state.writable:
            return state
        return self.set(control_id, not bool(state.value))

    def invoke(self, control_id: str) -> State:
        return self.set(control_id, True)

    # -- registration ----------------------------------------------------------------------------
    def _add(self, control_id: str, kind: str, title: str, reader, writer=None) -> None:
        self._controls[control_id] = Control(control_id, kind, title, reader, writer)

    def _build(self) -> None:
        self._build_prefs()
        self._build_display()
        self._build_sound()
        self._build_network()
        self._build_bluetooth()
        self._build_power()
        self._build_input()
        self._build_time_language()
        self._build_privacy()
        self._build_accounts()
        self._build_apps()
        self._build_storage()
        self._build_updates()

    # -- shell preferences ---------------------------------------------------------------------
    def _build_prefs(self) -> None:
        """The switches that change the shell itself. Real state, stored on disk, applied live."""
        titles = {
            "taskbar.search": "Поиск на панели задач",
            "taskbar.widgets": "Виджеты",
            "taskbar.taskview": "Представление задач",
            "taskbar.clock": "Часы",
            "visual.transparency": "Эффекты прозрачности",
            "visual.animations": "Анимация",
            "start.recent": "Недавние файлы в Пуске",
            "notifications.banners": "Уведомления приложений",
            "notifications.dnd": "Не беспокоить",
            "notifications.sound": "Звук уведомлений",
            "privacy.recent_files": "Журнал недавних файлов",
            "clipboard.history": "Журнал буфера обмена",
        }
        def write(key: str, value) -> tuple[bool, str]:
            stored = prefs.set_value(key, bool(value), self._home)
            return stored, "" if stored else "этот переключатель не реализован"

        for key in prefs.DEFAULTS:
            self._add(f"pref:{key}", SWITCH, titles.get(key, key),
                      lambda key=key: State(SWITCH, True, prefs.load(self._home)[key], "", True,
                                            "", [], str(prefs.config_path(self._home))),
                      lambda value, key=key: write(key, value))

    # -- display -----------------------------------------------------------------------------
    def _outputs(self) -> list:
        return self._backend.display.outputs()

    def _primary_output(self):
        outputs = [output for output in self._outputs() if output.get("enabled")]
        if not outputs:
            return None
        for output in outputs:
            if output.get("primary"):
                return output
        return outputs[0]

    def _build_display(self) -> None:
        def resolution() -> State:
            output = self._primary_output()
            if output is None:
                return State(CHOICE, False, None, "", False, "экраны не определены")
            modes = output.get("modes", [])
            current = f"{output.get('width')}x{output.get('height')}"
            return State(CHOICE, True, current, current, bool(modes), "" if modes else NO_HARDWARE,
                         [{"id": f"{w}x{h}", "title": f"{w} × {h}"} for w, h in modes],
                         output.detail)

        def set_resolution(value) -> tuple[bool, str]:
            output = self._primary_output()
            if output is None:
                return False, "экраны не определены"
            width, _, height = str(value).partition("x")
            return _ok(self._backend.display.set_output_mode(output.detail, int(width),
                                                             int(height)))

        self._add("display.resolution", CHOICE, "Разрешение экрана", resolution, set_resolution)

        def refresh() -> State:
            output = self._primary_output()
            if output is None:
                return State(CHOICE, False, None, "", False, "экраны не определены")
            rates = output.get("refresh_rates", [])
            current = output.get("refresh", 0)
            title = f"{current:g} Гц" if current else "–"
            return State(CHOICE, bool(current), f"{current:g}", title, bool(rates),
                         "" if rates else "частота не сообщается",
                         [{"id": f"{rate:g}", "title": f"{rate:g} Гц"} for rate in rates],
                         output.detail)

        def set_refresh(value) -> tuple[bool, str]:
            output = self._primary_output()
            if output is None:
                return False, "экраны не определены"
            return _ok(self._backend.display.set_output_mode(
                output.detail, int(output.get("width", 0)), int(output.get("height", 0)),
                float(value)))

        self._add("display.refresh", CHOICE, "Частота обновления", refresh, set_refresh)

        def scale() -> State:
            output = self._primary_output()
            if output is None:
                return State(CHOICE, False, None, "", False, "экраны не определены")
            current = float(output.get("scale", 1) or 1)
            return State(CHOICE, True, f"{current:g}", f"{round(current * 100)} %", True, "",
                         [{"id": f"{value:g}", "title": f"{round(value * 100)} %"}
                          for value in (1.0, 1.25, 1.5, 1.75, 2.0)], output.detail)

        def set_scale(value) -> tuple[bool, str]:
            output = self._primary_output()
            if output is None:
                return False, "экраны не определены"
            return _ok(self._backend.display.set_output_scale(output.detail, float(value)))

        self._add("display.scale", CHOICE, "Масштаб интерфейса", scale, set_scale)

        def brightness() -> State:
            reading = self._backend.display.brightness()
            if not reading.available:
                return State(CHOICE, False, None, "", False, reading.detail, [], reading.source)
            writable = bool(reading.get("writable"))
            return State(CHOICE, True, str(reading.value), f"{reading.value} %", writable,
                         "" if writable else READ_ONLY, _percent_choices(), reading.source)

        self._add("display.brightness", CHOICE, "Яркость",
                  brightness,
                  lambda value: _ok(self._backend.display.set_brightness(int(value))))

        # Multiple monitors: one switch per connected screen, created from what is plugged in.
        for output in self._outputs():
            name = output.detail
            self._add(f"display.output.{name}", SWITCH, f"Экран {name}",
                      lambda name=name: self._output_state(name),
                      lambda value, name=name: _ok(
                          self._backend.display.set_output_enabled(name, bool(value))))

    def _output_state(self, name: str) -> State:
        for output in self._outputs():
            if output.detail == name:
                detail = (f"{output.get('width')}×{output.get('height')} @ "
                          f"{output.get('refresh'):g} Гц")
                return State(SWITCH, True, bool(output.get("enabled")), detail, True, "", [],
                             output.source)
        return State(SWITCH, False, None, "", False, "экран отключён от машины")

    # -- sound -------------------------------------------------------------------------------
    def _build_sound(self) -> None:
        def volume() -> State:
            reading = self._backend.audio.volume()
            if not reading.available:
                return State(CHOICE, False, None, "", False, reading.detail, [], reading.source)
            return State(CHOICE, True, str(reading.value), f"{reading.value} %", True, "",
                         _percent_choices(), reading.source)

        self._add("sound.volume", CHOICE, "Громкость", volume,
                  lambda value: _ok(self._backend.audio.set_volume(int(value))))

        def muted() -> State:
            reading = self._backend.audio.volume()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            return State(SWITCH, True, bool(reading.get("muted")),
                         "звук выключен" if reading.get("muted") else "звук включён", True, "",
                         [], reading.source)

        self._add("sound.muted", SWITCH, "Отключить звук", muted,
                  lambda value: _ok(self._backend.audio.set_muted(bool(value))))

        def output_device() -> State:
            outputs = self._backend.audio.outputs()
            if not outputs:
                return State(CHOICE, False, None, "", False, "устройства вывода не найдены")
            current = next((output for output in outputs if output.get("default")), outputs[0])
            # `value` of an output reading is the WirePlumber node id — what set-default takes.
            return State(CHOICE, True, str(current.value), current.detail, True, "",
                         [{"id": str(output.value), "title": output.detail}
                          for output in outputs], current.source)

        self._add("sound.output", CHOICE, "Устройство вывода", output_device,
                  lambda value: _ok(self._backend.audio.set_default_output(int(value))))

        def microphone() -> State:
            reading = self._backend.audio.microphone()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            muted_now = bool(reading.get("muted"))
            return State(SWITCH, True, muted_now,
                         f"{reading.value} %" + (", выключен" if muted_now else ""), True, "",
                         [], reading.source)

        self._add("sound.microphone_muted", SWITCH, "Отключить микрофон", microphone,
                  lambda value: _ok(self._backend.audio.set_microphone_muted(bool(value))))

    # -- network -----------------------------------------------------------------------------
    def _build_network(self) -> None:
        def wifi() -> State:
            reading = self._backend.network.wifi_enabled()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            status = self._backend.network.status()
            return State(SWITCH, True, bool(reading.get("enabled")),
                         status.detail if status.available else reading.detail, True, "", [],
                         reading.source)

        self._add("network.wifi", SWITCH, "Wi-Fi", wifi,
                  lambda value: _ok(self._backend.network.set_wifi_enabled(bool(value))))

        def networking() -> State:
            reading = self._backend.network.networking_enabled()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            status = self._backend.network.status()
            return State(SWITCH, True, bool(reading.get("enabled")),
                         status.detail if status.available else "", True, "", [],
                         reading.source)

        self._add("network.enabled", SWITCH, "Сеть", networking,
                  lambda value: _ok(self._backend.network.set_networking_enabled(bool(value))))

        def airplane() -> State:
            wifi_reading = self._backend.network.wifi_enabled()
            adapter = self._backend.bluetooth.adapter()
            radios = [reading for reading in (wifi_reading, adapter) if reading.available]
            if not radios:
                return State(SWITCH, False, None, "", False, "радиомодулей нет")
            wifi_on = bool(wifi_reading.available and wifi_reading.get("enabled"))
            bluetooth_on = bool(adapter.available and adapter.get("powered"))
            return State(SWITCH, True, not (wifi_on or bluetooth_on),
                         "Wi-Fi и Bluetooth выключены" if not (wifi_on or bluetooth_on) else "",
                         True, "", [], "NetworkManager + BlueZ")

        def set_airplane(value) -> tuple[bool, str]:
            """One switch, two radios: on means both off. Reports what actually happened."""
            radio_on = not bool(value)
            errors = []
            for result in (self._backend.network.set_wifi_enabled(radio_on),
                           self._backend.bluetooth.set_powered(radio_on)):
                if not result.ok:
                    errors.append(result.error)
            return (not errors), "; ".join(errors)

        self._add("network.airplane", SWITCH, "Режим «в самолёте»", airplane, set_airplane)

        self._add("network.scan", ACTION, "Искать сети",
                  lambda: State(ACTION, True, None, "", True, "", [], "NetworkManager"),
                  lambda _value: _ok(self._backend.network.request_scan()))

        def ethernet() -> State:
            wired = [device for device in self._backend.network.devices()
                     if device.get("kind") == "ethernet"]
            if not wired:
                return State(INFO, False, None, "", False, "проводных адаптеров нет")
            names = ", ".join(f"{device.detail} — {device.get('state', '')}"
                              for device in wired)
            return State(INFO, True, len(wired), names, False, READ_ONLY, [], "NetworkManager")

        self._add("network.ethernet", INFO, "Ethernet", ethernet)

    # -- bluetooth ---------------------------------------------------------------------------
    def _build_bluetooth(self) -> None:
        def adapter() -> State:
            reading = self._backend.bluetooth.adapter()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            return State(SWITCH, True, bool(reading.get("powered")), reading.detail, True, "",
                         [], reading.source)

        self._add("bluetooth.power", SWITCH, "Bluetooth", adapter,
                  lambda value: _ok(self._backend.bluetooth.set_powered(bool(value))))

        def discovery() -> State:
            reading = self._backend.bluetooth.adapter()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            return State(SWITCH, True, bool(reading.get("discovering")), "", True, "", [],
                         reading.source)

        self._add("bluetooth.discovery", SWITCH, "Поиск устройств", discovery,
                  lambda value: _ok(self._backend.bluetooth.start_discovery() if value
                                    else self._backend.bluetooth.stop_discovery()))

    # -- power, battery and recovery -------------------------------------------------------------
    def _build_power(self) -> None:
        def battery() -> State:
            reading = self._backend.power.battery()
            if not reading.available:
                return State(INFO, False, None, "", False, reading.detail, [], reading.source)
            return State(INFO, True, reading.value, f"{reading.value} % — {reading.detail}",
                         False, READ_ONLY, [], reading.source)

        self._add("power.battery", INFO, "Состояние батареи", battery)

        for action, title in (("suspend", "Спящий режим"), ("hibernate", "Гибернация"),
                              ("reboot", "Перезагрузка"), ("power_off", "Выключение")):
            def state(action=action) -> State:
                allowed = self._backend.power.capabilities().get(action.replace("_", ""), False)
                return State(ACTION, allowed, None, "", allowed,
                             "" if allowed else "система этого не умеет", [], "logind")

            self._add(f"power.{action}", ACTION, title, state,
                      lambda _value, action=action: _ok(getattr(self._backend.power, action)()))

        def firmware() -> State:
            reading = self._backend.power.firmware_setup()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            return State(SWITCH, True, bool(reading.get("enabled")), reading.detail, True, "",
                         [], reading.source)

        self._add("recovery.firmware_setup", SWITCH, "Открыть параметры UEFI при перезагрузке",
                  firmware,
                  lambda value: _ok(self._backend.power.set_firmware_setup(bool(value))))

    # -- keyboard, mouse, touchpad -----------------------------------------------------------
    def _build_input(self) -> None:
        options = (
            ("mouse.left_handed", "pointer", "left_handed", SWITCH, "Основная кнопка — правая"),
            ("mouse.natural_scroll", "pointer", "natural_scroll", SWITCH, "Обратная прокрутка"),
            ("mouse.middle_emulation", "pointer", "middle_emulation", SWITCH,
             "Средняя кнопка эмуляцией"),
            ("mouse.acceleration", "pointer", "acceleration", CHOICE, "Скорость указателя"),
            ("touchpad.enabled", "touchpad", "enabled", SWITCH, "Сенсорная панель"),
            ("touchpad.tap_to_click", "touchpad", "tap_to_click", SWITCH, "Касание = щелчок"),
            ("touchpad.natural_scroll", "touchpad", "natural_scroll", SWITCH,
             "Обратная прокрутка"),
            ("touchpad.disable_while_typing", "touchpad", "disable_while_typing", SWITCH,
             "Отключать при наборе"),
            ("touchpad.acceleration", "touchpad", "acceleration", CHOICE, "Скорость указателя"),
        )
        for control_id, kind, option, control_kind, title in options:
            self._add(control_id, control_kind, title,
                      lambda kind=kind, option=option, control_kind=control_kind:
                          self._input_state(kind, option, control_kind),
                      lambda value, kind=kind, option=option, control_kind=control_kind:
                          _ok(self._backend.input.set_for_kind(
                              kind, option,
                              bool(value) if control_kind == SWITCH else float(value))))

        def keyboard_layout() -> State:
            layouts, current = self._backend.session.layouts()
            if not layouts:
                return State(CHOICE, False, None, "", False, "раскладки не сообщаются")
            index = current if current is not None else 0
            return State(CHOICE, True, str(index),
                         layouts[index][1] if index < len(layouts) else "", True, "",
                         [{"id": str(position), "title": display or short}
                          for position, (short, display, _long) in enumerate(layouts)],
                         "org.kde.keyboard")

        def set_layout(value) -> tuple[bool, str]:
            """KWin switches the running session; localed stores the default for the next one.
            Both, in that order — one without the other is the classic Linux half-change."""
            layouts, _current = self._backend.session.layouts()
            wanted = int(value)
            for _step in range(len(layouts) or 1):
                _layouts, now = self._backend.session.layouts()
                if now == wanted:
                    break
                if not self._backend.session.switch_layout():
                    return False, "KWin не переключил раскладку"
            codes = ",".join(short for short, _display, _long in layouts)
            if codes:
                self._backend.localetime.set_x11_keyboard(codes)
            _layouts, now = self._backend.session.layouts()
            return (now == wanted), "" if now == wanted else "раскладка не переключилась"

        self._add("keyboard.layout", CHOICE, "Раскладка клавиатуры", keyboard_layout, set_layout)

    def _input_state(self, kind: str, option: str, control_kind: str) -> State:
        reading = self._backend.input.value_for_kind(kind, option)
        if not reading.available:
            return State(control_kind, False, None, "", False,
                         reading.detail or NO_HARDWARE, [], reading.source)
        value = reading.get("setting")
        if control_kind == SWITCH:
            return State(SWITCH, True, bool(value), reading.get("device", ""), True, "", [],
                         reading.source)
        # libinput's acceleration is -1 .. 1; Windows shows a coarse speed, so five steps.
        steps = [-1.0, -0.5, 0.0, 0.5, 1.0]
        titles = ["очень низкая", "низкая", "обычная", "высокая", "очень высокая"]
        closest = min(steps, key=lambda step: abs(step - float(value or 0)))
        return State(CHOICE, True, f"{closest:g}", titles[steps.index(closest)], True, "",
                     [{"id": f"{step:g}", "title": title}
                      for step, title in zip(steps, titles)], reading.source)

    # -- time and language ---------------------------------------------------------------------
    def _build_time_language(self) -> None:
        def ntp() -> State:
            reading = self._backend.localetime.clock()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            can = bool(reading.get("can_ntp"))
            return State(SWITCH, True, bool(reading.get("ntp")),
                         "синхронизировано" if reading.get("synchronized") else "не синхронизировано",
                         can, "" if can else "служба времени не установлена", [], reading.source)

        self._add("time.ntp", SWITCH, "Синхронизация времени", ntp,
                  lambda value: _ok(self._backend.localetime.set_ntp(bool(value))))

        def timezone() -> State:
            reading = self._backend.localetime.clock()
            if not reading.available:
                return State(CHOICE, False, None, "", False, reading.detail, [], reading.source)
            zones = self._backend.localetime.timezones()
            current = reading.get("timezone", "")
            return State(CHOICE, True, current, current, bool(zones),
                         "" if zones else "список поясов недоступен",
                         [{"id": zone, "title": zone} for zone in zones], reading.source)

        self._add("time.timezone", CHOICE, "Часовой пояс", timezone,
                  lambda value: _ok(self._backend.localetime.set_timezone(str(value))))

        def local_rtc() -> State:
            reading = self._backend.localetime.clock()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            return State(SWITCH, True, bool(reading.get("local_rtc")),
                         "часы BIOS по местному времени" if reading.get("local_rtc")
                         else "часы BIOS по UTC", True, "", [], reading.source)

        self._add("time.local_rtc", SWITCH, "Часы BIOS по местному времени", local_rtc,
                  lambda value: _ok(self._backend.localetime.set_local_rtc(bool(value))))

        def language() -> State:
            reading = self._backend.localetime.locale()
            if not reading.available:
                return State(CHOICE, False, None, "", False, reading.detail, [], reading.source)
            available = self._backend.localetime.locales()
            current = reading.get("lang", "")
            return State(CHOICE, True, current, current, bool(available),
                         "" if available else "в системе один язык",
                         [{"id": name, "title": name} for name in available], reading.source)

        self._add("language.lang", CHOICE, "Язык интерфейса", language,
                  lambda value: _ok(self._backend.localetime.set_language(str(value))))

    # -- privacy, permissions, firewall ----------------------------------------------------------
    def _build_privacy(self) -> None:
        for device, title in (("camera", "Камера"), ("microphone", "Микрофон"),
                              ("location", "Расположение")):
            def state(device=device) -> State:
                reading = self._backend.permissions.device(device)
                if not reading.available:
                    return State(SWITCH, False, None, "", False,
                                 "портал разрешений не запущен", [], reading.source)
                apps = reading.get("apps", {})
                if not apps:
                    return State(SWITCH, True, True, "ни одно приложение ещё не запрашивало",
                                 False, "нечего менять, пока никто не запросил", [],
                                 reading.source)
                return State(SWITCH, True, bool(reading.get("enabled")), reading.detail, True, "",
                             [], reading.source)

            self._add(f"privacy.{device}", SWITCH, f"Доступ приложений: {title.lower()}", state,
                      lambda value, device=device: _ok(
                          self._backend.permissions.set_device(device, bool(value))))

        def firewall() -> State:
            reading = self._backend.firewall.status()
            if not reading.available:
                return State(SWITCH, False, None, "", False, reading.detail, [], reading.source)
            writable = bool(reading.get("writable"))
            return State(SWITCH, True, bool(reading.get("enabled")),
                         f"{reading.get('backend', '')}: {reading.detail}", writable,
                         "" if writable else "нет прав на изменение", [], reading.source)

        self._add("privacy.firewall", SWITCH, "Брандмауэр", firewall,
                  lambda value: _ok(self._backend.firewall.set_enabled(bool(value))))

    # -- accounts ------------------------------------------------------------------------------
    def _build_accounts(self) -> None:
        def automatic() -> State:
            reading = self._backend.accounts.automatic_login()
            if not reading.available:
                return State(SWITCH, False, None, "", False, "accountsservice недоступен", [],
                             reading.source)
            # The switch applies to *this* account. If the daemon has never heard of the session
            # user (a container, a system account), say so instead of quietly changing someone
            # else's login.
            name = self._backend.session.user_name()
            known = self._backend.accounts.user(name).available
            return State(SWITCH, True, bool(reading.get("enabled")),
                         reading.get("user", ""), known,
                         "" if known else f"учётной записи {name} нет в accountsservice",
                         [], reading.source)

        def set_automatic(value) -> tuple[bool, str]:
            name = self._backend.session.user_name()
            return _ok(self._backend.accounts.set_automatic_login(name, bool(value)))

        self._add("accounts.automatic_login", SWITCH, "Автоматический вход", automatic,
                  set_automatic)

        for user in self._backend.accounts.users():
            name = user.get("name", "")
            if not name:
                continue
            self._add(f"accounts.admin.{name}", SWITCH, f"{name} — администратор",
                      lambda name=name: self._user_flag(name, "admin"),
                      lambda value, name=name: _ok(
                          self._backend.accounts.set_admin(name, bool(value))))
            self._add(f"accounts.locked.{name}", SWITCH, f"{name} — вход запрещён",
                      lambda name=name: self._user_flag(name, "locked"),
                      lambda value, name=name: _ok(
                          self._backend.accounts.set_locked(name, bool(value))))

    def _user_flag(self, name: str, flag: str) -> State:
        user = self._backend.accounts.user(name)
        if not user.available:
            return State(SWITCH, False, None, "", False, "учётная запись исчезла")
        return State(SWITCH, True, bool(user.get(flag)), user.get("kind", ""), True, "", [],
                     user.source)

    # -- applications ----------------------------------------------------------------------------
    def _build_apps(self) -> None:
        from zaldros_backend.defaultapps import ROLES

        from . import desktop_entries

        def installed() -> list:
            try:
                return desktop_entries.discover()
            except OSError:
                return []

        for role, (title, _types) in ROLES.items():
            def state(role=role, title=title) -> State:
                reading = self._backend.apps.role(role)
                applications = installed()
                choices = [{"id": app.desktop_id, "title": app.name}
                           for app in applications if app.desktop_id]
                if not reading.available:
                    return State(CHOICE, True, "", "не задано", bool(choices),
                                 "" if choices else "приложений не найдено", choices,
                                 reading.source)
                return State(CHOICE, True, reading.get("desktop_id", ""), reading.detail,
                             bool(choices), "" if choices else "приложений не найдено", choices,
                             reading.source)

            self._add(f"apps.default.{role}", CHOICE, title, state,
                      lambda value, role=role: _ok(
                          self._backend.apps.set_role(role, str(value))))

        self._add("apps.installed", INFO, "Установленные приложения",
                  lambda: State(INFO, True, len(installed()),
                                f"{len(installed())} приложений", False, READ_ONLY, [],
                                "/usr/share/applications"))

    # -- storage ---------------------------------------------------------------------------------
    def _build_storage(self) -> None:
        def volumes() -> State:
            found = self._backend.storage.volumes(include_system=True)
            if not found:
                return State(INFO, False, None, "", False,
                             self._backend.storage.unavailable_reason())
            return State(INFO, True, len(found),
                         ", ".join(volume.detail for volume in found), False, READ_ONLY, [],
                         "udisks2")

        self._add("storage.volumes", INFO, "Тома", volumes)

        for volume in self._backend.storage.volumes(include_system=False):
            path, label = volume.source, volume.detail
            if not path:
                continue
            self._add(f"storage.mounted.{label}", SWITCH, f"{label} — подключён",
                      lambda path=path, label=label: self._volume_state(path, label),
                      lambda value, path=path: _ok(self._backend.storage.mount(path)
                                                   if value
                                                   else self._backend.storage.unmount(path)))

    def _volume_state(self, path: str, label: str) -> State:
        for volume in self._backend.storage.volumes(include_system=True):
            if volume.source == path:
                mounted = bool(volume.get("mounted"))
                return State(SWITCH, True, mounted, volume.get("mount_point", ""), True, "", [],
                             volume.source)
        return State(SWITCH, False, None, "", False, "том отключён от машины")

    # -- updates ---------------------------------------------------------------------------------
    def _build_updates(self) -> None:
        def available() -> State:
            if not self._backend.updates.available():
                return State(INFO, False, None, "", False, "служба обновлений недоступна")
            reading = self._backend.updates.updates()
            if not reading.available:
                return State(INFO, False, None, "", False, reading.detail, [], reading.source)
            return State(INFO, True, reading.value, reading.detail, False, READ_ONLY, [],
                         reading.source)

        self._add("updates.available", INFO, "Доступные обновления", available)

        def check() -> State:
            ready = self._backend.updates.available()
            return State(ACTION, ready, None, "", ready,
                         "" if ready else "служба обновлений недоступна", [], "PackageKit")

        self._add("updates.check", ACTION, "Проверить обновления", check,
                  lambda _value: _ok(self._backend.updates.refresh()))
