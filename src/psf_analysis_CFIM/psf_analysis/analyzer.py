import os
from os.path import join
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from botocore.model import InvalidShapeError
from numpy._typing import ArrayLike

from psf_analysis_CFIM.debug.debug import report_error_debug
from psf_analysis_CFIM.error_widget.error_display_widget import report_error, report_error_box
from psf_analysis_CFIM.psf_analysis.extract.BeadExtractor import BeadExtractor
from psf_analysis_CFIM.psf_analysis.image import Calibrated3DImage
from psf_analysis_CFIM.psf_analysis.parameters import PSFAnalysisInputs
from psf_analysis_CFIM.psf_analysis.psf import PSF


class Analyzer:
    def __init__(self, parameters: PSFAnalysisInputs, settings: dict = {"wavelength_color": "red"}):
        self._parameters = parameters
        bead_extractor = BeadExtractor(
            image=Calibrated3DImage(
                data=parameters.img_data, spacing=parameters.spacing
            ),
            patch_size=parameters.patch_size,
        )
        self._wavelength_color = settings["wavelength_color"]
        self._invalid_beads_index = []
        self._beads = bead_extractor.extract_beads(points=self._parameters.point_data)

        self._results = None
        self._result_figures = {}
        self._index = 0
        try:
            self._debug = os.environ["PSF_ANALYSIS_CFIM_DEBUG"] == "1"
        except Exception:
            self._debug = False
        if self._debug:
            print("Analyzer | Debug")

    def __iter__(self):
        return self

    def __len__(self):
        return len(self._beads)

    def __next__(self):
        if self._index < len(self._beads):
            bead = self._beads[self._index]
            try:
                if 0 in bead.data.shape:
                    raise InvalidShapeError(f"Discarding bead with invalid shape: {bead.data.shape}")
                psf = PSF(image=bead)
                psf.analyze()
                if psf.error:
                    raise InvalidShapeError(f"Discarding bead due to analyze error: {self._index}")
                results = psf.get_summary_dict()
                extended_results = self._extend_result_table(bead, results)
                self._add(
                    extended_results,
                    psf.get_summary_image(
                        date=self._parameters.date,
                        version=self._parameters.version,
                        dpi=self._parameters.dpi,
                        ellipsoid_color=self._wavelength_color,
                        centroid= (extended_results["z_mu"], extended_results["y_mu"], extended_results["x_mu"]),
                    ),
                )
            except InvalidShapeError as e:
                self._invalid_beads_index.append(self._index)
                # min_cord, max_cord = bead.get_box()
                report_error("", bead.get_middle_coordinates())
            self._index += 1
            return self._index + (len(self._parameters.point_data) - len(self._beads))
        else:
            raise StopIteration()

    def get_date(self):
        """Return the date of the image."""
        return self._parameters.date

    def get_version(self):
        """Return the version of the analysis."""
        return self._parameters.version

    def get_dpi(self):
        """Return the DPI of the analysis."""
        return self._parameters.dpi

    def get_raw_beads(self):
        """Return the raw data of the beads before analysis."""
        return self._beads

    def get_raw_beads_filtered(self):
        """ Return the raw data of the beads before analysis, but filtered for found invalid shapes."""
        beads = [bead for i, bead in enumerate(self._beads) if i not in self._invalid_beads_index]
        return beads

    def get_averaged_bead(self):
        """Average the raw bead data before analysis."""
        filtered_beads = [bead.data for bead in self.get_raw_beads_filtered()]
        try:
            averaged_bead_data = np.mean(filtered_beads, axis=0).astype(np.uint16)
            averaged_bead = Calibrated3DImage(data=averaged_bead_data, spacing=self._parameters.spacing)
            return averaged_bead
        except (ValueError, AttributeError) as e:
            print(f"Error getting average bead: {e}")
            if self._debug:
                report_error_debug(filtered_beads, "3d_array")



    def _extend_result_table(self, bead, results):
        extended_results = results.copy()
        extended_results["z_mu"] += bead.offset[0] * self._parameters.spacing[0]
        extended_results["y_mu"] += bead.offset[1] * self._parameters.spacing[1]
        extended_results["x_mu"] += bead.offset[2] * self._parameters.spacing[2]
        extended_results["image_name"] = self._parameters.name
        extended_results["date"] = self._parameters.date
        extended_results["microscope"] = self._parameters.microscope
        extended_results["mag"] = self._parameters.magnification
        extended_results["NA"] = self._parameters.na
        extended_results["yx_spacing"] = self._parameters.spacing[1]
        extended_results["z_spacing"] = self._parameters.spacing[0]
        extended_results["version"] = self._parameters.version
        return extended_results

    def _add(self, result: dict, summary_fig: ArrayLike):
        if self._results is None:
            self._results = {}
            for key in result.keys():
                self._results[key] = [result[key]]
            self._results["PSF_path"] = []
        else:
            for key in result.keys():
                self._results[key].append(result[key])

        centroid = np.round([result["x_mu"], result["y_mu"], result["z_mu"]], 1)
        bead_name = "{}_Bead_X{}_Y{}_Z{}".format(result["image_name"], *centroid)
        unique_bead_name = self._make_unique(bead_name)
        self._result_figures[unique_bead_name] = summary_fig
        self._results["PSF_path"].append(join(unique_bead_name + ".png"))

    def _make_unique(self, name: str):
        count = 1
        unique_name = name
        while unique_name in self._result_figures.keys():
            unique_name = f"{name}-({count})"
            count += 1
        return unique_name

    def get_results(self) -> Optional[pd.DataFrame]:
        """Create result table from dict.

        Parameters
        ----------
        results :
            Result dict obtained from `analyze_bead`

        Returns
        -------
        result_table
            Result table with "nice" column names
        """
        if self._results is not None:
            return self._build_dataframe()
        else:
            return None

    def get_summary_figure_stack(
        self,
        bead_img_scale: Tuple[float, float, float],
        bead_img_shape: Tuple[int, int, int],
    ) -> Optional[Tuple[ArrayLike, ArrayLike]]:
        """
        Create a (N, Y, X, 3) stack of all summary figures.

        Parameters
        ----------
        bead_img_scale : scaling of the whole bead image in (Z, Y, X) nm/px
        bead_img_shape : shape of the whole bead image

        Returns
        -------
        stack of all summary figures
        scaling to display them with napari
        """
        if len(self._result_figures) > 0:
            measurement_stack = self._build_figure_stack()
            measurement_scale = self._compute_figure_scaling(
                bead_img_scale, bead_img_shape, measurement_stack
            )

            return measurement_stack, measurement_scale
        else:
            return None, None

    def _compute_figure_scaling(self, bead_scale, bead_shape, measurement_stack):
        measurement_scale = np.array(
            [
                bead_scale[0],
                bead_scale[1] / measurement_stack.shape[1] * bead_shape[1],
                bead_scale[1] / measurement_stack.shape[1] * bead_shape[1],
            ]
        )
        return measurement_scale

    def _build_figure_stack(self):
        measurement_stack = np.stack(
            [self._result_figures[k] for k in self._result_figures.keys()]
        )
        return measurement_stack

    def  _build_dataframe(self):
        return pd.DataFrame(
            {
                "ImageName": self._results["image_name"],
                "Date": self._results["date"],
                "Microscope": self._results["microscope"],
                "Magnification": self._results["mag"],
                "NA": self._results["NA"],
                "Amplitude_1D_Z": self._results["z_amp"],
                "Amplitude_2D_XY": self._results["yx_amp"],
                "Amplitude_3D_XYZ": self._results["zyx_amp"],
                "Background_1D_Z": self._results["z_bg"],
                "Background_2D_XY": self._results["yx_bg"],
                "Background_3D_XYZ": self._results["zyx_bg"],
                "Z_1D": self._results["z_mu"],
                "X_2D": self._results["x_mu"],
                "Y_2D": self._results["y_mu"],
                "X_3D": self._results["zyx_x_mu"],
                "Y_3D": self._results["zyx_y_mu"],
                "Z_3D": self._results["zyx_z_mu"],
                "FWHM_1D_Z": self._results["z_fwhm"],
                "FWHM_2D_X": self._results["x_fwhm"],
                "FWHM_2D_Y": self._results["y_fwhm"],
                "FWHM_3D_Z": self._results["zyx_z_fwhm"],
                "FWHM_3D_Y": self._results["zyx_y_fwhm"],
                "FWHM_3D_X": self._results["zyx_x_fwhm"],
                "FWHM_PA1_2D": self._results["yx_pc1_fwhm"],
                "FWHM_PA2_2D": self._results["yx_pc2_fwhm"],
                "FWHM_PA1_3D": self._results["zyx_pc1_fwhm"],
                "FWHM_PA2_3D": self._results["zyx_pc2_fwhm"],
                "FWHM_PA3_3D": self._results["zyx_pc3_fwhm"],
                "SignalToBG_1D_Z": (
                    np.array(self._results["z_amp"]) / np.array(self._results["z_bg"])
                ).tolist(),
                "SignalToBG_2D_XY": (
                    np.array(self._results["yx_amp"]) / np.array(self._results["yx_bg"])
                ).tolist(),
                "SignalToBG_3D_XYZ": (
                    np.array(self._results["zyx_amp"])
                    / np.array(self._results["zyx_bg"])
                ).tolist(),
                "xy_pixelsize": self._results["yx_spacing"],# Changed these two from XYspacing and Zspacing
                "z_spacing": self._results["z_spacing"],
                "cov_xx_3D": self._results["zyx_cxx"],
                "cov_xy_3D": self._results["zyx_cyx"],
                "cov_xz_3D": self._results["zyx_czx"],
                "cov_yy_3D": self._results["zyx_cyy"],
                "cov_yz_3D": self._results["zyx_czy"],
                "cov_zz_3D": self._results["zyx_czz"],
                "cov_xx_2D": self._results["yx_cxx"],
                "cov_xy_2D": self._results["yx_cyx"],
                "cov_yy_2D": self._results["yx_cyy"],
                "sde_amp_1D_Z": self._results["z_amp_sde"],
                "sde_amp_2D_XY": self._results["yx_amp_sde"],
                "sde_amp_3D_XYZ": self._results["zyx_amp_sde"],
                "sde_background_1D_Z": self._results["z_bg_sde"],
                "sde_background_2D_XY": self._results["yx_bg_sde"],
                "sde_background_3D_XYZ": self._results["zyx_bg_sde"],
                "sde_Z_1D": self._results["z_mu_sde"],
                "sde_X_2D": self._results["x_mu_sde"],
                "sde_Y_2D": self._results["y_mu_sde"],
                "sde_X_3D": self._results["zyx_x_mu_sde"],
                "sde_Y_3D": self._results["zyx_y_mu_sde"],
                "sde_Z_3D": self._results["zyx_z_mu_sde"],
                "sde_cov_xx_3D": self._results["zyx_cxx_sde"],
                "sde_cov_xy_3D": self._results["zyx_cyx_sde"],
                "sde_cov_xz_3D": self._results["zyx_czx_sde"],
                "sde_cov_yy_3D": self._results["zyx_cyy_sde"],
                "sde_cov_yz_3D": self._results["zyx_czx_sde"],
                "sde_cov_zz_3D": self._results["zyx_czz_sde"],
                "sde_cov_xx_2D": self._results["yx_cxx_sde"],
                "sde_cov_xy_2D": self._results["yx_cyx_sde"],
                "sde_cov_yy_2D": self._results["yx_cyy_sde"],
                "z_pos": self._results["z_mu"],
                "y_pos": self._results["y_mu"],
                "x_pos": self._results["x_mu"],
                "version": self._results["version"],
                "PSF_path": self._results["PSF_path"],
            }
        )
