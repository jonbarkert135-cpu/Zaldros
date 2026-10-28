# Reusable development environments

Use Linux with Python 3.12 or newer. The verified Python versions are recorded
with each run; this is not a promise that every future interpreter is supported.
The interpreter needs venv/ensurepip (`python3-venv` on Debian/Ubuntu).
The script uses stdlib `venv` and pip inside the selected venv. It never runs apt,
installs system packages, or changes the caller's active Python environment.

All commands below start in the repository root.

## Shell and backend

```sh
python3 tools/dev/setup.py shell
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest shell/zaldros-shell/tests -q
```

The default target is `.venv`. The profile installs pinned pytest, PySide6,
Pillow and numpy and imports their required modules before accepting the setup.
The Linux host must provide `dbus-daemon`, `gpg`, `curl`, `tar` and Qt's native
runtime libraries. On Ubuntu, install the host prerequisites once:

```sh
sudo apt-get update
sudo apt-get install -y python3-venv dbus-daemon gnupg curl tar \
  libgl1 libegl1 libxkbcommon0 libdbus-1-3 fonts-noto-color-emoji
```

Render from the shell's module directory (project source is not globally installed):

```sh
cd shell/zaldros-shell
QT_QPA_PLATFORM=offscreen ../../.venv/bin/python -m zaldros_shell render --out /tmp/zaldros-desktop.png
```

## Lightweight tooling

```sh
python3 tools/dev/setup.py tools
.venv-tools/bin/python -m pytest tools -q
```

This profile installs pytest without Qt. Tools with their own `-m` entry points
still run from their documented module directories.

## Office

```sh
/usr/bin/python3 tools/dev/setup.py office
QT_QPA_PLATFORM=offscreen .venv-office/bin/python tools/ci/office.py writer --junitxml office-results/writer.xml
```

Office uses `/usr/bin/python3` by default and requires an already installed matching
`python3-uno` and LibreOffice executable. Its venv includes system site packages so
the compiled UNO binding stays visible. The script checks the selected interpreter's
actual UNO import before creating a target. It then verifies UNO again in the venv.
Missing UNO is a failure, not permission to substitute another engine or skip tests.
Component packages and all three required test commands: [Office setup](../office/BUILD.md).

## Inspection, reuse and safeguards

```sh
python3 tools/dev/setup.py shell --check
python3 tools/dev/setup.py tools --venv /tmp/zaldros-tools --python /usr/bin/python3
```

`--check` validates an existing environment without running pip or creating it.
Probes disable bytecode writes. The JSON result reports actual imports, versions,
prefixes and UNO origin where applicable. CI also exposes this receipt through a
`Development environment` Checks annotation. Dependency readiness does not certify
real services, Office round trips, a compositor, hardware or the installed OS.

The default directories are `.venv`, `.venv-tools` and `.venv-office`; they are
gitignored. `--venv` accepts another explicit directory. Defaults resolve inside
the repository even when the script is called from elsewhere; an explicit relative
path resolves against the caller's current directory. `--python` selects the creation
interpreter; `--check` inspects the target itself.

Existing non-venv directories and symlink targets are refused. Reuse requires the
same base interpreter and profile's system-site mode. An existing venv is never
deleted/recreated automatically. Every pip invocation uses the validated target
Python with `--require-virtualenv`; user site packages are disabled. A failed install
can leave a partial venv and returns nonzero; choose a new target or repair the
explicit development directory rather than replacing an unrelated user folder.

Child processes ignore `PYTHONPATH`/`PYTHONHOME`, pip destination/extra-requirement
overrides and user/system pip configuration files. Network/source/TLS/verification
options listed in `PIP_SOURCE_OPTIONS` are retained, including configured indexes,
wheelhouses and hash requirements. Configure private indexes via `PIP_INDEX_URL`
or `PIP_EXTRA_INDEX_URL`; the bootstrap does not echo network-option values. These
changes apply to child processes, not the caller's environment.

Direct versions live once in `tools/dev/constraints.txt`. The tools, shell and
Office requirement files reference those pins. This fixes direct dependencies;
transitive packages, interpreter builds and apt repositories are not an immutable
lockfile/snapshot. CI uses this same preparation script for tools, shell and Office.
## Environment publication and GitHub delivery

Publishing the cloud environment applies its saved setup/network configuration and
snapshot. It is needed after changing that configuration, not for every coding
session or PR. A normal project change uses branch → PR → checks → GitHub merge.
Publishing an OS release or ISO for users is a separate action; environment Publish
does not release Zaldros or replace the GitHub PR workflow.
