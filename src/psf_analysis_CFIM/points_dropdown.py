from PyQt5.QtWidgets import QComboBox


class PointsDropdown(QComboBox):
    def __init__(self, parent=None):
        super(PointsDropdown, self).__init__(parent)
        self.multi_selection = []
        self.multi_selection_index = -1
        self.setEditable(False)

        self.currentIndexChanged.connect(self._on_change)


    # region c to python translations
    def add_item(self, item):
        self.addItem(item)

    def insert_item(self,index, item):
        self.insertItem(index, item)

    def item_text(self, item):
        return self.itemText(item)

    def remove_item(self, item):
        self.removeItem(item)

    def current_text(self):
        return self.currentText()

    # endregion

    def get_selected(self):
        if self.multi_selection is not []:
            dropdown_names = []
            names = {}
            for index in range(self.count()):
                dropdown_names.append(self.itemText(index))
            for wavelength in self.multi_selection:
                for name in dropdown_names:
                    if wavelength in name:
                        names[wavelength] = name

            return names
        else:
            print("No layers selected")
            return {"0":self.currentText()}


    def set_multi_selection(self, index_list):
        self.multi_selection = index_list
        text = f"{len(self.multi_selection)} layers selected"
        self.add_item(text)
        self.setCurrentText(text)
        return self._check_multi_selection()

    def set_multi_selection_by_wavelength(self, wavelength_list):
        self.multi_selection = wavelength_list
        if len(wavelength_list) == 1:
            # Find the wavelength in the list
            for index in range(self.count()):
                if wavelength_list[0] in self.itemText(index):
                    self.setCurrentIndex(index)
                    return
        text = f"{len(self.multi_selection)} layers selected"
        self.add_item(text)
        self.setCurrentText(text)
        self.multi_selection_index = self.currentIndex()

    def _on_change(self):
        if self.currentText() != f"{len(self.multi_selection)} layers selected":
            self._clear_multi_selection()



    def _clear_multi_selection(self):
        self.multi_selection = []
        # remove the text that says how many layers are selected
        self.removeItem(self.multi_selection_index)

    def _check_multi_selection(self):
        for index in self.multi_selection:
            if not self.itemText(index):
                return False
        return True