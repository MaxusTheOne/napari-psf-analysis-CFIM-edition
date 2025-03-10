import re
from qtpy.QtGui import QValidator


class DualSeparatorValidator(QValidator):
    def __init__(self, bottom, top, decimals, parent=None):
        super(DualSeparatorValidator, self).__init__(parent)
        self.bottom = bottom
        self.top = top
        self.decimals = decimals

    def validate(self, input_str, pos):
        if input_str == "":
            return (QValidator.Intermediate, input_str, pos)

        # Replace comma with dot so both separators are allowed.
        text = input_str.replace(',', '.')

        # Build a regex pattern for a float number with the specified decimals.
        pattern = r'^\d+(\.\d{0,' + str(self.decimals) + r'})?$'
        if not re.match(pattern, text):
            return (QValidator.Invalid, input_str, pos)

        try:
            value = float(text)
        except ValueError:
            return (QValidator.Invalid, input_str, pos)

        if value < self.bottom or value > self.top:
            return (QValidator.Invalid, input_str, pos)

        return (QValidator.Acceptable, input_str, pos)

    def fixup(self, input_str):
        return input_str.replace(',', '.')
