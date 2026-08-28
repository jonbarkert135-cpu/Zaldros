# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt model for Zaldros Slides. A view of the engine, never a second copy of the deck."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from .engine import EngineError, LAYOUTS, TRANSITIONS, impress_available

RIBBON_TABS = ("Файл", "Главная", "Вставка", "Конструктор", "Переходы", "Анимация",
               "Слайд-шоу", "Рецензирование", "Вид")


class DeckModel(QObject):
    """The slide pane, the canvas and the notes box."""

    changed = Signal()

    def __init__(self, presentation=None) -> None:
        super().__init__()
        self._deck = presentation
        self._slides: list[dict] = []
        self._current = 0
        self._status = "" if presentation is not None else self._missing_reason()
        if presentation is not None:
            self.refresh()

    @staticmethod
    def _missing_reason() -> str:
        if not impress_available():
            return "Движок Impress не установлен (пакет libreoffice-impress-nogui)"
        return "Презентация не открыта"

    @Slot()
    def refresh(self) -> None:
        if self._deck is None:
            self._slides = []
            self.changed.emit()
            return
        try:
            self._slides = [
                {"index": item.index, "name": item.name, "title": item.title,
                 "body": item.body, "layout": item.layout, "layoutName": item.layout_name,
                 "notes": item.notes, "shapes": item.shapes}
                for item in self._deck.slides()]
            self._status = ""
        except EngineError as error:
            self._slides = []
            self._status = str(error)
        self._current = min(self._current, max(0, len(self._slides) - 1))
        self.changed.emit()

    # --- editing -----------------------------------------------------------------------------
    @Slot(int, result=bool)
    def addSlide(self, layout: int = 1) -> bool:  # noqa: N802
        if self._deck is None:
            return False
        self._current = self._deck.add_slide(layout=layout)
        self.refresh()
        return True

    @Slot(int, result=bool)
    def removeSlide(self, index: int) -> bool:  # noqa: N802
        if self._deck is None:
            return False
        try:
            self._deck.remove_slide(index)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return True

    @Slot(int, str, str, result=bool)
    def setText(self, index: int, title: str, body: str) -> bool:  # noqa: N802
        """Fills the layout's placeholders. A layout without one refuses, and says so."""
        if self._deck is None:
            return False
        try:
            self._deck.set_text(index, title=title, body=body)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return True

    @Slot(int, str, result=bool)
    def setNotes(self, index: int, text: str) -> bool:  # noqa: N802
        if self._deck is None:
            return False
        try:
            self._deck.set_notes(index, text)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return True

    @Slot(int, int, result=bool)
    def setLayout(self, index: int, layout: int) -> bool:  # noqa: N802
        if self._deck is None:
            return False
        try:
            self._deck.set_layout(index, layout)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return True

    @Slot(int, int, result=bool)
    def setTransition(self, index: int, effect: int) -> bool:  # noqa: N802
        if self._deck is None:
            return False
        try:
            self._deck.set_transition(index, effect)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return True

    @Slot(str, result=bool)
    def saveAs(self, path: str) -> bool:  # noqa: N802
        if self._deck is None:
            return False
        try:
            self._deck.save_as(path)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        return True

    @Slot(int)
    def select(self, index: int) -> None:
        if 0 <= index < len(self._slides):
            self._current = index
            self.changed.emit()

    # --- what QML draws -------------------------------------------------------------------------
    @Property("QVariantList", notify=changed)
    def slides(self) -> list:
        return list(self._slides)

    @Property("QVariantMap", notify=changed)
    def current(self) -> dict:
        return dict(self._slides[self._current]) if self._slides else {}

    @Property(int, notify=changed)
    def currentIndex(self) -> int:  # noqa: N802
        return self._current

    @Property("QVariantList", constant=True)
    def tabs(self) -> list:
        return list(RIBBON_TABS)

    @Property("QVariantList", constant=True)
    def layouts(self) -> list:
        return [{"id": key, "title": title} for key, title in sorted(LAYOUTS.items())]

    @Property("QVariantList", constant=True)
    def transitions(self) -> list:
        return [{"id": key, "title": title} for key, title in sorted(TRANSITIONS.items())]

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def live(self) -> bool:
        return self._deck is not None
