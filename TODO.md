# TODO

Priority follows the owner's order: bootable system → real desktop → shell → taskbar/Start →
Explorer → Settings → hardware → installer/updates → compatibility → performance → visual fidelity.

## Blocking everything
- [ ] Confirm the GitHub Actions `image` job builds a container image (first real build evidence)
- [ ] Get a build host with `/dev/kvm` (CI cannot boot a VM comfortably) — or the owner's machine
- [ ] Settle the base distribution with the test in `docs/research/03-base-distribution-reopened.md`

## Real desktop (next slice)
- [ ] Turn the taskbar into a real Wayland **layer-shell** panel on KWin (not a window)
- [x] Parse `.desktop` files; pins now cross-checked against the real application database
- [x] Launch applications from Start and from the taskbar
- [ ] Track real windows from the compositor; group them in the taskbar
- [x] Wire quick-settings toggles to NetworkManager / BlueZ / PipeWire / UPower — through the one
      backend layer (ADR-0014); slots exist and are tested against mock services, still unproven on
      real hardware
- [x] Vendor Fluent UI System Icons (MIT) and PT Sans (OFL) — done, in use (Selawik dropped: no Cyrillic)
- [x] Install the Fluent cursor theme (GPL-3) — the only borrowed pack (ADR-0010)
- [x] Draw our own Aurorae decoration theme (`tools/theme/make_aurorae.py`) — awaiting the first boot screenshot of a real app titlebar
- [ ] Replace the vendored GPL-3 app/place SVGs with our own artwork (last borrowed pixels besides the cursors)
- [ ] Extend the `Zaldros` icon theme to mime and device names (currently apps/places/actions only)
- [ ] Ship Win11-gtk-theme (GPL-3) so GTK applications match the shell
- [ ] Build the ISO the AnduinOS way (debootstrap + squashfs + xorriso) — no container runtime needed
- [ ] Window management: Alt+Tab (own KWin script — run #37 proved the shortcut fires and switches;
      the boot test now waits for a second window before measuring it), snap layouts,
      minimise/maximise/close on real windows
- [ ] Autostart the shell in a session (login → desktop)
- [ ] Search: applications first, then settings, then files
- [ ] Right-click context menus (Windows 11 rounded style)
- [x] Win+V — clipboard history flyout backed by the real QClipboard (pins persist, unpinned never
      touches the disk)
- [x] Win+G — capture widget: screenshot through the first grabber that really exists, recording
      through the portal's ScreenCast node + ffmpeg, every missing tool named on screen
- [ ] Win+G — the «last 30 seconds» ring buffer (needs a continuous encode we do not run yet)
- [ ] Part-by-part visual audit against public Windows 11 screenshots: one reference per component,
      measured and diffed, not eyeballed (the maintainer asked for this after the first game bar)
- [x] Quick settings backed by real NetworkManager / PipeWire / UPower / BlueZ / udisks2 / logind
      via `backend/zaldros_backend` (ADR-0014)
- [ ] Claim `org.freedesktop.Notifications` at runtime — the server is written and tested, but the
      shell does not own the name yet (KDE's daemon would collide)
- [ ] Publish the backend as `org.zaldros.Backend1` on the session bus — today apps import the
      Python package instead

## Zaldros Sheets (ADR-0013)
- [x] Исследовать LOK / UNO / форк / тему VCL и выбрать шов — выбран UNO сейчас, LOK потом
- [x] Мост к движку + 6 тестов на живом LibreOffice (формула, ошибка, XLSX туда-обратно)
- [x] Своё окно: лента, строка формул, сетка, вкладки листов, строка состояния — по замерам
- [x] Библиотека подлинных снимков Excel с контрольными суммами
- [ ] Ввод в ячейку с клавиатуры и правка в строке формул (сейчас модель умеет, UI ещё нет)
- [ ] Кнопки ленты через `.uno:` команды движка, а не свои реализации
- [ ] Фаза 2: тайловый вид на LOK для диаграмм и предпросмотра печати
- [ ] Недостающие эталоны: предпросмотр печати, параметры Excel, строка состояния, контекстное
      меню ячейки, вкладки Data/Review/Page Layout/Formulas
- [ ] Поставить `libreoffice-calc-nogui` и `python3-uno` в ISO

## Диспетчер задач (ADR-0016)
- [x] Процессы, ЦП/память/диск/сеть/время работы, автозагрузка, завершение процесса, поиск,
      сортировка — всё из `/proc` и sysfs, без выдуманных метрик
- [ ] Страница «Службы» в окне диспетчера (фасет `services` готов с ADR-0014)
- [ ] Раздел «Приложения»: нужен список окон от композитора (тот же протокол, что и для таскбара)
- [ ] Графики ЦП/памяти рисуются, но история теряется при закрытии окна
- [ ] «Журнал приложений» и «Пользователи» — не делались

## Диспетчер устройств (ADR-0017)
- [x] Дерево категорий из sysfs/DMI/procfs, свойства устройства, пометка «драйвер не загружен»,
      причина у каждой пустой ветки, пересканирование шины PCI
- [ ] Ветка Bluetooth из BlueZ (имя адаптера, состояние) вместо строки PCI/USB
- [ ] Модули памяти из DMI type 17 (нужен root)
- [ ] Диагностика: перезагрузка модуля ядра, журнал устройства из journald

## Сеть, звук, Bluetooth, питание (ADR-0018)
- [x] Wi-Fi с паролем, отключение, сохранённые профили, VPN вкл/выкл, DNS, прокси
- [x] Сопряжение и удаление Bluetooth, батарея устройства
- [x] Громкость по приложениям, выбор устройства записи
- [x] Режимы питания power-profiles-daemon
- [ ] Агент сопряжения BlueZ (ввод PIN-кода)
- [ ] Создание и редактирование профилей VPN, ручная настройка прокси

## After the desktop stands up
- [ ] Explorer (Dolphin fork) — first real system application
- [x] Settings: every row backed by a real control with read + write (ADR-0015) — display,
      resolution, refresh, scale, multiple monitors, sound, microphone, Wi-Fi, Ethernet,
      Bluetooth, power, battery, keyboard, mouse, touchpad, language, timezone, notifications,
      privacy, firewall, users, applications, default apps, storage, updates, recovery
- [ ] Settings on real hardware: none of the controls has been exercised on a machine that has
      kscreen-doctor, a portal, accountsservice or PackageKit — the ISO boot report is the proof
- [ ] Settings still missing: night light, PowerDevil power profiles, creating and deleting users
      (needs a confirmation flow), VPN and proxy profiles
- [ ] **FIRST ISO BUILD PASS** — nothing else in this cycle; then first QEMU boot PASS
- [ ] Installer, then recovery/rollback tested by deliberately breaking a VM
- [ ] **Re-earn what the bootc base gave us** (ADR-0009): atomic updates, rollback, read-only `/usr`,
      on-disk recovery entry. Until these exist, do not claim any of them anywhere in the docs.
- [ ] Pin package versions in `build/iso/build-iso.sh` — builds are repeatable, not reproducible
- [ ] Mark `build/Containerfile.*` dead or delete them; they belong to the superseded bootc base
- [ ] First hardware evidence records; first performance baselines vs Ubuntu/Mint/Fedora/Debian
- [ ] Accessibility pass (Orca, keyboard-only, high contrast)
- [ ] Paste the verbatim GPL-3.0 text into `LICENSE` (no network in the build sandbox)
