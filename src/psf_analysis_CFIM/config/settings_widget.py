import os
import pathlib
import subprocess
import sys

import yaml
from PyQt5.QtWidgets import QGroupBox, QWidget, QVBoxLayout, QPushButton
from appdirs import user_data_dir
from napari.settings import get_settings

psf_default_settings = {
    "version": "1.3",
    "microscopes": [
        "TIRF",
        "Zeiss Z1"
    ],
    "ui_settings": {
        "ri_mounting_medium": 1.4,
        "bead_size": 100,
        "box_size_xy": 2000,
        "box_size_z": 2500,
    },
    "image_analysis_settings": {
        "noise_settings": {
            "high_noise_threshold": 120,
            "low_snr_threshold": 10,
        },
        "intensity_settings": {
            "lower_warning_percent": 0.08,
            "lower_error_percent": 0.12,
            "upper_warning_percent": 0.01,
            "upper_error_percent": 0.08,
        },
    }
}

class SettingsWidget(QWidget):
    def __init__(self, path=None, parent=None):
        super().__init__(parent=parent)
        if path:
            self.settings_folder_path = os.path.expanduser(path)
        else:
            self._init_settings_file_path()

        self.settings_name = "psf_analysis_CFIM_settings.yaml"

        self.settings_file_path = os.path.join(self.settings_folder_path, self.settings_name)

        self.settings = self._load_settings()
        if not self.settings:
            self._make_settings_file()


    def init_ui(self):
        pane = QGroupBox(self)
        pane.setTitle("Settings")
        pane.setLayout(QVBoxLayout())

        open_settings_button = QPushButton("Open")
        open_settings_button.clicked.connect(self.open_settings)
        pane.layout().addWidget(open_settings_button)

        return pane

    def open_settings(self):
        file_path = self.settings_file_path
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.call(["open", file_path])
        else:  # assume Linux or similar
            subprocess.call(["xdg-open", file_path])

    def _init_settings_file_path(self):
        napari_settings_path = get_settings().config_path
        self.settings_folder_path = os.path.dirname(os.path.abspath(napari_settings_path))

    def _load_settings(self):
        if os.path.exists(self.settings_file_path):
            with open(self.settings_file_path, "r") as file:
                try:
                    settings = yaml.safe_load(file)
                    return settings
                except yaml.YAMLError as exception:
                    print(f"Error loading settings: {exception}")
                    return None
        else:
            print("Settings file not found.")
            return None

    def _make_settings_file(self):
        print(f"Making new settings file at {self.settings_file_path}")
        self.settings = psf_default_settings
        local_data_base_dir = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        self.local_data_dir = os.path.join(local_data_base_dir, "psf-analysis-cfim")
        print(f"Local data directory: {self.local_data_dir}")
        self.settings["output_folder"] = os.path.join(self.local_data_dir, 'output')
        print(f"Default output folder: {self.settings['output_folder']}")
        self._save_settings()

    def _save_settings(self):
        with open(self.settings_file_path, "w") as file:
            yaml.dump(self.settings, file)


if __name__ == "__main__":
    SettingsWidget()