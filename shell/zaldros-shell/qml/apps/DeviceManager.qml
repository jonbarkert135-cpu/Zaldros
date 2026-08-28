import QtQuick
import QtQuick.Controls
import ZaldrosTheme
import ".."

// Zaldros «Диспетчер устройств»: the Windows tree of categories on the left, the properties of
// the selected device on the right, and a command bar with «Обновить конфигурацию оборудования».
//
// Every row comes from sysfs through DeviceModel. A device without a bound driver is marked, an
// empty category keeps its reason («ядро не показывает /sys/bus/pci/devices в этой среде»), and
// nothing is ever labelled with a marketing name the machine did not report.
Item {
    id: deviceManager
    property var model: null
    property int selected: -1
    property string status: ""

    Rectangle { anchors.fill: parent; color: Theme.appBackground }

    // --- command bar ---------------------------------------------------------------------------
    Item {
        id: commandBar
        width: parent.width
        height: Theme.commandBarHeight

        Text {
            x: 16
            anchors.verticalCenter: parent.verticalCenter
            text: deviceManager.model ? deviceManager.model.summary : "—"
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
        }

        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 264; height: 32; radius: Theme.radiusSmall
            color: rescanArea.containsMouse ? Theme.surfaceElevated : Theme.surface
            border.width: 1
            border.color: Theme.border
            Text {
                anchors.centerIn: parent
                text: "Обновить конфигурацию оборудования"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
            MouseArea {
                id: rescanArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    var result = deviceManager.model.rescan();
                    deviceManager.status = result.detail;
                }
            }
        }
    }

    // --- tree ----------------------------------------------------------------------------------
    ListView {
        id: tree
        objectName: "deviceTree"
        anchors.top: commandBar.bottom
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        width: parent.width * 0.52
        clip: true
        model: deviceManager.model
        delegate: Rectangle {
            width: tree.width
            height: Theme.listRowHeight
            color: index === deviceManager.selected && model.kind === "device"
                   ? Theme.surfaceElevated
                   : (hover.containsMouse ? Theme.surfaceCard : "transparent")
            Row {
                anchors.fill: parent
                anchors.leftMargin: model.kind === "category" ? 8 : 30
                spacing: 6
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: model.kind === "category"
                    text: model.expanded ? "⌄" : "›"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: tree.width - 120
                    elide: Text.ElideRight
                    text: model.title + (model.kind === "device" && !model.working ? "  ⚠" : "")
                    color: model.kind === "category" ? Theme.textPrimary
                         : (model.working ? Theme.textPrimary : "#ffb900")
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    font.bold: model.kind === "category"
                }
            }
            Text {
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                visible: model.kind === "category" && model.status !== ""
                text: model.status
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
            MouseArea {
                id: hover
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    if (model.kind === "category")
                        deviceManager.model.toggle(index);
                    else
                        deviceManager.selected = index;
                }
            }
        }
    }

    // --- properties ------------------------------------------------------------------------------
    Rectangle {
        id: properties
        anchors.top: commandBar.bottom
        anchors.left: tree.right
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        anchors.margins: 8
        radius: Theme.radiusMedium
        color: Theme.surfaceCard
        border.width: 1
        border.color: Theme.border

        property var row: deviceManager.selected >= 0 && deviceManager.model
                          ? deviceManager.model.get(deviceManager.selected) : null

        Text {
            anchors.centerIn: parent
            visible: !properties.row
            text: "Выберите устройство"
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
        }

        Column {
            x: 16; y: 14
            width: parent.width - 32
            spacing: 8
            visible: properties.row !== null

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                text: properties.row ? properties.row.title : ""
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSubtitle
            }
            Text {
                text: properties.row ? "Состояние: " + properties.row.status : ""
                color: properties.row && properties.row.working ? Theme.textSecondary : "#ffb900"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
            Repeater {
                model: properties.row ? properties.row.detailKeys.length : 0
                delegate: Row {
                    spacing: 8
                    Text {
                        width: 180
                        text: properties.row.detailKeys[index]
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    Text {
                        width: properties.width - 220
                        elide: Text.ElideRight
                        text: properties.row.detailValues[index]
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                }
            }
            Text {
                width: parent.width
                wrapMode: Text.WrapAnywhere
                text: properties.row ? "Источник: " + properties.row.source : ""
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
        }
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        text: deviceManager.status
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption
    }
}
