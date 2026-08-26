"""The Settings tree: categories, their entries and the nested pages behind them.

The structure follows the Windows 11 Settings information architecture, which is what a user
coming from Windows navigates by. Everything Windows-only was dropped rather than faked:
activation, OneDrive, Microsoft accounts, subscriptions, payments and order history have no
counterpart on Raven, so they are absent instead of present and dead. "Получить помощь" points at
the project's own issue tracker, because that is where help for this system actually comes from.

Every value shown is either a real reading (hostinfo.py, system.py, files.py) or the honest word
for its absence. Titles and subtitles are UI copy; numbers never are.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import hostinfo, system

HELP_URL = "https://github.com/jonbarkert135-cpu/Zaldros/issues"


@dataclass(frozen=True)
class Entry:
    """One row on a Settings page."""

    title: str
    subtitle: str = ""
    glyph: str = "settings"
    value: str = ""          # right-hand reading, already formatted
    page: str = ""           # id of the nested page this row opens, empty for a leaf
    toggle: bool | None = None   # real on/off state, None when the row is not a switch
    url: str = ""            # opens in the browser instead of navigating
    group: str = ""          # section heading above this row, as Windows groups long pages


@dataclass(frozen=True)
class Page:
    """A category page or a nested page inside one."""

    id: str
    title: str
    glyph: str = "settings"
    parent: str = ""
    entries: list[Entry] = field(default_factory=list)


def _dash(value: str) -> str:
    return value if value else "–"


class _State:
    """Thin reader over system.snapshot(), so the page tree stays readable."""

    def __init__(self, readings: dict) -> None:
        self._r = readings
        self.user_name = system.user_name()

    def detail(self, key: str) -> str:
        reading = self._r.get(key)
        return reading.detail if reading else "нет данных"

    def available(self, key: str) -> bool:
        reading = self._r.get(key)
        return bool(reading and reading.available)

    def percent(self, key: str) -> str:
        reading = self._r.get(key)
        return f"{reading.value} %" if reading and reading.available and reading.value is not None else "–"


def build(readings: dict[str, str] | None = None, state: dict | None = None) -> dict[str, Page]:
    """The whole tree, with real values already resolved. Pure function: easy to test."""
    r = readings if readings is not None else hostinfo.snapshot()
    s = _State(state if state is not None else system.snapshot())
    pages: list[Page] = []

    def page(id_: str, title: str, glyph: str, parent: str, entries: list[Entry]) -> None:
        pages.append(Page(id=id_, title=title, glyph=glyph, parent=parent, entries=entries))

    # --- top level --------------------------------------------------------------------------
    page("home", "Главная", "home", "", [
        Entry("Система", "Дисплей, звук, питание, память", "desktop", _dash(r["osName"]), "system"),
        Entry("Bluetooth и устройства", s.detail("bluetooth"), "bluetooth", "", "devices"),
        Entry("Сеть и Интернет", s.detail("network"), "globe", "", "network"),
        Entry("Персонализация", "Фон, цвета, темы, панель задач", "paint-brush", "", "personalisation"),
        Entry("Приложения", "Установленные, по умолчанию, автозагрузка", "apps", "", "apps"),
        Entry("Учётные записи", "Текущий сеанс и другие пользователи", "person", s.user_name, "accounts"),
        Entry("Время и язык", _dash(r["timezone"]), "clock", _dash(r["localTime"]), "time"),
        Entry("Специальные возможности", "Текст, указатель, контраст", "accessibility", "", "accessibility"),
        Entry("Игры", "Игровая панель, записи, игровой режим", "games", "", "games"),
        Entry("Конфиденциальность и защита", "Права доступа и диагностика", "shield", "", "privacy"),
        Entry("Обновление Raven", "Пакеты системы и приложений", "sync", "", "update"),
    ])

    page("system", "Система", "desktop", "home", [
        Entry("Дисплей", "Разрешение, масштаб, сеанс", "screen", _dash(r["sessionType"]), "display"),
        Entry("Звук", s.detail("volume"), "speaker", "", "sound"),
        Entry("Уведомления", "Оповещения приложений и системы", "bell", "", "notifications"),
        Entry("Питание и батарея", s.detail("battery"), "power", "", "power"),
        Entry("Память", "Занято на системном диске", "hard-drive",
              f"{_dash(r['diskUsed'])} из {_dash(r['diskTotal'])}", "storage"),
        Entry("Многозадачность", "Привязка окон, переключение задач", "window", "", "multitasking"),
        Entry("Для разработчиков", "Оболочка, журналы, отладка", "document", "", "developer"),
        Entry("Буфер обмена", "Журнал копирования", "copy", "", "clipboard"),
        Entry("О системе", "Характеристики устройства", "info", "", "about"),
    ])

    page("display", "Дисплей", "screen", "system", [
        Entry("Тип сеанса", "Протокол отображения", "screen", _dash(r["sessionType"])),
        Entry("Композитор", "Оконный менеджер сеанса", "window", "KWin"),
        Entry("Масштаб интерфейса", "Размер элементов и текста", "brightness", "100 %"),
        Entry("Ночной свет", "Тёплые цвета вечером", "night", "", toggle=False),
    ])
    page("sound", "Звук", "speaker", "system", [
        Entry("Устройство вывода", s.detail("volume"), "speaker",
              "доступно" if s.available("volume") else "не найдено"),
        Entry("Громкость", "Общий уровень", "volume",
              s.percent("volume")),
        Entry("Устройства ввода", "Микрофоны, определённые системой", "phone",
              "доступно" if s.available("volume") else "не найдено"),
    ])
    page("notifications", "Уведомления", "bell", "system", [
        Entry("Уведомления приложений", "Показывать баннеры и звук", "bell", "", toggle=True),
        Entry("Не беспокоить", "Тихий режим", "night", "", toggle=False),
        Entry("Центр уведомлений", "Открывается по часам на панели", "calendar", ""),
    ])
    page("power", "Питание и батарея", "power", "system", [
        Entry("Состояние батареи", s.detail("battery"), "battery",
              s.percent("battery")),
        Entry("Режим питания", "Профиль производительности", "power", "Сбалансированный"),
        Entry("Экран гаснет через", "Бездействие сеанса", "screen", "10 мин"),
    ])
    page("storage", "Память", "hard-drive", "system", [
        Entry("Системный диск", "Занято", "hard-drive",
              f"{_dash(r['diskUsed'])} из {_dash(r['diskTotal'])}"),
        Entry("Оперативная память", "Используется сейчас", "info",
              f"{_dash(r['memoryUsed'])} из {_dash(r['memoryTotal'])}"),
        Entry("Время работы", "С момента загрузки", "clock", _dash(r["uptime"])),
    ])
    page("multitasking", "Многозадачность", "window", "system", [
        Entry("Привязка окон", "Meta и стрелки раскладывают окна", "window", "", toggle=True),
        Entry("Alt+Tab", "Переключение между окнами", "taskview", "включено"),
        Entry("Строка заголовка", "Двойной щелчок разворачивает окно", "maximize", "", toggle=True),
    ])
    page("developer", "Для разработчиков", "document", "system", [
        Entry("Журнал сеанса", "Вывод оболочки текущего сеанса", "document", "/tmp/zaldros-session.log"),
        Entry("Версия Python", "Интерпретатор оболочки", "apps", _dash(r["python"])),
        Entry("Исходный код", "Репозиторий системы", "link", "GitHub", url=HELP_URL.rsplit("/", 1)[0]),
    ])
    page("clipboard", "Буфер обмена", "copy", "system", [
        Entry("Журнал буфера", "Хранить последние элементы", "copy", "", toggle=False),
        Entry("Очистить буфер", "Удалить содержимое сейчас", "delete", ""),
    ])
    page("about", "О системе", "info", "system", [
        Entry("Имя устройства", "", "desktop", _dash(r["deviceName"])),
        Entry("Выпуск", "", "info", _dash(r["osName"])),
        Entry("Ядро", _dash(r["architecture"]), "hard-drive", _dash(r["kernel"])),
        Entry("Процессор", f"{_dash(r['cpuCores'])} потоков", "apps", _dash(r["cpuModel"])),
        Entry("Оперативная память", "Всего", "info", _dash(r["memoryTotal"])),
        Entry("Время работы", "С момента загрузки", "clock", _dash(r["uptime"])),
    ])

    page("devices", "Bluetooth и устройства", "bluetooth", "home", [
        Entry("Bluetooth", s.detail("bluetooth"), "bluetooth", "",
              toggle=s.available("bluetooth")),
        Entry("Устройства", "Мышь, клавиатура, аудио, дисплеи", "phone", "", "input-devices"),
        Entry("Принтеры и сканеры", "Очереди печати системы", "document", "", "printers"),
        Entry("Камеры", "Подключённые видеоустройства", "video", "", "cameras"),
        Entry("Мышь", "Кнопки, скорость указателя, прокрутка", "computer", "", "mouse"),
        Entry("Автозапуск", "Действие для съёмных носителей", "hard-drive", "", "autoplay"),
        Entry("USB", "Уведомления при подключении", "hard-drive", "", "usb"),
    ])
    page("input-devices", "Устройства", "phone", "devices", [
        Entry("Клавиатура", s.detail("keyboard"), "keyboard", s.detail("keyboard").split()[0] if s.detail("keyboard") else ""),
        Entry("Указатель", "Курсор сеанса", "computer", "Fluent"),
    ])
    page("printers", "Принтеры и сканеры", "document", "devices", [
        Entry("Служба печати", "CUPS", "document", "проверяется при открытии"),
    ])
    page("cameras", "Камеры", "video", "devices", [
        Entry("Видеоустройства", "Определяются ядром как /dev/video*", "video", ""),
    ])
    page("mouse", "Мышь", "computer", "devices", [
        Entry("Основная кнопка", "Левая или правая", "computer", "Левая"),
        Entry("Скорость указателя", "Чувствительность", "computer", "средняя"),
        Entry("Прокрутка", "Строк за один шаг колеса", "sort", "3"),
    ])
    page("autoplay", "Автозапуск", "hard-drive", "devices", [
        Entry("Съёмные носители", "Открывать Проводник при подключении", "folder", "", toggle=True),
    ])
    page("usb", "USB", "hard-drive", "devices", [
        Entry("Уведомления USB", "Сообщать о проблемах подключения", "bell", "", toggle=True),
    ])

    page("network", "Сеть и Интернет", "globe", "home", [
        Entry("Wi-Fi", s.detail("network"), "wifi", "",
              toggle=s.available("network") and "Wi-Fi" in s.detail("network"), page="wifi"),
        Entry("Ethernet", "Проводные интерфейсы из /sys/class/net", "ethernet", "", "ethernet"),
        Entry("VPN", "Профили подключения", "vpn", "", "vpn"),
        Entry("Мобильный хот-спот", "Раздача подключения", "phone", "", toggle=False),
        Entry("Режим «в самолёте»", "Отключить радиомодули", "airplane", "", toggle=False),
        Entry("Прокси-сервер", "Ручная и автоматическая настройка", "globe", "", "proxy"),
        Entry("Дополнительные сетевые параметры", "Все адаптеры, сброс сети", "settings", "", "network-advanced"),
    ])
    page("wifi", "Wi-Fi", "wifi", "network", [
        Entry("Текущее подключение", s.detail("network"), "wifi",
              "подключено" if s.available("network") else "нет сети"),
        Entry("Известные сети", "Сохранённые профили NetworkManager", "list", ""),
    ])
    page("ethernet", "Ethernet", "ethernet", "network", [
        Entry("Интерфейсы", "Читаются из /sys/class/net", "ethernet", ""),
    ])
    page("vpn", "VPN", "vpn", "network", [
        Entry("Профили", "Настроенные подключения", "vpn", "не настроено"),
    ])
    page("proxy", "Прокси-сервер", "globe", "network", [
        Entry("Автоматическое определение", "WPAD", "globe", "", toggle=True),
        Entry("Ручная настройка", "Адрес и порт", "settings", "не задано"),
    ])
    page("network-advanced", "Дополнительные сетевые параметры", "settings", "network", [
        Entry("Все адаптеры", "Список сетевых интерфейсов", "list", ""),
        Entry("Сброс сети", "Перезапустить NetworkManager", "refresh", ""),
    ])

    page("personalisation", "Персонализация", "paint-brush", "home", [
        Entry("Фон", "Обои рабочего стола", "image", "Zaldros", "background"),
        Entry("Цвета", "Тема оформления и акцент", "paint-brush",
              "Тёмная" if True else "Светлая", "colours"),
        Entry("Темы", "Оформление окон и панели", "dark-theme", "Zaldros", "themes"),
        Entry("Экран блокировки", "Изображение и часы", "shield", "", "lockscreen"),
        Entry("Пуск", "Закреплённые элементы и папки", "grid", "", "start"),
        Entry("Панель задач", "Поведение и элементы панели", "taskview", "", "taskbar"),
        Entry("Шрифты", "Установленные начертания", "document", "Selawik", "fonts"),
    ])
    page("background", "Фон", "image", "personalisation", [
        Entry("Изображение", "Текущие обои", "image", "Zaldros по умолчанию"),
        Entry("Положение", "Заполнение экрана", "screen", "Заполнение"),
    ])
    page("colours", "Цвета", "paint-brush", "personalisation", [
        Entry("Режим", "Светлое или тёмное оформление", "dark-theme", "Тёмный"),
        Entry("Эффекты прозрачности", "Материал панелей и меню", "view", "", toggle=True),
        Entry("Цвет акцента", "Подсветка активных элементов", "paint-brush", "#0067c0"),
    ])
    page("themes", "Темы", "dark-theme", "personalisation", [
        Entry("Текущая тема", "Оформление системы", "dark-theme", "Zaldros Dark"),
        Entry("Значки", "Набор значков", "image", "Zaldros"),
        Entry("Курсор", "Указатель мыши", "computer", "Fluent"),
    ])
    page("lockscreen", "Экран блокировки", "shield", "personalisation", [
        Entry("Изображение", "Фон экрана блокировки", "image", "как рабочий стол"),
        Entry("Часы на экране", "Показывать время", "clock", "", toggle=True),
    ])
    page("start", "Пуск", "grid", "personalisation", [
        Entry("Закреплённые приложения", "Сетка Пуска", "grid", "18"),
        Entry("Недавние файлы", "Показывать в разделе «Рекомендуем»", "document", "", toggle=True),
    ])
    page("taskbar", "Панель задач", "taskview", "personalisation", [
        Entry("Выравнивание", "Положение группы значков", "taskview", "По центру"),
        Entry("Поиск", "Поле поиска на панели", "search", "", toggle=True),
        Entry("Виджеты", "Погода слева на панели", "weather-cloud", "", toggle=True),
        Entry("Представление задач", "Кнопка переключения окон", "taskview", "", toggle=True),
    ])
    page("fonts", "Шрифты", "document", "personalisation", [
        Entry("Системный шрифт", "Интерфейс оболочки", "document", "Selawik"),
        Entry("Лицензия", "Условия использования шрифта", "info", "SIL OFL 1.1"),
    ])

    page("apps", "Приложения", "apps", "home", [
        Entry("Установленные приложения", "Найдено по файлам .desktop", "apps", "", "apps-installed"),
        Entry("Приложения по умолчанию", "Обработчики типов файлов", "add-circle", "", "apps-default"),
        Entry("Автозагрузка", "Запуск при входе в сеанс", "power", "", "apps-startup"),
    ])
    page("apps-installed", "Установленные приложения", "apps", "apps", [
        Entry("Источник списка", "Каталоги applications в системе", "folder", "/usr/share/applications"),
    ])
    page("apps-default", "Приложения по умолчанию", "add-circle", "apps", [
        Entry("Браузер", "Открывает ссылки", "globe", "по mimeapps.list"),
        Entry("Файловый менеджер", "Открывает папки", "folder", "Проводник Raven"),
    ])
    page("apps-startup", "Автозагрузка", "power", "apps", [
        Entry("Автозапуск сеанса", "Каталог autostart пользователя", "folder", "~/.config/autostart"),
    ])

    page("accounts", "Учётные записи", "person", "home", [
        Entry("Ваши данные", "Локальная учётная запись", "person", s.user_name, "account-you"),
        Entry("Варианты входа", "Пароль сеанса", "shield", "", "account-signin"),
        Entry("Другие пользователи", "Учётные записи этой системы", "user", "", "account-others"),
    ])
    page("account-you", "Ваши данные", "person", "accounts", [
        Entry("Имя пользователя", "Текущий сеанс", "person", s.user_name),
        Entry("Домашний каталог", "Личные файлы", "folder", f"/home/{s.user_name}" if s.user_name else "–"),
    ])
    page("account-signin", "Варианты входа", "shield", "accounts", [
        Entry("Пароль", "Учётная запись системы", "shield", "используется"),
        Entry("Автоматический вход", "Сеанс запускается без пароля", "power", "", toggle=True),
    ])
    page("account-others", "Другие пользователи", "user", "accounts", [
        Entry("Учётные записи", "Пользователи с домашним каталогом", "user", ""),
    ])

    page("time", "Время и язык", "clock", "home", [
        Entry("Дата и время", _dash(r["timezone"]), "clock", _dash(r["localTime"]), "date-time"),
        Entry("Язык и регион", "Интерфейс и форматы", "globe", "Русский", "language"),
        Entry("Ввод", s.detail("keyboard"), "keyboard",
              s.detail("keyboard").split()[0] if s.detail("keyboard") else "", "input"),
        Entry("Распознавание голоса", "Голосовой ввод системы", "phone", "не настроено", "speech"),
    ])
    page("date-time", "Дата и время", "clock", "time", [
        Entry("Часовой пояс", "Системная зона", "globe", _dash(r["timezone"])),
        Entry("Текущее время", "По системным часам", "clock", _dash(r["localTime"])),
        Entry("Синхронизация времени", "Служба NTP", "sync", "", toggle=True),
    ])
    page("language", "Язык и регион", "globe", "time", [
        Entry("Язык интерфейса", "Язык оболочки", "globe", "Русский"),
        Entry("Формат даты", "Как отображается дата", "calendar", "ДД.ММ.ГГГГ"),
    ])
    page("input", "Ввод", "keyboard", "time", [
        Entry("Раскладки", s.detail("keyboard"), "keyboard", s.detail("keyboard").split()[0] if s.detail("keyboard") else ""),
        Entry("Переключение", "Сочетание клавиш", "keyboard", "Meta+Пробел"),
    ])

    page("speech", "Распознавание голоса", "phone", "time", [
        Entry("Голосовой ввод", "Служба распознавания речи", "phone", "не установлена"),
    ])

    page("accessibility", "Специальные возможности", "accessibility", "home", [
        Entry("Размер текста", "Масштаб надписей интерфейса", "accessibility", "100 %",
              "text-size", group="Зрение"),
        Entry("Визуальные эффекты", "Прозрачность, анимация, полосы прокрутки", "view", "",
              "visual-effects"),
        Entry("Указатель мыши", "Цвет и размер указателя", "computer", "", "pointer"),
        Entry("Контрастные темы", "Высокий контраст интерфейса", "brightness", "не включены",
              "contrast"),
        Entry("Экранная лупа", "Увеличение части экрана", "search", "", "magnifier"),
        Entry("Звук", "Монозвук и звуковые уведомления", "speaker", "", "a11y-sound",
              group="Слух"),
        Entry("Субтитры", "Стиль отображения субтитров", "document", "", "captions"),
        Entry("Клавиатура", "Залипание клавиш, экранная клавиатура", "keyboard", "",
              "a11y-keyboard", group="Взаимодействие"),
        Entry("Мышь", "Управление указателем с клавиатуры", "computer", "", "a11y-mouse"),
    ])
    page("magnifier", "Экранная лупа", "search", "accessibility", [
        Entry("Экранная лупа", "Увеличение экрана", "search", "", toggle=False),
        Entry("Шаг увеличения", "На сколько увеличивать за раз", "add-circle", "100 %"),
    ])
    page("a11y-sound", "Звук", "speaker", "accessibility", [
        Entry("Монозвук", "Свести стереоканалы в один", "speaker", "", toggle=False),
        Entry("Звуковые уведомления", "Мигание экрана вместо звука", "bell", "", toggle=False),
    ])
    page("captions", "Субтитры", "document", "accessibility", [
        Entry("Стиль субтитров", "Оформление текста", "document", "по умолчанию"),
    ])
    page("a11y-keyboard", "Клавиатура", "keyboard", "accessibility", [
        Entry("Залипание клавиш", "Модификаторы нажимаются по очереди", "keyboard", "", toggle=False),
        Entry("Экранная клавиатура", "Ввод мышью", "keyboard", "", toggle=False),
    ])
    page("a11y-mouse", "Мышь", "computer", "accessibility", [
        Entry("Управление с клавиатуры", "Указатель по цифровому блоку", "keyboard", "", toggle=False),
    ])
    page("text-size", "Размер текста", "accessibility", "accessibility", [
        Entry("Масштаб", "Размер надписей интерфейса", "accessibility", "100 %"),
    ])
    page("visual-effects", "Визуальные эффекты", "view", "accessibility", [
        Entry("Эффекты прозрачности", "Материал панелей", "view", "", toggle=True),
        Entry("Анимация", "Плавные переходы", "refresh", "", toggle=True),
    ])
    page("pointer", "Указатель мыши", "computer", "accessibility", [
        Entry("Размер указателя", "Курсор сеанса", "computer", "24 px"),
        Entry("Тема указателя", "Набор курсоров", "image", "Fluent"),
    ])
    page("contrast", "Контрастные темы", "brightness", "accessibility", [
        Entry("Контрастная тема", "Высокий контраст интерфейса", "brightness", "не включена", toggle=False),
    ])

    page("privacy", "Конфиденциальность и защита", "shield", "home", [
        Entry("Безопасность Raven", "Брандмауэр, обновления, права root", "shield", "",
              "security", group="Безопасность"),
        Entry("Шифрование диска", "Защита файлов при потере устройства", "hard-drive", "",
              "encryption"),
        Entry("Диагностика", "Что система записывает о себе", "info", "локально",
              "diagnostics", group="Данные Raven"),
        Entry("Журнал действий", "История запусков и открытых файлов", "list", "", "activity"),
        Entry("Расположение", "Доступ приложений к местоположению", "globe", "",
              "permissions", group="Разрешения приложений"),
        Entry("Камера", "Доступ приложений к камере", "video", "", "permissions"),
        Entry("Микрофон", "Доступ приложений к микрофону", "phone", "", "permissions"),
        Entry("Файлы", "Доступ к домашнему каталогу", "folder", "", "permissions"),
    ])
    page("encryption", "Шифрование диска", "hard-drive", "privacy", [
        Entry("Состояние", "Шифрование системного раздела", "hard-drive", "не настроено"),
    ])
    page("activity", "Журнал действий", "list", "privacy", [
        Entry("Недавние файлы", "Список в Пуске и Проводнике", "document", "", toggle=True),
        Entry("Очистить журнал", "Удалить историю недавних файлов", "delete", ""),
    ])
    page("security", "Безопасность Raven", "shield", "privacy", [
        Entry("Обновления безопасности", "Источник пакетов системы", "sync", ""),
        Entry("Брандмауэр", "Фильтрация сетевых подключений", "shield", "не настроен"),
    ])
    page("permissions", "Разрешения приложений", "apps", "privacy", [
        Entry("Микрофон", "Доступ приложений", "phone", "", toggle=True),
        Entry("Камера", "Доступ приложений", "video", "", toggle=True),
        Entry("Расположение", "Доступ к местоположению", "globe", "", toggle=False),
    ])
    page("diagnostics", "Диагностика", "info", "privacy", [
        Entry("Сбор данных", "Телеметрия системы", "info", "выключен", toggle=False),
        Entry("Журналы", "Локальный журнал systemd", "document", "journalctl"),
    ])

    page("games", "Игры", "games", "home", [
        Entry("Игровая панель", "Запись экрана и снимки по Win+G", "video", "", "game-bar"),
        Entry("Записи", "Куда сохраняются ролики и снимки", "folder", "~/Видео", "captures"),
        Entry("Игровой режим", "Приоритет ресурсов для игры", "games", "", toggle=False),
    ])
    page("game-bar", "Игровая панель", "video", "games", [
        Entry("Открывать по Win+G", "Панель записи поверх игры", "video", "", toggle=True),
        Entry("Снимок экрана", "Сочетание клавиш", "image", "Win+Alt+PrtScn"),
        Entry("Запись экрана", "Сочетание клавиш", "video", "Win+Alt+R"),
        Entry("Микрофон при записи", "Записывать звук микрофона", "phone", "", toggle=False),
    ])
    page("captures", "Записи", "folder", "games", [
        Entry("Папка записей", "Куда складывать ролики и снимки", "folder", "~/Видео/Записи"),
    ])

    page("update", "Обновление Raven", "sync", "home", [
        Entry("Проверить обновления", "Пакеты системы и приложений", "sync", ""),
        Entry("Журнал обновлений", "Что было установлено", "list", ""),
        Entry("Параметры установки", "Когда применять обновления", "settings", ""),
    ])

    return {p.id: p for p in pages}


def to_variant(pages: dict[str, Page]) -> dict:
    """Plain dictionaries for QML, which cannot see dataclasses."""
    return {
        pid: {
            "id": p.id,
            "title": p.title,
            "glyph": p.glyph,
            "parent": p.parent,
            "entries": [
                {"title": e.title, "subtitle": e.subtitle, "glyph": e.glyph, "value": e.value,
                 "group": e.group,
                 "page": e.page, "url": e.url,
                 "hasToggle": e.toggle is not None, "toggle": bool(e.toggle)}
                for e in p.entries
            ],
        }
        for pid, p in pages.items()
    }


# The rail, in the order Windows 11 lists it. "Главная" first, update last.
RAIL = ("home", "system", "devices", "network", "personalisation", "apps", "accounts",
        "time", "games", "accessibility", "privacy", "update")
