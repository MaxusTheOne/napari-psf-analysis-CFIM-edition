import sys
from typing import overload, List, TypedDict, Optional
from uuid import UUID

import napari
import numpy as np
from IPython.terminal.shortcuts.auto_suggest import accept
from PyQt5.QtCore import QSettings, Qt, pyqtSlot
from PyQt5.QtGui import QPalette, QImage, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QComboBox, QPushButton, QApplication, QTabWidget, QLabel, QMessageBox, \
    QGroupBox, QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox, QFormLayout, QLineEdit, QGridLayout
from six import reraise

from psf_analysis_CFIM.library_workarounds.MultiKeyDict import MultiKeyDict
from psf_analysis_CFIM.library_workarounds.QLineEditWithColormapBg import QLineEditWithColormap

class ImageReference(TypedDict):
    name: Optional[str]
    unique_id: UUID
    index: Optional[int]
    wavelength: Optional[int]

class NapariImageLayer(napari.layers.Image):
    def __init__(self, name: str, *args, **kwargs):
        if not name:
            raise ValueError("A name is required for NapariImageLayer.")
        # Pass additional arguments to the base class __init__
        super().__init__(*args, **kwargs)
        self.name = name



# TODO: Potentially change this to manage access to image layers
class ImageInteractionManager(QWidget):
    def __init__(self, parent=None, viewer=None):
        super().__init__(parent)
        self.drop_down: QComboBox = None
        self.open_images_button = None

        self._viewer = viewer
        # Too scared of layers changing position in the viewer to use references instead of storing the layers
        self._selected_as_layers: dict[NapariImageLayer] # This is a bit deprecated now, replaced by .selected property
        self._multi_image_selection = ""

        self._pre_select = {}

        self.image_layers_reference = MultiKeyDict()
        self._viewer.layers.events.inserted.connect(self.update_image_references)
        self._viewer.layers.events.removed.connect(self.remove_image_references)


    def update_image_references(self):

        for index, layer in enumerate(self._viewer.layers):
            if isinstance(layer, napari.layers.Image):
                data = layer.metadata
                if data == {}:
                    continue
                elif not data.get("type") in ("image", None):
                    continue

                if self.image_layers_reference.has_id(layer.unique_id):
                    continue

                # Keys from the layer data we want to store # Why do layers not have a .get() method?
                data["colormap"] = layer.colormap.name

                if self._pre_select.get(layer.name, False):
                    data["selected"] = True
                    self._pre_select.clear()

                self.image_layers_reference[layer.name, layer.unique_id, int(layer.metadata["EmissionWavelength"])] = data


    def remove_image_references(self):
        dicts_to_delete = []
        for reference in self.image_layers_reference:
            uuid = self.image_layers_reference[reference]["unique_id"]
            for layer in self._viewer.layers:
                if layer.unique_id == uuid:
                    break
                dicts_to_delete.append(uuid)

        self.image_layers_reference.remove(dicts_to_delete)

    # image means a napari.layers.Image object
    @overload
    def get_image(self, index: int) -> NapariImageLayer:
        pass
    @overload
    def get_image(self, name: str) -> NapariImageLayer:
        pass
    def get_image(self, *args):
        if type(args[0]) is int:
            index = args[0]
            return self._viewer.layers[index]
        elif type(args[0]) is str:
            name = args[0]
            return self._viewer.layers[name]
        else:
            raise ValueError(f"Invalid argument type, must be str or int | Got {type(args[0])}")

    def get_image_index(self, name: str):
        return self._viewer.layers[name].index

    @overload
    def get_images(self) -> List[NapariImageLayer]:
        ...
    @overload
    def get_images(self, indexes: List[int]) -> List[NapariImageLayer]:
        ...

    @overload
    def get_images(self, names: List[str]) -> List[NapariImageLayer]:
        ...

    def get_images(self, *args) -> List[NapariImageLayer]:
        if not args:
            return self.get_selected_as_list()
        if not isinstance(args[0], list):
            raise ValueError(f"Invalid argument type, must be list | Got {type(args[0]) if args else 'None'}")
        items = args[0]
        if not items:
            return []
        if isinstance(items[0], str):
            return [self.get_image(name) for name in items]
        elif isinstance(items[0], int):
            return [self.get_image(index) for index in items]
        else:
            raise ValueError(f"List items must be int or str | Got {type(items[0])}")

    @overload
    def get_image_name(self, index: int) -> str:
        ...
    @overload
    def get_image_name(self) -> str:
        ...
    def get_image_name(self, *args) -> str:
        if not args:
            return self.get_images()[0].name
        if isinstance(args[0], int):
            index = args[0]
            return self.get_images()[index].name

    @overload
    def get_metadata(self, index: int) -> dict:
        ...
    @overload
    def get_metadata(self) -> List[dict]:
        ...
    def get_metadata(self, *args) -> dict | List[dict]:
        if not args:
            return [metadata for metadata in self.get_images()]
        if isinstance(args[0], int):
            index = args[0]
            return self.get_images()[index].metadata
        else:
            raise ValueError(f"Invalid argument type, must be int | Got {type(args[0])}")

    @overload
    def get_selected_image_name(self, index: int) -> str:
        ...
    @overload
    def get_selected_image_name(self) -> str:
        ...

    def get_selected_image_name(self, *args) -> str:
        if not self._selected_as_layers:
            return ""
        if not args:
            return self._selected_as_layers[0].name
        if isinstance(args[0], int):
            if self._selected_as_layers < args[0]:
                raise ValueError(f"Index out of range | {args[0]}")
            index = args[0]
            return self._selected_as_layers[index].name

    def get_color_by_wavelength(self, wavelength: int | str) -> str:
        if type(wavelength) is str:
            wavelength = int(wavelength)
        try:
            return self.image_layers_reference[wavelength]["colormap"]
        except KeyError:
            print(f"Invalid wavelength: {wavelength}")
            return ""

    # region dropdown methods
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

        selected_images_dict = {}
        dialog = ImageSelectionDialog(parent= self, images = self.image_layers_reference)
        if dialog.exec() == QDialog.Accepted:
            selected_images_dict = dialog.get_selected_images()

            self.update_layers(selected_images_dict)


    def get_selected(self):
        return self._selected_as_layers

    def get_selected_as_list(self):
        layers_selected = self.image_layers_reference.get_all("selected", True)
        return [self._viewer.layers[layer["name"]] for layer in layers_selected]

    def get_selected_as_dict(self):
        layers_selected = self.image_layers_reference.get_all("selected", True)
        return {layer["name"]: self._viewer.layers[layer["name"]] for layer in layers_selected}

    def get_selected_if_single(self):
        if len(self._selected_as_layers) == 1:
            return self._selected_as_layers[0]
        else:
            raise ValueError("More than one image selected | Temp fix for legacy code, intended to break on purpose :3 ")

    @overload
    def update_layers(self, layers: List[UUID | int | str:dict]) -> None:
        ...
    @overload
    def update_layers(self, layers: dict[UUID | int | str:dict]) -> None:
        ...

    def update_layers(self, layers): # Usually we expect a dict with UUID: dict.
        if isinstance(layers, list):
            layers = {layer.unique_id: layer for layer in layers}
        elif len(layers) == 1:
            print(f"1 layer selected: {layers}")


        self._clear_multi_image_selection()

        # Update the image reference with the new data
        for uuid in layers:
            self.image_layers_reference[uuid].update(layers[uuid])
        selected_layers = [uuid for uuid in layers if layers[uuid].get("selected", False)]
        selected_len = len(selected_layers)
        if selected_len == 1:
            text = self.image_layers_reference[selected_layers[0]]["name"]

            self.drop_down.setCurrentIndex(self.drop_down.findText(text))
        elif len(layers) > 1:
            self._set_multi_image_dropdown(selected_len)


        if len(layers) == 1:
            for layer in layers:
                text = self.image_layers_reference[layer]["name"]
                self.drop_down.setCurrentIndex(self.drop_down.findText(text))
                return



        if len(layers) == 0:
            print(f"Selected layers: {layers} | multi: {self._multi_image_selection}")

    def select_layer(self, uuid: UUID):
        if UUID == "":
            return
        layers_to_change = {uuid: {"selected": True}}
        for layer in self.image_layers_reference.to_dict(): # .to_dict() identifier is UUID, we can use that to simplify this
            if layer != uuid:
                layers_to_change[layer] = {"selected": False}
        self.update_layers(layers_to_change)



    def _on_index_changed(self):
        text = self.drop_down.currentText()

        if text == self._multi_image_selection:
            return
        if text != self._multi_image_selection:
            if text is None:
                return
            self._clear_multi_image_selection()
        layer_dict = self.image_layers_reference.get(text, None)
        if layer_dict is None:
            self._pre_select = {text: True}
            print(f"Pre-selecting {text}")
            return
        self.select_layer(self.image_layers_reference[text].get("unique_id", ""))
        self._selected_as_layers = [self._viewer.layers[text]]

    # region private methods
    def _check_layers_validity(self, layers):
        for layer in layers:
            exists = False
            for viewer_layers in self._viewer.layers:
                if layer == viewer_layers:
                    exists = True
                    break
            if not exists:
                return False
        return True

    def _change_dropdown_to_images(self, selected_images_dict: list):
        self._selected_as_layers = self._names_to_layers(selected_images_dict)

        self._set_multi_image_dropdown(len(selected_images_dict))

    def _set_multi_image_dropdown(self, images_amount:int):
        self._clear_multi_image_selection()

        x_images_text = f"{images_amount} images"
        self._multi_image_selection = x_images_text

        self.drop_down.addItem(x_images_text)
        self.drop_down.setCurrentIndex(self.drop_down.findText(x_images_text))


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
    def _set_dropdown_to_index(self, image_name: str):
        pass
    @overload
    def _set_dropdown_to_index(self, index: int):
        pass

    def _set_dropdown_to_index(self, *args): # This overload is a bit silly
        if type(args[0]) is str:
            image_name = args[0]
            index = self._index_from_name(image_name)
        elif type(args[0]) is int:
            index = args[0]
            image_name = self.drop_down.itemText(index)
        else:
            raise ValueError("Invalid argument type, must be str or int | Got {type(args[0])}")
        self.drop_down.setCurrentIndex(index)
        selected_layer = self._viewer.layers[image_name]
        self._selected_as_layers = [selected_layer]
        if not args:
            print(f"Index changed to {index} | {self._selected_as_layers}")


    def _index_from_name(self, image_name):
        index = self.drop_down.findText(image_name)
        return index




    # endregion
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
    def __init__(self, images: MultiKeyDict, parent=None):
        super().__init__(parent)
        self.image_layers = images.to_dict() # Expected to be out image reference dict.
        self.selected_images: dict = {}
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

        for row, uuid in enumerate(self.image_layers, start=1):
            layer = self.image_layers[uuid]
            checkbox = QCheckBox(self)
            checkbox.setChecked(layer.get("selected", False))

            image_label = QLabel(layer["name"], self)


            colormap_input = QLineEditWithColormap(parent = self, colormap_name= layer["colormap"])
            colormap_input.setText(layer["colormap"])

            # Order: Checkbox | Image Name | Colormap Input
            grid_layout.addWidget(checkbox, row, 0)
            grid_layout.addWidget(image_label, row, 1)
            grid_layout.addWidget(colormap_input, row, 2)

            self.checkboxes[uuid] = checkbox
            self.colormaps[uuid] = colormap_input


        rows = len(self.image_layers)
        # Add OK/Cancel buttons below the image rows, spanning all 3 columns.
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        grid_layout.addWidget(button_box, rows + 1, 0, 1, 3)

    def on_accept(self):
        # Iterate through checkboxes to determine selected images.
        colormaps = [colormap.text() for image, colormap in self.colormaps.items()]
        image_layers = [image for image, cb in self.checkboxes.items()]
        selected = [cb.isChecked() for cb in self.checkboxes.values()]


        for i in range(len(image_layers)):
            try:
                data = {"selected": selected[i], "colormap": colormaps[i]}
                self.selected_images[image_layers[i]] = data
            except (IndexError, TypeError) as e:
                print(f"Error: {e}")
                raise
        self.accept()  # Close dialog with accepted status.

    def get_selected_images(self):
        return self.selected_images

