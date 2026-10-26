# Передача контекста

Обновлено: 2026-10-26. Базовый HEAD: `12afe1f572193fa105e0b2cd27a77b0715b4d605`.

## Текущая задача и результат

Владелец запросил анализ и точный план последовательного совершенствования Zaldros,
с clean-room подходом и рабочим backend, а не только внешним видом.
Подготовлены README/AUDIT/PLAN/PROMPTS/PROGRESS в `docs/development/`.
В исходном аудите/P01 функциональный код не менялся. P02 меняет сборку и тесты.
P01 закоммичен как `ec1ca56` и отправлен в `codex/p01-capability-baseline`.
Пользователь затем явно разрешил GitHub push/PR/merge и потребовал доставлять
проверенные изменения в main. Текущий P02 готовится в `codex/p02-trusted-rootfs`;
способ доставки при заблокированном API — обычный Git merge/push без force и
без обхода ограничений ветки. Публикация релиза/готовность ОС этим не подтверждается.

**P01 DONE. P02 PARTIAL.** P03–P20 ещё не выполнены.
Реестр [CAPABILITIES.md](CAPABILITIES.md) связывает 35 групп сценариев и все 69
страниц Settings с кодом, проверками и разрывами. README, PROJECT_STATE и ROADMAP
актуализированы; исходные state/roadmap сохранены в `docs/state/history/pre-P01/`.
В P02 уже реализованы download → signed manifest → digest → staged extract и
provenance/shipping inventory. Остаются live Ubuntu verification и лицензирование
части исторических assets; весь P02 ещё не закрыт. Следующий необходимый шаг:
применить подготовленные egress-настройки, проверить настоящий Ubuntu manifest/key
и получить проверяемые license/source сведения либо согласовать замену fallback icons.

## Проверки предшествующего аудита (тот же исходный HEAD)

Среда: Linux container, Python 3.12.14,
`/workspace/.venvs/zaldros`, pytest 9.1.1, PySide6-Essentials 6.12.0.

| Команда / cwd | Результат |
| --- | --- |
| `python -m pytest tools -q`, корень | 44 passed, exit 0 |
| `QT_QPA_PLATFORM=offscreen python -m pytest tests -q -rs`, shell/zaldros-shell | 514 passed, 1 skipped, 61 warnings, 147.81s, exit 0 |
| Причина shell skip | `test_context_menu_fit.py`: нет PIL; это пропущенная группа, не пройденная визуальная проверка |
| Предупреждения | forkpty из многопоточного процесса: возможен deadlock; не падение текущего прогона, учесть при P04/P11 |
| `python -m pytest tests -q -rs`, apps/writer | 9 passed, 6 skipped, exit 0; пропущен реальный engine из-за LibreOffice/UNO |
| `importlib.util.find_spec('uno')` в venv | False |

Локальные логи текущей машины: `/tmp/zaldros-audit-shell.log`.
Артефакты предыдущей настройки: `/tmp/zaldros-start.png`,
`/tmp/zaldros-start.json`, `/tmp/zaldros-desktop.png`, `/tmp/zaldros-hardware.json`.
Это временные пути, они не обещаны как долговечное хранилище доказательств.
При новой сессии повторить необходимые проверки вместо доверия отсутствующим файлам.

## Ограничения и решения

- Работающий systemd и настоящая KWin-сессия в текущем контейнере не подтверждены;
  предыдущий live sysprobe вернул exit 1: no systemd services.
- ISO/QEMU/KVM/hardware/удалённые CI артефакты в этом аудите не проверялись.
- Не устанавливался LibreOffice ради планирования. В аудите Sheets/Slides не запускались;
  в P01 выполнены с явными engine skips, результаты ниже.
- Backend существует; требуется завершение операций, async UI, reconnect и реальные
  service/E2E проверки. Не переписывать его целиком без обоснования.
- Сохранены настройки среды install_script/start_skill из onboarding; публикация
  среды пользователем не подтверждена. Это не публикация приложения/релиза.
