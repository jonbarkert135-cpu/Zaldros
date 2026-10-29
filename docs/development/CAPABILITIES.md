# Реестр возможностей Zaldros OS

Срез P01: 2026-10-26, HEAD `12afe1f572193fa105e0b2cd27a77b0715b4d605`.
P02 update: [trusted build/provenance](../../build/provenance/README.md) now implements
the rootfs authenticity gate and explicit asset staging described as missing below.
The P01 matrix remains the baseline; subsequent results are in PROGRESS.md. Real
Ubuntu artifact authentication/extraction subsequently passed; asset licensing
gaps remain open. This does not promote system/boot/E2E/hardware checks to PASS.
Статус относится к этому исходному коду и указанной среде, а не к последнему
непроверенному сообщению CI. Рабочая цель — developer alpha из [PLAN.md](PLAN.md).
Это реестр сценариев, не процент готовности и не замена спецификации.

## Как читать доказательства

Реализация: **PARTIAL** — часть сценария есть, **ABSENT** — завершённого пути не
найдено, **PRESENT** — указанный ограниченный механизм есть в коде.
Отсутствие проверки не означает, что механизм сломан.

- **U** — unit/локальные файлы/Qt offscreen; тест может запускать настоящий PTY,
  но это ещё не desktop E2E.
- **B** — приватный dbus-daemon с MockSystem/тестовыми службами; не NetworkManager
  или BlueZ целевой системы. Некоторые проверки CLI используют fake runner.
- **S** — настоящая служба в целевой Linux-сессии; **E** — действие пользователя
  до независимого readback; **H** — реальное устройство/драйвер.
- PASS / FAIL / SKIPPED / UNRUN описывают результат проверки, BLOCKED — конкретный
  отсутствующий prerequisite. Наличие тестового файла само по себе не даёт PASS.

**Для всех строк ниже S/E/H = UNRUN в текущем цикле**, кроме явно отмеченного
локального воспроизведения. Нет принятой текущей VM/hardware-матрицы.
Причины: отсутствует подтверждённая целевая Wayland/systemd-сессия, QEMU/KVM и
целевое оборудование; установка их в рамках документационного P01 не выполнялась.
Исторические отчёты ISO перечислены отдельно, не перенесены в текущие PASS.

## Источники и выполнявшиеся проверки

