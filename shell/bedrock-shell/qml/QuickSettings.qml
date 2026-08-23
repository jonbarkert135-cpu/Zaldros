import QtQuick
import BedrockTheme

// Windows-like quick settings flyout, 360 px wide, anchored above the tray.
// Hard rule (brief §8): no decorative fake switches. A tile whose backend is not present on this
// machine renders disabled and states why, instead of pretending to toggle something.
Item {
    id: quick
    property bool shown: false
    property var system: null
    width: Theme.quickWidth
    height: content.implicitHeight + 32
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    y: shown ? baseY : baseY + 16
    property real baseY: 0
    enabled: shown
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }

    // Opaque base: the shipping shell will use KWin's blur behind the acrylic tint; the prototype
    // renderer has no live blur, so a solid base keeps the panel readable instead of ghosting.
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.background
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: content
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Grid {
                columns: 3
                spacing: 8
                QuickTile {
                    glyph: quick.system && quick.system.networkDetail.indexOf("Wi-Fi") >= 0 ? "wifi" : "ethernet"
                    label: "Сеть"
                    detail: quick.system ? quick.system.networkDetail : "нет данных"
                    on: quick.system ? quick.system.networkAvailable : false
                    available: quick.system ? quick.system.networkAvailable : false
                }
                QuickTile {
                    glyph: "bluetooth"; label: "Bluetooth"
                    detail: quick.system ? quick.system.bluetoothDetail : "нет данных"
                    available: quick.system ? quick.system.bluetoothAvailable : false
                }
                QuickTile {
                    glyph: "vpn"; label: "VPN"
                    detail: "не настроен"
                    available: false
                }
                QuickTile {
                    glyph: "night"; label: "Ночной свет"
                    detail: "нужен вывод"
                    available: false
                }
                QuickTile {
                    glyph: "accessibility"; label: "Спец. возможности"
                    detail: "не подключено"
                    available: false
                }
                QuickTile {
                    glyph: "cast"; label: "Проецирование"
                    detail: "нет дисплеев"
                    available: false
                }
            }

            QuickSlider {
                width: parent.width
                glyph: "volume"
                label: "Громкость"
                value: quick.system ? quick.system.volumePercent : -1
                available: quick.system ? quick.system.volumeAvailable : false
                unavailableText: quick.system ? quick.system.volumeDetail : "нет данных"
            }

            QuickSlider {
                width: parent.width
                glyph: "brightness"
                label: "Яркость"
                value: quick.system ? quick.system.brightnessPercent : -1
                available: quick.system ? quick.system.brightnessAvailable : false
                unavailableText: "регулировка недоступна"
            }

            Item { width: parent.width; height: 28
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    SysIcon {
                        glyph: "battery"; width: 16; height: 16
                        color: Theme.textPrimary
                        dim: !(quick.system && quick.system.batteryAvailable)
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: quick.system && quick.system.batteryAvailable
                              ? (quick.system.batteryPercent + " %")
                              : (quick.system ? quick.system.batteryDetail : "нет данных")
                        color: quick.system && quick.system.batteryAvailable
                               ? Theme.textPrimary : Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                }
                TrayButton {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    height: 28
                    glyph: "power"
                    tooltip: "Питание"
                }
            }
        }
    }
}
