import sys

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QComboBox, QPushButton, QApplication, QTabWidget, QLabel


class ImageSelectorDropDown(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drop_down = None
        self.open_images_button = None


    def add_item(self, item):
        self.drop_down.addItem(item)


    def init_ui(self):
        layout = QHBoxLayout()
        print(f"Init ui")

        self.drop_down = QComboBox(self)
        self.drop_down.setToolTip(
            "Image layer with the measured point spread functions (PSFs)."
        )

        self.drop_down.currentIndexChanged.connect(self._on_index_changed)

        self.open_images_button = QPushButton("+", self)

        layout.addWidget(self.drop_down,3)
        layout.addWidget(self.open_images_button,1)

        return layout


    def _on_index_changed(self):
        print("Index changed")




if __name__ == "__main__":
    app = QApplication(sys.argv)
    tabs = QTabWidget()
    basic_settings = QWidget(tabs)
    widget = ImageSelectorDropDown(basic_settings)
    tabs.addTab(basic_settings, "Basic Settings")
    tabs.show()  # Make the widget visible
    sys.exit(app.exec_())