- Важные находки F01–F12 изложены в AUDIT.md; воспроизводимые риски и гипотезы
  отделены от фактически падающих пользовательских сценариев.

## P01 — завершён 2026-10-26

Исходный/конечный HEAD одинаков: `12afe1f572193fa105e0b2cd27a77b0715b4d605`;
результат uncommitted. Приложение, тесты, workflow, manifests и lockfiles не менялись.
Исходные пять редактируемых документов дополнительно сохранены в
`/tmp/zaldros-p01-before/`; долговечные архивы предыдущих state/roadmap лежат в проекте.

Изменения: CAPABILITIES.md, текущие README/PROJECT_STATE/ROADMAP, указатели/эта
передача контекста и отчёт `docs/state/iteration-reports/0010-capability-baseline.md`.
Новые ADR не нужны: решения о базе/варианте не принимались без VM gate.

Проверено повторно F01–F12. Новый подтверждённый дефект D01:
`settingspages.build(state={})['fonts'].entries[0].value` сообщает Selawik,
`app.UI_FONT_PREFERENCE` — PT Sans. Также найдены 16 static toggle rows без control,
но их число не является числом работающих настроек. D02/F08 остаётся первым
кодовым prerequisite P02; D01 исправляется вместе с контрактом UI-статуса в P16.

Команды под `/workspace/.venvs/zaldros/bin/python`, Python 3.12.14:

| Проверка / cwd | Результат P01 |
| --- | --- |
| `-m pytest tools -q`, корень | 44 passed, exit 0, 0.13s |
| `-m pytest tests/test_settings_tree.py tests/test_settings_controls.py tests/test_backend_settings.py tests/test_backend_connectivity.py tests/test_system.py tests/test_kwin_switcher_script.py tests/test_files.py -q -rs`, shell/zaldros-shell, QT_QPA_PLATFORM=offscreen | 112 passed, 0 skipped, exit 0, 72.69s |
| `-m pytest tests -q -rs`, apps/sheets, offscreen | 6 passed, 9 skipped (engine/UNO), exit 0, 0.49s |
| `-m pytest tests -q -rs`, apps/slides, offscreen | 3 passed, 12 skipped (engine/UNO, включая один UI scenario), exit 0, 0.25s |
| `-m zaldros_compat --check`, tools/zaldros-compat | PASS 8 apps / 13 hardware entries, exit 0 |
| Та же compat команда из корня | Initial exit 1: module not found; исправлено только cwd, повтор выше успешен |
| Инвентаризация AST Settings + static font reproduction | 69 pages; Selawik != PT Sans; 16 uncontrolled toggle rows; exit 0 |

Полный shell-набор повторно не запускался: функциональный код не менялся,
результат 514/1 того же HEAD сохранён как результат предыдущего аудита, а не P01.
S/E/H остаются UNRUN. Нет готового установленного продукта и подтверждённых
current-SHA ISO/VM/hardware результатов.

Критерии P01: реестр всех alpha-сценариев/Settings создан, происхождение evidence
указано, устаревшие текущие статусы отделены, scope/приоритеты и следующий дефект
зафиксированы. Проверки документов: локальные ссылки, 69 page IDs, C01–C35,
порядок 20 промптов, сохранность архивов и `git diff --check`.

## P02 — локальная реализация, внешние gates открыты

Дата: 2026-10-26. Parent commit `ec1ca56`; результат — коммит, содержащий эту запись.
Работа ведётся в `codex/p02-trusted-rootfs`, доставка в main разрешена пользователем.

Изменения:

- `fetch-rootfs.py` и отдельная Ubuntu signing policy: строгий HTTPS, изолированный
  GnuPG, полный fingerprint, проверенная подпись SHA256SUMS, единственная запись
  имени архива, SHA256 и распаковка в staged directory. Fail-closed, без fallback.
- Обработчик ошибок не исполняет chroot до успешной аутентификации rootfs и не
  размонтирует дерево, если этот запуск ещё не делал mount.
