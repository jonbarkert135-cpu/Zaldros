/*
 * Zaldros window switching fallback (ADR-0012, phase 3).
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the Zaldros project
 *
 * This file no longer draws anything, and it no longer owns Alt+Tab.
 *
 * What was measured. Phase 1 (main.js) proved the shortcut fires and the window really changes
 * (run 33161193018: `switched: true`, `switched_fraction: 0.475`) but a JavaScript KWin script
 * cannot put pixels on screen. Phase 2 rewrote it as a QML `declarativescript` with its own
 * `Window`; run #39 drew nothing, and run #40 — with the popup flags removed and a diagnostic
 * line added — answered why in one line:
 *
 *     ZALDROS-SWITCHER overlay window visible=false geometry=0,0 1280x800
 *
 * We asked for the window, the geometry was right, and Qt/KWin still refused to create it: a KWin
 * script is not allowed to own a window at all, whatever the flags. So the overlay is gone.
 *
 * The switcher a Zaldros session actually shows is KWin's own tabbox running our layout
 * (system/theme/tabbox/zaldros), which KWin draws above the session itself; Alt+Tab is bound to
 * KWin's "Walk Through Windows" again in system/theme/install-visual-theme.sh.
 *
 * What is left here: the same window cycling on Meta+Tab — a switcher with no UI, kept because it
 * is the one path that is proven to change windows if the tabbox regresses — and the diagnostic
 * probes.
 */
import QtQuick
import org.kde.kwin

Item {
    id: root

    // KWin gives a *QML* script no `workspace` global — only plain JS scripts get one; the
    // declarative API exposes the singleton `Workspace` from org.kde.kwin instead (run #38 in a
    // booted ISO: "ReferenceError: workspace is not defined" from this file, twice per Alt+Tab).
    // One alias keeps the rest of the file reading like the documented API.
    readonly property var workspace: Workspace

    readonly property string logPrefix: "ZALDROS-SWITCHER "

    function log(message) {
        console.log(root.logPrefix + message);
    }

    function switchable() {
        // Only real, user-facing windows on the current desktop, bottom-to-top as KWin stacks them.
        var out = [];
        var stack = workspace.stackingOrder;
        for (var i = 0; i < stack.length; i++) {
            var w = stack[i];
            if (!w || !w.normalWindow || w.skipSwitcher || w.deleted) {
                continue;
            }
            if (!w.onAllDesktops && w.desktops && w.desktops.length > 0
                    && workspace.currentDesktop && w.desktops.indexOf(workspace.currentDesktop) === -1) {
                continue;
            }
            out.push(w);
        }
        return out;
    }

    function cycle(reverse) {
        var windows = switchable();
        log("cycle reverse=" + reverse + " candidates=" + windows.length);
        if (windows.length < 2) {
            // One window (or none) is not a failure: there is simply nothing to switch to.
            log("nothing to switch to");
            return;
        }
        var active = workspace.activeWindow;
        var index = windows.indexOf(active);
        var next;
        if (index === -1) {
            next = windows[windows.length - 1];
        } else if (reverse) {
            next = windows[(index + 1) % windows.length];
        } else {
            // Not reversed = the window one step *below* the active one in the stack, which is the
            // most-recently-used order a person expects from Alt+Tab.
            next = windows[(index - 1 + windows.length) % windows.length];
        }
        log("activating " + next.caption + " (was " + (active ? active.caption : "none") + ")");
        if (next.minimized) {
            // Activating a minimized window leaves it minimized in KWin; Alt+Tab in Windows 11
            // restores it, and the boot test can only see a restored window.
            next.minimized = false;
        }
        workspace.activeWindow = next;
    }

    ShortcutHandler {
        name: "Zaldros Walk Through Windows"
        text: "Zaldros: следующее окно"
        sequence: "Meta+Tab"
        onActivated: root.cycle(false)
    }

    ShortcutHandler {
        name: "Zaldros Walk Through Windows (Reverse)"
        text: "Zaldros: предыдущее окно"
        sequence: "Meta+Shift+Tab"
        onActivated: root.cycle(true)
    }

    // Diagnostic probes. They do nothing but print, and they exist so one boot can say *which* key
    // presses reach a global shortcut instead of only whether Alt+Tab did. The host driver presses
    // these (build/iso/ui-drive.py, PROBE_KEYS) and the late report lists the lines that appeared.
    // Its fourth press, Meta+Tab, now lands on the fallback cycle above and logs "cycle reverse=".
    ShortcutHandler {
        name: "Zaldros Probe Meta F9"
        text: "Zaldros: проверка Meta+F9"
        sequence: "Meta+F9"
        onActivated: console.log("ZALDROS-PROBE meta_f9")
    }

    ShortcutHandler {
        name: "Zaldros Probe Alt F9"
        text: "Zaldros: проверка Alt+F9"
        sequence: "Alt+F9"
        onActivated: console.log("ZALDROS-PROBE alt_f9")
    }

    ShortcutHandler {
        name: "Zaldros Probe Ctrl Shift F9"
        text: "Zaldros: проверка Ctrl+Shift+F9"
        sequence: "Ctrl+Shift+F9"
        onActivated: console.log("ZALDROS-PROBE ctrl_shift_f9")
    }

    Component.onCompleted: log("loaded (qml), windows=" + switchable().length)
}
