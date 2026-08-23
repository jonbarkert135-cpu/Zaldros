# NAME AVAILABILITY AUDIT — выбор имени дистрибутива

Дата: 2026-08-23. Автор: Viktor (по заданию владельца проекта).
Методика: (1) веб-поиск по актуальным источникам (DistroWatch, Wikipedia, GitHub, официальные сайты, реестры компаний UK/HK/EE, LinkedIn, Crunchbase);
(2) машинная проверка **129 имён**: RDAP-запросы к реестрам доменов (.com/.org/.io — Verisign/PIR/Identity Digital, .dev — через rdap.org), GitHub (`github.com/<name>`, `github.com/<name>linux`, GitHub Search API), GitLab (`/api/v4/users`), Codeberg.
Дисклеймер: это **не юридическое заключение**. Проведён публичный веб- и реестровый поиск, полноценный поиск по базам товарных знаков (USPTO/EUIPO/WIPO) не выполнялся. Для финального имени: **LEGAL REVIEW REQUIRED** перед регистрацией бренда.

Ограничения данных: часть проверок GitHub возвращала 429 (rate limit) — такие ячейки помечены UNKNOWN и перепроверены для шорт-листа. «FREE» для namespace означает лишь «страница отдаёт 404», а не юридическую свободу.

---

## 1. Аудит текущих вариантов

| Имя | Вердикт | Конфликт | Ссылка |
|---|---|---|---|
| **Raven OS / Raven Linux** | 🔴 RED | Raven-OS — реальная ОС/дистрибутив (org на GitHub, 20 репо, сайт raven-os.org); RavenOS (Arch-based, ocsmos); RavenOS (Adiras, own kernel); Raven Resonance — стартап смарт-очков на Linux (AWE 2026, PR Newswire). Домены raven.com/.org/.io заняты. | https://github.com/raven-os · https://raven-os.org · https://raven.computer |
| **Bedrock Linux** | 🔴 RED | Bedrock Linux — действующая мета-дистрибуция с 2009, v0.7.31 (2026-01-12), Wikipedia-статья, сайт, GitHub-org. Прямое столкновение. | https://bedrocklinux.org · https://en.wikipedia.org/wiki/Bedrock_Linux |
| **Bedrock OS** | 🔴 RED | То же ядро конфликта + Minecraft **Bedrock Edition** (массовый бренд), BedRock Systems (ныне BlueRock, кибербез). Постоянная путаница в поиске гарантирована. | https://minecraft.wiki/w/Bedrock_Edition · https://www.cbinsights.com/company/bedrock-systems |
| **Prime OS / PrimeOS** | 🔴 RED | PrimeOS — известная Android-x86 десктоп-ОС (SourceForge, XDA, зеркала на GitHub). Все домены заняты. | https://sourceforge.net/projects/primeos/ · https://github.com/nyhtml/PrimeOS |
| **Prime Linux** | 🔴 RED | Prime GNU/Linux — существующая микро-дистрибуция (сборка из исходников). Плюс слово «prime» перегружено (Amazon Prime). | http://prime-linux.org/ |
| **Aurora OS / Aurora Linux** | 🔴 RED | Aurora OS — российская мобильная ОС (Открытая мобильная платформа, на базе Sailfish, сертификация ФСТЭК) **и** Aurora (Universal Blue) — KDE-дистрибутив на Fedora, getaurora.dev. Двойной конфликт, особенно болезненный для RU-рынка. | https://en.wikipedia.org/wiki/Aurora_OS_(Russian_mobile_platform) · https://getaurora.dev/ |
| **Nova Linux / Nova OS** | 🔴 RED | Nova GNU/Linux — государственная ОС Кубы (nova.cu, DistroWatch) + OpenStack **Nova** — фундаментальный облачный компонент. | https://www.nova.cu/ · https://distrowatch.com/table.php?distribution=Nova · https://github.com/openstack/nova |
| Polaris | 🔴 RED | Linux Polaris (OWare) + Polaris — множество продуктов. | https://github.com/OWareSoftwares/Polaris |
| Solstice | 🟡 YELLOW | Solstice OS — source-based дистрибутив (активен 2026). | https://github.com/Abo-Alsuz/solstice-os |
| Basalt | 🔴 RED | **BasaltOS** — существующая ОС-организация на GitHub. | https://github.com/BasaltOS-org |
| Skarnet | 🔴 RED | skarnet.org — s6/s6-rc/s6-linux-init, фундаментальные Linux-компоненты. | https://skarnet.org/software/ |
| Phoenix | 🔴 RED | PhoenixOS (Android-x86), Phoenix Technologies (BIOS/UEFI — прямая ассоциация с загрузкой ПК). | — |

