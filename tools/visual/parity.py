"""Windows 11 visual parity check for the Zaldros shell.

Renders the shell offscreen, reads back the real geometry of every named component and compares it
with the numbers measured from the Windows 11 captures (system/theme/win11-reference.json).
A component that drifts fails the run, so "looks close" can never pass for "matches".

    python3 tools/visual/parity.py               # check, write report + component crops
    python3 tools/visual/parity.py --quiet       # only the verdict line

Outputs:
    docs/visual/current/<state>.png              full frames
    docs/visual/current/components/<name>.png    per-component crops (the before/after evidence)
    docs/visual/parity-report.json               machine-readable result
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "shell" / "zaldros-shell"
REFERENCE = ROOT / "system" / "theme" / "win11-reference.json"
OUTPUT = ROOT / "docs" / "visual"

sys.path.insert(0, str(SHELL))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

WIDTH, HEIGHT = 1600, 1000

STATES = {
    "desktop": {},
    "start": {"start_open": True},
    "search": {"search_open": True},
    "quick": {"quick_open": True},
    "notifications": {"notifications_open": True},
    "clipboard": {"clipboard_open": True},
    "gamebar": {"game_bar_open": True},
    "menu": {"context_open": True},
    "settings": {"focused_window": "settings"},
    "snap": {"snap_open": True},
    "snapped": {"snap_zone": (0, 0), "snap_window": "explorer"},
    "snapbar": {"snap_bar": True},
}

# Component crops for the evidence sheet: name -> (state, padding)
CROPS = {
    "taskbar": ("desktop", 0),
    "startPanel": ("start", 12),
    "searchFlyout": ("search", 12),
    "quickPanel": ("quick", 12),
    "notificationCentre": ("notifications", 12),
    "clipboardFlyout": ("clipboard", 12),
    "gameBarFlyout": ("gamebar", 12),
    "contextMenu": ("menu", 12),
    "snapFlyout": ("snap", 12),
    "snapBar": ("snapbar", 12),
    "explorerWindow": ("desktop", 12),
    "settingsWindow": ("settings", 12),
}


@dataclass
class Check:
    component: str
    metric: str
    expected: float
    actual: float
    tolerance: float
    comparator: str = "eq"   # "eq": within tolerance; "min": at least expected - tolerance

    @property
    def passed(self) -> bool:
        if self.comparator == "min":
            return self.actual >= self.expected - self.tolerance
        return abs(self.actual - self.expected) <= self.tolerance

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        relation = ">=" if self.comparator == "min" else "  "
        return (f"{mark}  {self.component:<18} {self.metric:<22} "
                f"expected {relation}{self.expected:>7.1f}   actual {self.actual:>7.1f}")


def render_states(directory: Path) -> dict[str, dict]:
    """Render every state and return {state: geometry}. Import is local: Qt must see QT_QPA_PLATFORM."""
    from zaldros_shell.app import render

    directory.mkdir(parents=True, exist_ok=True)
    geometry: dict[str, dict] = {}
    for name, options in STATES.items():
        png = directory / f"{name}.png"
        geometry_file = directory / f"{name}.geometry.json"
        render(str(png), width=WIDTH, height=HEIGHT,
               geometry_output=str(geometry_file), **options)
        geometry[name] = json.loads(geometry_file.read_text())["items"]
    return geometry


def collect_checks(geometry: dict[str, dict], reference: dict) -> list[Check]:
    checks: list[Check] = []

    def add(component: str, metric: str, expected: float, actual: float, tolerance: float,
            comparator: str = "eq") -> None:
        checks.append(Check(component, metric, float(expected), float(actual), float(tolerance),
                            comparator))

    desktop, start_state = geometry["desktop"], geometry["start"]

    # --- taskbar -------------------------------------------------------------------------------
    bar = reference["taskbar"]
    tolerance = bar["tolerance"]
    taskbar = desktop["taskbar"]
    add("taskbar", "height", bar["height"], taskbar["height"], tolerance)
    add("taskbar", "start button pitch", bar["button_pitch"], desktop["startButton"]["width"], tolerance)
    add("taskbar", "group centred", WIDTH / 2, desktop["taskbarGroup"]["x"], tolerance)
    add("taskbar", "search height", bar["search_height"],
        desktop["taskbarSearch"]["height"] - 16, tolerance)   # search pill inside the 48 px band
    add("taskbar", "search width", bar["search_width"],
        desktop["taskbarSearch"]["width"] - 8, tolerance)      # the pill inside its hit area
    add("taskbar", "tray right margin", bar["right_margin"],
        WIDTH - (desktop["trayGroup"]["left"] + desktop["trayGroup"]["width"]), tolerance)
    # Widgets button: Windows 11 puts weather at the left end, icon then two text lines.
    add("taskbar", "widget icon left", bar["widget_icon_left"], desktop["weatherIcon"]["left"], tolerance)
    add("taskbar", "widget icon size", bar["widget_icon"], desktop["weatherIcon"]["width"], tolerance)
    add("taskbar", "widget text left", bar["widget_text_left"],
        desktop["weatherTemperature"]["left"], tolerance)
    add("taskbar", "widget second line below the first", 1.0,
        1.0 if desktop["weatherCondition"]["top"] > desktop["weatherTemperature"]["top"] else 0.0, 0.01)

    # --- Start ---------------------------------------------------------------------------------
    start = reference["start"]
    tolerance = start["tolerance"]
    panel = start_state["startPanel"]
    add("start", "width", start["width"], panel["width"], tolerance)
    add("start", "height", start["height"], panel["height"], tolerance)
    add("start", "centred", WIDTH / 2, panel["x"], tolerance)
    add("start", "gap above taskbar", start["gap_above_taskbar"],
        desktop["taskbar"]["top"] - (panel["top"] + panel["height"]), tolerance)
    add("start", "padding", start["padding"], start_state["startSearch"]["left"] - panel["left"], tolerance)
    add("start", "search width", start["search_width"], start_state["startSearch"]["width"], tolerance)
    add("start", "search height", start["search_height"], start_state["startSearch"]["height"], tolerance)
    add("start", "search top inset", start["search_top_inset"],
        start_state["startSearch"]["top"] - panel["top"], tolerance)
    add("start", "pin cell width", start["pin_cell_width"],
        start_state["startPinnedGrid"]["width"] / start["pin_columns"], tolerance)
    add("start", "pin cell height", start["pin_cell_height"],
        start_state["startPinnedGrid"]["height"] / 3, tolerance)
    add("start", "footer height", start["footer_height"], start_state["startFooter"]["height"], tolerance)

    # --- windows -------------------------------------------------------------------------------
    window = reference["window"]
    tolerance = window["tolerance"]
    add("window", "title bar height", window["title_bar_height"], desktop["titleBar"]["height"], tolerance)
    add("window", "caption button width", window["caption_button_width"],
        desktop["captionButtons"]["width"] / 3, tolerance)

    # --- Explorer ------------------------------------------------------------------------------
    explorer = reference["explorer"]
    tolerance = explorer["tolerance"]
    add("explorer", "tab strip height", explorer["tab_strip_height"],
        desktop["explorerWindow"]["top"] and _explorer_bar_height(desktop), tolerance)
    add("explorer", "navigation bar height", explorer["navigation_bar_height"],
        desktop["explorerNavBar"]["height"], tolerance)
    add("explorer", "command bar height", explorer["command_bar_height"],
        desktop["explorerCommandBar"]["height"], tolerance)
    add("explorer", "sidebar width", explorer["sidebar_width"],
        desktop["explorerSidebar"]["width"], tolerance)

    # --- Settings ------------------------------------------------------------------------------
    settings = reference["settings"]
    add("settings", "rail width", settings["sidebar_width"],
        geometry["settings"]["settingsRail"]["width"], settings["tolerance"])

    # --- flyouts -------------------------------------------------------------------------------
    quick = reference["quick_settings"]
    quick_panel = geometry["quick"]["quickPanel"]
    add("quick settings", "width", quick["width"], quick_panel["width"], quick["tolerance"])
    add("quick settings", "gap from edge", quick["gap_from_edge"],
        WIDTH - (quick_panel["left"] + quick_panel["width"]), quick["tolerance"])

    notifications = reference["notifications"]
    centre = geometry["notifications"]["notificationCentre"]
    add("notifications", "width", notifications["width"], centre["width"], notifications["tolerance"])
    add("notifications", "gap from edge", notifications["gap_from_edge"],
        WIDTH - (centre["left"] + centre["width"]), notifications["tolerance"])

    clipboard = reference["clipboard"]
    clip_panel = geometry["clipboard"]["clipboardFlyout"]
    add("clipboard", "width", clipboard["width"], clip_panel["width"], clipboard["tolerance"])
    add("clipboard", "gap from edge", clipboard["gap_from_edge"], clip_panel["left"],
        clipboard["tolerance"])

    game_bar = reference["game_bar"]
    bar = geometry["gamebar"]["gameBarFlyout"]
    add("game bar", "width", game_bar["width"], bar["width"], game_bar["tolerance"])
    add("game bar", "gap from edge", game_bar["gap_from_edge"], bar["left"], game_bar["tolerance"])
    toolbar = geometry["gamebar"]["gameBarToolbar"]
    add("game bar", "bar width", game_bar["bar"]["width"], toolbar["width"], game_bar["tolerance"])
    add("game bar", "bar height", game_bar["bar"]["height"], toolbar["height"],
        game_bar["tolerance"])
    # Windows centres the bar on the screen; so do we, and the render proves it rather than the code
    add("game bar", "bar centred", WIDTH / 2, toolbar["left"] + toolbar["width"] / 2,
        game_bar["tolerance"])

    # --- snap layouts ---------------------------------------------------------------------------
    snap = reference["snap_layouts"]
    snap_state = geometry["snap"]
    flyout = snap_state["snapFlyout"]
    add("snap layouts", "panel width", snap["panel_width"], flyout["width"], snap["tolerance"])
    add("snap layouts", "panel height", snap["panel_height"], flyout["height"], snap["tolerance"])
    thumbs = [snap_state[f"snapThumb{index}"] for index in range(snap["layouts"])]
    add("snap layouts", "layouts", snap["layouts"], len(thumbs), 0)
    add("snap layouts", "thumb width", snap["thumb_width"], thumbs[0]["width"], snap["tolerance"])
    add("snap layouts", "thumb height", snap["thumb_height"], thumbs[0]["height"],
        snap["tolerance"])
    add("snap layouts", "thumb gap", snap["thumb_gap"],
        thumbs[1]["left"] - (thumbs[0]["left"] + thumbs[0]["width"]), snap["tolerance"])
    add("snap layouts", "padding", snap["padding"], thumbs[0]["left"] - flyout["left"],
        snap["tolerance"])
    # Every zone of every layout, against the cell rectangles measured in the Windows capture.
    for layout, zones in enumerate(snap["zones"]):
        columns = sorted({zone[0] for zone in zones if zone[0] > 0})
        rows = sorted({zone[1] for zone in zones if zone[1] > 0})
        content_width = snap["thumb_width"] - snap["cell_gap"] * len(columns)
        content_height = snap["thumb_height"] - snap["cell_gap"] * len(rows)
        for index, zone in enumerate(zones):
            box = snap_state[f"snapZone{layout}_{index}"]
            inside_x = sum(1 for edge in columns if zone[0] < edge < zone[0] + zone[2] - 0.0001)
            inside_y = sum(1 for edge in rows if zone[1] < edge < zone[1] + zone[3] - 0.0001)
            add(f"snap zone {layout + 1}.{index + 1}", "width",
                round(zone[2] * content_width) + snap["cell_gap"] * inside_x,
                box["width"], snap["tolerance"])
            add(f"snap zone {layout + 1}.{index + 1}", "height",
                round(zone[3] * content_height) + snap["cell_gap"] * inside_y,
                box["height"], snap["tolerance"])

    # --- snap bar -------------------------------------------------------------------------------
    bar_reference = reference["snap_bar"]
    bar_state = geometry["snapbar"]
    bar = bar_state["snapBar"]
    bar_tolerance = bar_reference["tolerance"]
    add("snap bar", "panel width", bar_reference["panel_width"], bar["width"], bar_tolerance)
    add("snap bar", "panel height", bar_reference["panel_height"], bar["height"], bar_tolerance)
    bar_thumbs = [bar_state[f"snapBarThumb{index}"] for index in range(snap["layouts"])]
    add("snap bar", "layouts", snap["layouts"], len(bar_thumbs), 0)
    add("snap bar", "header band", bar_reference["header_band"],
        bar_thumbs[0]["top"] - bar["top"], bar_tolerance)
    add("snap bar", "bottom padding", bar_reference["bottom_padding"],
        bar["top"] + bar["height"] - (bar_thumbs[0]["top"] + bar_thumbs[0]["height"]),
        bar_tolerance)
    add("snap bar", "side padding", bar_reference["side_padding"],
        bar_thumbs[0]["left"] - bar["left"], bar_tolerance)
    add("snap bar", "thumb width", snap["thumb_width"], bar_thumbs[0]["width"], snap["tolerance"])
    add("snap bar", "thumb height", snap["thumb_height"], bar_thumbs[0]["height"],
        snap["tolerance"])
    add("snap bar", "centred on screen", 0,
        round(bar["left"] + bar["width"] / 2 - WIDTH / 2), 1)

    # A snapped window really takes its zone: the left half of the work area, to the pixel.
    snapped = geometry["snapped"]["explorerWindow"]
    work_height = HEIGHT - reference["taskbar"]["height"]
    add("snapped window", "left", 0, snapped["left"], 1)
    add("snapped window", "top", 0, snapped["top"], 1)
    add("snapped window", "width", WIDTH / 2, snapped["width"], 1)
    add("snapped window", "height", work_height, snapped["height"], 1)

    menu = reference["context_menu"]
    menu_box = geometry["menu"]["contextMenu"]
    # the desktop menu has eight commands and two separators; its height must be exactly the
    # Windows 11 stack: items + separators + the 4 px padding at the top and bottom
    expected_height = 8 * menu["item_height"] + 2 * menu["separator_height"] + 2 * menu["padding"]
    # Windows 11 grows a menu to fit its widest row, so this is a floor, not an equality.
    add("context menu", "min width", menu["min_width"], menu_box["width"], menu["tolerance"],
        comparator="min")
    add("context menu", "stack height", expected_height, menu_box["height"], menu["tolerance"])

    return checks


def _explorer_bar_height(desktop: dict) -> float:
    """Explorer's tab strip is its title bar; its height is the gap above the navigation bar."""
    return desktop["explorerNavBar"]["top"] - desktop["explorerWindow"]["top"]


