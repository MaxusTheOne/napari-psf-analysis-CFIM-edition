import sys
from typing import overload

import napari
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit

napari_cmap_list = list(napari.utils.colormaps.AVAILABLE_COLORMAPS.keys())
@overload
def get_colormap_pixmap(colormap_name: str, width: int, height: int) -> QPixmap:
    pass
@overload
def get_colormap_pixmap(colormap_name: napari.utils.Colormap, width: int, height: int) -> QPixmap:
    pass

def get_colormap_pixmap(colormap_name, width=200, height=20):
    """
        Gets a colormap from napari and converts it to a QPixmap.
    """
    if type(colormap_name) is str:
        napari_cmap = napari.utils.colormaps.ensure_colormap(colormap_name)
    else:
        napari_cmap = colormap_name

    gradient_1d = np.linspace(0, 1, width)

    gradient_2d = np.tile(gradient_1d, (height, 1))

    gradient_rgba = napari_cmap.map(gradient_2d)
    gradient_rgba_uint8 = (gradient_rgba * 255).astype(np.uint8)

    # Create a QImage from the RGBA array
    height, width, channels = gradient_rgba.shape

    q_image = QImage(gradient_rgba_uint8, width, height, QImage.Format_RGBA8888)
    pixmap = QPixmap.fromImage(q_image)

    return pixmap



class QLineEditWithColormap(QLineEdit):
    def __init__(self, colormap_name: str, parent=None):
        super().__init__(parent)
        self._colormap_name = colormap_name
        if self.width() < 100 or self.height() < 30:
            print(f"Element size: {self.width()} x {self.height()}")
        self._pixmap = get_colormap_pixmap(colormap_name, self.width(), self.height())

        self.setStyleSheet("QLineEdit { background: transparent; color: white; }")




    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._pixmap)
        painter.end()

        super().paintEvent(event)

    def keyReleaseEvent(self, event):

        color_map = valid_cmap(self.text())
        if color_map:
            self._set_colormap(color_map)
        super().keyReleaseEvent(event)

    def _set_colormap(self, colormap_name):
        self._colormap_name = colormap_name
        self._pixmap = get_colormap_pixmap(colormap_name)
        self.update()

def valid_cmap(cmap_name):
    """
        Validates if the colormap name is in the napari colormap list.
    """
    if len(cmap_name) < 3:
        return False
    try:
        cmap = napari.utils.colormaps.ensure_colormap(cmap_name)
        return cmap
    except KeyError:
        return False






if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create a simple window with a vertical layout.
    window = QWidget()
    layout = QVBoxLayout(window)

    title_label = QLabel("QLineEditWithColormap Test:")
    layout.addWidget(title_label)

    # Instantiate your custom QLineEdit with a colormap name.
    custom_line_edit = QLineEditWithColormap("red")
    layout.addWidget(custom_line_edit)

    window.setWindowTitle("Test QLineEditWithColormap")
    window.resize(300, 100)
    window.show()

    sys.exit(app.exec_())