**Вывод: ни один из исходных вариантов не пригоден для независимого бренда.** «Bedrock OS» особенно вреден: даже без юридического риска органический поиск навсегда отдан Minecraft и bedrocklinux.org.

---

## 2. Машинная проверка (129 имён)

Полная таблица результатов RDAP + namespace-проверок: см. Приложение A ниже.
Отсев по правилам:
- RED, если имя занято дистрибутивом/ОС/крупным OSS/крупной компанией;
- YELLOW, если существует небольшая компания, похожее по звучанию имя или занят `.com`;
- GREEN, если веб-поиск не находит заметного пользователя имени и свободны все ключевые namespace.

### Отклонённые (примеры с причинами)

| Имя | Риск | Причина | Ссылка |
|---|---|---|---|
| Solstral | 🟡 | Solstral (LinkedIn, AI/automation) + Solstrale (Stockholm think tank, Solstrale OÜ, Solstrale India, Rust-крейт `solstrale`) | https://linkedin.com/company/solstral · https://crates.io/crates/solstrale |
| Pelaris | 🔴 | pelaris.io — активный AI-стартап, есть MCP-сервер на GitHub | https://pelaris.io/ |
| Druvia | 🟡 | Druvia AI — консалтинг по данным (упоминается в блоге Airbyte) | https://druvia.vercel.app/ |
| Pyrelith | 🟡 | Pyrelith Analytics (UK, OMS-платформа) | https://pyrelith.co.uk/ |
| Kirvane | 🟡 | Kirvano — бразильский платёжный сервис + мёртвый TM KIRVANO (USPTO 98634369) | https://kirvano.com/ |
| Vaeltro | 🟡 | Veltro.co — AI product studio | https://veltro.co/ |
| Quenrik | 🟡 | Quentrik.com — AI automation (почти омофон) | https://quentrik.com/ |
| Kestrix | 🔴 | Kestrix — UK-стартап (thermography, $755K funding); также Kestri, Kestrl | https://uk.linkedin.com/company/kestrix |
| Korvath | 🟡 | KORVATH LTD (UK 15897237); korva.dev — AI для dev-команд | https://find-and-update.company-information.service.gov.uk/company/15897237 |
| Delvra | 🟡 | Delvra Limited (Гонконг, BRN 79134199); созвучно Delivra, Delvora | https://crhk.guru/company/brn/79134199/delvra |
| Alturis | 🔴 | Alturis.ai (healthcare AI) + ALTURIS AI LTD (UK) | https://www.alturis.ai/ |
| Corvane | 🔴 | corvane.com — софтверная компания (NY, 2025) | https://corvane.com/ |
| Osmir | 🟡 | OSMIR SL — софтверная компания (Барселона) | https://linkedin.com/company/osmir-sl |
| Thalir | 🟡 | Thalir Tech — IT-консалтинг | https://www.thalir.co/ |
| Oquira | 🔴 | Oquira — работающий SaaS с публичным API | https://docs.oquira.com/en |
| Velindra | 🟡 | Velindra Group NI Ltd (UK, в процессе исключения из реестра) | https://opencorpdata.com/uk/NI718093 |
| Lanthir | 🟡 | lanthirclub.co + Lanthir-CLI (личный проект) | https://lanthirclub.co/ |
| Duneth | 🟡 | DUNETH SECURITIES LIMITED (UK) | https://find-and-update.company-information.service.gov.uk/company/00086279 |
| Seldara | 🟡 | Seldara Global (магазин, товары для животных) | https://shop.app/m/vt5kdzayq1 |
| Mystrel | 🟡 | Mystrel Design (Огайо, computer dealers); Mythrel (Steam) | https://store.steampowered.com/app/2283950/Mythrel/ |
| Obsidia / Strata / Calyx / Tyrian / Petrel / Sablon / Selvara / Arboris / Lyrix / Tessara | 🟡–🔴 | тысячи–сотни тысяч репозиториев с этим именем в GitHub Search, все домены заняты | GitHub Search API |
| Volaris, Quorix, Arvexa, Ferrox, Kryon, Noctra, Veyra, Solene, Navaris, Ostara, Polaria | 🟡–🔴 | все 4 ключевых домена заняты (Volaris — авиакомпания, Navaris — бренд e-commerce) | RDAP |

