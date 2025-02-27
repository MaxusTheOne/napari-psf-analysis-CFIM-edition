import numpy as np
from qtpy.QtCore import QObject, Signal
from napari.utils.events import EventEmitter
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox
from qtpy.QtGui import QPixmap


def upscale_to_3d(coordinate):
    # If a scalar is given, wrap it in a tuple.
    if isinstance(coordinate, (int, float)):
        coordinate = (coordinate,)
    else:
        coordinate = tuple(coordinate)

    if len(coordinate) == 1:
        # For a 1D coordinate, use (value, 0, 0)
        return coordinate[0], 0, 0
    elif len(coordinate) == 2:
        # For a 2D coordinate, use (0, first, second)
        return 0, coordinate[0], coordinate[1]
    elif len(coordinate) == 3:
        return coordinate
    else:
        raise ValueError("Coordinate must have at most 3 dimensions")


def report_error(message, point=()):
    error_emitter.errorOccurred.emit(message, point)

def report_warning(message, point=()):
    error_emitter.warningOccurred.emit(message, point)

class ErrorEmitter(QObject):
    errorOccurred = Signal(str, tuple)
    warningOccurred = Signal(str, tuple)


error_emitter = ErrorEmitter()


class ErrorDisplayWidget(QWidget):
    def __init__(self, parent=None, viewer=None, scale=(1, 1, 1)):
        super().__init__(parent)
        self.warnings = []
        self.errors = []
        self._viewer = viewer
        self._scale = scale
        self.error_points_layer = None
        self.warning_points_layer = None
        error_emitter.errorOccurred.connect(self._on_error_event)
        error_emitter.warningOccurred.connect(self._on_warning_event)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.summary_button = QPushButton(self)
        self.summary_button.clicked.connect(self._show_details)
        self.layout().addWidget(self.summary_button)

        self._update_summary()

    def _init_error_points_layer(self):
        layer_name = "Errors"
        if layer_name in self._viewer.layers:
            return self._viewer.layers[layer_name]
        else:
            return self._viewer.add_points(np.empty((0, 3)), name=layer_name, face_color='red', scale=self._scale,
                                           size=7)

    def _init_warning_points_layer(self):
        layer_name = "Filtered beads"
        if layer_name in self._viewer.layers:
            return self._viewer.layers[layer_name]
        else:
            return self._viewer.add_points(np.empty((0, 3)), name=layer_name, face_color='yellow', scale=self._scale,
                                           size=6)

    def _on_error_event(self, string: str, point: tuple):
        """Add an error message to the display."""

        if string != "":
            self.add_error(string)
        if point:
            self.add_error_point(point)

    def add_error_point(self, coordinate):
        """
        Add a new point to the error points layer.
        Expected coordinate is a 3D tuple (z, x, y).
        """

        # TODO: Grab the right scale
        if self.error_points_layer is None:
            self._scale = self._viewer.layers[0].scale
            self.error_points_layer = self._init_error_points_layer()
        coordinate = upscale_to_3d(coordinate)

        data = self.error_points_layer.data.tolist() if self.error_points_layer.data.size else []
        data.append(coordinate)
        self.error_points_layer.data = np.array(data)

    def _on_warning_event(self, string: str, point: tuple):
        """Add a warning message to the display."""

        if string != "":
            self.add_warning(string)
        if point:
            self.add_warning_point(point)

    def add_warning_point(self, coordinate):
        """
        Add a new point to the warning points layer.
        Expected coordinate is a 3D tuple (z, x, y).
        """

        if self.warning_points_layer is None:
            self._scale = self._viewer.layers[0].scale
            self.warning_points_layer = self._init_warning_points_layer()
        coordinate = upscale_to_3d(coordinate)

        data = self.warning_points_layer.data.tolist() if self.warning_points_layer.data.size else []
        data.append(coordinate)
        self.warning_points_layer.data = np.array(data)

    def _update_summary(self):
        """Update the button text with a summary of warnings and errors."""
        num_warnings = len(self.warnings)
        num_errors = len(self.errors)

        parts = []
        if num_warnings:
            parts.append(f"{num_warnings} warning{'s' if num_warnings > 1 else ''}")
        if num_errors:
            parts.append(f"{num_errors} error{'s' if num_errors > 1 else ''}")

        summary_text = " ".join(parts) if parts else "No issues"
        self.summary_button.setText(summary_text)

    def _show_details(self):
        """Show a dialog with detailed error and warning messages."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Issue Details")

        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        warning_icon = QPixmap("src/psf_analysis_CFIM/resources/warning_triangle.png")
        error_icon = QPixmap("src/psf_analysis_CFIM/resources/error_triangle.png")

        def add_message(icon, message):
            label = QWidget()
            h_layout = QHBoxLayout(label)
            icon_label = QLabel()

            # Scale the icon to match the height of the text
            scaled_icon = icon.scaledToHeight(30)
            icon_label.setPixmap(scaled_icon)

            text_label = QLabel(message)
            text_label.setAlignment(Qt.AlignLeft)

            h_layout.addWidget(icon_label)
            h_layout.addWidget(text_label)
            h_layout.setAlignment(Qt.AlignLeft)  # Align the layout to the left
            details_layout.addWidget(label)

        for warning in self.warnings:
            add_message(warning_icon, warning)

        for error in self.errors:
            add_message(error_icon, error)

        if not self.warnings and not self.errors:
            details_layout.addWidget(QLabel("No issues detected."))

        msg_box.layout().addWidget(details_widget)
        msg_box.exec_()

    def add_warning(self, message: str):
        """Add a warning message and update the summary."""
        self.warnings.append(message)
        self._update_summary()

    def add_error(self, message: str):
        """Add an error message and update the summary."""
        self.errors.append(message)
        self._update_summary()

    def clear(self):
        self.warnings = []
        self.errors = []
        self._update_summary()