- `build/provenance/assets.json`: 158 файлов, хеши, компоненты/источники/лицензии,
  явные provenance gaps. `stage-assets.py` пакует 154 файла; refs и generator не
  попадают в ISO. Проверяются новые/изменённые/отсутствующие файлы и symlinks.
- Cursor source закреплён на полном SHA; настоящий fetch/checkout выполнен успешно.
  GNUPG/curl/Python явно добавлены в активный и документированный ISO workflow.
- Flat-layout regression теперь вызывает настоящий staging step, а не только cp.
- README дополнен английским contributor/funding разделом без эмодзи. Возобновлённая
  разработка и ограничения описаны честно. $5,300 — предварительная цель, не смета.
  Bitcoin mainnet address предоставлен владельцем; checksum проверен, ключей не запрашивали.

Проверки:

| Команда / проверка | Итог |
| --- | --- |
| `QT_QPA_PLATFORM=offscreen python -m pytest tests -q -rs`, shell directory, финальная версия | 536 passed, 1 skipped (нет PIL), 61 forkpty warning; 148.57s; exit 0 |
| Пять targeted suites: rootfs_authentication, asset_provenance, build_iso_diagnostics, visual_layer, flat_layout | 34 passed, exit 0, 2.78s |
| `python -m pytest tools -q` | 44 passed, exit 0 |
| `python -m zaldros_compat --check`, tools/zaldros-compat | PASS 8 apps / 13 hardware entries, exit 0 |
| `python3 build/iso/stage-assets.py` + staging в новый /tmp каталог | 158 записей проверены, 154 staged + manifest, exit 0 |
| `bash system/theme/fetch-sources.sh /tmp/zaldros-p02-upstreams` | Полный pinned commit загружен/выбран, exit 0 |
| `bash -n` для shell scripts, `py_compile` helpers, идентичность двух ISO workflow | PASS |

Первый targeted run: 31 passed / 1 failed — старый flat-layout harness понимал только
cp, поэтому не готовил новые staged assets. Harness обновлён; повтор прошёл.
Промежуточный full run: 535 passed / 1 skipped до дополнительного теста chroot guard;
после него выполнен финальный full run выше. Проверки OpenPGP используют реальные
одноразовые ключи/подписи, проверяют tamper/wrong signer/missing manifest entry/
duplicate/invalid tar, не подменяют GnuPG mock-ответом.
Логи текущей машины: `/tmp/zaldros-p02-tests.log`, `/tmp/zaldros-p02-final-tests.log`.

Открыто:

- Git read/write доступен, но `gh api` и HTTPS к Ubuntu endpoints возвращают
  tunnel `403 Forbidden` из-за egress policy. Это не доказательство отсутствия
  GitHub-токена: GH_TOKEN уже присутствует. Новый секрет не запрашивался.
- В draft сохранены добавления `api.github.com`, `cdimage.ubuntu.com`, `ubuntu.com`,
  `keyserver.ubuntu.com`. Сохранение draft не применяет runtime policy и не публикует
  среду. Для live gate нужны сохранение настроек/публикация через UI среды.
- Настоящий текущий Ubuntu manifest/signing key, ISO build/boot и remote CI status
  не проверены. Не считать fixture PASS доказательством работающей загрузки Ubuntu.
- В fallback icon archive не найдено точных LICENSE/LICENSE.txt/COPYING/AUTHORS/
  COPYRIGHT files. Историческая store GPL claim не закрывает per-file права.
  Остальные unknown upstream revisions/ancestry перечислены в provenance README.
  Нужны verifiable notice/source или отдельно проверенная замена до public release.

P02 остаётся PARTIAL; не переходить к объявлению alpha/release ready.

## Шаблон следующей записи

Для каждого этапа добавлять: Pxx/подэтап; исходный и конечный SHA (либо uncommitted);
изменённые файлы; проблема/воспроизведение; решение/ADR; команды и exit codes;
pass/fail/skip counts; system/E2E/hardware evidence и артефакты; нерешённое;
DONE/PARTIAL/BLOCKED с причиной; точный следующий шаг.