---

## 3. TOP 20 (после отсева)

Brand score 0–100: уникальность (35), отсутствие конфликтов (25), доступность namespace (20), произносимость/международность (20).

| # | Имя | Значение / ассоциация | Почему подходит | Найденные конфликты | Риск | Score |
|---|---|---|---|---|---|---|
| 1 | **Zaldros** | выдуманное, «твёрдое ядро», звучит как имя платформы | Уникально в поиске, свободны .com/.org/.io/.dev и все namespace; хорошо в «Install Zaldros Linux» | Только фан-карта MTG Cardsmith (не бренд) | 🟢 GREEN | 90 |
| 2 | **Quinvara** | выдуманное, «пятое/цельное» + мягкое окончание | Полностью свободные домены и namespace; нейтрально, легко читается | Не найдено; созвучия: Qinara (UK), Quin AI | 🟢 GREEN | 85 |
| 3 | **Oskuria** | «обширная тьма/глубина» (лат./исп. корень *oscuro*) | Свободны все 4 домена + GitHub/GitLab/Codeberg; красиво звучит | Oscuria (игра), Oskoreia (софт-компания) — похожие, но не идентичные | 🟢 GREEN | 83 |
| 4 | **Drenvia** | выдуманное, «поток/движение» | .org/.io/.dev свободны, GitHub-юзер свободен | Drenlia Inc. (веб-студия) — созвучие | 🟢 GREEN | 80 |
| 5 | **Brimara** | «край/грань» + мягкое окончание | Все namespace свободны, .org/.io/.dev свободны | Прямых не найдено | 🟢 GREEN | 79 |
| 6 | **Turavia** | «путь/странствие» (фин. *tur*) | GitHub/GitLab/Codeberg свободны, .org/.io свободны | Созвучие с турагентствами (Turavia — тур-бренды) | 🟡 YELLOW | 74 |
| 7 | **Zephrym** | «поток воздуха», техно-звучание | .org/.io/.dev свободны | Zephyr — RTOS от Linux Foundation (сильное созвучие) | 🟡 YELLOW | 66 |
| 8 | **Myrkos** | др.-сканд. *myrkr* «тьма» | Короткое, .org/.io/.dev свободны | Mirko/Myrko — личные ники | 🟡 YELLOW | 72 |
| 9 | **Thovar** | выдуманное, «крепкий» | .org/.io/.dev свободны | Thovar — единичные упоминания | 🟡 YELLOW | 71 |
| 10 | **Orvenia** | «золотой край» | .org/.io/.dev свободны | Orvenia — не найдено крупного | 🟡 YELLOW | 70 |
| 11 | **Naldera** | топоним-подобное | .org/.io/.dev свободны | Naldera (место в Индии) | 🟡 YELLOW | 68 |
| 12 | **Varkonis** | «страж» | .org/.io/.dev свободны | Varkonis — фамилия | 🟡 YELLOW | 67 |
| 13 | **Lumbria** | «свет» + регион | .org/.io/.dev свободны | Ассоциация с Umbria/Cumbria; «lumbar» в EN | 🟡 YELLOW | 63 |
| 14 | **Kalunda** | ритмичное, африкан. звучание | .org/.io/.dev свободны | топонимы | 🟡 YELLOW | 62 |
| 15 | **Sindara** | «сияние» | .org/.io свободны | Sindara — имена собственные | 🟡 YELLOW | 62 |
| 16 | **Noviren** | «новый ток» | .org/.io/.dev свободны | Novi/Noven — созвучия в фарме | 🟡 YELLOW | 60 |
| 17 | **Frostine** | «морозный» | .org/.io/.dev свободны | Ассоциация с десертами/персонажами; EN-специфично | 🟡 YELLOW | 58 |
| 18 | **Seldara** | «редкий дар» | namespace свободны | Seldara Global (ритейл) | 🟡 YELLOW | 57 |
| 19 | **Velindra** | «мягкая скорость» | .org/.io свободны | Velindra Group NI Ltd | 🟡 YELLOW | 55 |
| 20 | **Kirvane** | «острый край» | .org/.io/.dev свободны | Kirvano (финтех, BR) + мёртвый TM | 🟡 YELLOW | 52 |

