import sys
from typing import overload, List

import napari
import numpy as np
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QPalette, QImage, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QComboBox, QPushButton, QApplication, QTabWidget, QLabel, QMessageBox, \
    QGroupBox, QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox, QFormLayout, QLineEdit, QGridLayout

from psf_analysis_CFIM.library_workarounds.QLineEditWithColormapBg import QLineEditWithColormap

# TODO: Potentially change this to manage access to image layers
class ImageSelectorDropDown(QWidget):
    def __init__(self, parent=None, viewer=None):
        super().__init__(parent)
        self.drop_down = None
        self.open_images_button = None

        self._viewer = viewer

        # Too scared of layers changing position in the viewer to use references instead of storing the layers
        self._selected_as_layers: List[napari.layers.Image] = []
        self._multi_image_selection = ""


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

    def open_images_clicked(self):

        images = []
        for layer in self._viewer.layers:
            if isinstance(layer, napari.layers.Image):
                images.append(layer)

        selected_images_dict = []
        dialog = ImageSelectionDialog(parent= self, images = images)
        if dialog.exec() == QDialog.Accepted:
            selected_images_dict = dialog.get_selected_images()


        if len(selected_images_dict) == 0: return

        elif len(selected_images_dict) == 1: self._change_dropdown_to_image(selected_images_dict[0]["name"])

        elif len(selected_images_dict) <= len(images):
            self._change_dropdown_to_images(selected_images_dict)

    def get_images(self):
        return self._selected_as_layers

    def get_as_layers(self):
        return self._selected_as_layers

    def get_image_if_single(self):
        if len(self._selected_as_layers) == 1:
            return self._selected_as_layers[0]
        else:
            raise ValueError("More than one image selected | Legacy code, will break on purpose")

    def set_selected_to_layers(self, layers):
        if type(layers) != list:
            layers = [layers]

        self._clear_multi_image_selection()

        if type(layers) != list:
            layers = [layers]

        if len(layers) == 1:
            self._selected_as_layers = [self._viewer.layers[layers[0].name]]
        self._selected_as_layers = layers



    def _on_index_changed(self):
        text = self.drop_down.currentText()
        if text != self._multi_image_selection:
            self._clear_multi_image_selection()
        self._selected_as_layers = [self._viewer.layers[text]]

    # region private methods
    def _change_dropdown_to_images(self, selected_images_dict: list):
        self._selected_as_layers = self._names_to_layers(selected_images_dict)

        self._clear_multi_image_selection()
        text = f"{len(self._selected_as_layers)} images"
        self.drop_down.addItem(text)
        self.drop_down.setCurrentIndex(self.drop_down.findText(text))

        self._multi_image_selection = text


    def _clear_multi_image_selection(self):
        if self._multi_image_selection != "":
            self.drop_down.removeItem(self.drop_down.findText(self._multi_image_selection))
        self._multi_image_selection = ""


    # I'm a maniac for using overloads in private methods, but they kinda fun.
    @overload
    def _names_to_layers(self, images_list: list[dict]) -> list[napari.layers.Image]:
        pass
    @overload
    def _names_to_layers(self, images_list: list[str]) -> list[napari.layers.Image]:
        pass
    def _names_to_layers(self, images_list): # The urge to rewrite this 2 minutes after writing it is strong
        image_layers = []
        if type(images_list) == list:
            for image in images_list:
                if type(image) == str:
                    image_layers.append(self._viewer.layers[image])
                elif type(image) == dict:
                    image_layers.append(self._viewer.layers[image["name"]])
                else:
                    raise ValueError(f"Invalid type in list: {type(image)}")
        else:
            raise ValueError(f"Invalid type: {type(images_list)}")

        return image_layers



    @overload
    def _change_dropdown_to_image(self, image_name: str):
        pass
    @overload
    def _change_dropdown_to_image(self, index: int):
        pass

    def _change_dropdown_to_image(self, *args): # This overload is a bit silly
        if type(args[0]) is str:
            image_name = args[0]
            index = self._index_from_name(image_name)
        elif type(args[0]) is int:
            index = args[0]
        else:
            raise ValueError("Invalid argument type, must be str or int | Got {type(args[0])}")
        self.drop_down.setCurrentIndex(index)
        self._selected_as_layers = args[0]
        print(f"Index changed to {index}")


    def _index_from_name(self, image_name):
        index = self.drop_down.findText(image_name)
        return index




    # endregion



# region debug methods
def _log_combo_properties(combo: QComboBox):
    print("QComboBox isEditable:", combo.isEditable())
    le = combo.lineEdit()
    if le is None:
        print("LineEdit is None")
        return
    print("LineEdit isReadOnly:", le.isReadOnly())
    print("LineEdit alignment:", alignment_to_str(le.alignment()))
    print(f"LineEdit frame: {le.hasFrame()}")

def alignment_to_str(alignment):
    flags = []
    if alignment & Qt.AlignLeft:
        flags.append("AlignLeft")
    if alignment & Qt.AlignRight:
        flags.append("AlignRight")
    if alignment & Qt.AlignHCenter:
        flags.append("AlignHCenter")
    if alignment & Qt.AlignJustify:
        flags.append("AlignJustify")
    if alignment & Qt.AlignTop:
        flags.append("AlignTop")
    if alignment & Qt.AlignBottom:
        flags.append("AlignBottom")
    if alignment & Qt.AlignVCenter:
        flags.append("AlignVCenter")
    return " | ".join(flags)


# endregion

class ImageSelectionDialog(QDialog):
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.images = images
        self.selected_images: list[dict] = []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Select Images")
        grid_layout = QGridLayout(self)  # Changed layout from QFormLayout to QGridLayout

        # Header row (row 0): empty header for checkbox, then titles for image name and colormap
        grid_layout.addWidget(QWidget(self), 0, 0)  # Empty placeholder for the checkbox column header
        grid_layout.addWidget(QLabel("Image name", self), 0, 1)
        grid_layout.addWidget(QLabel("Color map", self), 0, 2)

        self.checkboxes = {}
        self.colormaps = {}
        for row, image in enumerate(self.images, start=1):
            checkbox = QCheckBox(self)
            image_label = QLabel(image.name, self)


            colormap_input = QLineEditWithColormap(parent = self, colormap_name= image.colormap.name)
            colormap_input.setText(image.colormap.name)

            # Order: Checkbox | Image Name | Colormap Input
            grid_layout.addWidget(checkbox, row, 0)
            grid_layout.addWidget(image_label, row, 1)
            grid_layout.addWidget(colormap_input, row, 2)

            self.checkboxes[image] = checkbox
            self.colormaps[image] = colormap_input


        rows = len(self.images)
        # Add OK/Cancel buttons below the image rows, spanning all 3 columns.
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        grid_layout.addWidget(button_box, rows + 1, 0, 1, 3)

    def on_accept(self):
        # Iterate through checkboxes to determine selected images.
        colormaps = [colormap.text() for image, colormap in self.colormaps.items() if self.checkboxes[image].isChecked()]
        image_layers = [image for image, cb in self.checkboxes.items() if cb.isChecked()]
        self.selected_images = [{"colormap": colormaps[i], "name": image_layers[i].name} for i in range(len(image_layers))]
        self.accept()  # Close dialog with accepted status.

    def get_selected_images(self):
        return self.selected_images