Корень тестов **T** = `shell/zaldros-shell/tests/`, моделей **M** =
`shell/zaldros-shell/zaldros_shell/`, QML **Q** = `shell/zaldros-shell/qml/`,
backend **B/** = `backend/zaldros_backend/`. Пути в таблице относительно этих корней.
Имена методов — точки для навигации по коду, а не обещание их UI-доступности.

| ID | Команда и среда | Результат |
| --- | --- | --- |
| V1 | `python -m pytest tools -q`, root, подготовленный venv | 44 PASS, exit 0, повторено в P01 |
| V2 | `QT_QPA_PLATFORM=offscreen python -m pytest tests -q -rs`, shell directory, предшествующий аудит того же HEAD | 514 PASS, 1 SKIPPED (нет PIL), 61 warning о forkpty, exit 0; полный лог `/tmp/zaldros-audit-shell.log` |
| V3 | P01: семь файлов T: settings_tree, settings_controls, backend_settings, backend_connectivity, system, kwin_switcher_script, files | 112 PASS, 0 skipped, exit 0, 72.69s; не отдельная проверка живых служб |
| V4 | `python -m pytest tests -q -rs`, apps/writer, предшествующий аудит того же HEAD | 9 PASS, 6 SKIPPED (движок/UNO), exit 0 |
| V5 | Та же команда, apps/sheets, P01 | 6 PASS, 9 SKIPPED (движок/UNO), exit 0 |
| V6 | Та же команда, apps/slides, P01 | 3 PASS, 12 SKIPPED (движок/UNO), exit 0 |
| V7 | `python -m zaldros_compat --check`, tools/zaldros-compat, P01 | PASS: 8 apps / 13 hardware записей, exit 0; это gate структуры/доказательств записей |
| V8 | `settingspages.build(state={})` и `app.UI_FONT_PREFERENCE`, P01 | Подтверждено расхождение: UI Selawik, shell PT Sans; 69 страниц, 16 toggle-строк без control |

Временные логи не считаются долговечными release-артефактами. Повторение тестов
после изменения кода необходимо; V2 не описывает будущие версии.

## Матрица сценариев

P0 — целостность/безопасность/доверие сборки; P1 — обязательный alpha workflow;
P2 — расширение или поздний release gate. Это приоритет разрыва, а не severity
воспроизведённой аварии. Критерии выполнения указаны в PLAN/PROMPTS.

| ID / сценарий | UI → код → системный источник | Реализация и U/B evidence | Разрыв и следующий этап |
| --- | --- | --- | --- |
| C01 Boot/login/logout | build/iso/build-iso.sh session unit → KWin/logind; B/session.py:session,terminate | PARTIAL; T/test_boot_report.py, test_flat_layout.py, test_iso_packages.py в V2 — U проверяет контракты/упаковку | P1: installed login отсутствует, live autologin не равен login manager; P05/P13/P17/P18 |
| C02 Настоящие окна/taskbar | Q/Shell.qml, AppWindow.qml → M/model.py:AppModel → отдельные KWin script/tabbox в system/theme | PARTIAL; T/test_switcher.py, test_kwin_switcher_script.py, test_snap_layouts.py, test_snap_assist.py в V2; script tests в V3 — U | P1: внутренний QML Item не внешний Wayland client; panel/workarea, external taskbar, global shortcuts; P05 |
| C03 Start/launch/search | Q/StartMenu.qml, SearchFlyout.qml → InstalledAppModel.launchRow → M/desktop_entries.py:discover,launch → .desktop/Popen | PARTIAL; T/test_desktop_entries.py, test_input.py в V2 — U/render; поиск фильтрует приложения | P1: XDG desktop-id/override, поля запуска, launch failure и окно; settings/file search не доказан; P06 |
| C04 Экран/DPI/яркость | Settings display/displays-multiple, QuickSettings → Registry → B/display.py:set_output_mode,set_output_scale,set_brightness → KScreen/PowerDevil/sysfs | PARTIAL; T/test_backend_facets.py, test_settings_controls.py в V2/V3 — U/B | P1: multi-monitor shell и безопасный rollback не завершены; P10 |
| C05 Звук/микрофон/микшер | Settings sound, QuickSettings → Registry/SystemState → B/audio.py:outputs,inputs,streams,set_* → wpctl/pactl | PARTIAL; T/test_backend_facets.py, test_backend_connectivity.py в V2/V3 — fake CLI/U | P1: readback на PipeWire, внешние изменения/hotplug/restart; watch не даёт live подписку; P08 |
| C06 Сеть/Wi-Fi/Ethernet | Settings network/wifi, QuickSettings → Registry/SystemState → B/network.py:status,request_scan,connect_wifi,set_wifi_enabled → NM | PARTIAL; T/test_backend_facets.py, test_backend_connectivity.py, test_settings_controls.py — U/B V2/V3 | P1: toggle/scan в UI не полный connect flow; WPA modes/secrets/activation result; P07 |
| C07 VPN/DNS/proxy/airplane | Settings vpn/proxy → Registry → B/network.py:activate_saved,deactivate,dns_servers,proxy; Bluetooth power | PARTIAL; T/test_backend_connectivity.py, test_settings_controls.py — U/B V2/V3 | P1: VPN сохранённых профилей, DNS/proxy в основном чтение; airplane не доказывает rfkill всех радио и откат частичного отказа; P07/P09 |
| C08 Bluetooth/периферия | Settings devices/input-devices → Registry → B/bluetooth.py:pair,trust,connect,remove → BlueZ | PARTIAL; T/test_backend_connectivity.py, test_backend_facets.py — B V2/V3 | P1: pairing agent/consent/PIN, полный UI и железо; P09 |
| C09 Mouse/touchpad/layout | Settings mouse/touchpad/input → Registry → B/inputdevices.py:set_for_kind; session.py:switch_layout; localetime.py:set_x11_keyboard → KWin/localed | PARTIAL; T/test_backend_settings.py, test_settings_controls.py, test_system.py — U/B V2/V3 | P1: active/default layout разные контракты, несколько устройств и recovery; P10 |
| C10 Notification/DND | Q/NotificationCenter.qml → M/model.py:SystemState/Prefs; B/notifications.py:NotificationServer/Client, service.py:ObjectServer | PARTIAL; T/test_backend.py, test_prefs.py, test_settings_controls.py — U/B; test_incoming_methods.py проверяет transport FIFO на private bus, не внешний notify в оболочке | P1: wiring NotificationServer и drain scheduling, внешний notify, действия/timeout/owner conflict, история/баннеры в сессии; P04/P12 |
| C11 Clipboard | Q/ClipboardFlyout.qml → M/model.py:ClipboardModel → M/clipboard.py, Qt clipboard | PRESENT ограниченная история; T/test_clipboard.py, test_settings_controls.py — U V2/V3 | P1: external apps/Wayland lifecycle, sensitive MIME и retention; P12/P13 |
| C12 Питание/профили/suspend | Settings power/recovery, shell → Registry → B/power.py:suspend,hibernate,profiles,set_profile,power_off,reboot → UPower/logind | PARTIAL; T/test_backend_facets.py, test_backend_connectivity.py — B V2/V3 | P1: resume всех подсистем, inhibitors, реальная батарея/крышка; P14 |
| C13 Files/trash/restore/open | Q/apps/Explorer.qml → M/model.py:FileModel → M/files.py:create_folder,rename,move_to_trash,open_with_default_application | PARTIAL; T/test_files.py — реальные temp files/U V2/V3 | P1: copy/move/restore, symlink/FS/metadata consistency; launch не подтверждает открытие файла; P11 |
| C14 Носители/mount/eject | Settings storage/storage-volumes → Registry → B/storage.py:mount,unmount,eject → UDisks | PARTIAL; T/test_backend_facets.py, test_settings_controls.py — B V2/V3 | P1: readback/занятое устройство, hotplug, безопасное извлечение и UX; P11 |
| C15 Установленные/default/autostart | Settings apps-*; Task Manager startup → Registry/StartupModel → B/defaultapps.py:set_role; processes.py:set_startup_enabled; .desktop | PARTIAL; T/test_backend_settings.py, test_processes.py — U/temp files V2/V3 | P1: XDG precedence, типы MIME, UI startup внутри Task Manager, не все Settings строки — controls; P06/P11 |
| C16 Установка приложений | Settings apps-installed показывает список; системный package install UI/transaction не найден | ABSENT завершённый install/remove; специальный E2E тест не найден | P1: app channel/install/uninstall/signatures/progress; P15 |
| C17 Аккаунты/авторизация/lock | Settings account-* → Registry → B/accounts.py:set_admin,set_locked,set_automatic_login; auth.py:check; session.py:lock → accountsservice/polkit/logind | PARTIAL; T/test_backend_settings.py, test_settings_controls.py, test_backend_facets.py — B V2/V3 | P1: create/delete/password, последний admin, lock/unlock и agent в сессии; P13 |
| C18 Дата/язык/регион | Settings date-time/language → Registry → B/localetime.py:set_timezone,set_ntp,set_language → timedated/localed | PARTIAL; T/test_backend_settings.py, test_settings_controls.py — B V2/V3 | P1: системная LANG не перевод UI, RU/EN pipeline не доказан; P13/P16 |
| C19 Privacy/firewall | Settings privacy/security/permissions → Registry → B/permissions.py:set_device,set_app → PermissionStore; firewall.py:set_enabled → firewalld/ufw/pkexec | PARTIAL; T/test_backend_settings.py, test_settings_controls.py — B/temp file/fake runner V2/V3 | P0: actual rules и denied/agent/readback; portal permission не ограничивает native app; P13 |
| C20 Обновления | Settings update → UpdateCheck/private worker Bus → B/updates.py:updates,refresh → PackageKit; Registry для CLI/legacy | PARTIAL query/refresh, cached UI/deadline/stop waiting и service-file activation; T/test_backend_settings.py, test_settings_controls.py, test_update_check.py, test_update_activation.py — B/Qt на test service | P1: реальный PackageKit/polkit/network gate открыт; install lifecycle/reboot/dpkg recovery нет; общий transport recovery и прочие GUI reads остаются P04/P15 |
| C21 Recovery/encryption | Settings recovery: reboot/UEFI controls; encryption — статическая строка; RECOVERY.md — контракт | PARTIAL только firmware/reboot; T/test_backend_settings.py — B V2/V3 | P0: нет проверенного rollback/restore/encryption readback; не обещать bootc на apt; P18 |
| C22 Accessibility | Settings accessibility и дочерние страницы → преимущественно static Entry; pref:visual.animations реальный pref | PARTIAL UI; render/input tests V2 не проверяют screen reader | P1: отсутствует доказательство системных magnifier/sticky keys/contrast и AT-SPI, focus core workflow; P16 |
| C23 Personalisation | Settings background/colours/themes/fonts/start/taskbar → Prefs/Registry → M/prefs.py и Q theme | PARTIAL prefs; T/test_prefs.py, test_ui_font.py в V2; V8 подтверждает неверный font label | P1: static vs applied settings; Selawik/stale product labels; P16, дефект D01 ниже |
| C24 Gaming/capture | Q/GameBar*, Settings games → M/model.py:GameBarModel → capture.py/portal.py → Spectacle/ffmpeg/portal/PipeWire | PARTIAL; T/test_capture.py — U с fake runner V2 | P2: consent/Unix FD, декодирование видео, global hotkeys, GameMode только строка; P12/P19 |
| C25 Terminal | Q/apps/Terminal.qml → M/model.py:TerminalModel → B/terminal.py:PtySession/Screen → настоящий PTY/shell | PRESENT ограниченный terminal; T/test_terminal.py — U/PTY V2 | P1: полная эмуляция, lifecycle и forkpty warning требуют проверки; external process не desktop E2E; P04/P11/P17 |
| C26 Task Manager | Q/apps/TaskManager.qml → ProcessModel/StartupModel → B/processes.py:sample,end → /proc/signals/autostart | PRESENT ограниченная утилита; T/test_processes.py, test_backend_overhead.py — U/fixtures V2 | P1: права, PID reuse, реальные процессы/нагрузки/GPU и sampling в сессии; P14/P17 |
| C27 Device Manager | Q/apps/DeviceManager.qml → DeviceModel → B/devices.py:tree,problems,rescan → sysfs | PRESENT inventory/rescan; T/test_devices.py — U/fixtures V2 | P2: driver install/update не следует из tree; реальный hardware matrix; P20 |
| C28 Services/diagnostics | Settings developer/diagnostics, tools → B/services.py:start,stop,restart; facade.status; collect-logs.sh | PARTIAL; T/test_backend_facets.py, test_collect_logs.py, test_backend_overhead.py V2; tools V1 | P1: работающий systemd, wait job completion, privacy журналов; P14/P17 |
| C29 Writer | apps/writer QML → model/engine:WriterEngine/convert → LibreOffice Writer/UNO | PARTIAL; V4 U PASS; engine SKIPPED | P2: настоящие edit/save/reopen/PDF и fidelity fixtures; P19 |
| C30 Sheets | apps/sheets QML → model/engine → Calc/UNO | PARTIAL; V5 U PASS; engine SKIPPED | P2: формулы/ошибки/XLSX round-trip на реальном Calc, UI не равен engine; P19 |
| C31 Slides | apps/slides QML → model/engine:ImpressEngine → Impress/UNO | PARTIAL; V6 U PASS; engine и один UI scenario SKIPPED | P2: настоящий deck/edit/export/PPTX round-trip; P19 |
| C32 Windows apps/games | tools/zaldros-compat/data registry → check; выбран Wine/Proton в документах | PARTIAL registry; V7 PASS только evidence gate | P2: не найден завершённый install/launch flow и свежая app/hardware evidence; P19 |
| C33 Installer | INSTALL.md design; live ISO builder не устанавливает ОС на выбранный диск | ABSENT завершённый installer; install E2E не найден | P0: partition confirmation/boot/пользователь/шифрование/recovery, только disposable VM; P18 |
| C34 Доверие и сборка | build/iso/build-iso.sh → BASE_TARBALL curl → tar; theme installer, THIRD_PARTY_LICENSES.md | PARTIAL; T/test_build_iso_diagnostics.py, test_iso_uefi_evidence.py, test_publish_evidence.py V2 — U shell fixtures | P0: нет проверки rootfs signed digest перед tar; provenance и SBOM; P02/P03 |
| C35 Измерения и release | tools/zaldros-bench → collect/compare; build/iso/selftest.py, uitest.py, ui-drive.py, report.py | PARTIAL; tools V1, T/test_serial_reports.py, test_boot_report.py V2 — U | P2: текущий boot+functional evidence, KVM/TCG distinction, hardware/performance/signing gates; P17/P20 |

## Alpha-контракт и ограничения

Обязательны C01–C23, C25–C26, C28 и C34–C35 в границах сценария PLAN.md:
работа обычного пользователя с настоящими окнами, сетью/звуком/файлами/настройками,
понятные отказы, отсутствие зависаний, сохранение состояния после relogin.
Наличие control в реестре ещё не означает законченный UI всех действий.
C21 до installed alpha ограничивается честной информацией и reboot/firmware;
полный recovery/installer C33 — следующий рубеж P18, не скрытая обязанность первого ISO.
Office/Wine, gaming/performance enhancements и release certification не блокируют
первый Linux developer alpha, но не объявляются работающими без соответствующего gate.

Предположения: x86_64; Ubuntu 26.04 и KWin 6 сохраняются как текущая гипотеза;
full — контрольный кандидат для первого VM smoke, не победитель сравнения;
RU/EN обязательны, системные update — apt/PackageKit без обещания атомарности;
Flatpak из ADR — кандидат app channel, технический lifecycle ещё не реализован.
Выбор железа, Secure Boot и release brand clearance остаются открытыми.

## Подтверждённый дефект и следующий кодовый шаг

**D01 (C23): страница fonts сообщает Selawik при UI_FONT_PREFERENCE = PT Sans.**
Воспроизведение в P01: импорт settingspages/app под подготовленным venv,
`settingspages.build(state={})['fonts'].entries[0].value` → `Selawik`,
`app.UI_FONT_PREFERENCE` → `('PT Sans',)`. Это ошибка информации, не падение GUI.
Рядом есть 16 toggle-строк без control и статический encryption status «не настроено»:
они не доказывают состояние соответствующих подсистем. Нужен общий contract
measured/configured/unsupported, а не смена одного hardcoded названия.
Исправление — в UI/локализации P16; не маскировать неверный статус как SYSTEM PASS.

Следующий этап P02 начинается с **D02/F08 (C34)**: rootfs распаковывается до
проверки подписанного checksum. Подтверждено чтением полного build-iso.sh:
единственный fetch-путь `curl -fsSL "$BASE_TARBALL" | tar -xz -C "$ROOT"`,
в скрипте нет SHA256/gpg проверки этого архива. До root-сборки заменить путь на
download → authenticated manifest → digest → extract; тест повреждения/неверной
подписи обязан отказать до tar. Отдельно составить provenance поставляемых assets.

F01–F12 аудита сверены на неизменившемся HEAD: F01/F02/F03/F05/F06/F07/F08/F10/F11/F12
остаются наблюдениями кода/документации; F04 — неподтверждённый recovery gap,
F09 — edge-case риски, не доказанная потеря данных. D01 — дополнительное
воспроизведённое расхождение. Общий reimplementation не обоснован.

Уточнение 2026-10-28: F04 воспроизведён на реальном приватном dbus-daemon.
Перезапуск службы терял sender-bound события; отсутствующий/unique sender допускал
чужие сигналы; повторный AddMatch оставлял правило после отмены; presence cache не
следовал смене владельца. Исправление и восемь регрессий:
T/test_backend_owner_recovery.py, [итерация 0020](../state/iteration-reports/0020-service-owner-recovery.md).
Проверена доставка до facade/Qt. Перезапуск самой шины, независимый snapshot при
смене owner, асинхронный GUI и настоящие системные службы остаются отдельными gates.

## Полнота разделов Settings

Следующая таблица охватывает все literal `page()` в settingspages.py.
Группа Cxx ведёт к UI/backend, источнику, тестам и разрыву выше; страницы навигации
сами не выполняют системных операций. Перечень control — прямые literal `C(...)`;
динамические выходы/тома/аккаунты/VPN/потоки указаны отдельно, не выдуманы для контейнера.
Здесь фиксируется код, а не доступность устройства на текущем хосте.

| Page ID | Раздел | Группа | Прямые controls |
| --- | --- | --- | --- |
| `home` | Главная | C01 | Нет literal controls; см. группу |
| `system` | Система | C28 | Нет literal controls; см. группу |
| `display` | Дисплей | C04 | `display.brightness`, `display.resolution`, `display.refresh`, `display.scale` |
| `displays-multiple` | Несколько дисплеев | C04 | Нет literal controls; см. группу |
| `sound` | Звук | C05 | `sound.output`, `sound.volume`, `sound.muted`, `sound.microphone_muted` |
| `notifications` | Уведомления | C10 | `pref:notifications.banners`, `pref:notifications.dnd`, `pref:notifications.sound` |
| `power` | Питание и батарея | C12 | `power.battery`, `power.suspend`, `power.hibernate` |
| `recovery` | Восстановление | C21 | `recovery.firmware_setup`, `power.reboot`, `power.power_off` |
| `storage` | Память | C13 | `storage.volumes` |
| `storage-volumes` | Съёмные носители | C14 | Нет literal controls; см. группу |
| `multitasking` | Многозадачность | C02 | Нет literal controls; см. группу |
| `developer` | Для разработчиков | C28 | Нет literal controls; см. группу |
| `clipboard` | Буфер обмена | C11 | `pref:clipboard.history` |
| `about` | О системе | C28 | Нет literal controls; см. группу |
| `devices` | Bluetooth и устройства | C08 | `bluetooth.power` |
| `input-devices` | Устройства | C08 | `bluetooth.discovery`, `keyboard.layout` |
| `printers` | Принтеры и сканеры | C08 | Нет literal controls; см. группу |
| `cameras` | Камеры | C08 | Нет literal controls; см. группу |
| `mouse` | Мышь | C09 | `mouse.left_handed`, `mouse.acceleration`, `mouse.natural_scroll`, `mouse.middle_emulation` |
| `touchpad` | Сенсорная панель | C09 | `touchpad.enabled`, `touchpad.tap_to_click`, `touchpad.natural_scroll`, `touchpad.disable_while_typing`, `touchpad.acceleration` |
| `autoplay` | Автозапуск | C08 | Нет literal controls; см. группу |
| `usb` | USB | C08 | Нет literal controls; см. группу |
| `network` | Сеть и Интернет | C06 | `network.wifi`, `network.enabled`, `network.airplane` |
| `wifi` | Wi-Fi | C06 | `network.scan` |
| `ethernet` | Ethernet | C06 | `network.ethernet` |
| `vpn` | VPN | C07 | `network.vpn_summary` |
| `proxy` | Прокси-сервер | C07 | `network.proxy`, `network.dns` |
| `network-advanced` | Дополнительные сетевые параметры | C07 | `network.ethernet`, `network.scan` |
| `personalisation` | Персонализация | C23 | Нет literal controls; см. группу |
| `background` | Фон | C23 | Нет literal controls; см. группу |
| `colours` | Цвета | C23 | `pref:visual.transparency` |
| `themes` | Темы | C23 | Нет literal controls; см. группу |
| `lockscreen` | Экран блокировки | C23 | `pref:taskbar.clock` |
| `start` | Пуск | C23 | `pref:start.recent` |
| `taskbar` | Панель задач | C23 | `pref:taskbar.search`, `pref:taskbar.widgets`, `pref:taskbar.taskview` |
| `fonts` | Шрифты | C23 | Нет literal controls; см. группу |
| `apps` | Приложения | C15 | Нет literal controls; см. группу |
| `apps-installed` | Установленные приложения | C15 | `apps.installed` |
| `apps-default` | Приложения по умолчанию | C15 | `apps.default.browser`, `apps.default.mail`, `apps.default.files`, `apps.default.images`, `apps.default.music`, `apps.default.video`, `apps.default.documents` |
| `apps-startup` | Автозагрузка | C15 | Нет literal controls; см. группу |
| `accounts` | Учётные записи | C17 | Нет literal controls; см. группу |
| `account-you` | Ваши данные | C17 | Нет literal controls; см. группу |
| `account-signin` | Варианты входа | C17 | `accounts.automatic_login` |
| `account-others` | Другие пользователи | C17 | Нет literal controls; см. группу |
| `time` | Время и язык | C18 | Нет literal controls; см. группу |
| `date-time` | Дата и время | C18 | `time.timezone`, `time.ntp`, `time.local_rtc` |
| `language` | Язык и регион | C18 | `language.lang` |
| `input` | Ввод | C09 | `keyboard.layout` |
| `speech` | Распознавание голоса | C18 | Нет literal controls; см. группу |
| `accessibility` | Специальные возможности | C22 | Нет literal controls; см. группу |
| `magnifier` | Экранная лупа | C22 | Нет literal controls; см. группу |
| `a11y-sound` | Звук | C22 | Нет literal controls; см. группу |
| `captions` | Субтитры | C22 | Нет literal controls; см. группу |
| `a11y-keyboard` | Клавиатура | C22 | Нет literal controls; см. группу |
| `a11y-mouse` | Мышь | C22 | Нет literal controls; см. группу |
| `text-size` | Размер текста | C22 | Нет literal controls; см. группу |
| `visual-effects` | Визуальные эффекты | C22 | `pref:visual.animations` |
| `pointer` | Указатель мыши | C22 | Нет literal controls; см. группу |
| `contrast` | Контрастные темы | C22 | Нет literal controls; см. группу |
| `privacy` | Конфиденциальность и защита | C19 | Нет literal controls; см. группу |
| `encryption` | Шифрование диска | C21 | Нет literal controls; см. группу |
| `activity` | Журнал действий | C19 | `pref:privacy.recent_files`, `pref:clipboard.history` |
| `security` | Безопасность Zaldros OS | C19 | `updates.available`, `privacy.firewall` |
| `permissions` | Разрешения приложений | C19 | `privacy.microphone`, `privacy.camera`, `privacy.location` |
| `diagnostics` | Диагностика | C28 | Нет literal controls; см. группу |
| `games` | Игры | C24 | Нет literal controls; см. группу |
| `game-bar` | Игровая панель | C24 | Нет literal controls; см. группу |
| `captures` | Записи | C24 | Нет literal controls; см. группу |
| `update` | Обновление Zaldros OS | C20 | `updates.available`, `updates.check` |

Динамические controls: `display.output.*` (C04), `network.vpn:*` и `sound.app:*`
(C07/C05), `accounts.admin.*`/`accounts.locked.*` (C17), `storage.mounted.*` (C14).
Имена префиксов проверены по Registry; наличие control не гарантирует, что конкретная
страница его показывает, состояние проверяется отдельно по реальной системе.
