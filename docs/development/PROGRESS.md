# Передача контекста

Обновлено: 2026-10-26. Исходный аудит: `12afe1f572193fa105e0b2cd27a77b0715b4d605`.
Текущий цикл Office CI начинается с main `870c361` (PR #3 MERGED).

## Текущая задача и результат

Владелец запросил анализ и точный план последовательного совершенствования Zaldros,
с clean-room подходом и рабочим backend, а не только внешним видом.
Подготовлены README/AUDIT/PLAN/PROMPTS/PROGRESS в `docs/development/`.
В исходном аудите/P01 функциональный код не менялся. P02 меняет сборку и тесты.
P01 закоммичен как `ec1ca56` и отправлен в `codex/p01-capability-baseline`.
Пользователь затем явно разрешил GitHub push/PR/merge и потребовал доставлять
проверенные изменения в main. P02 code commit `b133e96` отправлен, PR #1 создан
и MERGED: merge commit `6168e9bd5f55d879630d34b4e1ae0509ec1b3eb4` в main.
API заработал после первоначальных 403; обычное Git-слияние/push принято сервером
без force/обхода правил. GitHub подтвердил состояние PR MERGED. Публикация
релиза/готовность ОС этим не подтверждается.

**P01 DONE. P02/P03/P17 PARTIAL.** В P03/P17 проверен D03; остальные требования
этих этапов остаются открытыми. P04–P16 и P18–P20 ещё не выполнены.
Реестр [CAPABILITIES.md](CAPABILITIES.md) связывает 35 групп сценариев и все 69
страниц Settings с кодом, проверками и разрывами. README, PROJECT_STATE и ROADMAP
актуализированы; исходные state/roadmap сохранены в `docs/state/history/pre-P01/`.
В P02 уже реализованы download → signed manifest → digest → staged extract и
provenance/shipping inventory. Live Ubuntu verification после восстановления
связности прошёл. Остаётся лицензирование части исторических assets; весь P02
ещё не закрыт. Следующий необходимый шаг: получить проверяемые license/source
сведения либо подготовить отдельно проверенную замену fallback icons.

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

### Последующее восстановление доступа и live validation

После первоначального 403 следующие запросы GitHub API и официальных Ubuntu HTTPS
endpoints прошли. Требование нового токена не возникло; публикация снимка среды
по-прежнему не подтверждена. Чтение branch-protection metadata отдельно возвращает
`Resource not accessible by integration`; это scope endpoint, не блокировка всех PR.

- PR #1: https://github.com/jonbarkert135-cpu/Zaldros/pull/1 — MERGED.
- Main после слияния: `6168e9bd5f55d879630d34b4e1ae0509ec1b3eb4`, совпадение
  local HEAD и `git ls-remote origin refs/heads/main` проверено.
- Официальный Ubuntu tutorial получен по HTTPS и содержит полный fingerprint
  `843938DF228D22F7B3742BC0D94AA3F0EFE21092`, совпадающий с policy.
- Настоящий `fetch-rootfs.py` с URL Ubuntu 26.04 amd64 завершился exit 0:
  signature → SHA256 → staged extraction. Digest
  `046fcabb7f16f45a80ae11824664f2a07e01386c6fb1ed9dc1e225a66a6553a2`.
  `/etc/os-release` извлечённого дерева сообщает Ubuntu 26.04 Resolute.
- Долговечные публичные артефакты: `docs/state/evidence/p02-rootfs/`.
  Сам tar/rootfs не добавлен в Git; это не VM boot и не запуск кода из rootfs.
- Remote main CI/ISO runs начались на 6168e9b; их окончательный результат
  фиксируется отдельно, а не предполагается по факту запуска.

Первоначальные ограничения выше сохранены как хронология. Live artifact gate
теперь PASS; license reviews и функциональные system/E2E/hardware gates открыты.

## Каноническое имя и обновлённые визуальные материалы

По прямому запросу владельца удалено прежнее обозначение проекта из всех текущих
файлов, включая naming research и ADR-0006. Неактуальные строки исследования
удалены, а не переименованы в несуществующие сторонние проекты/URL. Указано, что
число 129 относится к первоначальному исследованию. Обновлены WORKLOG, README,
NAMING, Settings, тестовые комментарии и capability index. История Git не переписывалась.

Изменённые видимые строки Settings используют gettext и каноническое Zaldros OS.
44 отслеживаемых visual artifacts перегенерированы настоящим renderer/parity tool,
измерительные reference targets не менялись. Поиск по всем текстовым файлам —
ноль совпадений прежнего обозначения; OCR по 38 tracked PNG/JPG — ноль совпадений.
OCR вспомогательный, основное доказательство изображений — их регенерация из
исправленного кода. Старый медленный OCR-процесс остановлен и заменён ограниченным
по потокам сканированием, которое завершилось успешно.

Для ранее пропущенной группы установлены Pillow 13.0.0 / numpy 2.5.4 в venv;
их точные версии добавлены в install_script draft среды. Изменение draft не
является публикацией снимка. Финальный `pytest tests -q -rs`: **538 passed,
0 skipped**, 62 forkpty warnings, 146.71s, exit 0. После gettext-изменения отдельно
прошли settings_tree + context_menu_fit: **8 passed**, exit 0. Полный финальный
набор уже включает эти проверки. `tools/visual/parity.py --quiet --output
/tmp/zaldros-naming-visual`: **110/110**, exit 0; оттуда скопированы current artifacts.

Remote CI для main `6168e9b`: все 5 jobs SUCCESS;
`docs/state/evidence/p02-rootfs/main-ci.json` хранит результат с исходным SHA.
Результаты ISO workflow и прямое чтение отчётов фиксируются отдельно. Загрузка
zip artifacts через временный blob URL пока заблокирована egress; подписи URL
не сохранялись в репозиторий. Диагностические ветки доступны через Git.

Логи: `/tmp/zaldros-canonical-final-tests.log`, `/tmp/zaldros-naming-parity.log`.
Следующая доставка — PR с canonical branding и live Ubuntu evidence в main.

ISO run `40333303076` на `6168e9b` завершён: **3/3 builds и 9/9 boot jobs SUCCESS**.
Через Git прочитаны все девять свежих BOOT PASS отчётов, сохранены точные commits
публичных diagnostic refs и раздельные UI статусы в `vm-report-summary.json`.
`report.py` на всех девяти отчётах вернул exit 0. Старый August legacy/mid отчёт
не использовался: дождались новой публикации. ZIP route всё ещё 403; raw временные
redirect credentials не попадали в Git.

**D03:** во всех трёх legacy profiles screenshot = FAIL, но job зелёный, поскольку
report.py определяет exit code только по BOOT. Это подтверждённый acceptance-gate
дефект, а не доказательство полного UI PASS. Остальные измеренные host/window шаги
имеют свои PASS, frame_stability — BLOCKED. Исправить функциональные gates и
capability contract в P03/P17; не отключать проверки ради зелёного статуса.

CI shell install теперь фиксирует проверенные PySide6/pytest/Pillow/numpy versions,
чтобы context-menu suite выполнялся и в GitHub, а не только в текущем venv.

## P03/P17 — достоверность функционального CI (по следующему запросу владельца)

База: `7660f2c3ec63dd592f88e6be8fb04d0fa58e5598`, PR #2 MERGED.
Владелец поручил продолжить с ранее обозначенного D03. Это независимое исправление
корректности CI; P02 licensing и остальные требования P03 не объявляются закрытыми.
На базе 7660f2c normal CI run 40338140411 и ISO run 40338140298 были зелёными,
что само по себе не устраняло подтверждённый дефект D03.

Изменения:

- report.py требует PASS всех 11 обязательных UI steps от их владельца. Ошибка
  второго наблюдателя не маскируется; missing/blocked/skipped/unknown не заменяют
  результат. QMP и явно измеренные diagnostic/report FAIL тоже дают exit 1.
- Гость отвечает за окно/запуск/снимок; host — за input-driven шаги. BLOCKED guest
  entries для host steps не трактуются как второй провал, когда host PASS.
  Frame pacing не измеряется VM и не объявляется проверенным.
- Boot producer и consumer используют один boot_checks; пустой список pending jobs
  при starting больше не является доказательством успеха. Имена unit проверяются
  точно, failed units всегда дают fail. boot-test.sh сохраняет неуспешный exit code.
- Оба ISO workflow передают ожидаемый variant/profile; stale, missing, extra и
  duplicate targets отклоняются. Source-SHA correlation внутри guest — ещё P17 work.
- Spectacle и KDE portal включены в BASE всех вариантов. Существующий screenshot
  тест не отключён; legacy получает недостающий runtime. ffmpeg остаётся full-only.
  Старые размер/RAM цифры не характеризуют изменённый minimal image.
- Решение и ограниченный контракт: ADR-0026. Исторические отчёты не изменялись.

Проверки до отправки:

| Проверка | Итог |
| --- | --- |
| Новые regression tests на старом коде | 38 failed / 2 passed; дефект воспроизведён |
| Финальные gate/boot-report/serial/package suites | 72 passed, exit 0 |
| Полный shell/backend pytest | 587 passed, 0 skipped, 62 forkpty warnings, exit 0, 154.20s |
| Tools | 44 passed, exit 0 |
| Replay девяти сохранённых VM reports новым report.py | exit 1: ровно legacy/low, legacy/mid, legacy/modern screenshot FAIL |
| bash -n, синхронность двух ISO workflow, diff whitespace | PASS |

Actual composition heredoc boot-test.sh исполняется в regression test из внешнего
cwd и сохраняет failure как для boot, так и для screenshot. Форматировочные старые
fixtures дополнены полноценными UI результатами; assertions не ослаблялись.
Финальные логи: `/tmp/zaldros-functional-final-tests.log`,
`/tmp/zaldros-functional-replay.log`. Новая VM-матрица должна подтвердить реальный
скриншот в legacy; старые FAIL не пересчитаны в PASS и не являются новым прогоном.
Перед доставкой в main — PR, normal CI и новый ISO/VM прогон. Точное подтверждение
remote результатов добавляется отдельно после их получения.

### Дополнительная диагностика производителя результатов

Первый кандидат `dfe9237` прошёл CI, но просмотр сырого legacy/modern отчёта выявил
`status=PASS` одновременно с `error=the tool ran but wrote no file`. Этот результат
не принят как функциональное подтверждение. В старых services отчётах найдена
та же ошибка. step() принимал любой словарь за успех; итоговый gate теперь отклоняет
непустой error независимо от PASS, а producer не превращает error/None/пустые
результаты в успех. Таким образом исходный false-green дефект имел два уровня.

Полный набор пакетов сравнен по реальным CI manifests: kwin-common установлен
только в full, тогда как Spectacle присутствовал в services. Подписанный
resolute-updates InRelease проверен keyring из аутентифицированного Ubuntu base,
индекс Packages и deb сверены по SHA256. В kwin-common найдены screenshot.so и
screencast.so. kwin-common теперь также в BASE; приватные данные/секреты не нужны.
Receipt: `docs/state/evidence/functional-gate/screenshot-dependency.json`.

Снимок считается выполненным только при exit 0 и свежем изображении, которое
декодируется QImage с width/height > 0. stderr/return code не теряются. Реальные
window probes теперь сохраняют UUID запущенного Dolphin, проверяют его геометрию
и переход minimized на том же окне, а не наличие произвольного окна. internalId
проверен по официальному KWin v6.6.6 window.h.

Новые проверки: **126 passed** в focused suites, **612 passed / 0 skipped** в
полном наборе, 62 существующих forkpty warnings, 152.85s. В первом полном прогоне
после правки producer было 611 passed / 1 failed: старый capture test проверял
буквальную строку ошибки. Он заменён более строгой поведенческой проверкой:
команда exit 0 без файла должна дать FAIL через настоящий step()+_screenshot().
Assertions не отключались. Финальный лог: `/tmp/zaldros-functional-final-evidence-tests.log`.

Replay исходных девяти VM reports финальным gate теперь даёт exit 1 с шестью
ошибками screenshot (legacy + services), включая ранее замаскированные error fields.
PR #3 обновляется; до нового VM прогона эти screenshot функции не объявляются PASS.
Предложенные владельцем варианты нового имени обсуждаются отдельно; переименование
без выбранного окончательного имени в этот PR не добавлялось.

### Исправление перемещения Wayland

Run [40353950450](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40353950450)
на `e5c98f0` завершился failure: девять window_move FAIL, остальные обязательные
шаги PASS. Все девять screenshot теперь содержат свежие PNG 1280×800; это
подтверждает исправление пакетов, но не является приёмкой всей матрицы.
Точные commits диагностических отчётов сохранены в
`docs/state/evidence/functional-gate/geometry-failure.json` с ограничением provenance.

Причина воспроизведена реальным QJSEngine и QObject с QRectF: запись g.x/g.y
отправляет промежуточные setters, последняя запись возвращает исходные координаты
до Wayland ack. Новый regression на старом коде: 1 failed. Отправляем одно
отдельное значение x/y/width/height; этот формат подтверждён исходником
[KWin v6.6.6 scripting.cpp](https://github.com/KDE/kwin/blob/v6.6.6/src/scripting/scripting.cpp).
Focused producer/gate: 73 passed. Подтверждение в VM требуется заново.
Полный набор после исправления: **613 passed / 0 skipped**, 62 прежних forkpty
warnings, 152.23s; tools: **44 passed**. Лог:
`/tmp/zaldros-functional-geometry-tests.log`. Assertions/gate не ослаблялись.

### D03 — удалённая приёмка выполнена

Проверенный runtime source: `4c35535a33466c0b4c6bd28139e12b75c56f4a44`.
Normal CI [40375589292](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40375589292):
5/5 jobs PASS. ISO [40375579596](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40375579596):
3/3 builds, 9/9 boot jobs PASS. Все девять новых сырых JSON перепроверены
`python build/iso/report.py /tmp/zaldros-4c-vm-reports`: exit 0, **99/99** обязательных
UI steps PASS. На каждом target проверены одинаковый UUID при move/minimize/restore,
геометрия (256,115) → (376,195), minimized true → false и screenshot PNG 1280×800
без error; размер 307398–309895 bytes. Пакеты screenshot runtime подтверждены
актуальными installed-packages manifests всех трёх сборок.

Точные workflow metadata, commits диагностических веток, версии пакетов и результаты:
`docs/state/evidence/functional-gate/vm-acceptance.json`. Guest JSON ещё не содержит
source SHA/run ID: ограничение явно сохранено, не заменено догадкой. Этот rerun
подтверждает D03/одиннадцать шагов boot/UI; P02 licensing, остальные P03/P17,
installed-system, hardware и frame pacing остаются открытыми. Старые FAIL сохранены.

Временный независимый fault-injection baseline для будущего P04: приватный
dbus-daemon, синхронный Bus.call timeout 0.2s из Qt event loop; фактически call
0.2006s, max gap heartbeat 204.8ms при интервале 5ms. Это измерение транспорта,
не полный Settings/VM/recovery тест. Script/receipt в текущей среде:
`/tmp/zaldros-gui-timeout-baseline.py` и `/tmp/zaldros-gui-timeout-baseline.json`.
Следующий этап: оставшиеся P02/P03 gates, затем async lifecycle с heartbeat/recovery
регрессиями. Эти измерения не объявляют P04 выполненным.

### P03 — обязательный CI Writer / Sheets / Slides

База: main `870c361`, ветка `codex/office-ci-gates`. Активный workflow не запускал
Office, хотя docs/sheets/BUILD.md утверждал обратное. Воспроизведение на текущем
интерпретаторе без UNO: Calc engine pytest → 9 skipped, exit 0. Новый
`tools/ci/office.py sheets --junitxml ...` → preflight FAIL, exit 1.

Добавлена матрица трёх Ubuntu 24.04 jobs: системный Python + python3-uno + нужный
LibreOffice component; изолированный system-site-packages venv с фиксированными
pytest/Qt. Runner требует исполненных engine/UI suites и отклоняет любой skip,
включая collection skip. Unit test отсутствующего Writer теперь инжектирует
условие и не пропускается на машине с установленным Writer. Versions/JUnit
сохраняются как Office artifacts. Normal CI contents permission: read-only.
Reference workflow синхронизирован с активным без переноса старых retry предложений.

Локально: **53 tools passed**, включая 9 новых subprocess/preflight regressions;
проверка отсутствующего Writer — 1 passed. UI: Writer 5 passed, Sheets 6 passed;
Slides 3 passed / 1 skipped (нет UNO). Это optional/local результат, не принятие
Office CI. Полноценный движок локально не проверен. Команды установки и строгого
запуска: `docs/office/BUILD.md`; iteration `0014-office-ci-gates.md`.
Далее: новый PR → реальный remote UNO/Qt → исправление выявленных ошибок → merge.
P02 licensing, ISO path filters и прочие P03/P17 gates не объявляются закрытыми.

## Шаблон следующей записи

Для каждого этапа добавлять: Pxx/подэтап; исходный и конечный SHA (либо uncommitted);
изменённые файлы; проблема/воспроизведение; решение/ADR; команды и exit codes;
pass/fail/skip counts; system/E2E/hardware evidence и артефакты; нерешённое;
DONE/PARTIAL/BLOCKED с причиной; точный следующий шаг.
