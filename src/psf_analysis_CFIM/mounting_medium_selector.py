from qtpy.QtWidgets import QComboBox, QWidget
from psf_analysis_CFIM.library_workarounds.QDualSeperatorValidator import DualSeparatorValidator

medium_to_ri = {
    "Water": 1.33,
    "Glycerol": 1.45,
    "Vectashield Hardset": 1.46,
    "Vectashield Vibrance": 1.46,
    "Prolong Gold": 1.47,
    "Prolong Diamond": 1.47,
    "MightyMount": 1.518,
    "ProLong Glass": 1.52
}
# TODO: Add medium to config file, and make a refresh function for the combo box.
class MountingMediumSelector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.combo = QComboBox(self)
        self.combo.setEditable(True)

        # Adds items to the combo box using keys given in the dictionary.
        for key in medium_to_ri.keys():
            self.combo.addItem(key)

        self.combo.addItem("more")

        # Attach custom validator for accepting both comma and dot decimal separators.
        self.validator = DualSeparatorValidator(1.0, 1.6, 2, self)
        self.combo.lineEdit().setValidator(self.validator)

        # Preset options should remain un-editable.
        self.combo.lineEdit().setReadOnly(True)

        # Connect signal to handle switching between preset and custom input.
        self.combo.currentIndexChanged.connect(self.on_index_changed)

    def on_index_changed(self, index):
        text = self.combo.itemText(index)
        if text == "more":
            # Enable editing for custom input and clear the field.
            self.combo.lineEdit().setReadOnly(False)
            self.combo.setEditText("")
            self.combo.lineEdit().setFocus()
        else:
            # For preset options, disable editing.
            self.combo.lineEdit().setReadOnly(True)
            self.combo.setEditText(text)

    def value(self, value = None):
        """
            Returns the value of the combo box if no value is given.
            If a value is given, sets the value of the combo box.
        """
        text = self.combo.currentText().strip()
        try:
            # Attempt to parse the text as a number.
            value = float(text.replace(',', '.'))
            return value
        except ValueError:
            # Not a number: treat as preset and lookup its mapping.
            return medium_to_ri.get(text, text)

    def text(self):
        """
            Returns the value of the combo box as a string.
        """
        return str(self.value())

    def setValue(self, value):
        """
            Sets the value of the combo box.
        """
        self.combo.setEditText(str(value))