def write_crops(directory: Path, geometry: dict[str, dict]) -> list[str]:
    from PIL import Image

    crops = directory / "components"
    crops.mkdir(parents=True, exist_ok=True)
    written = []
    for name, (state, padding) in CROPS.items():
        box = geometry[state].get(name)
        if box is None:
            continue
        image = Image.open(directory / f"{state}.png")
        left = max(0, box["left"] - padding)
        top = max(0, box["top"] - padding)
        right = min(image.width, box["left"] + box["width"] + padding)
        bottom = min(image.height, box["top"] + box["height"] + padding)
        image.crop((left, top, right, bottom)).save(crops / f"{name}.png")
        written.append(f"{name}.png")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    output = Path(args.output)
    reference = json.loads(REFERENCE.read_text())
    geometry = render_states(output / "current")
    checks = collect_checks(geometry, reference)
    crops = write_crops(output / "current", geometry)

    failures = [check for check in checks if not check.passed]
    report = {
        "reference": str(REFERENCE.relative_to(ROOT)),
        "checks": [asdict(check) | {"passed": check.passed} for check in checks],
        "failed": len(failures),
        "total": len(checks),
        "components": crops,
    }
    (output / "parity-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    if not args.quiet:
        for check in checks:
            print(check.line())
    print(f"\nvisual parity: {len(checks) - len(failures)}/{len(checks)} checks match Windows 11")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