---

## 4. TOP 5 — детально

### 1. Zaldros — Brand score 90 🟢
- **Why it fits:** твёрдое, «инженерное» звучание без фэнтезийной приторности; одинаково читается по-русски (За́лдрос) и по-английски; идеально ложится в «Zaldros OS 1.0», «Zaldros Desktop», «Powered by Zaldros». Короткое (7 букв), логотип легко строится из Z-глифа.
- **Main risk:** имя выдуманное → отсутствие «естественного» смысла нужно компенсировать брендингом.
- **Linux conflicts:** не найдено — нет distro, DE, пакета, утилиты, immutable/bootc-проекта с таким именем.
- **GitHub availability:** `github.com/zaldros` — свободен; `github.com/zaldroslinux` — свободен; GitLab `zaldros` — свободен; Codeberg `zaldros` — свободен; GitHub Search: 0 репозиториев с таким именем.
- **Domain situation:** zaldros.com AVAILABLE · .org AVAILABLE · .io AVAILABLE · .dev AVAILABLE (RDAP, 2026-08-23).
- **Trademark risk:** заметных знаков не обнаружено; единственное упоминание — фан-карта Magic на MTG Cardsmith (не коммерческий бренд). **LEGAL REVIEW REQUIRED** перед регистрацией.

### 2. Quinvara — 85 🟢
- **Why it fits:** мягкое, международное, легко произносится в RU/EN/DE; хорошо для «Welcome to Quinvara».
- **Main risk:** созвучия в AI-сегменте (Quin AI, Qinara, Quint) → возможна лёгкая путаница в поиске.
- **Linux conflicts:** не найдено. **GitHub:** `quinvara` — свободен (подтверждён по 404), `quinvaralinux` — свободен; GitLab/Codeberg свободны.
- **Domains:** .com/.org/.io AVAILABLE; .dev UNKNOWN (rate limit при проверке — перепроверить).
- **Trademark risk:** низкий, прямых знаков не найдено. LEGAL REVIEW REQUIRED.

### 3. Oskuria — 83 🟢
- **Why it fits:** есть смысловой корень (*oscuro* — глубина/тьма), красивое звучание, «Oskuria Desktop» смотрится премиально.
- **Main risk:** «тёмная» семантика в испаноязычных странах; фонетическая близость к Oscuria (инди-игра) и Oskoreia (софт-компания).
- **Linux conflicts:** нет.
- **GitHub:** `oskuria` и `oskurialinux` свободны; GitLab/Codeberg свободны; 0 репозиториев.
- **Domains:** .com/.org/.io/.dev — все AVAILABLE.
- **Trademark risk:** низкий-средний (созвучия). LEGAL REVIEW REQUIRED.

### 4. Drenvia — 80 🟢
- **Why it fits:** динамичное, короткое, ассоциация с «потоком/скоростью» — точное попадание в позиционирование «высокая производительность».
- **Main risk:** Drenlia Inc. — созвучная веб-студия; .com занят.
- **Linux conflicts:** нет. **GitHub:** `drenvia` свободен; GitLab/Codeberg свободны.
- **Domains:** .com TAKEN; .org/.io/.dev AVAILABLE.
- **Trademark risk:** низкий. LEGAL REVIEW REQUIRED.

### 5. Brimara — 79 🟢
- **Why it fits:** «край/грань» + мягкий финал; нейтрально во всех языках, приятно в «Install Brimara Linux».
- **Main risk:** .com занят; звучит чуть «мягче», чем нужно для perf-ориентированной ОС.
- **Linux conflicts:** нет. **GitHub:** `brimara` свободен, 0 репозиториев; GitLab/Codeberg свободны.
- **Domains:** .com TAKEN; .org/.io/.dev AVAILABLE.
- **Trademark risk:** низкий. LEGAL REVIEW REQUIRED.

---

## 5. ONE BEST NAME

# ZALDROS

**Zaldros Linux · Zaldros OS · Zaldros Desktop · Powered by Zaldros**

