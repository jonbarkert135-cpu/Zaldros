import QtQuick
import BedrockTheme

// Composition root of the Bedrock Shell prototype: wallpaper, Start menu and taskbar.
Item {
    id: shell
    width: 1280
    height: 800
    property bool startOpen: false
    // Context properties supplied by the Python backend (see bedrock_shell/app.py).
    property var backendState: shellState
    property var backendApps: appModel

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#123b63" }
            GradientStop { position: 0.55; color: "#0d2745" }
            GradientStop { position: 1.0; color: "#08192c" }
        }
        MouseArea { anchors.fill: parent; onClicked: shell.startOpen = false }
    }

    StartMenu {
        id: startMenu
        shown: shell.startOpen
        state: shell.backendState
        apps: shell.backendApps
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: taskbar.top
        anchors.bottomMargin: 12
        onAppLaunched: function(execName) { shell.startOpen = false }
    }

    Taskbar {
        id: taskbar
        width: parent.width
        anchors.bottom: parent.bottom
        startActive: shell.startOpen
        state: shell.backendState
        apps: shell.backendApps
        onStartToggled: shell.startOpen = !shell.startOpen
    }
}
