from weakref import WeakKeyDictionary

from PySide6.QtCore import QObject, QEvent, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip


class DelayedToolTipHelper(QObject):
    """
    Bietet Tooltips mit einstellbarer Verzögerung, damit Hinweise nicht sofort erscheinen.
    Widgets werden über `register` angemeldet; der Tooltip wird erst nach `delay_ms` angezeigt.
    """

    def __init__(self, delay_ms: int = 800, parent=None):
        super().__init__(parent)
        self.delay_ms = delay_ms
        self._texts = WeakKeyDictionary()
        self._timers = {}
        self._positions = {}

    def register(self, widget, text: str):
        if widget is None:
            return
        self._texts[widget] = text
        widget.setToolTip("")  # Standard-Tooltip deaktivieren
        widget.installEventFilter(self)

    def unregister(self, widget):
        if widget in self._texts:
            widget.removeEventFilter(self)
            self._texts.pop(widget, None)
            self._cancel_timer(widget)
            self._positions.pop(widget, None)

    def eventFilter(self, obj, event):
        if obj in self._texts:
            if event.type() == QEvent.Enter:
                self._positions[obj] = QCursor.pos()
                self._start_timer(obj)
            elif event.type() == QEvent.MouseMove:
                self._positions[obj] = obj.mapToGlobal(event.pos())
            elif event.type() in (QEvent.Leave, QEvent.Hide, QEvent.FocusOut):
                self._cancel_timer(obj)
                self._positions.pop(obj, None)
                QToolTip.hideText()
            elif event.type() == QEvent.ToolTip:
                return True  # Qt-Standard-Tooltip unterdrücken
            elif event.type() == QEvent.MouseButtonPress:
                self._cancel_timer(obj)
                QToolTip.hideText()
        return super().eventFilter(obj, event)

    def _start_timer(self, widget):
        self._cancel_timer(widget)
        timer = QTimer(widget)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda w=widget: self._show_tooltip(w))
        self._timers[widget] = timer
        timer.start(self.delay_ms)

    def _cancel_timer(self, widget):
        timer = self._timers.pop(widget, None)
        if timer is not None:
            timer.stop()

    def _show_tooltip(self, widget):
        text = self._texts.get(widget)
        if not text or not widget.isVisible():
            return
        pos = self._positions.get(widget, QCursor.pos())
        QToolTip.showText(pos, text, widget)

