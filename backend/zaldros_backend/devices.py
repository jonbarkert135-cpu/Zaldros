# SPDX-License-Identifier: GPL-3.0-or-later
"""Device Manager — the machine as the kernel enumerates it.

Windows' Device Manager is a tree of categories, and under each one a device with a driver, a
status and a properties sheet. Linux already keeps exactly that: `/sys/bus/pci`, `/sys/bus/usb`,
`/sys/class/*` and DMI. This module reads those files and nothing else — no `lshw`, no `hwinfo`,
no `lspci` (which is a parser over the same sysfs plus a 2 MB ids file we do not ship), and no
downloaded vendor database.

The consequences are deliberate and visible in the UI:

* A device without a bound driver is shown as **«драйвер не загружен»**, which is the same fact
  Windows shows with a yellow triangle. It is read from the absence of `device/driver`, not
  guessed.
* A name we cannot resolve stays a vendor:device id. Zaldros does not invent marketing names for
  hardware it cannot identify; the id is checkable, a made-up name is not.
* Categories with nothing in them are still listed, with the reason («шина PCI не видна из этой
  среды» in a container, for instance) — an empty tree with no explanation looks like a bug.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .reading import Reading

# PCI class codes → the Windows-shaped category. The high byte of the class is enough for the
# grouping a Device Manager needs; the full three-byte code is kept in the details.
PCI_CLASSES = {
    0x01: "Дисковые контроллеры", 0x02: "Сетевые адаптеры", 0x03: "Видеоадаптеры",
    0x04: "Звук, видео и игровые устройства", 0x05: "Контроллеры памяти",
    0x06: "Системные устройства", 0x07: "Порты (COM и LPT)", 0x08: "Системные устройства",
    0x09: "Устройства HID", 0x0a: "Системные устройства", 0x0b: "Процессоры",
    0x0c: "Контроллеры USB", 0x0d: "Сетевые адаптеры", 0x0e: "Системные устройства",
    0x0f: "Сетевые адаптеры", 0x10: "Шифрование", 0x11: "Сбор данных",
}

# Same short vendor table the rest of the backend uses: enough to name the common cases without
# shipping pci.ids, and honest about the rest.
VENDORS = {"0x8086": "Intel", "0x10de": "NVIDIA", "0x1002": "AMD", "0x1022": "AMD",
           "0x1af4": "Red Hat", "0x1234": "QEMU", "0x1b36": "QEMU", "0x15ad": "VMware",
           "0x1414": "Microsoft", "0x14e4": "Broadcom", "0x10ec": "Realtek",
           "0x168c": "Qualcomm Atheros", "0x1969": "Qualcomm Atheros", "0x1106": "VIA",
           "0x1d6b": "Linux Foundation", "0x8087": "Intel"}

CATEGORY_ORDER = ("Процессоры", "Оперативная память", "Материнская плата и микропрограмма",
                  "Видеоадаптеры", "Дисковые устройства", "Дисковые контроллеры",
                  "Сетевые адаптеры", "Bluetooth", "Звук, видео и игровые устройства",
                  "Контроллеры USB", "USB-устройства", "Камеры",
                  "Клавиатуры, мыши и сенсорные панели", "Мониторы", "Принтеры",
                  "Контроллеры памяти", "Системные устройства", "Порты (COM и LPT)",
                  "Устройства HID", "Шифрование", "Сбор данных", "Процессоры (PCI)")

NO_DRIVER = "драйвер не загружен"


def _text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _driver(device_dir: Path) -> str:
    try:
        return os.path.basename(os.readlink(device_dir / "driver"))
    except OSError:
        return ""


@dataclass(frozen=True)
class Device:
    """One row in the tree. `available` is about the *reading*, `working` about the device."""

    category: str
    name: str
    driver: str
    source: str
    details: dict[str, str] = field(default_factory=dict)
    working: bool = True
    problem: str = ""

    def as_row(self) -> dict:
        return {"category": self.category, "name": self.name, "driver": self.driver,
                "source": self.source, "details": dict(self.details),
                "working": self.working, "problem": self.problem,
                "status": self.problem or ("работает нормально" if self.working else NO_DRIVER)}


def _named(vendor: str, device: str, fallback: str) -> str:
    vendor_name = VENDORS.get(vendor, "")
    ids = f"{vendor.replace('0x', '')}:{device.replace('0x', '')}" if vendor and device else ""
    if vendor_name and ids:
        return f"{vendor_name} {fallback} [{ids}]"
    if ids:
        return f"{fallback} [{ids}]"
    return fallback


# -- PCI ---------------------------------------------------------------------------------------
def pci_devices(root: str = "/sys/bus/pci/devices") -> list[Device]:
    out: list[Device] = []
    try:
        entries = sorted(Path(root).iterdir())
    except OSError:
        return out
    for entry in entries:
        class_code = _text(entry / "class")
        try:
            class_high = int(class_code, 16) >> 16
        except ValueError:
            class_high = -1
        vendor, device = _text(entry / "vendor"), _text(entry / "device")
        driver = _driver(entry)
        category = PCI_CLASSES.get(class_high, "Системные устройства")
        out.append(Device(
            category=category,
            name=_named(vendor, device, "устройство PCI"),
            driver=driver or NO_DRIVER,
            source=str(entry),
            working=bool(driver),
            problem="" if driver else NO_DRIVER,
            details={"Шина": "PCI", "Адрес": entry.name, "Класс": class_code,
                     "Производитель": VENDORS.get(vendor, vendor or "—"),
                     "Идентификатор": f"{vendor}:{device}",
                     "Модуль ядра": driver or "—",
                     "Ревизия": _text(entry / "revision") or "—"}))
    return out


# -- USB ---------------------------------------------------------------------------------------
def usb_devices(root: str = "/sys/bus/usb/devices") -> list[Device]:
    """Real USB devices only: the `usbN` roots are the host controllers PCI already listed, and
    the `x-y:1.0` entries are interfaces of a device, not devices."""
    out: list[Device] = []
    try:
        entries = sorted(Path(root).iterdir())
    except OSError:
        return out
    for entry in entries:
        if ":" in entry.name or entry.name.startswith("usb"):
            continue
        vendor, product = _text(entry / "idVendor"), _text(entry / "idProduct")
        name = _text(entry / "product") or _named(f"0x{vendor}", f"0x{product}", "USB-устройство")
        manufacturer = _text(entry / "manufacturer")
        driver = _driver(entry)
        out.append(Device(
            category="USB-устройства",
            name=f"{manufacturer} {name}".strip() if manufacturer else name,
            driver=driver or NO_DRIVER,
            source=str(entry),
            working=bool(driver),
            problem="" if driver else NO_DRIVER,
            details={"Шина": "USB", "Порт": entry.name,
                     "Идентификатор": f"{vendor}:{product}",
                     "Скорость, Мбит/с": _text(entry / "speed") or "—",
                     "Серийный номер": _text(entry / "serial") or "—",
                     "Модуль ядра": driver or "—"}))
    return out


# -- classes that deserve their own category ----------------------------------------------------
def _class_devices(class_root: str, name: str, category: str,
                   extra: dict[str, str] | None = None) -> list[Device]:
    out: list[Device] = []
    try:
        entries = sorted(Path(class_root, name).iterdir())
    except OSError:
        return out
    for entry in entries:
        driver = _driver(entry / "device") or _driver(entry)
        details = {"Класс sysfs": name, "Узел": entry.name, "Модуль ядра": driver or "—"}
        for label, filename in (extra or {}).items():
            details[label] = _text(entry / filename) or "—"
        out.append(Device(category=category, name=entry.name, driver=driver or NO_DRIVER,
                          source=str(entry), working=bool(driver),
                          problem="" if driver else NO_DRIVER, details=details))
    return out


def network_devices(class_root: str = "/sys/class") -> list[Device]:
    devices = _class_devices(class_root, "net", "Сетевые адаптеры",
                             {"MAC-адрес": "address", "Состояние": "operstate",
                              "MTU": "mtu", "Скорость, Мбит/с": "speed"})
    # `lo` is the kernel, not a device: Windows does not show a loopback adapter by default either.
    return [device for device in devices if device.name != "lo"]


def block_devices(class_root: str = "/sys/class") -> list[Device]:
    out: list[Device] = []
    try:
        entries = sorted(Path(class_root, "block").iterdir())
    except OSError:
        return out
    for entry in entries:
        if entry.name.startswith(("loop", "ram", "zram", "dm-")):
            continue
        if (entry / "partition").exists():
            continue                             # a partition is not a disk
        sectors = _text(entry / "size")
        size = f"{int(sectors) * 512 / 1000 ** 3:.1f} ГБ" if sectors.isdigit() else "—"
        model = _text(entry / "device" / "model") or entry.name
        rotational = _text(entry / "queue" / "rotational")
        out.append(Device(
            category="Дисковые устройства", name=model.strip(),
            driver=_driver(entry / "device") or NO_DRIVER, source=str(entry),
            working=True,
            details={"Узел": f"/dev/{entry.name}", "Объём": size,
                     "Тип": {"0": "SSD/NVMe", "1": "жёсткий диск"}.get(rotational, "—"),
                     "Серийный номер": _text(entry / "device" / "serial") or "—",
                     "Микропрограмма": _text(entry / "device" / "firmware_rev") or "—"}))
    return out


def input_devices(proc_root: str = "/proc") -> list[Device]:
    """From /proc/bus/input/devices: the file libinput itself starts from."""
    out: list[Device] = []
    text = _text(os.path.join(proc_root, "bus/input/devices"))
    if not text:
        return out
    for block in text.split("\n\n"):
        name = handlers = phys = ""
        for line in block.splitlines():
            if line.startswith("N: Name="):
                name = line.split("=", 1)[1].strip('"')
            elif line.startswith("H: Handlers="):
                handlers = line.split("=", 1)[1].strip()
            elif line.startswith("P: Phys="):
                phys = line.split("=", 1)[1].strip()
        if not name:
            continue
        out.append(Device(category="Клавиатуры, мыши и сенсорные панели", name=name,
                          driver="evdev", source=f"{proc_root}/bus/input/devices",
                          details={"Обработчики": handlers or "—", "Физический путь": phys or "—"}))
    return out


def displays(drm_root: str = "/sys/class/drm") -> list[Device]:
    out: list[Device] = []
    try:
        entries = sorted(path for path in Path(drm_root).glob("card*-*"))
    except OSError:
        return out
    for entry in entries:
        status = _text(entry / "status")
        if status != "connected":
            continue                              # Windows lists connected monitors, not sockets
        modes = _text(entry / "modes").splitlines()
        out.append(Device(
            category="Мониторы", name=entry.name.split("-", 1)[1], driver="drm", source=str(entry),
            details={"Состояние": status, "Лучший режим": modes[0] if modes else "—",
                     "Режимов": str(len(modes)),
                     "Тип соединения": entry.name.split("-", 1)[1].rstrip("0123456789-")}))
    return out


def cameras(class_root: str = "/sys/class") -> list[Device]:
    out: list[Device] = []
    try:
        entries = sorted(Path(class_root, "video4linux").iterdir())
    except OSError:
        return out
    for entry in entries:
        out.append(Device(category="Камеры", name=_text(entry / "name") or entry.name,
                          driver=_driver(entry / "device") or NO_DRIVER, source=str(entry),
                          working=True,
                          details={"Узел": f"/dev/{entry.name}",
                                   "Драйвер": _driver(entry / "device") or "—"}))
    return out


def sound_cards(proc_root: str = "/proc") -> list[Device]:
    out: list[Device] = []
    for line in _text(os.path.join(proc_root, "asound/cards")).splitlines():
        if not line[:1].isdigit():
            continue
        _, _, rest = line.partition(":")
        name = rest.strip()
        if name:
            out.append(Device(category="Звук, видео и игровые устройства", name=name,
                              driver="snd", source=f"{proc_root}/asound/cards",
                              details={"Источник": "ALSA", "Строка": line.strip()}))
    return out


def processors(proc_root: str = "/proc", dmi_root: str = "/sys/class/dmi/id") -> list[Device]:
    from . import hardware
    model = hardware.cpu_model(proc_root)
    if not model:
        return []
    return [Device(category="Процессоры", name=model, driver="—",
                   source=os.path.join(proc_root, "cpuinfo"),
                   details={"Логических ядер": str(hardware.cpu_cores()),
                            "Архитектура": os.uname().machine,
                            "Микрокод": _first_value(proc_root, "microcode")})]


def _first_value(proc_root: str, key: str) -> str:
    for line in _text(os.path.join(proc_root, "cpuinfo")).splitlines():
        name, _, value = line.partition(":")
        if name.strip() == key:
            return value.strip()
    return "—"


def memory(proc_root: str = "/proc") -> list[Device]:
    from . import hardware
    values = hardware.meminfo_bytes(proc_root)
    total = values.get("MemTotal")
    if not total:
        return []
    return [Device(category="Оперативная память", name=f"{total / 1024 ** 3:.1f} ГиБ",
                   driver="—", source=os.path.join(proc_root, "meminfo"),
                   details={"Всего": f"{total / 1024 ** 3:.1f} ГиБ",
                            "Доступно": f"{values.get('MemAvailable', 0) / 1024 ** 3:.1f} ГиБ",
                            "Подкачка": f"{values.get('SwapTotal', 0) / 1024 ** 3:.1f} ГиБ",
                            "Примечание": "модули DIMM видны только через DMI type 17, "
                                          "которое требует root"})]


def board(dmi_root: str = "/sys/class/dmi/id") -> list[Device]:
    from . import hardware
    values = hardware.firmware(dmi_root)
    if not values:
        return []
    name = " ".join(part for part in (values.get("board_vendor", ""),
                                      values.get("board_name", "")) if part) or "системная плата"
    details = {"Производитель платы": values.get("board_vendor", "—"),
               "Плата": values.get("board_name", "—"),
               "BIOS/UEFI": values.get("bios_version", "—"),
               "Дата микропрограммы": values.get("bios_date", "—"),
               "Режим загрузки": hardware.boot_mode()}
    secure = hardware.secure_boot()
    details["Безопасная загрузка"] = "—" if secure is None else ("включена" if secure else "выключена")
    return [Device(category="Материнская плата и микропрограмма", name=name, driver="—",
                   source=dmi_root, details=details)]


def printers(runner=None) -> list[Device]:
    """CUPS queues via `lpstat -p`. No CUPS, no queues — and the reason says which it was."""
    import shutil
    import subprocess
    run = runner or subprocess.run
    tool = shutil.which("lpstat")
    if not tool:
        return []
    try:
        result = run([tool, "-p"], capture_output=True, text=True, timeout=5)
    except Exception:                                        # noqa: BLE001 - reported by absence
        return []
    out: list[Device] = []
    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "printer":
            out.append(Device(category="Принтеры", name=parts[1], driver="cups", source="lpstat -p",
                              working="disabled" not in line,
                              problem="" if "disabled" not in line else "очередь остановлена",
                              details={"Очередь": parts[1], "Строка состояния": line.strip()}))
    return out


class DevicesFacet:
    """The whole tree, and the honest reason for every empty branch."""

    def __init__(self, sysfs: str = "/sys", proc_root: str = "/proc") -> None:
        self.sysfs = sysfs
        self.proc_root = proc_root

    def _class_root(self) -> str:
        return os.path.join(self.sysfs, "class")

    def devices(self) -> list[Device]:
        found: list[Device] = []
        found += processors(self.proc_root, os.path.join(self._class_root(), "dmi", "id"))
        found += memory(self.proc_root)
        found += board(os.path.join(self._class_root(), "dmi", "id"))
        found += pci_devices(os.path.join(self.sysfs, "bus/pci/devices"))
        found += usb_devices(os.path.join(self.sysfs, "bus/usb/devices"))
        found += network_devices(self._class_root())
        found += block_devices(self._class_root())
        found += sound_cards(self.proc_root)
        found += cameras(self._class_root())
        found += displays(os.path.join(self._class_root(), "drm"))
        found += input_devices(self.proc_root)
        found += printers()
        return found

    def tree(self) -> list[dict]:
        """Categories in Windows's order, each with its devices — and empty ones explained."""
        devices = self.devices()
        by_category: dict[str, list[Device]] = {}
        for device in devices:
            by_category.setdefault(device.category, []).append(device)
        order = list(CATEGORY_ORDER) + [name for name in sorted(by_category)
                                        if name not in CATEGORY_ORDER]
        tree = []
        for category in order:
            members = sorted(by_category.get(category, []), key=lambda item: item.name.lower())
            if not members and category not in _ALWAYS_SHOWN:
                continue
            tree.append({"category": category,
                         "devices": [device.as_row() for device in members],
                         "reason": "" if members else self._reason(category)})
        return tree

    def _reason(self, category: str) -> str:
        checks = {"Видеоадаптеры": os.path.join(self.sysfs, "bus/pci/devices"),
                  "Контроллеры USB": os.path.join(self.sysfs, "bus/pci/devices"),
                  "USB-устройства": os.path.join(self.sysfs, "bus/usb/devices"),
                  "Сетевые адаптеры": os.path.join(self._class_root(), "net"),
                  "Дисковые устройства": os.path.join(self._class_root(), "block"),
                  "Мониторы": os.path.join(self._class_root(), "drm"),
                  "Камеры": os.path.join(self._class_root(), "video4linux"),
                  "Принтеры": "lpstat"}
        path = checks.get(category)
        if category == "Принтеры":
            import shutil
            return "CUPS не установлен" if not shutil.which("lpstat") else "очередей печати нет"
        if path and not os.path.isdir(path):
            return f"ядро не показывает {path} в этой среде"
        return "устройств этого типа не найдено"

    def counts(self) -> dict[str, int]:
        devices = self.devices()
        return {"devices": len(devices),
                "problems": sum(1 for device in devices if not device.working)}

    def problems(self) -> list[Device]:
        """The only list most users should ever be shown: what is not working."""
        return [device for device in self.devices() if not device.working]

    def rescan(self) -> Reading:
        """«Обновить конфигурацию оборудования». Rescanning the PCI bus needs root, and the
        refusal is reported instead of being swallowed into a fake success."""
        path = os.path.join(self.sysfs, "bus/pci/rescan")
        if not os.path.exists(path):
            return Reading.missing("шина PCI не видна из этой среды", path)
        try:
            with open(path, "w", encoding="ascii") as handle:
                handle.write("1")
        except PermissionError:
            return Reading.missing("нужны права root", path)
        except OSError as error:
            return Reading.missing(str(error), path)
        return Reading.measured(None, "шина PCI пересканирована", path)


# Categories a Device Manager should list even when empty, because their absence is itself
# information ("this machine has no camera" is an answer; a missing row is not).
_ALWAYS_SHOWN = {"Видеоадаптеры", "Сетевые адаптеры", "Дисковые устройства", "USB-устройства",
                 "Камеры", "Мониторы", "Принтеры", "Звук, видео и игровые устройства"}
