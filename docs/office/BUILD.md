# Office development and required CI

Writer, Sheets and Slides use LibreOffice through UNO, with their own Qt UI.
The required CI matrix in `.github/workflows/ci.yml` tests each application in a
separate process/job on Ubuntu 24.04. It installs the corresponding Writer/Calc/
Impress component and the distribution's `python3-uno`. This runner is a test
environment, not a change to the Ubuntu 26.04 ISO candidate.

## Matching the interpreter

UNO is compiled for the distribution's Python. Use `/usr/bin/python3`, not the
Python selected by `actions/setup-python` or an unrelated venv. A venv created
with `--system-site-packages` keeps the matching UNO binding visible and installs
pytest/Qt without changing the system's Python packages.

From the repository root on Ubuntu 24.04:

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends python3-uno python3-venv \
  libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui \
  libgl1 libegl1 libxkbcommon0 libdbus-1-3 fonts-liberation fonts-dejavu-core
/usr/bin/python3 tools/dev/setup.py office
QT_QPA_PLATFORM=offscreen .venv-office/bin/python tools/ci/office.py writer --junitxml office-results/writer.xml
QT_QPA_PLATFORM=offscreen .venv-office/bin/python tools/ci/office.py sheets --junitxml office-results/sheets.xml
QT_QPA_PLATFORM=offscreen .venv-office/bin/python tools/ci/office.py slides --junitxml office-results/slides.xml
```

Each engine process uses a private temporary LibreOffice profile and local UNO
socket. Tests include real DOCX/XLSX/PPTX round trips, PDF export for Writer/Slides,
Calc arithmetic/errors, and offscreen Qt rendering. They do not certify complete
Microsoft Office compatibility, interactive editing or ISO-installed integration.

## Acceptance

`tools/ci/office.py` first requires UNO, Qt and LibreOffice in the selected
interpreter. Missing dependencies fail before optional-test skip logic runs.
Then real pytest runs both `test_engine.py` and `test_ui.py` for the selected app.
Any skipped test or skipped module fails the mandatory run; both suites must
execute passing tests. Empty collections and ordinary test failures remain
nonzero. Engine assertions are retained. The Writer missing-component unit test
injects that condition so it also executes on a fully provisioned runner.

For optional development without an engine, ordinary pytest remains available:
`cd apps/sheets && python -m pytest tests -q`. Its skips are not CI acceptance.

CI uploads JUnit XML and interpreter/LibreOffice/package versions as
`office-writer`, `office-sheets` and `office-slides` artifacts, including on failure.
Bounded failure details and executed test counts are also emitted as GitHub Checks
annotations, so diagnosis does not depend solely on artifact download access.
LibreOffice/UNO come from the runner's signed apt repositories. Qt and pytest are
pinned in `tools/ci/office-requirements.txt`; apt package versions are recorded,
not claimed to be an immutable distribution snapshot.

Office requirements reference the shared exact pins in `tools/dev/constraints.txt`.
Local and CI preparation use the same script. Read-only checks and reuse safeguards:
[development setup](../development/SETUP.md). The owner's Windows Office visual
references and unchanged-engine requirement are recorded in
[REFERENCE_BRIEF.md](REFERENCE_BRIEF.md).
