/*
 * Zaldros window switching, owned by us (ADR-0012, phase 2: ADR-0025).
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the Zaldros project
 *
 * Phase 1 (main.js, replaced by this file) proved the shortcut fires and the window really
 * changes: iso run 33161193018 reported `switched: true`, `switched_fraction: 0.475`. The same
 * report also said `switcher_overlay_fraction: 0.0` — nothing was ever drawn while Alt was held,
 * because a JavaScript KWin script has no way to put anything on screen.
 *
 * A QML script does: `X-Plasma-API: declarativescript` gives this file the same `workspace`
 * global the JS API had, plus the ability to own a Window. KWin draws it as an internal window,
 * above the session, which is the one place in a Zaldros session where an overlay can appear at
 * all — the shell is a normal Wayland client and cannot raise itself over Dolphin.
 *
 * KWin's own tabbox stays out of this: runs #29-#34 pressed Alt+Tab in a booted ISO, the
 * framebuffer never moved and not one kwin_tabbox line appeared with that category on.
 *
 * Colours are substituted at install time from the same tokens as the shell theme; see
 * system/theme/install-visual-theme.sh.
 */
import QtQuick
import QtQuick.Window
import org.kde.kwin

Item {
    id: root

    readonly property color backdropColour: "@BACKDROP@"
    readonly property color surfaceColour: "@SURFACE@"
    readonly property color textColour: "@TEXT@"
    readonly property color accentColour: "@ACCENT@"
    readonly property int cornerRadius: @RADIUS@

    // Captions of the windows the last Alt+Tab walked through, and which one it landed on.
    property var captions: []
    property int current: -1
    property bool overlayVisible: false

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
        show(windows, windows.indexOf(next));
    }

    function show(windows, selected) {
        var names = [];
        for (var i = 0; i < windows.length; i++) {
            names.push(String(windows[i].caption));
        }
        root.captions = names;
        root.current = selected;
        root.overlayVisible = true;
        hideTimer.restart();
        log("overlay shown windows=" + names.length + " current=" + selected);
    }

    function screenRect() {
        // One overlay across the whole virtual screen. ponytail: on two monitors it spans both;
        // per-output placement when someone actually runs two.
        var geometry = workspace.virtualScreenGeometry;
        if (geometry && geometry.width > 0) {
            return geometry;
        }
        var size = workspace.virtualScreenSize;
        if (size && size.width > 0) {
            return Qt.rect(0, 0, size.width, size.height);
        }
        log("no screen geometry from the workspace, falling back to 1280x800");
        return Qt.rect(0, 0, 1280, 800);
    }

    Timer {
        id: hideTimer
        // ponytail: KWin's scripting API reports no modifier release, so the overlay lives on a
        // timer instead of on the Alt key. Every further Alt+Tab restarts it, so walking a list
        // keeps it up; letting go early leaves it for the rest of this second. Replace with a real
        // "modifiers released" signal if KWin ever exposes one to scripts.
        interval: 1600
        onTriggered: {
            root.overlayVisible = false;
            root.log("overlay hidden");
        }
    }

    Window {
        id: overlay
        // Borderless and full-screen: Windows 11 dims the whole desktop behind the switcher rather
        // than showing a small dialog, and KWin treats this as an internal window, so nothing else
        // in the session has to cooperate.
        flags: Qt.Popup | Qt.X11BypassWindowManagerHint
        visible: root.overlayVisible
        color: "transparent"
        x: root.screenRect().x
        y: root.screenRect().y
        width: root.screenRect().width
        height: root.screenRect().height

        Rectangle {
            anchors.fill: parent
            color: root.backdropColour

            Rectangle {
                anchors.centerIn: parent
                width: Math.min(row.width + 24, parent.width * 0.9)
                height: row.height + 24
                radius: root.cornerRadius
                color: root.surfaceColour

                Row {
                    id: row
                    anchors.centerIn: parent
                    spacing: 12

                    Repeater {
                        model: root.captions

                        // ponytail: caption cards, not live thumbnails. WindowThumbnail is a
                        // tabbox/effect type and is not offered to scripts; the caption is what we
                        // can render truthfully today.
                        Rectangle {
                            width: 200
                            height: 120
                            radius: root.cornerRadius
                            color: index === root.current ? Qt.rgba(1, 1, 1, 0.10)
                                                          : Qt.rgba(1, 1, 1, 0.04)
                            border.width: index === root.current ? 2 : 0
                            border.color: root.accentColour

                            Text {
                                anchors.fill: parent
                                anchors.margins: 12
                                text: modelData
                                color: root.textColour
                                elide: Text.ElideRight
                                wrapMode: Text.Wrap
                                maximumLineCount: 4
                                textFormat: Text.PlainText
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }
        }
    }

    ShortcutHandler {
        name: "Zaldros Walk Through Windows"
        text: "Zaldros: следующее окно"
        sequence: "Alt+Tab"
        onActivated: root.cycle(false)
    }

    ShortcutHandler {
        name: "Zaldros Walk Through Windows (Reverse)"
        text: "Zaldros: предыдущее окно"
        sequence: "Alt+Shift+Tab"
        onActivated: root.cycle(true)
    }

    // Diagnostic probes. They do nothing but print, and they exist so one boot can say *which* key
    // presses reach a global shortcut instead of only whether Alt+Tab did. The host driver presses
    // all four (build/iso/ui-drive.py, PROBE_KEYS) and the late report lists the lines that appeared.
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

    ShortcutHandler {
        name: "Zaldros Probe Meta Tab"
        text: "Zaldros: проверка Meta+Tab"
        sequence: "Meta+Tab"
        onActivated: console.log("ZALDROS-PROBE meta_tab")
    }

    Component.onCompleted: log("loaded (qml), windows=" + switchable().length)
}
