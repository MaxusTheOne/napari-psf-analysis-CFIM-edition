from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox
from qtpy.QtGui import QPixmap


class ErrorDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.warnings = []
        self.errors = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.summary_button = QPushButton(self)
        self.summary_button.clicked.connect(self._show_details)
        self.layout().addWidget(self.summary_button)

        self._update_summary()




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