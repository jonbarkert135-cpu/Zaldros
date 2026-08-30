/*
 * The application icon on a switcher card.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the Zaldros project
 *
 * Its own file on purpose. KWin's tabbox model hands out `icon` as a QIcon, and QIcon is the one
 * thing plain QtQuick cannot paint: `Image.source` rejects it ("Unable to assign QIcon to QUrl",
 * measured in the sandbox) and QtQuick.Controls.impl.IconImage wants a theme name, which the model
 * does not publish. Kirigami.Icon accepts a QIcon directly — but a QML import that is missing kills
 * the whole file it appears in, and main.qml is the switcher. Loaded through a Loader, a missing
 * qml6-module-org-kde-kirigami costs the icon and nothing else.
 */
import QtQuick
import org.kde.kirigami as Kirigami

Kirigami.Icon {
    // Set by the Loader once this file has loaded; the QIcon from the tabbox model.
    property var iconSource: null

    source: iconSource
    implicitWidth: 16
    implicitHeight: 16
    Component.onCompleted: console.log("ZALDROS-SWITCHER card icon loaded")
}
