import math
import os
import pathlib
import re
from datetime import datetime
from importlib.metadata import version
from os.path import basename, dirname, exists, getctime, join
from typing import overload, Tuple

import napari.layers
import numpy as np
import yaml
from PyQt5.QtCore import Qt
from qtpy.QtWidgets import QLayout
from napari import viewer
from napari.qt.threading import FunctionWorker, thread_worker, GeneratorWorker
from napari.settings import get_settings
from napari.utils.notifications import show_info, show_warning
from qtpy.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from skimage.io import imsave
from urllib3.connectionpool import xrange

from psf_analysis_CFIM.bead_finder_CFIM import BeadFinder
from psf_analysis_CFIM.config.settings_widget import SettingsWidget
from psf_analysis_CFIM.debug import global_vars
from psf_analysis_CFIM.debug.debug import report_error_debug
from psf_analysis_CFIM.error_widget.error_display_widget import ErrorDisplayWidget, report_error, report_warning
from psf_analysis_CFIM.image_selector_dropdown import ImageInteractionManager
from psf_analysis_CFIM.library_workarounds.RangeDict import RangeDict
from psf_analysis_CFIM.mounting_medium_selector import MountingMediumSelector
from psf_analysis_CFIM.points_dropdown import PointsDropdown
from psf_analysis_CFIM.psf_analysis.analyzer import Analyzer
from psf_analysis_CFIM.psf_analysis.image_analysis import analyze_image, filter_psf_beads_by_box
from psf_analysis_CFIM.psf_analysis.parameters import PSFAnalysisInputs
from psf_analysis_CFIM.psf_analysis.psf import PSF, PSFRenderEngine
from psf_analysis_CFIM.range_indicator_button import ToggleRangeIndicator
from psf_analysis_CFIM.report_widget.report_widget import ReportWidget


def get_microscopes(psf_settings_path):
    if psf_settings_path and exists(psf_settings_path):
        settings = load_settings(psf_settings_path)

        if settings and "microscopes" in settings.keys():
            return [s for s in settings["microscopes"]]

    return "Microscope"


def get_dpi(psf_settings_path):
    if psf_settings_path and exists(psf_settings_path):
        settings = load_settings(psf_settings_path)

        if settings and "dpi" in settings.keys():
            return settings["dpi"]

    return "150"


def get_output_path(psf_settings_path):
    if psf_settings_path and exists(psf_settings_path):
        settings = load_settings(psf_settings_path)

        if settings and "output_path" in settings.keys():
            return pathlib.Path(settings["output_path"])

    return pathlib.Path.home()


def load_settings(psf_settings_path):
    print(f"Path: {psf_settings_path}")
    with open(psf_settings_path) as stream:
        settings = yaml.safe_load(stream)
    return settings


def get_psf_analysis_settings_path():
    config_pointer = join(
        dirname(get_settings()._config_path), "psf_analysis_config_pointer.yaml"
    )
    if exists(config_pointer):
        settings = load_settings(config_pointer)
        if settings and "psf_analysis_config_file" in settings.keys():
            return settings["psf_analysis_config_file"]

    return None


