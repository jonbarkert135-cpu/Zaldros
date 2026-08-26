"""Weather for the taskbar widget button.

Windows 11 shows temperature and a condition at the left end of the taskbar. Ours shows the same
two lines, but only when a reading was actually fetched. There is no sample data and no guess: if
the network is down, if the location is unknown, or if the service answers with anything we do not
understand, the widget says so and the shell renders a dash.

Location comes from `/etc/zaldros/weather.conf` (`latitude=`, `longitude=`, optional `place=`).
The forecast comes from Open-Meteo, which needs no API key and no account. Both the lookup and the
request run off the UI thread; the widget shows "нет данных" until the first answer arrives.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CONFIG = Path("/etc/zaldros/weather.conf")
ENDPOINT = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 4.0

# WMO weather codes, grouped the way the taskbar needs them: a Russian label and one of our glyphs.
_CODES: dict[int, tuple[str, str]] = {
    0: ("Ясно", "weather-sun"),
    1: ("Малооблачно", "weather-sun"),
    2: ("Переменная облачность", "weather-cloud"),
    3: ("Облачно", "weather-cloud"),
    45: ("Туман", "weather-cloud"),
    48: ("Изморозь", "weather-cloud"),
    51: ("Морось", "weather-rain"),
    53: ("Морось", "weather-rain"),
    55: ("Морось", "weather-rain"),
    61: ("Небольшой дождь", "weather-rain"),
    63: ("Дождь", "weather-rain"),
    65: ("Сильный дождь", "weather-rain"),
    71: ("Небольшой снег", "weather-snow"),
    73: ("Снег", "weather-snow"),
    75: ("Сильный снег", "weather-snow"),
    80: ("Ливень", "weather-rain"),
    81: ("Ливень", "weather-rain"),
    82: ("Сильный ливень", "weather-rain"),
    95: ("Гроза", "weather-rain"),
    96: ("Гроза с градом", "weather-rain"),
    99: ("Гроза с градом", "weather-rain"),
}


@dataclass(frozen=True)
class Reading:
    available: bool
    temperature: str = ""   # already formatted, e.g. "19°C"
    condition: str = ""
    place: str = ""
    glyph: str = "weather-cloud"
    detail: str = "нет данных"


UNAVAILABLE = Reading(available=False)


def read_location(path: Path = CONFIG) -> tuple[float, float, str] | None:
    """Latitude, longitude and place name from the config file, or None when it is not set."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    try:
        return float(values["latitude"]), float(values["longitude"]), values.get("place", "")
    except (KeyError, ValueError):
        return None


def describe(code: int) -> tuple[str, str]:
    return _CODES.get(code, ("", "weather-cloud"))


def parse(payload: dict, place: str) -> Reading:
    current = payload.get("current") or {}
    temp = current.get("temperature_2m")
    code = current.get("weather_code")
    if temp is None or code is None:
        return UNAVAILABLE
    condition, glyph = describe(int(code))
    if not condition:
        # An unknown WMO code is not an excuse to invent a label.
        condition = "нет описания"
    return Reading(
        available=True,
        temperature=f"{round(float(temp))}°C",
        condition=condition,
        place=place,
        glyph=glyph,
        detail=(f"{place}: " if place else "") + f"{round(float(temp))}°C, {condition.lower()}",
    )


def fetch(timeout: float = TIMEOUT) -> Reading:
    """One blocking lookup. Never raises: an unreachable service is a normal state for a laptop."""
    location = read_location()
    if location is None:
        return Reading(available=False, detail="местоположение не задано")
    lat, lon, place = location
    url = (f"{ENDPOINT}?latitude={lat:.4f}&longitude={lon:.4f}"
           "&current=temperature_2m,weather_code")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed host
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return Reading(available=False, detail="служба погоды недоступна")
    return parse(payload, place)


def fetch_async(callback) -> threading.Thread:
    """Run `fetch` on a worker thread and hand the reading to `callback`."""
    def run() -> None:
        callback(fetch())

    thread = threading.Thread(target=run, name="zaldros-weather", daemon=True)
    thread.start()
    return thread
