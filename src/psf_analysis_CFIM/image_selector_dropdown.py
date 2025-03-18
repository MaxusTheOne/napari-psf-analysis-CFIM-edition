import sys

import napari
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QComboBox, QPushButton, QApplication, QTabWidget, QLabel, QMessageBox, \
    QGroupBox, QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox


class ImageSelectorDropDown(QWidget):
    def __init__(self, parent=None, viewer=None):
        super().__init__(parent)
        self.drop_down = None
        self.open_images_button = None

        self._viewer = viewer


        self._images = None
        self._selection_dialog = None


    def add_item(self, item):
        self.drop_down.addItem(item)


    def init_ui(self):
        layout = QHBoxLayout()

        self.drop_down = QComboBox(self)
        self.drop_down.setToolTip(
            "Image layer with the measured point spread functions (PSFs)."
        )

        self.drop_down.currentIndexChanged.connect(self._on_index_changed)

        self.open_images_button = QPushButton("+", self)
        self.open_images_button.clicked.connect(self.open_images_clicked)

        layout.addWidget(self.drop_down,4)
        layout.addWidget(self.open_images_button,1)

        return layout


    def _on_index_changed(self):
        print("Index changed")

    def open_images_clicked(self):

        images = []
        for layer in self._viewer.layers:
            if isinstance(layer, napari.layers.Image):
                images.append(layer)
        self._images = images
        print(f"Images: {images}")

        self._selection_dialog = ImageSelectionDialog(parent= self, images = images)
        self._selection_dialog.exec_()



class ImageSelectionDialog(QDialog):
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.images = images
        self.selected_images = []  # Will store selected images on accept.
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Select Images")
        layout = QVBoxLayout(self)

        # Create a row for each image with a label and a checkbox.
        self.checkboxes = {}
        for image in self.images:
            row_layout = QHBoxLayout()
            label = QLabel(image.name)
            checkbox = QCheckBox()
            row_layout.addWidget(label)
            row_layout.addWidget(checkbox)
            layout.addLayout(row_layout)
            self.checkboxes[image] = checkbox

        # Add OK and Cancel buttons.
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_accept(self):
        # Iterate through checkboxes to determine selected images.
        self.selected_images = [image for image, cb in self.checkboxes.items() if cb.isChecked()]
        self.accept()  # Close dialog with accepted status.

    def get_selected_images(self):
        return self.selected_images


if __name__ == "__main__":
    app = QApplication(sys.argv)
    tabs = QTabWidget()
    basic_settings = QWidget(tabs)
    widget = ImageSelectorDropDown(basic_settings)
    tabs.addTab(basic_settings, "Basic Settings")
    tabs.show()  # Make the widget visible
    sys.exit(app.exec_())