class PsfAnalysis(QWidget):
    def __init__(self, napari_viewer, parent=None):
        super().__init__(parent=parent)
        self.viewer: viewer = napari_viewer

        # Event listeners
        napari_viewer.layers.events.inserted.connect(self._layer_inserted)
        napari_viewer.layers.events.removed.connect(self._layer_removed)
        napari_viewer.layers.selection.events.changed.connect(self._on_selection)

        # Variables
        self._debug = False
        self._debug_progress = False
        self._debug_dict = {}
        self.summary_figs: dict = {}
        self.results = []
        self.warnings = []
        self.errors = []

        self.settings = {}

        # UI
        self.settings_Widget = SettingsWidget(parent=self)

        self.bead_finder = None

        self.cancel_extraction = False
        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)
        self._add_logo()

        setting_tabs = QTabWidget(parent=self)

        self._add_basic_settings_tab(setting_tabs)
        self._add_advanced_settings_tab(setting_tabs)

        self.layout().addWidget(setting_tabs)
        self._add_analyse_buttons()

        self._add_interaction_buttons()

        self.report_widget = ReportWidget(parent=self)
        self._add_save_dialog()

        self.layout().addWidget(self.settings_Widget.init_ui())

        self.current_img_index = -1
        self.cbox_img.currentIndexChanged.connect(self._img_selection_changed)
        self.fill_layer_boxes()

        # setup after UI
        self.update_settings()
        self.use_config()
        if os.getenv("PSF_ANALYSIS_CFIM_DEBUG") == "1":
            print(f"Main widget | Debug")
            self._debug = True
            self._debug_dict["bead_collection"] = False
            debug = global_vars.debug_instance
            debug.set_PSFAnalysis_instance(self)

    def update_settings(self):
        self.settings = self.settings_Widget.update_settings()
        if self.settings.get("debug"):
            print(f"Debug | Settings: {self.settings}")

    def use_config(self):
        settings = self.settings
        ui_settings = settings["ui_settings"]
        settings_keys_to_widget_attributes = {
            "output_folder": "save_dir_line_edit",
        }
        ui_settings_keys_to_widget_attributes = {
            "bead_size": "bead_size",
            "box_size_xy": "psf_yx_box_size",
            "box_size_z": "psf_z_box_size",
            "ri_mounting_medium": "mounting_medium",
        }
        try:
            if settings:
                for key, value in settings.items():
                    if key in settings_keys_to_widget_attributes.keys():
                        getattr(self, settings_keys_to_widget_attributes[key]).setText(value)
            if ui_settings:
                for key, value in ui_settings.items():
                    if key in ui_settings_keys_to_widget_attributes.keys():
                        getattr(self, ui_settings_keys_to_widget_attributes[key]).setValue(value)
        except AttributeError as e:
            print(f"Error in use_config: {e}")

    def _add_logo(self):
        logo = pathlib.Path(__file__).parent / "resources" / "logo_smol_q.png"
        link = "https://github.com/MaxusTheOne/napari-psf-analysis-CFIM-edition?tab=readme-ov-file#readme" # TODO: Retrieve this from setup.cfg
        logo_label = QLabel()
        logo_label.setText(f'<a href="{link}"><img src="{logo}" width="320"></a>')
        logo_label.setOpenExternalLinks(True)

        self.layout().addWidget(logo_label)

    def _add_analyse_buttons(self):
        pane = QGroupBox(parent=self)
        pane.setLayout(QFormLayout())

        self.find_beads_button = QPushButton("Find Beads")
        self.find_beads_button.setEnabled(True)
        self.find_beads_button.clicked.connect(self._find_beads)
        pane.layout().addRow(self.find_beads_button)

        self.analyse_img_button = QPushButton("Re-Analyse Image")
        self.analyse_img_button.setEnabled(True)
        self.analyse_img_button.clicked.connect(self._validate_image)
        pane.layout().addRow(self.analyse_img_button)

        self.error_widget = ErrorDisplayWidget(parent=self, viewer=self.viewer)
        pane.layout().addRow(self.error_widget)

        self.toggle_range_indicator = ToggleRangeIndicator(self, parent=pane)
        pane.layout().addWidget(self.toggle_range_indicator.init_ui())

        self.layout().addWidget(pane)

    def _test_error(self):
        report_error("Test Error", (20, 20, 20))

    def _find_beads(self):

        # Estimates points for the user.
        self._create_bead_finder() # TODO: Put settings in here
        points_dict_list = self.bead_finder.find_beads()

        # Displays the points in the viewer with a name like "xxλ | Estimated Beads"
        self._estimated_beads_to_viewer(points_dict_list)

        # Sets the point dropdown to the estimated beads
        self.point_dropdown.set_multi_selection_by_wavelength([channel["wavelength"] for channel in points_dict_list])

        for channel in points_dict_list:
            report_warning("", points=channel["discarded"])

    def _estimated_beads_to_viewer(self, estimated_beads: list[dict]):
        scale = self.bead_finder.get_scale()
        base_name = "Estimated Beads"
        points = [beads_dict["points"] for beads_dict in estimated_beads]
        wavelengths = [beads_dict["wavelength"] for beads_dict in estimated_beads]
        bead_colors = [self.image_manager.get_color_by_wavelength(wavelength) for wavelength in wavelengths]

        layer_amount = len(estimated_beads)
        estimated_beads_layers = [layer for layer in self.viewer.layers if base_name in layer.name]
        for layer in estimated_beads_layers:
            self.viewer.layers.remove(layer)

        keys = {"points": points, "wavelength": wavelengths, "bead_colors": bead_colors}
        for key_name, key_value in keys.items():
            if len(key_value) != layer_amount:
                raise ValueError(f"Missing key: {key_name} had len: {len(key_value)} | expected: {layer_amount}")

        for i in range(layer_amount):
            self.viewer.add_points(points[i], scale=scale, face_color=bead_colors[i], border_color="cyan",
                                   name=f"{wavelengths[i]}λ | {base_name}", size=4, opacity=0.7)

    def _img_to_viewer(self, image, scale=None, name="BeadTest"):
        self.viewer.add_image(image, name=name, scale=scale)

    def _point_list_to_viewer(self, points, scale=None, name="Points", size=10):
        self.viewer.add_points(points, size=size, scale=scale, name=name, face_color="cyan")

    def _add_save_dialog(self):
        self.report_widget.set_title("PSF Analysis Report")  # TODO: Put this in settings

        pane = self.report_widget.init_ui()
        self.save_dir_line_edit = self.report_widget.save_dir_line_edit  # Exposing this for use in use_config
        self.save_path = self.report_widget.save_path

        self.layout().addWidget(pane)

    def _add_interaction_buttons(self):
        pane = QGroupBox(parent=self)
        pane.setLayout(QFormLayout())

        self.extract_psfs = QPushButton("Extract PSFs")
        self.extract_psfs.clicked.connect(self.prepare_measure)
        pane.layout().addRow(self.extract_psfs)

        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.request_cancel)
        pane.layout().addRow(self.cancel)

        self._channel_progress = {}
        self.progressbar = QProgressBar(parent=self)
        self.progressbar.setValue(0)
        pane.layout().addRow(self.progressbar)

        self.delete_measurement = QPushButton("Delete Displayed Measurement")
        self.delete_measurement.setEnabled(False)
        self.delete_measurement.clicked.connect(self.delete_measurement_action)
        pane.layout().addRow(self.delete_measurement)

        self.layout().addWidget(pane)

    def _add_advanced_settings_tab(self, setting_tabs):
        advanced_settings = QWidget(parent=setting_tabs)
        setting_tabs.addTab(advanced_settings, "Advanced")
        advanced_settings.setLayout(QFormLayout(setting_tabs))
        self.temperature = QDoubleSpinBox(parent=advanced_settings)
        self.temperature.setToolTip("Temperature at which this PSF was " "acquired.")
        self.temperature.setMinimum(-100)
        self.temperature.setMaximum(200)
        self.temperature.setSingleStep(0.1)
        self.temperature.clear()
        advanced_settings.layout().addRow(
            QLabel("Temperature", advanced_settings), self.temperature
        )
        self.airy_unit = QDoubleSpinBox(parent=advanced_settings)
        self.airy_unit.setToolTip(
            "The airy unit relates to your pinhole " "size on confocal systems."
        )
        self.airy_unit.setMinimum(0)
        self.airy_unit.setMaximum(1000)
        self.airy_unit.setSingleStep(0.1)
        self.airy_unit.clear()
        advanced_settings.layout().addRow(
            QLabel("Airy Unit", advanced_settings), self.airy_unit
        )
        self.bead_size = QDoubleSpinBox(parent=advanced_settings)
        self.bead_size.setToolTip("Physical bead size in nano meters.")
        self.bead_size.setMinimum(0)
        self.bead_size.setMaximum(1000)
        self.bead_size.setSingleStep(1)
        self.bead_size.setValue(100)
        advanced_settings.layout().addRow(
            QLabel("Bead Size [nm]", advanced_settings), self.bead_size
        )
        self.bead_supplier = QLineEdit()
        self.bead_supplier.setToolTip("Manufacturer of the beads.")
        advanced_settings.layout().addRow(
            QLabel("Bead Supplier", advanced_settings), self.bead_supplier
        )
        # self.mounting_medium = QDoubleSpinBox(parent=advanced_settings)
        # self.mounting_medium.setToolTip("RI index of the mounting medium.")
        # self.mounting_medium.setMinimum(0)
        # self.mounting_medium.setMaximum(2)
        # self.mounting_medium.setValue(1.4)
        self.mounting_medium = MountingMediumSelector(parent=advanced_settings)
        advanced_settings.layout().addRow(
            QLabel("RI Mounting Medium", advanced_settings), self.mounting_medium.combo
        )
        self.operator = QLineEdit()
        self.operator.setToolTip("Person in charge of the PSF acquisition.")
        advanced_settings.layout().addRow(
            QLabel("Operator", advanced_settings), self.operator
        )
        self.microscope_type = QLineEdit()
        self.microscope_type.setToolTip(
            "Type of microscope used for the PSF acquisition."
        )
        advanced_settings.layout().addRow(
            QLabel("Microscope Type", advanced_settings), self.microscope_type
        )
        self.excitation = QDoubleSpinBox(parent=advanced_settings)
        self.excitation.setToolTip("Excitation wavelength used to image the " "beads.")
        self.excitation.setMinimum(0)
        self.excitation.setMaximum(1000)
        self.excitation.setSingleStep(1)
        self.excitation.clear()
        advanced_settings.layout().addRow(
            QLabel("Excitation", advanced_settings), self.excitation
        )
        self.emission = QDoubleSpinBox(parent=advanced_settings)
        self.emission.setToolTip("Emission wavelength of the beads.")
        self.emission.setMinimum(0)
        self.emission.setMaximum(1000)
        self.emission.setSingleStep(1)
        self.emission.clear()
        advanced_settings.layout().addRow(
            QLabel("Emission", advanced_settings), self.emission
        )
        self.comment = QLineEdit()
        self.comment.setToolTip("Additional comment for this specific " "measurement.")
        advanced_settings.layout().addRow(
            QLabel("Comment", advanced_settings), self.comment
        )
        self.summary_figure_dpi = QComboBox(parent=advanced_settings)
        self.summary_figure_dpi.setToolTip("DPI/PPI of summary figure.")
        self.summary_figure_dpi.addItems(["96", "150", "300"])
        self.summary_figure_dpi.setCurrentText(
            get_dpi(get_psf_analysis_settings_path())
        )
        advanced_settings.layout().addRow(
            QLabel("DPI/PPI", advanced_settings), self.summary_figure_dpi
        )

    def _add_basic_settings_tab(self, setting_tabs):
        basic_settings = QWidget(parent=setting_tabs)
        setting_tabs.addTab(basic_settings, "Basic")

        layout = QFormLayout(basic_settings)
        basic_settings.setLayout(layout)

        self.image_manager = ImageInteractionManager(parent=basic_settings, viewer=self.viewer)
        layout.addRow(QLabel("Channels", basic_settings), self.image_manager.init_ui())
        self.cbox_img = self.image_manager.drop_down  # Exposing this as a "legacy" fix

        self.point_dropdown = PointsDropdown(parent=basic_settings)
        self.point_dropdown.setToolTip(
            "Points layer indicating which PSFs should " "be measured."
        )
        layout.addRow(
            QLabel("Points", basic_settings), self.point_dropdown
        )
        self.date = QDateEdit(datetime.today())
        self.date.setToolTip("Acquisition date of the PSFs.")
        layout.addRow(
            QLabel("Acquisition Date", basic_settings), self.date
        )
        self.microscope = QLineEdit("Undefined")
        self.microscope.setToolTip(
            "Name of the microscope which was used to" " acquire the PSFs."
        )
        layout.addRow(
            QLabel("Microscope", basic_settings), self.microscope
        )
        self.magnification = QSpinBox(parent=basic_settings)
        self.magnification.setToolTip("Total magnification of the system.")
        self.magnification.setMinimum(0)
        self.magnification.setMaximum(10000)
        self.magnification.setValue(100)
        self.magnification.setSingleStep(10)
        layout.addRow(
            QLabel("Magnification", basic_settings), self.magnification
        )
        self.objective_id = QLineEdit("obj_1")
        self.objective_id.setToolTip("Objective identifier (or name).")
        layout.addRow(
            QLabel("Objective ID", basic_settings), self.objective_id
        )
        self.na = QDoubleSpinBox(parent=basic_settings)
        self.na.setToolTip("Numerical aperture of the objective.")
        self.na.setMinimum(0.0)
        self.na.setMaximum(1.7)
        self.na.setSingleStep(0.05)
        self.na.setValue(1.4)
        layout.addRow(QLabel("NA", basic_settings), self.na)
        self.xy_pixelsize = QDoubleSpinBox(parent=basic_settings)
        self.xy_pixelsize.setToolTip("Pixel size in XY dimensions in nano " "meters.")
        self.xy_pixelsize.setMinimum(0.0)
        self.xy_pixelsize.setMaximum(10000.0)
        self.xy_pixelsize.setSingleStep(10.0)
        self.xy_pixelsize.setValue(65.0)
        layout.addRow(
            QLabel("XY-Pixelsize [nm]", basic_settings), self.xy_pixelsize
        )
        self.z_spacing = QDoubleSpinBox(parent=basic_settings)
        self.z_spacing.setToolTip(
            "Distance between two neighboring planes " "in nano meters."
        )
        self.z_spacing.setMinimum(0.0)
        self.z_spacing.setMaximum(10000.0)
        self.z_spacing.setSingleStep(10.0)
        self.z_spacing.setValue(200.0)
        layout.addRow(
            QLabel("Z-Spacing [nm]", basic_settings), self.z_spacing
        )
        self.psf_yx_box_size = QDoubleSpinBox(parent=basic_settings)
        self.psf_yx_box_size.setToolTip(
            "For analysis each PSF is cropped "
            "out of the input image. This is the XY size of the crop in nano meters."
        )
        self.psf_yx_box_size.setMinimum(1.0)
        self.psf_yx_box_size.setMaximum(100000.0)
        self.psf_yx_box_size.setSingleStep(500.0)
        self.psf_yx_box_size.setValue(2000.0)
        layout.addRow(
            QLabel("PSF YX Box Size [nm]", basic_settings), self.psf_yx_box_size
        )
        self.psf_z_box_size = QDoubleSpinBox(parent=basic_settings)
        self.psf_z_box_size.setToolTip(
            "This is the Z size of the PSF crop " "in nano meters. "
        )
        self.psf_z_box_size.setMinimum(1.0)
        self.psf_z_box_size.setMaximum(1000000.0)
        self.psf_z_box_size.setSingleStep(500.0)
        self.psf_z_box_size.setValue(2500.0)
        layout.addRow(
            QLabel("PSF Z Box Size [nm]", basic_settings), self.psf_z_box_size
        )

    # Rework to interact with settings | And do something I guess
    def select_save_dir(self):
        self.save_path.exec_()
        self.save_path.setToolTip(
            "Select the directory in which the "
            "extracted values and summary images are "
            "stored."
        )
        self.save_dir_line_edit.setText(self.save_path.directory().path())
        self.save_dir_line_edit.setToolTip(
            "Select the directory in which the "
            "extracted values and summary images are "
            "stored."
        )

    def fill_layer_boxes(self):
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Image):
                self.cbox_img.addItem(str(layer))
                self._img_selection_changed()
            elif isinstance(layer, napari.layers.Points):
                self.point_dropdown.addItem(str(layer))

    def _img_selection_changed(self):
        if self.current_img_index != self.cbox_img.currentIndex():
            self.current_img_index = self.cbox_img.currentIndex()
            for layer in self.viewer.layers:
                if str(layer) == self.cbox_img.itemText(self.cbox_img.currentIndex()):
                    self.date.setDate(
                        datetime.fromtimestamp(getctime(layer.source.path))
                    )
                    # NOTE: maybe put these in their own function
                    self.fill_settings_boxes(layer)

                    self.error_widget.set_img_index(self.current_img_index)
        self._validate_image()

    def fill_settings_boxes(self, layer):
        metadata = layer.metadata
        required_keys = [
            "CameraName", "ObjectiveName", "NominalMagnification", "LensNA",
            "PinholeSizeAiry", "ExcitationWavelength", "EmissionWavelength"
        ]
        missing_keys = []
        for key in required_keys:
            if key not in metadata.keys():
                missing_keys.append(key)
        if missing_keys:
            show_warning(
                f"Missing metadata: {missing_keys} | Plugin only made for .CZI (for now) | Plugin might behave unexpectedly")

        try:
            self.microscope.setText(metadata["CameraName"])
            self.objective_id.setText(metadata["ObjectiveName"])
            self.magnification.setValue(int(metadata["NominalMagnification"]))
            self.na.setValue(float(metadata["LensNA"]))
            self.airy_unit.setValue(round(float(metadata["PinholeSizeAiry"]), 2))
            self.excitation.setValue(round(float(metadata["ExcitationWavelength"]), 2))
            self.emission.setValue(round(float(metadata["EmissionWavelength"]), 2))
            self.xy_pixelsize.setValue(round(float(layer.scale[1]), 2))
            self.z_spacing.setValue(round(float(layer.scale[0]), 2))
        except KeyError as e:
            print(f"Missing metadata for settings: {e} and possible more")

    def _create_bead_finder(self):

        image_layers = self.image_manager.get_selected_as_list()
        print(f"Image layers len: {len(image_layers)}")

        self.bead_finder = BeadFinder(image_layers, self.get_scale(),bead_finder_settings=self.settings["bead_finder_settings"], bounding_box=(
            self.psf_z_box_size.value(), self.psf_yx_box_size.value(), self.psf_yx_box_size.value()))

    def _layer_inserted(self, event):
        if isinstance(event.value, napari.layers.Image):
            self.cbox_img.insertItem(self.cbox_img.count() + 1, str(event.value))
        elif isinstance(event.value, napari.layers.Points):
            self.point_dropdown.insertItem(self.point_dropdown.count() + 1, str(event.value))

    def _layer_removed(self, event):
        if isinstance(event.value, napari.layers.Image):
            items = [self.cbox_img.itemText(i) for i in range(self.cbox_img.count())]
            self.cbox_img.removeItem(items.index(str(event.value)))
            self.changed_manually = False
            self.current_img_index = -1
            self._img_selection_changed()
        elif isinstance(event.value, napari.layers.Points):
            items = [
                self.point_dropdown.itemText(i) for i in range(self.point_dropdown.count())
            ]
            self.point_dropdown.removeItem(items.index(str(event.value)))

    def _on_selection(self, event):
        if self.viewer.layers.selection.active is not None:
            self.delete_measurement.setEnabled(
                "PSF Summary" in self.viewer.layers.selection.active.name
            )

    def request_cancel(self):
        self.cancel_extraction = True
        self.cancel.setText("Cancelling...")

    def prepare_measure(self):  # Time to refactor this; Support for color channels; and use imageManager
        # Note: Why is it called measurement_stack? It's a stack of summary images.
        channel_zyx_fwhm = {}
        channel_beads = {}

        def _on_done(result):  # TODO: Refactor this out of scope
            if result is not None:

                # unpacks the result from analyzer. Should contain a stack of summary images and the scale.
                measurement_stack, measurement_scale, current_analyzer = result

                # filtered_figs = filter_psf_beads_by_box(self.results, measurement_stack, (self.psf_z_box_size.value(), self.psf_yx_box_size.value(), self.psf_yx_box_size.value()))
                # print(f"Theoretical filtered list len: {len(filtered_figs)}")

                # Creates an image of the average bead, runs the PSF analysis on it and creates summary image.
                averaged_bead = current_analyzer.get_averaged_bead()
                averaged_psf = PSF(image=averaged_bead, psf_settings=self.settings["analyzer_settings"]["psf_settings"])

                averaged_psf.analyze()

                self.report_widget.add_bead_stats_psf(averaged_psf.get_record(), title="Average from image")

                channel_wavelength = current_analyzer.get_wavelength()
                averaged_summary_image = averaged_psf.get_summary_image(
                    date=analyzer.get_date(),
                    version=analyzer.get_version(),
                    dpi=analyzer.get_dpi(),
                    top_left_message=f"Average PSF of {len(measurement_stack)} beads",
                    ellipsoid_color=current_analyzer.get_wavelength_color(),
                )

                figure_title = f"PSF Summary | {channel_wavelength}λ | {current_analyzer.get_wavelength_color()}"

                # Combines the summary image from average bead with the summary image stack from the entire psf analysis.
                averaged_summary_image_expanded = np.expand_dims(averaged_summary_image, axis=0)
                combined_stack = np.concatenate((averaged_summary_image_expanded, measurement_stack), axis=0)
                self.display_measurement_stack(combined_stack, measurement_scale, name=figure_title, metadata={"wavelength": channel_wavelength})

                self.summary_figs[channel_wavelength] = combined_stack

                """
                    If we have all color channels done, we create a combined summary image.
                    
                    We need to store the zyx fwhm for each average bead.
                """
                channel_zyx_fwhm[channel_wavelength] = {"zyx": averaged_psf.get_fwhm(),
                                                        "color": current_analyzer.get_wavelength_color()}
                channel_beads[channel_wavelength] = current_analyzer.get_centroids()

                # We check if analysis is done and if we have > 1 channel
                if self.progressbar.value() == self.progressbar.maximum():  # TODO: This could take advantage of the async
                    if len(channel_zyx_fwhm.keys()) > 1:
                        self.display_final_summary(channel_beads, channel_zyx_fwhm, scale = measurement_scale)
                    _reset_state()







        def _update_progress(return_val):  # TODO: Make this more efficient
            if self.cancel_extraction:
                worker.quit()
            progress = return_val[0]
            color = return_val[1]
            if not isinstance(progress, int) or not isinstance(color, str):
                raise ValueError(f"Expected int, str | Got: {type(progress)}, {type(color)}")

            self._channel_progress[color] = progress
            total_progress = 0
            for key in self._channel_progress.keys():
                total_progress += self._channel_progress[key]
            self.progressbar.setValue(total_progress)
            if self._debug_progress:
                print(f"Progress: {self.progressbar.value()} / {self.progressbar.maximum()}")

        def _reset_state(error = None):
            if error:
                print(f"Error from worker: {error}")
            if self.cancel_extraction:
                self.progressbar.setValue(0)
            self._channel_progress = {}
            self.cancel_extraction = False
            self.cancel.setEnabled(False)
            self.cancel.setText("Cancel")
            self.extract_psfs.setEnabled(True)
            self.progressbar.reset()

        self.update_settings()

        selected_image_layers = self.image_manager.get_selected_as_dict()
        point_data = self._get_points_as_dict()

        bead_amount = 0
        matched = {}
        for wavelength, point_layer_ref in point_data.items():
            for image_layer_name, image_layer in selected_image_layers.items():
                if int(image_layer.metadata["EmissionWavelength"]) == int(wavelength):
                    points = self.viewer.layers[point_layer_ref]
                    matched[wavelength] = (points, image_layer)
                    bead_amount += len(points.data)
                    break

        if len(matched) == 0:
            show_warning("No matching image and point layer found.")
            return
        if len(matched) != len(selected_image_layers):
            show_warning("Not all images have a matching point layer.")
            return

        self.results = []
        self._setup_progressbar(bead_amount)

        for points_layer, image_layer in matched.values():
            channel_image = image_layer.data
            channel_points = points_layer.data

            analyzer_settings = {  # TODO: Color needs to be gotten from the image manager
                "wavelength": int(image_layer.metadata["EmissionWavelength"]),
                "excitation": int(image_layer.metadata["ExcitationWavelength"]),
                "wavelength_color": self.color_from_emission_wavelength(
                    int(image_layer.metadata["EmissionWavelength"])),
                "airy_unit": self.airy_unit.value(),
            }

            analyzer = Analyzer(parameters=PSFAnalysisInputs(
                microscope=self._get_microscope(),
                magnification=self.magnification.value(),
                na=self.na.value(),
                spacing=self._get_spacing(),
                patch_size=self._get_patch_size(),
                name=image_layer.name,
                img_data=channel_image,
                point_data=channel_points,
                dpi=int(self.summary_figure_dpi.currentText()),
                date=datetime(*self.date.date().getDate()).strftime("%Y-%m-%d"),
                version=version("psf_analysis_CFIM")
            ),
                info_dict=analyzer_settings,
                analyzer_settings=self.settings["analyzer_settings"],
            )

            @thread_worker(progress={"total": bead_amount})
            def measure(current_image_layer=image_layer, current_analyzer=analyzer):

                yield from current_analyzer

                self.results.append(current_analyzer.get_results())
                measurement_stack, measurement_scale = current_analyzer.get_summary_figure_stack(
                    bead_img_scale=self.get_scale(),
                    bead_img_shape=current_image_layer.data.shape,
                )
                if measurement_stack is not None:
                    return measurement_stack, measurement_scale, current_analyzer

            worker: GeneratorWorker = measure()

            worker.yielded.connect(_update_progress)
            worker.returned.connect(_on_done)
            worker.aborted.connect(_reset_state)
            worker.errored.connect(_reset_state)
            worker.start()

            self.extract_psfs.setEnabled(False)
            self.cancel.setEnabled(True)

    def display_final_summary(self, channel_beads, channel_zyx_fwhm, scale=None):

        _local_debug = False

        psf_bead_collections = self.filter_bead_matches(channel_beads)

        if _local_debug:
            print(f"Debug | Putting found bead groups in viewer")
            for index, collection in enumerate(psf_bead_collections):
                point_group = []
                for key in collection.keys():
                    point_group.append(collection[key])
                color = ["red", "green", "blue", "cyan", "magenta", "yellow"][index % 6]
                _text = f"Group {index} | {color} | {len(point_group)} points"
                self._add_points_to_viewer_nm(point_group, _text, color)

        # Try to calculate a relative coordinate
        channel_rel_coords = {wavelength_key: [] for wavelength_key in channel_beads.keys()}
        wavelengths = [number for number in channel_beads.keys()]

        for bead_group in psf_bead_collections:  # This line gets 1 "group", containing 1 bead per channel
            max_zyx = [0, 0, 0]
            min_zyx = [0, 0, 0]
            # Dev, checking if it's actually a group of points
            if not isinstance(bead_group, dict):
                print(f"Error | Expected dict | Got: {type(bead_group)}")
            for point_key in bead_group:  # This line gets the key for 1 point in a group.
                point = bead_group[point_key]
                if not isinstance(point, tuple):
                    print(f"Error | Expected tuple | Got: {type(point)}")
                for i in range(3):
                    if point[i] > max_zyx[i]:
                        max_zyx[i] = point[i]
                    if point[i] < min_zyx[i] or min_zyx[i] == 0:
                        min_zyx[i] = point[i]

            middle_point = [(max_zyx[i] + min_zyx[i]) / 2 for i in range(3)]
            if _local_debug:
                print(f"Max: {max_zyx} | Min: {min_zyx} ->")
                print(f"Middle point: {middle_point}")
            for point_key in bead_group.keys():
                relative_point = [(bead_group[point_key][i] - middle_point[i]) for i in range(3)]
                channel_rel_coords[point_key].append(relative_point)
                if _local_debug: print(f"  |{point_key}: {bead_group[point_key]} -> {relative_point}")

        rel_coords_for_figure = {wavelength_key: (0, 0, 0) for wavelength_key in wavelengths}
        # Finally we, take the average of each wavelength coord.
        for wavelength_key in channel_rel_coords.keys():
            rel_coords: list[tuple[float, float, float]] = channel_rel_coords[wavelength_key]
            if len(rel_coords) == 0:
                print(f"Error | Missing relative coords: {channel_rel_coords}")
                break
            rel_coords_for_figure[wavelength_key] = tuple(
                [int(sum([point[i] for point in rel_coords]) / len(rel_coords)) for i in range(3)])

        render_settings = {}
        render_engine = PSFRenderEngine(render_settings=render_settings, channels=channel_zyx_fwhm)

        table_beads = {wavelength_key: {
            "colormap": channel_zyx_fwhm[wavelength_key]["color"],
            "bead": rel_coords_for_figure[wavelength_key]
        } for wavelength_key in rel_coords_for_figure.keys()}

        final_summary_image = render_engine.render_multi_channel_summary(
            channel_offset_dict=rel_coords_for_figure,
            table_beads=table_beads, date= datetime(*self.date.date().getDate()).strftime("%Y-%m-%d"),
            version=version("psf_analysis_CFIM"),
            microscope=self.microscope.text(),
            objective=self.objective_id.text(),
        )
        text = f"Summary of {len(channel_zyx_fwhm)} channels"

        final_summary_image = np.expand_dims(final_summary_image, axis=0)

        self.display_measurement_stack(final_summary_image, name=text, measurement_scale=scale)

        self._hide_point_layers()

    def display_measurement_stack(self, averaged_measurement, measurement_scale= None, name="PSF images", metadata: dict = {}):
        """Display the averaged measurement stack in the viewer."""
        default_metadata = {
            "type": "Summary",
        }
        default_metadata.update(metadata)
        if measurement_scale is None:
            measurement_scale = self.get_scale()

        self.viewer.add_image(
            averaged_measurement,
            name=name,
            interpolation2d="bicubic",
            rgb=True,
            scale=measurement_scale,
            metadata=default_metadata,
        )
        # Resets napari viewer to 0.0
        self.viewer.dims.set_point(0, 0)
        self.viewer.reset_view()

    def _hide_point_layers(self):
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Points):
                layer.visible = False

    def _add_points_to_viewer_nm(self, points_nm, name="PSF images", color="red"):  # TODO: Throw this in debug
        scale = self.get_scale()  # returns a tuple (z_scale, y_scale, x_scale)
        # Convert each point from nm to px by dividing by scale per axis.
        points_px = [
            (int(pt[0] / scale[0]), int(pt[1] / scale[1]), int(pt[2] / scale[2]))
            for pt in points_nm
        ]

        self.viewer.add_points(
            points_px,
            name=name,
            face_color=color,
            size=7,
            opacity=0.7,
            scale=scale,
        )

    def color_from_emission_wavelength(self, wavelength: int = None):
        """
            Returns a color based on the emission wavelength in nm.
        """
        if not wavelength:
            wavelength = self.emission.value()

        if wavelength is None or wavelength < 380:
            return "Gray"
        # Self-implemented range dict :) # Maybe move the dict elsewhere, since it gets created every time.
        # TODO: Move this to settings
        wavelength_color_range_dict = RangeDict(
            [(380, 450, "Violet"),
             (450, 485, "Blue"),
             (485, 500, "Cyan"),
             (500, 565, "Green"),
             (565, 590, "Yellow"),
             (590, 625, "Orange"),
             (625, 740, "Red")])
        color = wavelength_color_range_dict[wavelength]
        return color

    def filter_bead_matches(self, bead_dict):
        """
        Filters and groups beads from different color channels based on proximity.

        Parameters:
            bead_dict (dict): Keys are wavelengths (e.g., 668, 603) and values are lists of bead coordinates (zyx tuples).
            psf_box (tuple): A tuple of (z, y, x) dimension sizes used to compute the max distance threshold.

        Returns:
            List of dictionaries. Each dictionary represents a matched group with one bead per channel,
            e.g., {668: (z,y,x), 603: (z,y,x), 550: (z,y,x)}.
        """
        # Convert psf_box into a single max distance threshold (Euclidean norm of the psf_box dimensions).
        psf_box = self.get_bounding_box_nm()
        max_dist = math.sqrt(sum(dim ** 2 for dim in psf_box)) / 3 # TODO: Make this a setting

        # Choose the anchor channel: the one with the fewest beads.
        anchor_channel = min(bead_dict, key=lambda ch: len(bead_dict[ch]))

        # Make a working copy of bead lists so we can remove beads once they're used.
        beads_available = {ch: list(points) for ch, points in bead_dict.items()}

        groups = []

        # Iterate over each bead in the anchor channel (using a copy of the list).
        for anchor_bead in beads_available[anchor_channel][:]:
            group = {anchor_channel: anchor_bead}
            success = True

            # For each other channel, find a candidate bead near the anchor bead.
            for ch in bead_dict:
                if ch == anchor_channel:
                    continue

                candidates = []
                for bead in beads_available[ch]:
                    # Calculate Euclidean distance between anchor_bead and the candidate bead.
                    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(anchor_bead, bead)))
                    if dist <= max_dist:
                        candidates.append((dist, bead))

                if not candidates:
                    # No candidate bead found for this channel; skip forming this group.
                    success = False
                    break
                else:
                    # Log if there are multiple candidate beads.
                    if len(candidates) > 1:
                        candidate_beads = [bead for (_, bead) in candidates]
                        print(
                            f"Multiple candidates in channel {ch} for anchor bead {anchor_bead}: {candidate_beads}. Picking the nearest.")
                    # Choose the candidate with the smallest distance.
                    candidates.sort(key=lambda x: x[0])
                    group[ch] = candidates[0][1]

            # If a complete group (one bead from every channel) was found, remove the used beads and add the group.
            if success and len(group) == len(bead_dict):
                # Remove the used bead from the anchor channel.
                beads_available[anchor_channel].remove(anchor_bead)
                # Remove the chosen bead from each of the other channels.
                for ch in group:
                    if ch != anchor_channel:
                        beads_available[ch].remove(group[ch])
                groups.append(group)
        if len(groups) == 0:
            print(f"Warning: No groups found. From: {bead_dict}")
        return groups

    def _validate_image(self):
        try:
            expected_z_spacing = 0
            selection = self.image_manager.get_images()
            for selected in selection:
                wavelength = selected.metadata.get("EmissionWavelength", None)
                self.error_widget.clear_channel(wavelength)


                widget_settings = {
                    "RI_mounting_medium": self.mounting_medium.value(),
                    "Emission": selected.metadata.get("EmissionWavelength", None),
                    "NA": selected.metadata.get("LensNA", None),
                }
                widget_settings.update(self.settings["image_analysis_settings"])
                channel_expected_z_spacing = analyze_image(selected, widget_settings)
                if channel_expected_z_spacing > expected_z_spacing:
                    expected_z_spacing = channel_expected_z_spacing

            if expected_z_spacing != 0:
                self.psf_z_box_size.setValue(int(expected_z_spacing) * 3)

        except Exception as e:
            print("Error in image analysis: ", e)
            raise e

    def _setup_progressbar(self, max_points):
        self.progressbar.reset()
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(max_points)
        self.progressbar.setValue(0)

        self._channel_progress = {}

    def _get_points_as_dict(self):
        point_layers = self.point_dropdown.get_selected()

        if point_layers is None:
            show_info(
                "Please add a point-layer and annotate the beads you "
                "want to analyze."
            )
            return None
        else:
            return point_layers

    def _get_current_img_layers(self):
        img_layers = self.image_manager.get_selected_as_list()
        return img_layers

    def _get_current_img_data(self):

        img_layers = self._get_current_img_layers()

        if img_layers is None or len(img_layers) == 0:
            show_info("Please add an image and select it.")
            return None

        image_data_list = []
        for layer in img_layers:
            if len(layer.data.shape) != 3:
                raise NotImplementedError(
                    f"Only 3 dimensional data is "
                    f"supported. Your data has {layer.data.shape} dimensions."
                )

            from bfio.bfio import BioReader

            if isinstance(layer.data, BioReader):
                img_data = np.transpose(layer.data.br.read(), [2, 0, 1]).copy()
            else:
                img_data = layer.data.copy()

            image_data_list.append(img_data)

        return image_data_list

    @overload
    def _get_patch_size(self) -> Tuple[float, float, float]:
        ...

    @overload
    def _get_patch_size(self, index: int) -> Tuple[float, float, float]:
        ...

    def _get_patch_size(self, index: int = -1) -> Tuple[float, float, float]:
        if index > -1:
            metadata = self.image_manager.get_metadata(index)
            z_box = _calculate_expected_z_spacing(emission=metadata["EmissionWavelength"],
                                                  numerical_aperture=metadata["NA"],
                                                  refractive_index=metadata["RI_mounting_medium"])
            return z_box * 3, self.psf_yx_box_size.value(), self.psf_yx_box_size.value()
        else:
            return (
                (self.psf_z_box_size.value()),
                (self.psf_yx_box_size.value()),
                (self.psf_yx_box_size.value()),
            )

    def _get_spacing(self):
        spacing = (
            self.z_spacing.value(),
            self.xy_pixelsize.value(),
            self.xy_pixelsize.value(),
        )
        return spacing

    def _get_microscope(self):
        if isinstance(self.microscope, QComboBox):
            microscope = self.microscope.currentText()
        else:
            microscope = self.microscope.text()
        return microscope

    def get_current_points_layer(self):
        return self.viewer.layers[self.point_dropdown.currentText()]

    def get_current_img_layer(self):

        for layer in self.viewer.layers:
            if type(layer) == napari.layers.Image:
                return layer
        print(f"Error: No image layer found")
        return 0

    def get_scale(self):
        return self.image_manager.get_image(0).scale

    def get_bounding_box_px(self):
        """
            Assuming the input box is in nm
            Gets the bounding box in pixels from the settings in ui.

        """
        return (
            self.psf_z_box_size.value() / self.z_spacing.value(),
            self.psf_yx_box_size.value() / self.xy_pixelsize.value(),
            self.psf_yx_box_size.value() / self.xy_pixelsize.value(),
        )

    def get_bounding_box_nm(self):
        return (
            self.psf_z_box_size.value(),
            self.psf_yx_box_size.value(),
            self.psf_yx_box_size.value(),
        )

    def delete_measurement_action(self):
        if (len(self.viewer.layers.selection) > 0 and
                self.viewer.layers.selection.active.name.startswith("PSF Summary")):

            idx = self.viewer.dims.current_step[0]
            wavelength = self.viewer.layers.selection.active.metadata.get("wavelength", "None")

            results_index = [i for i, x in enumerate(self.results) if x["Emission"][0] == wavelength]
            if not results_index:
                show_info(f"No results found for wavelength: {wavelength}")
                return

            if idx > 0:
                self.results[results_index[0]] = self.results[results_index[0]].drop(idx - 1).reset_index(drop=True)

            if idx == 0:
                show_info("Can't delete the average bead.")
            elif idx == self.summary_figs[wavelength].shape[0] - 1:
                self.summary_figs[wavelength] = self.summary_figs[wavelength][:-1]
            else:
                self.summary_figs[wavelength] = np.concatenate(
                    [
                        self.summary_figs[wavelength][:idx],
                        self.summary_figs[wavelength][idx + 1:],  # noqa: E203
                    ]
                )
            if len(self.summary_figs.get(wavelength, [])) <= 1:
                self.viewer.layers.remove_selected()
            else:
                self.viewer.layers.selection.active.data = self.summary_figs[wavelength]
        else:
            show_info("Please select 'PSF Summary' layer.")

    def save_measurements(self):
        if not self.results:
            show_info("No results to save.")
            return
        out_path = self.settings_Widget.settings["output_folder"]
        os.makedirs(out_path, exist_ok=True)
        for psf_results in self.results:
            if psf_results.empty:
                continue
            formatted_bead = {
                "z_fwhm": psf_results["FWHM_1D_Z"].mean(),
                "y_fwhm": psf_results["FWHM_2D_Y"].mean(),
                "x_fwhm": psf_results["FWHM_2D_X"].mean(),
            }
            variation = {
                "z_fwhm_max": psf_results["FWHM_1D_Z"].max(),
                "z_fwhm_min": psf_results["FWHM_1D_Z"].min(),
                "y_fwhm_max": psf_results["FWHM_2D_Y"].max(),
                "y_fwhm_min": psf_results["FWHM_2D_Y"].min(),
                "x_fwhm_max": psf_results["FWHM_2D_X"].max(),
                "x_fwhm_min": psf_results["FWHM_2D_X"].min(),
            }

            if psf_results["Emission"].empty:
                psf_results["Emission"] = self.emission.value()

            wavelength_id = psf_results["Emission"][0] # Note: Change when we use UUID

            self.report_widget.add_bead_stats(formatted_bead, data_type="Average from measurements", channel=wavelength_id)
            self.report_widget.set_bead_variation(variation, channel=wavelength_id)

            for i, row in psf_results.iterrows():
                save_path = os.path.join(out_path, basename(row["PSF_path"]))
                sanitized_path = sanitize(save_path)
                figure = self.summary_figs[wavelength_id][i + 1] # +1 because the first one is the average
                imsave(sanitized_path, figure)

            if self.temperature.text() != "":
                psf_results["Temperature"] = self.temperature.value()

            if psf_results["AiryUnit"].empty:
                psf_results["AiryUnit"] = self.airy_unit.value()

            if self.bead_size.text() != "":
                psf_results["BeadSize"] = self.bead_size.value()

            if self.bead_supplier.text() != "":
                psf_results["BeadSupplier"] = self.bead_supplier.text()

            if self.mounting_medium.text() != "":
                psf_results["MountingMedium"] = self.mounting_medium.text()

            if self.objective_id.text() != "":
                psf_results["Objective_id"] = self.objective_id.text()

            if self.operator.text() != "":
                psf_results["Operator"] = self.operator.text()

            if self.microscope_type.text() != "":
                psf_results["MicroscopeType"] = self.microscope_type.text()

            if psf_results["Excitation"].empty:
                psf_results["Excitation"] = self.excitation.value()



            if self.comment.text() != "":
                psf_results["Comment"] = self.comment.text()


            entry = psf_results.iloc[0]
            psf_results.to_csv(
                join(
                    out_path,
                    "PSFMeasurement_"
                    + entry["Date"]
                    + "_"
                    + sanitize(entry["ImageName"])
                    + "_"
                    + entry["Microscope"]
                    + "_"
                    + str(entry["Magnification"])
                    + "_"
                    + str(entry["NA"])
                    + ".csv",
                ),
                index=False,
            )
        # TODO: Get the report module acceptable again.
        # self.report_widget.create_pdf(path=self.settings_Widget.settings["output_folder"])
        show_info("Saved results.")


def _calculate_expected_z_spacing(emission, refractive_index, numerical_aperture):
    """
        Calculates the expected z-spacing for the PSF analysis using belov formula.
        # Formula: (2 * RI * λ) / NA^2 = expected_bead_z_size (in nm)
    """
    return (2 * refractive_index * emission) / (numerical_aperture ** 2)

def sanitize(string):
    """
        Removes illegal characters from the path.
    """
    safe_basename = re.sub(r'[|]', '-', string)
    # Reassemble the safe path using the original directory
    return safe_basename

