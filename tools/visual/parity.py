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
    "menu": {"context_open": True},
    "settings": {"focused_window": "settings"},
}

# Component crops for the evidence sheet: name -> (state, padding)
CROPS = {
    "taskbar": ("desktop", 0),
    "startPanel": ("start", 12),
    "searchFlyout": ("search", 12),
    "quickPanel": ("quick", 12),
    "notificationCentre": ("notifications", 12),
    "contextMenu": ("menu", 12),
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

    @property
    def passed(self) -> bool:
        return abs(self.actual - self.expected) <= self.tolerance

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return (f"{mark}  {self.component:<18} {self.metric:<22} "
                f"expected {self.expected:>7.1f}   actual {self.actual:>7.1f}")


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

    def add(component: str, metric: str, expected: float, actual: float, tolerance: float) -> None:
        checks.append(Check(component, metric, float(expected), float(actual), float(tolerance)))

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
    add("taskbar", "tray right margin", bar["right_margin"],
        WIDTH - (desktop["trayGroup"]["left"] + desktop["trayGroup"]["width"]), tolerance)

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

    menu = reference["context_menu"]
    menu_box = geometry["menu"]["contextMenu"]
    # the desktop menu has eight commands and two separators; its height must be exactly the
    # Windows 11 stack: items + separators + the 4 px padding at the top and bottom
    expected_height = 8 * menu["item_height"] + 2 * menu["separator_height"] + 2 * menu["padding"]
    add("context menu", "width", menu["width"], menu_box["width"], menu["tolerance"])
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
