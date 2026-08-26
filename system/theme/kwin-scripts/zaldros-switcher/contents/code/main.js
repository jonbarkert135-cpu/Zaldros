// Zaldros window switching, owned by us (ADR-0012).
//
// KWin's built-in tabbox never drew anything in this session: runs #29-#34 pressed Alt+Tab in a
// booted ISO and the framebuffer did not change by a single pixel, with not one kwin_tabbox line
// in the session log even with that category on. Rather than keep guessing inside KWin's switcher
// machinery, the behaviour lives here, in KWin's own scripting API, where every step logs what it
// did and the next boot can read it back.
//
// Phase 1 (this file): the shortcut cycles the real windows and activates them, so Alt+Tab works
// as a *function* and the boot test can measure a genuine window change. The visual overlay is
// drawn by the Zaldros shell and is wired in once the shortcut itself is proven to fire.

var LOG = "ZALDROS-SWITCHER ";

function log(message) {
    print(LOG + message);
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

registerShortcut("Zaldros Walk Through Windows", "Zaldros: следующее окно", "Alt+Tab",
                 function () { cycle(false); });
registerShortcut("Zaldros Walk Through Windows (Reverse)", "Zaldros: предыдущее окно",
                 "Alt+Shift+Tab", function () { cycle(true); });

log("loaded, windows=" + switchable().length);
