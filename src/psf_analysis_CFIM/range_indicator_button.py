import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QWidget, QPushButton
from napari.utils.colormaps import Colormap

# TODO: Remove dependency on main widget being passed, instead get an event for image change
class ToggleRangeIndicator(QWidget):
    def __init__(self, main_widget,parent=None):
        super().__init__(parent)
        self._viewer = main_widget.viewer
        self.psf_analysis_widget = main_widget
        self.label_layer = None

    def init_ui(self):

        self.button = QPushButton("Toggle Range Indicator")
        self.button.clicked.connect(self.toggle_range_indicator)
        return self.button

    def toggle_range_indicator(self):
        layer = self.psf_analysis_widget.get_current_img_layer()

        if self.label_layer:
            try:
                self._viewer.layers.remove(self.label_layer)
            except ValueError:
                pass
            self.label_layer = None
        else:
            self.add_range_indicator_label(layer)

    def add_range_indicator_label(self, img_layer):
        image = img_layer.data
        labels = np.zeros_like(image, dtype=np.uint8)
        labels[image == 0] = 1
        labels[image == 65535] = 2

        # custom colormap for the label.
        label_colors = {
            None: (0, 0, 0, 0),  # Transparent
            0: (0, 0, 0, 0),  # Transparent
            1: (0, 0, 1, 1),  # Blue for minimum values
            2: (1, 0, 0, 1)  # Red for maximum values
        }

        # RaIn for Range Indicator :)
        # DEPRECATED: Hack used for the hidden tagged layer | to be removed in napari 0.6.0
        self.label_layer = self._viewer.add_labels(labels, name='RaIn_label <hidden>', colormap=label_colors, scale=img_layer.scale)