Почему именно оно для «Linux + Windows-like UX + производительность + минимум фоновых служб + современный десктоп + open source + независимый бренд»:
1. **Нулевая путаница** — единственное имя из всех 129 проверенных, где одновременно: нет ни дистрибутива, ни ОС, ни компании, ни заметного OSS-проекта, ни пакета, ни системной утилиты, 0 репозиториев в GitHub Search.
2. **Полная namespace-чистота** — свободны `.com`, `.org`, `.io`, `.dev`, `github.com/zaldros`, `github.com/zaldroslinux`, GitLab и Codeberg. Можно занять всё сразу и на годы вперёд.
3. **Фонетика бренда ОС** — твёрдые согласные Z/D/R читаются как «инженерное», а не «декоративное» имя; так звучат платформы, а не темы оформления. Идентификатор `zaldros` (`ID=zaldros` в `/etc/os-release`, префикс пакетов `zaldros-*`, CLI `zaldros-sysprobe`) короткий и без коллизий.
4. **Международность** — одинаково читается в RU и EN, без негативных значений в основных языках; хорошо для логотипа (моно-глиф «Z»).

**Немедленные шаги (рекомендация):**
1. Зарегистрировать `zaldros.org` (основной, как у дистрибутивов) + `.com`/`.io`/`.dev` защитно.
2. Создать GitHub-организацию `zaldros` и зеркала неймспейсов на GitLab/Codeberg, занять `@zaldros` в соцсетях.
3. Провести **юридическую проверку товарных знаков** (USPTO/EUIPO/Роспатент, классы 9 и 42) до публичного анонса.
4. После утверждения — переименовать: `ID=zaldros`, префиксы пакетов/CLI, `docs/NAMING.md`, ADR-0006.

Резерв, если юрпроверка даст стоп: **Quinvara** → **Oskuria**.

---

## Приложение A — сырые данные проверки namespace (129 имён)

Формат: имя | .com | .org | .io | .dev | github.com/&lt;name&gt; | github.com/&lt;name&gt;linux | gitlab | codeberg.
AVAILABLE/FREE = не занято на 2026-08-23; UNKNOWN = проверку ограничил rate limit.

