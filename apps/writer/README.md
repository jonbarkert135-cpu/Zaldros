# Zaldros Writer

Наше окно в форме Word на движке LibreOffice Writer (ADR-0020, продолжение ADR-0013).

* `zaldros_writer/engine.py` — мост к движку: живой документ через UNO, плюс `convert()` через
  `soffice --convert-to` для файловых преобразований без UNO.
* `zaldros_writer/model.py` — модель Qt; без движка документ пуст и в строке состояния написано,
  какого пакета не хватает.
* `qml/Writer.qml` — лента, страница A4, строка состояния.

Запуск: `python -m zaldros_writer render --out writer.png` (или `run`). Нужен
`libreoffice-writer-nogui` и `python3-uno`; интерпретатор — тот, под который собран `python3-uno`.
