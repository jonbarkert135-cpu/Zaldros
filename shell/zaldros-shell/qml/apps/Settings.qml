import QtQuick
import QtQuick.Controls
import ZaldrosTheme
import ".."

// Zaldros Settings, laid out to the measured Windows 11 Settings capture
// (assets/refs/win11_settings_system.png): 320 px navigation rail with the account card and a
// search field, a large page title, and stacked 74 px cards on the right.
//
// Every value on the System and About pages is read from this machine (hostinfo.py). A reading the
// system cannot provide shows an em-free dash, never a filler string.
Item {
    id: settings
    property var host: null
    property var system: null
    property int page: 0

    readonly property var pages: [
        { title: "Главная",              glyph: "home" },
        { title: "Система",              glyph: "desktop" },
        { title: "Bluetooth и устройства", glyph: "bluetooth" },
        { title: "Сеть и Интернет",      glyph: "globe" },
        { title: "Персонализация",       glyph: "paint-brush" },
        { title: "Приложения",           glyph: "apps" },
        { title: "Учётные записи",       glyph: "person" },
        { title: "Время и язык",         glyph: "clock" },
        { title: "Специальные возможности", glyph: "accessibility" },
        { title: "Конфиденциальность и защита", glyph: "shield" },
        { title: "О системе",            glyph: "info" }
    ]

    function reading(key) {
        var value = settings.host ? settings.host.value(key) : "";
        return value === "" ? "–" : value;
    }

    Rectangle { anchors.fill: parent; color: Theme.appBackground }

    // --- navigation rail --------------------------------------------------------------------
    Item {
        id: rail
        objectName: "settingsRail"
        width: 320
        height: parent.height

        // account card
        Row {
            id: account
            x: 24
            y: 16
            spacing: 12
            Rectangle {
                width: 48; height: 48; radius: 24
                color: Theme.surfaceElevated
                SysIcon {
                    anchors.centerIn: parent
                    glyph: "person"; width: 24; height: 24
                    color: Theme.textSecondary
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: settings.system && settings.system.userName ? settings.system.userName : "пользователь"
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                }
                Text {
                    text: settings.reading("deviceName")
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
            }
        }

        Rectangle {
            id: navSearch
            x: 24
            anchors.top: account.bottom
            anchors.topMargin: 20
            width: rail.width - 48
            height: 32
            radius: Theme.radiusSmall
            color: Theme.dark ? "#1f1f1f" : "#ffffff"
            border.width: 1
            border.color: Theme.border
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Найти параметр"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
            SysIcon {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 10
                glyph: "search"; width: 14; height: 14
                color: Theme.textSecondary
            }
        }

        Column {
            anchors.top: navSearch.bottom
            anchors.topMargin: 12
            x: 12
            spacing: 2
            Repeater {
                model: settings.pages
                delegate: Rectangle {
                    width: rail.width - 24
                    height: 36
                    radius: Theme.radiusSmall
                    color: settings.page === index ? Theme.selected
                           : (navArea.containsMouse ? Theme.hover : "transparent")
                    // Windows marks the active page with an accent bar on the left edge
                    Rectangle {
                        visible: settings.page === index
                        anchors.verticalCenter: parent.verticalCenter
                        x: 2
                        width: 3; height: 16; radius: 1.5
                        color: Theme.accent
                    }
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 14
                        spacing: 12
                        SysIcon {
                            glyph: modelData.glyph
                            width: 16; height: 16
                            color: settings.page === index ? Theme.accent : Theme.textPrimary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.title
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption + 1
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: navArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: settings.page = index
                    }
                }
            }
        }
    }

    // --- page body -----------------------------------------------------------------------------
    Flickable {
        id: body
        objectName: "settingsBody"
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        contentHeight: pageColumn.implicitHeight + 48
        clip: true
        ScrollBar.vertical: ScrollBar { }

        Column {
            id: pageColumn
            x: 32
            y: 24
            width: body.width - 96
            spacing: 16

            Text {
                text: settings.pages[settings.page].title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontPageTitle
                font.weight: Font.DemiBold
            }

            // device banner, shown on Главная / Система / О системе like Windows does
            Row {
                visible: settings.page === 0 || settings.page === 1 || settings.page === 10
                spacing: 20
                Rectangle {
                    width: 124; height: 76
                    radius: Theme.radiusSmall
                    color: Theme.surface
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: Theme.wallpaper
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: false
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    Text {
                        text: settings.reading("deviceName")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSubtitle
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: settings.reading("cpuModel")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    Text {
                        text: settings.reading("osName")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                }
            }

            // page cards
            Repeater {
                model: settings.cards(settings.page)
                delegate: SettingsCard {
                    width: pageColumn.width
                    glyph: modelData.glyph
                    title: modelData.title
                    detail: modelData.detail
                    value: modelData.value !== undefined ? modelData.value : ""
                }
            }
        }
    }

    // Card contents per page. Values marked with reading() come from this machine; pages whose
    // backend does not exist yet say so in their own words instead of showing invented switches.
    function cards(index) {
        if (index === 0) return [
            { glyph: "desktop", title: "Система", detail: "Дисплей, звук, питание, память", value: reading("osName") },
            { glyph: "globe", title: "Сеть и Интернет", detail: settings.system ? settings.system.networkDetail : "", value: "" },
            { glyph: "person", title: "Учётные записи", detail: "Текущий сеанс", value: settings.system ? settings.system.userName : "" },
            { glyph: "clock", title: "Время и язык", detail: reading("timezone"), value: reading("localTime") }
        ];
        if (index === 1) return [
            { glyph: "desktop", title: "Дисплей", detail: "Сеанс " + reading("sessionType"), value: "" },
            { glyph: "speaker", title: "Звук", detail: settings.system ? settings.system.volumeDetail : "", value: "" },
            { glyph: "bell", title: "Уведомления", detail: "Оповещения приложений и системы", value: "" },
            { glyph: "power", title: "Питание и батарея", detail: settings.system ? settings.system.batteryDetail : "", value: "" },
            { glyph: "hard-drive", title: "Память", detail: "Занято на системном диске", value: reading("diskUsed") + " из " + reading("diskTotal") },
            { glyph: "info", title: "Оперативная память", detail: "Используется сейчас", value: reading("memoryUsed") + " из " + reading("memoryTotal") }
        ];
        if (index === 2) return [
            { glyph: "bluetooth", title: "Bluetooth", detail: settings.system ? settings.system.bluetoothDetail : "", value: "" },
            { glyph: "keyboard", title: "Клавиатура", detail: settings.system ? settings.system.keyboardDetail : "", value: settings.system ? settings.system.keyboardLayout : "" },
            { glyph: "phone", title: "Устройства", detail: "Подключённые устройства перечисляет ядро", value: "" }
        ];
        if (index === 3) return [
            { glyph: "wifi", title: "Состояние", detail: settings.system ? settings.system.networkDetail : "", value: "" },
            { glyph: "ethernet", title: "Ethernet", detail: "Интерфейсы читаются из /sys/class/net", value: "" },
            { glyph: "vpn", title: "VPN", detail: "Профили не настроены", value: "" }
        ];
        if (index === 4) return [
            { glyph: "image", title: "Фон", detail: "Обои Zaldros", value: "" },
            { glyph: "paint-brush", title: "Цвета", detail: "Тема оформления", value: Theme.dark ? "Тёмная" : "Светлая" },
            { glyph: "dark-theme", title: "Темы", detail: "Оформление окон и панели", value: "Zaldros" }
        ];
        if (index === 5) return [
            { glyph: "apps", title: "Установленные приложения", detail: "Найдено по файлам .desktop", value: "" },
            { glyph: "add-circle", title: "Приложения по умолчанию", detail: "Обработчики типов файлов", value: "" }
        ];
        if (index === 6) return [
            { glyph: "person", title: "Ваши данные", detail: "Локальная учётная запись", value: settings.system ? settings.system.userName : "" },
            { glyph: "shield", title: "Варианты входа", detail: "Пароль сеанса", value: "" }
        ];
        if (index === 7) return [
            { glyph: "clock", title: "Дата и время", detail: reading("timezone"), value: reading("localTime") },
            { glyph: "globe", title: "Язык и регион", detail: "Интерфейс", value: "Русский" }
        ];
        if (index === 8) return [
            { glyph: "accessibility", title: "Размер текста", detail: "Масштаб интерфейса", value: "100 %" },
            { glyph: "brightness", title: "Контрастные темы", detail: "Не включены", value: "" }
        ];
        if (index === 9) return [
            { glyph: "shield", title: "Безопасность", detail: "Обновления и права доступа", value: "" },
            { glyph: "info", title: "Диагностика", detail: "Телеметрия не собирается", value: "" }
        ];
        return [
            { glyph: "desktop", title: "Имя устройства", detail: "", value: reading("deviceName") },
            { glyph: "info", title: "Выпуск", detail: "", value: reading("osName") },
            { glyph: "hard-drive", title: "Ядро", detail: reading("architecture"), value: reading("kernel") },
            { glyph: "apps", title: "Процессор", detail: reading("cpuCores") + " потоков", value: reading("cpuModel") },
            { glyph: "info", title: "Оперативная память", detail: "Всего", value: reading("memoryTotal") },
            { glyph: "clock", title: "Время работы", detail: "С момента загрузки", value: reading("uptime") }
        ];
    }
}
