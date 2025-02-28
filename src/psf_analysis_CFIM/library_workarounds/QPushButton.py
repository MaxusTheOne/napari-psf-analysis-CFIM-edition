from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QPushButton, QLabel


class RichTextPushButton(QPushButton):
    def __init__(self, parent=None, text=None):
        if parent is not None:
            super().__init__(parent)
        else:
            super().__init__()
        self._lbl = QLabel(self)
        if text is not None:
            self._lbl.setText(text)
        self._lyt = QHBoxLayout()
        self._lyt.setContentsMargins(0, 0, 0, 0)
        self._lyt.setSpacing(0)
        self.setLayout(self._lyt)
        self._lbl.setAttribute(Qt.WA_TranslucentBackground)
        self._lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._lbl.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setTextFormat(Qt.RichText)
        self._lyt.addWidget(self._lbl)
        return

    def setText(self, text):
        self._lbl.setText(text)
        self.updateGeometry()
        return

    def sizeHint(self):
        s = QPushButton.sizeHint(self)
        w = self._lbl.sizeHint()
        s.setWidth(w.width())
        s.setHeight(w.height())
        return s