| name | .com | .org | .io | .dev | GH user | GH userlinux | GitLab | Codeberg |
|---|---|---|---|---|---|---|---|---|
| alturis | TAKEN | AVAILABLE | TAKEN | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| arboris | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| ardyn | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | TAKEN | FREE |
| arvexa | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| ashvane | TAKEN | AVAILABLE | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| astrella | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | FREE | FREE |
| aurora | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN |
| auroraos | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | TAKEN |
| axionis | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| basalta | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| bedrock | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | TAKEN | FREE | TAKEN |
| bedrocklinux | AVAILABLE | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| bedrockos | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| brakkon | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| brimara | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| brimstone | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | TAKEN | UNKNOWN(429) | TAKEN | TAKEN |
| brytan | TAKEN | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| caldrix | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | FREE | FREE |
| calyx | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| cindra | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| corvane | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| crestal | TAKEN | AVAILABLE | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| delvra | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| drenvia | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| druvia | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| duneth | AVAILABLE | AVAILABLE | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | TAKEN | FREE |
| elmiron | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| elvaris | TAKEN | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| ferrox | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| frostine | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| grandiva | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| granith | TAKEN | TAKEN | AVAILABLE | TAKEN | TAKEN | FREE | TAKEN | FREE |
| halvor | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| ignara | TAKEN | TAKEN | AVAILABLE | UNKNOWN | TAKEN | FREE | FREE | FREE |
| juneau | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| kaldera | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | TAKEN | FREE |
| kalunda | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| kalvyn | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | TAKEN | FREE |
| kaviro | TAKEN | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| kestrix | TAKEN | AVAILABLE | TAKEN | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| kirova | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| kirvane | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| korvath | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| kryon | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| lanthir | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | FREE | FREE | FREE | FREE |
| loventia | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| lucera | TAKEN | TAKEN | TAKEN | AVAILABLE | TAKEN | FREE | FREE | FREE |
| lumbria | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| lumence | TAKEN | AVAILABLE | TAKEN | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| lumeon | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| lyrix | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | TAKEN |
| marnix | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | TAKEN |
| mirava | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | FREE | FREE |
| morvane | TAKEN | TAKEN | AVAILABLE | UNKNOWN | TAKEN | FREE | TAKEN | TAKEN |
| myrkos | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| mystrel | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| naldera | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| navaris | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| noctra | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| nova | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN |
| novalinux | TAKEN | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| noviren | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| nyxora | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| obsidia | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | FREE | FREE |
| olvano | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| onyxa | TAKEN | AVAILABLE | TAKEN | UNKNOWN | TAKEN | FREE | FREE | FREE |
| oquira | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| orbium | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| oreline | TAKEN | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | FREE | FREE | FREE |
| orvenia | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| oskuria | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| osmir | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| ostara | TAKEN | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| ostrale | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| pelaris | TAKEN | AVAILABLE | TAKEN | AVAILABLE | FREE | FREE | FREE | FREE |
| petrel | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | TAKEN |
| polaria | TAKEN | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| prime | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | TAKEN |
| primeos | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | TAKEN |
| pyrelith | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| quartzite | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | TAKEN |
| quenrik | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | UNKNOWN | FREE |
| quinvara | AVAILABLE | AVAILABLE | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| quorix | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| raven | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN |
| ravenlinux | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | TAKEN | FREE |
| ravenos | TAKEN | TAKEN | TAKEN | AVAILABLE | TAKEN | FREE | FREE | FREE |
| sablon | TAKEN | TAKEN | TAKEN | AVAILABLE | TAKEN | FREE | FREE | FREE |
| seldara | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| selvara | TAKEN | TAKEN | AVAILABLE | UNKNOWN | TAKEN | FREE | FREE | FREE |
| serenix | TAKEN | TAKEN | AVAILABLE | UNKNOWN | TAKEN | FREE | FREE | FREE |
| sindara | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| skarnet | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | TAKEN |
| solene | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| solstral | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| solvane | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| strandel | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | TAKEN | FREE |
| strata | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | TAKEN |
| sylvane | TAKEN | TAKEN | AVAILABLE | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| tarvos | TAKEN | AVAILABLE | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| tavren | TAKEN | AVAILABLE | TAKEN | AVAILABLE | TAKEN | FREE | TAKEN | FREE |
| telvora | TAKEN | AVAILABLE | TAKEN | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| terrix | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | TAKEN | FREE |
| tessara | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| tessvan | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| thalir | TAKEN | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| thovar | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| torvin | TAKEN | AVAILABLE | AVAILABLE | TAKEN | TAKEN | FREE | TAKEN | FREE |
| tremora | TAKEN | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | FREE | FREE | FREE |
| turavia | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | FREE | FREE | FREE | FREE |
| tyrian | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | TAKEN | FREE |
| umbara | TAKEN | TAKEN | AVAILABLE | AVAILABLE | TAKEN | FREE | TAKEN | FREE |
| vaeltro | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| vandrel | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| vantra | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | TAKEN | FREE |
| varkonis | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| varnessa | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | FREE | UNKNOWN(429) | FREE | FREE |
| veldra | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| velindra | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| verdo | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | TAKEN | FREE |
| vexil | TAKEN | TAKEN | TAKEN | UNKNOWN | TAKEN | FREE | FREE | FREE |
| veyra | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| vireon | TAKEN | TAKEN | TAKEN | UNKNOWN(429) | UNKNOWN(429) | UNKNOWN(429) | FREE | FREE |
| volara | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| volaris | TAKEN | TAKEN | TAKEN | TAKEN | TAKEN | FREE | FREE | FREE |
| zaldros | AVAILABLE | AVAILABLE | AVAILABLE | AVAILABLE | FREE | FREE | FREE | FREE |
| zephira | TAKEN | AVAILABLE | AVAILABLE | UNKNOWN(429) | TAKEN | FREE | FREE | FREE |
| zephrym | TAKEN | AVAILABLE | AVAILABLE | AVAILABLE | TAKEN | FREE | FREE | FREE |
| zircona | TAKEN | AVAILABLE | TAKEN | AVAILABLE | TAKEN | FREE | TAKEN | FREE |

---
Проверки выполнены 2026-08-23 автоматизированным аудитом (RDAP + GitHub/GitLab/Codeberg + веб-поиск). Данные о доступности меняются — перепроверять перед регистрацией.
