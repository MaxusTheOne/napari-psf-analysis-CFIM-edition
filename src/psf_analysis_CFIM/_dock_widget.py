import os
import pathlib
import warnings
from datetime import datetime
from importlib.metadata import version
from os.path import basename, dirname, exists, getctime, join

import napari.layers
import numpy as np
import yaml
from qtpy.QtWidgets import QLayout
from napari import viewer
from napari._qt.qthreading import FunctionWorker, thread_worker
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
from psf_analysis_CFIM.library_workarounds.RangeDict import RangeDict
from psf_analysis_CFIM.mounting_medium_selector import MountingMediumSelector
from psf_analysis_CFIM.psf_analysis.analyzer import Analyzer
from psf_analysis_CFIM.psf_analysis.image_analysis import analyze_image, filter_psf_beads_by_box
from psf_analysis_CFIM.psf_analysis.parameters import PSFAnalysisInputs
from psf_analysis_CFIM.psf_analysis.psf import PSF
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
        self.summary_figs = None
        self.results = None
        self.warnings = []
        self.errors = []

        # UI
        self.settings_Widget = SettingsWidget(parent=self)

        self.bead_finder = None

        self.cancel_extraction = False
        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)
        self.setMinimumSize(340, 900)
        self._add_logo()

        setting_tabs = QTabWidget(parent=self)

        self._add_basic_settings_tab(setting_tabs)
        self._add_advanced_settings_tab(setting_tabs)

        setting_tabs.setMinimumSize(210, 300)
        setting_tabs.setMaximumSize(320, 320)

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
        self.use_config()
        if os.getenv("PSF_ANALYSIS_CFIM_DEBUG") == "1":
            self._debug = True
            debug = global_vars.debug_instance
            debug.set_PSFAnalysis_instance(self)



    def use_config(self):
        settings = self.settings_Widget.settings
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
        logo = pathlib.Path(__file__).parent / "resources" / "logo.png"
        logo_label = QLabel()
        logo_label.setText(f'<img src="{logo}" width="320">')
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
        report_error("Test Error",(20,20,20))

    def _find_beads(self):
        self._create_bead_finder()

        scale= self.bead_finder.get_scale()

        beads, discarded_beads = self.bead_finder.find_beads()

        self._point_list_to_viewer(beads, scale, "Found Beads", size=4)


        for bead in discarded_beads:
            report_warning("", point=(bead[0], bead[1], bead[2]))



    def _img_to_viewer(self, image, scale=None, name="BeadTest"):
        self.viewer.add_image(image, name=name, scale=scale)

    def _point_list_to_viewer(self, points, scale=None, name="Points", size=10):
        self.viewer.add_points(points, size=size, scale=scale, name=name, face_color="cyan")

    def _add_save_dialog(self):
        self.report_widget.set_title("PSF Analysis Report") # TODO: Put this in settings

        pane = self.report_widget.init_ui()
        self.save_dir_line_edit = self.report_widget.save_dir_line_edit # Exposing this for use in use_config
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
        basic_settings.setLayout(QFormLayout(setting_tabs))
        self.cbox_img = QComboBox(parent=basic_settings)
        self.cbox_img.setToolTip(
            "Image layer with the measured point spread functions (PSFs)."
        )
        self.cbox_point = QComboBox(parent=basic_settings)
        self.cbox_point.setToolTip(
            "Points layer indicating which PSFs should " "be measured."
        )
        basic_settings.layout().addRow(QLabel("Image", basic_settings), self.cbox_img)
        basic_settings.layout().addRow(
            QLabel("Points", basic_settings), self.cbox_point
        )
        self.date = QDateEdit(datetime.today())
        self.date.setToolTip("Acquisition date of the PSFs.")
        basic_settings.layout().addRow(
            QLabel("Acquisition Date", basic_settings), self.date
        )
        # microscope_options = get_microscopes(get_psf_analysis_settings_path())
        # if isinstance(microscope_options, list):
        # self.microscope = QComboBox(parent=basic_settings)
            # self.microscope.addItems(microscope_options)
        # else:
        self.microscope = QLineEdit("Undefined")
        self.microscope.setToolTip(
            "Name of the microscope which was used to" " acquire the PSFs."
        )
        basic_settings.layout().addRow(
            QLabel("Microscope", basic_settings), self.microscope
        )
        self.magnification = QSpinBox(parent=basic_settings)
        self.magnification.setToolTip("Total magnification of the system.")
        self.magnification.setMinimum(0)
        self.magnification.setMaximum(10000)
        self.magnification.setValue(100)
        self.magnification.setSingleStep(10)
        basic_settings.layout().addRow(
            QLabel("Magnification", basic_settings), self.magnification
        )
        self.objective_id = QLineEdit("obj_1")
        self.objective_id.setToolTip("Objective identifier (or name).")
        basic_settings.layout().addRow(
            QLabel("Objective ID", basic_settings), self.objective_id
        )
        self.na = QDoubleSpinBox(parent=basic_settings)
        self.na.setToolTip("Numerical aperture of the objective.")
        self.na.setMinimum(0.0)
        self.na.setMaximum(1.7)
        self.na.setSingleStep(0.05)
        self.na.setValue(1.4)
        basic_settings.layout().addRow(QLabel("NA", basic_settings), self.na)
        self.xy_pixelsize = QDoubleSpinBox(parent=basic_settings)
        self.xy_pixelsize.setToolTip("Pixel size in XY dimensions in nano " "meters.")
        self.xy_pixelsize.setMinimum(0.0)
        self.xy_pixelsize.setMaximum(10000.0)
        self.xy_pixelsize.setSingleStep(10.0)
        self.xy_pixelsize.setValue(65.0)
        basic_settings.layout().addRow(
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
        basic_settings.layout().addRow(
            QLabel("Z-Spacing [nm]", basic_settings), self.z_spacing
        )
        self.psf_yx_box_size = QDoubleSpinBox(parent=basic_settings)
        self.psf_yx_box_size.setToolTip(
            "For analysis each PSF is cropped "
            "out of the input image. This is the XY size of the crop in nano meters."
        )
        self.psf_yx_box_size.setMinimum(1.0)
        self.psf_yx_box_size.setMaximum(1000000.0)
        self.psf_yx_box_size.setSingleStep(500.0)
        self.psf_yx_box_size.setValue(2000.0)
        basic_settings.layout().addRow(
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
        basic_settings.layout().addRow(
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
                self.cbox_point.addItem(str(layer))

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
                    break

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
            show_warning(f"Missing metadata: {missing_keys} | Plugin only made for .CZI (for now) | Plugin might behave unexpectedly")

        try:
            self.microscope.setText(metadata["CameraName"])
            self.objective_id.setText(metadata["ObjectiveName"])
            self.magnification.setValue(int(metadata["NominalMagnification"]))
            self.na.setValue(float(metadata["LensNA"]))
            self.airy_unit.setValue(round(float(metadata["PinholeSizeAiry"]), 2))
            self.excitation.setValue(round(float(metadata["ExcitationWavelength"]),2))
            self.emission.setValue(round(float(metadata["EmissionWavelength"]),2))
            self.xy_pixelsize.setValue(round(float(layer.scale[1]),2))
            self.z_spacing.setValue(round(float(layer.scale[0]),2))
        except KeyError as e:
            print(f"Missing metadata for settings: {e} and possible more")

    def _create_bead_finder(self):
        if self.bead_finder is None:
            self.find_beads_button.setEnabled(True)

        layer = self.viewer.layers[self.cbox_img.currentText()]
        self.bead_finder = BeadFinder(layer.data, layer.scale, bounding_box=(self.psf_z_box_size.value(), self.psf_yx_box_size.value(), self.psf_yx_box_size.value()))



    def _layer_inserted(self, event):
        if isinstance(event.value, napari.layers.Image):
            self.cbox_img.insertItem(self.cbox_img.count() + 1, str(event.value))
        elif isinstance(event.value, napari.layers.Points):
            self.cbox_point.insertItem(self.cbox_point.count() + 1, str(event.value))

    def _layer_removed(self, event):
        if isinstance(event.value, napari.layers.Image):
            items = [self.cbox_img.itemText(i) for i in range(self.cbox_img.count())]
            self.cbox_img.removeItem(items.index(str(event.value)))
            self.changed_manually = False
            self.current_img_index = -1
            self._img_selection_changed()
        elif isinstance(event.value, napari.layers.Points):
            items = [
                self.cbox_point.itemText(i) for i in range(self.cbox_point.count())
            ]
            self.cbox_point.removeItem(items.index(str(event.value)))

    def _on_selection(self, event):
        if self.viewer.layers.selection.active is not None:
            self.delete_measurement.setEnabled(
                self.viewer.layers.selection.active.name == "Analyzed Beads"
            )

    def request_cancel(self):
        self.cancel_extraction = True
        self.cancel.setText("Cancelling...")

    def prepare_measure(self):
        img_data = self._get_current_img_data()
        if img_data is None:
            return


        point_data = self._get_point_data()
        if point_data is None:
            return

        self._setup_progressbar(point_data)

        analyzer_settings = {
            "wavelength_color": self.color_from_emission_wavelength(),
        }

        analyzer = Analyzer(parameters=PSFAnalysisInputs(
            microscope=self._get_microscope(),
            magnification=self.magnification.value(),
            na=self.na.value(),
            spacing=self._get_spacing(),
            patch_size=self._get_patch_size(),
            name=self._get_img_name(),
            img_data=img_data,
            point_data=point_data,
            dpi=int(self.summary_figure_dpi.currentText()),
            date=datetime(*self.date.date().getDate()).strftime("%Y-%m-%d"),
            version=version("psf_analysis_CFIM")
            ),
            settings=analyzer_settings
        )

        # Note: Why is it called measurement_stack? It's a stack of summary images.
        def _on_done(result):
            if result is not None:

                # unpacks the result from analyzer. Should contain a stack of summary images and the scale.
                measurement_stack, measurement_scale = result
                self.summary_figs = measurement_stack

                bead_img_stack = analyzer.get_raw_beads_filtered()
                print(f"bead img stack 0: {bead_img_stack[0].shape()}")
                print(f"Position of 0: ({self.results["z_pos"][0]}, {self.results["y_pos"][0]}, {self.results["x_pos"][0]})")

                filtered_figs = filter_psf_beads_by_box(self.results, measurement_stack, (self.psf_z_box_size.value(), self.psf_yx_box_size.value(), self.psf_yx_box_size.value()))
                print(f"Figs length: {len(filtered_figs)}")

                # Creates an image of the average bead, runs the PSF analysis on it and creates summary image.
                averaged_bead = analyzer.get_averaged_bead()
                averaged_psf = PSF(image=averaged_bead)

                averaged_psf.analyze()

                self.report_widget.add_bead_stats_psf(averaged_psf.get_record(), title="Average from image")

                averaged_summary_image = averaged_psf.get_summary_image(
                    date=analyzer.get_date(),
                    version=analyzer.get_version(),
                    dpi=analyzer.get_dpi(),
                    top_left_message=f"Average PSF of {len(measurement_stack)} beads",
                    ellipsoid_color=self.color_from_emission_wavelength()
                )

                # Combines the summary image from average bead with the summary image stack from the entire psf analysis.
                averaged_summary_image_expanded = np.expand_dims(averaged_summary_image, axis=0)
                combined_stack = np.concatenate((averaged_summary_image_expanded, measurement_stack), axis=0)
                display_measurement_stack(combined_stack, measurement_scale)

                _hide_point_layers()

            _reset_state()

        def display_measurement_stack(averaged_measurement, measurement_scale):
            """Display the averaged measurement stack in the viewer."""
            self.viewer.add_image(
                averaged_measurement,
                name="PSF images",
                interpolation2d="bicubic",
                rgb=True,
                scale=measurement_scale,
            )
            # Resets napari viewer to 0.0
            self.viewer.dims.set_point(0, 0)
            self.viewer.reset_view()

        def _hide_point_layers():
            for layer in self.viewer.layers:
                if isinstance(layer, napari.layers.Points):
                    layer.visible = False

        def _update_progress(progress: int):
            self.progressbar.setValue(progress)
            if self.cancel_extraction:
                worker.quit()

        def _reset_state():
            if self.cancel_extraction:
                self.progressbar.setValue(0)
                self.cancel_extraction = False
                self.cancel.setEnabled(False)
                self.cancel.setText("Cancel")
                self.extract_psfs.setEnabled(True)
                self.progressbar.reset()

        @thread_worker(progress={"total": len(point_data)})
        def measure():

            yield from analyzer

            self.results = analyzer.get_results()
            measurement_stack, measurement_scale = analyzer.get_summary_figure_stack(
                bead_img_scale=self.viewer.layers[self.cbox_img.currentText()].scale,
                bead_img_shape=self.viewer.layers[
                    self.cbox_img.currentText()
                ].data.shape,
            )
            if measurement_stack is not None:
                return measurement_stack, measurement_scale

        worker: FunctionWorker = measure()

        worker.yielded.connect(_update_progress)
        worker.returned.connect(_on_done)
        worker.aborted.connect(_reset_state)
        worker.errored.connect(_reset_state)
        worker.start()

        self.extract_psfs.setEnabled(False)
        self.cancel.setEnabled(True)

    def color_from_emission_wavelength(self):
        """
            Returns a color based on the emission wavelength in nm.
        """
        wavelength = self.emission.value()
        if wavelength is None or wavelength <= 0:
            return "Gray"
        # Self-implemented range dict :) # Maybe move the dict elsewhere, since it gets created every time.
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

    def _validate_image(self):
        try:
            self.error_widget.clear()
            widget_settings = {**self.settings_Widget.settings["image_analysis_settings"], **{
                "RI_mounting_medium": self.mounting_medium.value(), "Emission": self.emission.value(),
                "NA": self.na.value()}}
            expected_z_spacing = analyze_image(self._get_current_img_layer(), self.error_widget,
                          widget_settings=widget_settings)
            self.psf_z_box_size.setValue(int(expected_z_spacing) * 3)

        except Exception as e:
            print("Error in image analysis: ", e)
            raise e

    def _setup_progressbar(self, point_data):
        self.progressbar.reset()
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(len(point_data))
        self.progressbar.setValue(0)

    def _get_img_name(self):
        img_layer = None
        for layer in self.viewer.layers:
            if str(layer) == self.cbox_img.currentText():
                img_layer = layer

        if img_layer is None:
            return None
        else:
            return basename(img_layer.source.path)

    def _get_point_data(self):
        point_layer = None
        for layer in self.viewer.layers:
            if str(layer) == self.cbox_point.currentText():
                point_layer = layer
        if point_layer is None:
            show_info(
                "Please add a point-layer and annotate the beads you "
                "want to analyze."
            )
            return None
        else:
            return point_layer.data.copy()

    def _get_current_img_layer(self):
        img_layer = None
        for layer in self.viewer.layers:
            if str(layer) == self.cbox_img.currentText():
                img_layer = layer
        return img_layer

    def _get_current_img_data(self):

        img_layer = self._get_current_img_layer()

        if img_layer is None:
            show_info("Please add an image and select it.")
            return None

        if len(img_layer.data.shape) != 3:
            raise NotImplementedError(
                f"Only 3 dimensional data is "
                f"supported. Your data has {img_layer.data.shape} dimensions."
            )

        from bfio.bfio import BioReader

        if isinstance(img_layer.data, BioReader):
            img_data = np.transpose(img_layer.data.br.read(), [2, 0, 1]).copy()
        else:
            img_data = img_layer.data.copy()

        return img_data
    
    def _get_patch_size(self):
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
        return self.viewer.layers[self.cbox_point.currentText()]

    def get_current_img_layer(self):
        return self.viewer.layers[self.cbox_img.currentText()]

    def get_scale(self):
        return self.get_current_img_layer().scale

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

    def delete_measurement_action(self):
        if len(
            self.viewer.layers.selection
        ) > 0 and self.viewer.layers.selection.active.name.startswith(
            "Analyzed " "Beads"
        ):
            idx = self.viewer.dims.current_step[0]
            self.results = self.results.drop(idx).reset_index(drop=True)
            if idx == 0:
                self.summary_figs = self.summary_figs[1:]
            elif idx == self.summary_figs.shape[0] - 1:
                self.summary_figs = self.summary_figs[:-1]
            else:
                self.summary_figs = np.concatenate(
                    [
                        self.summary_figs[:idx],
                        self.summary_figs[idx + 1 :],  # noqa: E203
                    ]
                )
            if len(self.summary_figs) == 0:
                self.viewer.layers.remove_selected()
            else:
                self.viewer.layers.selection.active.data = self.summary_figs
        else:
            show_info("Please select the 'Analyzed Beads' layer.")

    def save_measurements(self):
        if self.results is None:
            show_info("No results to save.")
            return
        out_path = self.settings_Widget.settings["output_folder"]
        os.makedirs(out_path, exist_ok=True)
        for i, row in self.results.iterrows():
            save_path = join(out_path, basename(row["PSF_path"]))
            imsave(save_path, self.summary_figs[i])

        formatted_bead = {
            "z_fwhm": self.results["FWHM_1D_Z"].mean(),
            "y_fwhm": self.results["FWHM_2D_Y"].mean(),
            "x_fwhm": self.results["FWHM_2D_X"].mean(),
        }
        self.report_widget.add_bead_stats(formatted_bead, title="Average from measurements")
        variation = {
            "z_fwhm_max": self.results["FWHM_1D_Z"].max(),
            "z_fwhm_min": self.results["FWHM_1D_Z"].min(),
            "y_fwhm_max": self.results["FWHM_2D_Y"].max(),
            "y_fwhm_min": self.results["FWHM_2D_Y"].min(),
            "x_fwhm_max": self.results["FWHM_2D_X"].max(),
            "x_fwhm_min": self.results["FWHM_2D_X"].min(),
        }
        self.report_widget.set_bead_variation(variation)



        if self.temperature.text() != "":
            self.results["Temperature"] = self.temperature.value()

        if self.airy_unit.text() != "":
            self.results["AiryUnit"] = self.airy_unit.value()

        if self.bead_size.text() != "":
            self.results["BeadSize"] = self.bead_size.value()

        if self.bead_supplier.text() != "":
            self.results["BeadSupplier"] = self.bead_supplier.text()

        if self.mounting_medium.text() != "":
            self.results["MountingMedium"] = self.mounting_medium.text()

        if self.objective_id.text() != "":
            self.results["Objective_id"] = self.objective_id.text()

        if self.operator.text() != "":
            self.results["Operator"] = self.operator.text()

        if self.microscope_type.text() != "":
            self.results["MicroscopeType"] = self.microscope_type.text()

        if self.excitation.text() != "":
            self.results["Excitation"] = self.excitation.value()

        if self.emission.text() != "":
            self.results["Emission"] = self.emission.value()

        if self.comment.text() != "":
            self.results["Comment"] = self.comment.text()

        entry = self.results.iloc[0]
        self.results.to_csv(
            join(
                out_path,
                "PSFMeasurement_"
                + entry["Date"]
                + "_"
                + entry["ImageName"]
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
        self.report_widget.create_pdf(path=self.settings_Widget.settings["output_folder"])
        show_info("Saved results.")

