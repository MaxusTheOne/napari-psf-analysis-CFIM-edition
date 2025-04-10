import os
import pathlib
import subprocess
import sys

import yaml
from pydantic import BaseModel, ValidationError
from qtpy.QtWidgets import QGroupBox, QWidget, QVBoxLayout, QPushButton

from napari.settings import get_settings

from psf_analysis_CFIM.config.settings_model import PSFAnalysisPluginSettings

class SettingsWidget(QWidget):
    def __init__(self, path=None, parent=None, debug=False):
        super().__init__(parent=parent)
        self.debug = debug
        if path:
            self.settings_folder_path = os.path.expanduser(path)
        else:
            self._init_settings_file_path()

        if debug: print(f"Debug | Settings folder path: {self.settings_folder_path}")

        self.settings_name = "psf_analysis_CFIM_settings.yaml"

        self.settings_file_path = os.path.join(self.settings_folder_path, self.settings_name)

        self.settings: BaseModel
        self._load_settings()
        if not self.settings:
            self._make_settings_file()

    def _init_settings_file_path(self):
        napari_settings_path = get_settings().config_path
        if self.debug: print(f"Debug | Napari settings path: {napari_settings_path}")
        self.settings_folder_path = os.path.dirname(os.path.abspath(napari_settings_path))


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

    def update_settings(self):
        """
            Gets the updated file and returns it
        """
        self._load_settings()
        return self.settings.model_dump()

    def get_settings(self):
        """
            Returns the settings dictionary.
        """

        return self.settings.model_dump()

    def _load_settings(self):
        if os.path.exists(self.settings_file_path):
            with open(self.settings_file_path, "r") as file:
                try:
                    raw_data = yaml.safe_load(file)

                    # Migrate non-destructively
                    updated_data, was_migrated = migrate_settings_if_needed(raw_data)

                    # Validate final result
                    self.settings = PSFAnalysisPluginSettings(**updated_data)

                    # Save only if new fields were added or version was bumped
                    if was_migrated:
                        print("[*] Saving migrated settings (non-destructive)...")
                        self._save_settings()

                    return self.settings

                except (yaml.YAMLError, ValidationError) as e:
                    print(f"[!] Failed to load or validate settings: {e}")

        else:
            print("[!] Settings file not found.")

        print("[*] Falling back to default settings.")
        self._make_settings_file()
        return self.settings



    def _make_settings_file(self):
        print(f"Making new settings file at {self.settings_file_path}")

        # Build the default output folder path using platform conventions
        local_data_base_dir = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        self.local_data_dir = os.path.join(local_data_base_dir, "psf-analysis-cfim")
        output_folder = os.path.join(self.local_data_dir, "output")

        print(f"Local data directory: {self.local_data_dir}")
        print(f"Default output folder: {output_folder}")

        # Create the default settings with a dynamic output path
        self.settings = PSFAnalysisPluginSettings().model_copy(update={"output_folder": output_folder})

        self._save_settings()

    def _save_settings(self):
        with open(self.settings_file_path, "w") as file:
            yaml.dump(self.settings.model_dump(), file, sort_keys=False)


def deep_merge(defaults: dict, user_data: dict) -> dict:
    """
    Recursively merge user_data into defaults without overwriting existing keys.
    """
    result = defaults.copy()
    for key, value in user_data.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def migrate_settings_if_needed(data: dict) -> tuple[dict, bool]:
    version = data.get("version", "0.0")
    newest_version = PSFAnalysisPluginSettings.__version__
    if version == newest_version:
        return data, False

    print(f"[*] Detected settings version {version}, upgrading to {newest_version}")

    defaults = PSFAnalysisPluginSettings().dict()
    merged = deep_merge(defaults, data)
    merged["version"] = newest_version

    return merged, True



if __name__ == "__main__":
    print("Local | Running settings widget")
    widget = SettingsWidget()
    settings = widget.get_settings()