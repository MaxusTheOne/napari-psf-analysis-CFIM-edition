from copy import copy
from typing import Dict, Tuple

import numpy as np
from matplotlib import pyplot as plt
from matplotlib_scalebar.scalebar import ScaleBar
from mpl_toolkits.mplot3d.axis3d import Axis
from numpy._typing import ArrayLike
from pydantic import ValidationError

from psf_analysis_CFIM.psf_analysis.fit.fitter import YXFitter, ZFitter, ZYXFitter
from psf_analysis_CFIM.psf_analysis.image import Calibrated2DImage, Calibrated3DImage
from psf_analysis_CFIM.psf_analysis.records import (
    PSFRecord,
    YXFitRecord,
    ZFitRecord,
    ZYXFitRecord,
)
from psf_analysis_CFIM.psf_analysis.sample import YXSample

# Patch matplotlib to render ticks in 3D correctly.
# See: https://stackoverflow.com/a/16496436
if not hasattr(Axis, "_get_coord_info_old"):

    def _get_coord_info_new(self, renderer):
        mins, maxs, centers, deltas, tc, highs = self._get_coord_info_old(renderer)
        mins += deltas / 4
        maxs -= deltas / 4
        return mins, maxs, centers, deltas, tc, highs

    Axis._get_coord_info_old = Axis._get_coord_info
    Axis._get_coord_info = _get_coord_info_new


class PSFRenderEngine:
    from matplotlib.figure import Axes, Figure

    settings = {
        "covariance_ellipsoid": False,
        "coordinate_annotation": False,
    }
    psf_image: Calibrated3DImage = None
    psf_record: PSFRecord = None
    _figure: Figure = None
    _ax_xy: Axes = None
    _ax_yz: Axes = None
    _ax_zx: Axes = None
    _ax_3d: Axes = None
    _ax_3d_text: Axes = None

    def __init__(self, render_settings: dict, psf_image: Calibrated3DImage=None, psf_record: PSFRecord=None, ellipsoid_color="black", channels: dict = None):
        if render_settings:
            self.settings.update(render_settings)
        self.ellipsoid_color = ellipsoid_color
        if channels is not None:
            self.channels: dict[str:dict] = channels
            self.psf_image = psf_image
        else:
            self.psf_image = psf_image
            self.psf_record = psf_record
            self.ellipsoid_color = ellipsoid_color

    def _build_layout(self, dpi: int = 300) -> None:

        self._figure = plt.figure(figsize=(10, 10), dpi=dpi)
        self._add_axes()

    def _add_axes(self):
        self._ax_xy = self._figure.add_axes([0.025, 0.525, 0.45, 0.45])
        self._ax_yz = self._figure.add_axes([0.525, 0.525, 0.45, 0.45])
        self._ax_zx = self._figure.add_axes([0.025, 0.025, 0.45, 0.45])
        self._ax_3d = self._figure.add_axes(
            [0.55, 0.025, 0.42, 0.42], projection="3d", computed_zorder=False
        )

        self._ax_3d_text = self._figure.add_axes([0.525, 0.025, 0.45, 0.45])
        self._ax_3d_text.axis("off")

        self._add_axis_annotations()

    def _add_axis_annotations(self) -> None:
        ax_X = self._figure.add_axes([0.25, 0.5, 0.02, 0.02])
        ax_X.text(0, -0.1, "X", fontsize=14, ha="center", va="center")
        ax_X.axis("off")
        ax_Y = self._figure.add_axes([0.5, 0.75, 0.02, 0.02])
        ax_Y.text(0, 0, "Y", fontsize=14, ha="center", va="center")
        ax_Y.axis("off")
        ax_Z = self._figure.add_axes([0.5, 0.25, 0.02, 0.02])
        ax_Z.text(-0.5, 0, "Z", fontsize=14, ha="center", va="center")
        ax_Z.axis("off")
        ax_Z1 = self._figure.add_axes([0.75, 0.5, 0.02, 0.02])
        ax_Z1.text(0, 0.5, "Z", fontsize=14, ha="center", va="center")
        ax_Z1.axis("off")

    def render(
        self, date: str = None, version: str = None, dpi: int = 300, *, top_left_message: str = None, centroid: Tuple[float, float, float] = None
    ) -> ArrayLike:

        self._build_layout(dpi=dpi)
        self._add_projections(dpi=dpi)
        self._add_ellipsoids(centroid)

        if date is not None:
            self._add_date(date)

        if version is not None:
            self._add_version(version)

        if top_left_message:
            self._add_top_left_message(top_left_message)

        return self._fig_to_image()

    def _add_projections(self, dpi: int):
        self._add_yx_projection(dpi=dpi)
        self._add_zx_projection(dpi=dpi)
        self._add_yz_projection(dpi=dpi)

    def _add_yz_projection(self, dpi: int):
        yz_sqrt_projection = self._compute_centered_isotropic_image(
            projection=Calibrated2DImage(
                data=np.sqrt(np.max(self.psf_image.data, axis=2)).T,
                spacing=(self.psf_image.spacing[1], self.psf_image.spacing[0]),
            ),
            centroid=(self.psf_record.yx_fit.y_mu, self.psf_record.z_fit.z_mu),
            dpi=dpi,
        )
        self._add_image_to_axes(yz_sqrt_projection.data, self._ax_yz, origin="lower")
        self._draw_fwhm_annotations(
            self._ax_yz,
            shape=yz_sqrt_projection.data.shape,
            spacing=yz_sqrt_projection.spacing,
            fwhm_values=(self.psf_record.yx_fit.y_fwhm, self.psf_record.z_fit.z_fwhm),
            origin_upper=False,
        )

    def _add_zx_projection(self, dpi: int):
        zx_sqrt_projection = self._compute_centered_isotropic_image(
            projection=Calibrated2DImage(
                data=np.sqrt(np.max(self.psf_image.data, axis=1)),
                spacing=(self.psf_image.spacing[0], self.psf_image.spacing[2]),
            ),
            centroid=(self.psf_record.z_fit.z_mu, self.psf_record.yx_fit.x_mu),
            dpi=dpi,
        )
        self._add_image_to_axes(zx_sqrt_projection.data, self._ax_zx, origin="upper")
        self._draw_fwhm_annotations(
            self._ax_zx,
            shape=zx_sqrt_projection.data.shape,
            spacing=zx_sqrt_projection.spacing,
            fwhm_values=(
                self.psf_record.z_fit.z_fwhm,
                self.psf_record.yx_fit.x_fwhm,
            ),
            origin_upper=True,
        )

    def _add_yx_projection(self, dpi: int):
        yx_sqrt_projection = self._compute_centered_isotropic_image(
            projection=Calibrated2DImage(
                data=np.sqrt(np.max(self.psf_image.data, axis=0)),
                spacing=self.psf_image.spacing[1:],
            ),
            centroid=(self.psf_record.yx_fit.y_mu, self.psf_record.yx_fit.x_mu),
            dpi=dpi,
        )
        self._add_image_to_axes(yx_sqrt_projection.data, self._ax_xy, origin="lower")
        self._add_scalebar(yx_sqrt_projection.data.shape)
        self._draw_fwhm_annotations(
            self._ax_xy,
            shape=yx_sqrt_projection.data.shape,
            spacing=yx_sqrt_projection.spacing,
            fwhm_values=(
                self.psf_record.yx_fit.y_fwhm,
                self.psf_record.yx_fit.x_fwhm,
            ),
            origin_upper=False,
        )

    def _get_display_min_max(self, image: ArrayLike) -> Dict[str, float]:
        return {
            "vmin": np.quantile(image[image != -1], 0.03),
            "vmax": image[image != -1].max(),
        }

    def _add_image_to_axes(self, image: ArrayLike, ax: Axes, origin: str):
        ax.set_xticks([])
        ax.set_yticks([])
        ax.imshow(
            self._num_to_nan(image, num=-1),
            cmap=self._get_cmap(),
            interpolation="nearest",
            origin=origin,
            **self._get_display_min_max(image),
        )

    def _add_scalebar(self, shape: Tuple[int, int]):
        scalebar = ScaleBar(
            4000 / shape[1],
            "nm",
            fixed_value=500,
            location="lower right",
            border_pad=0.2,
            box_alpha=0.8,
        )
        self._ax_xy.add_artist(scalebar)

    def _get_cmap(self):
        from matplotlib import cm

        cmap = copy(cm.turbo)
        cmap.set_bad("white")
        return cmap

    def _num_to_nan(self, data: ArrayLike, num: float = -1):
        replaced = copy(data)
        replaced[replaced == num] = np.nan
        return replaced

    def _compute_centered_isotropic_image(
        self, projection: Calibrated2DImage, centroid: Tuple[float, float], dpi: int
    ) -> Calibrated2DImage:
        padded_projection = YXSample(
            image=Calibrated2DImage(
                data=np.pad(projection.data, 1, mode="constant", constant_values=(-1,)),
                spacing=projection.spacing,
            )
        )

        source_points = (
            padded_projection.get_ravelled_coordinates()
            - np.array([centroid])
            - np.array(padded_projection.image.spacing)
        )

        num_samples = self._estimate_number_of_samples(
            spacing=padded_projection.image.spacing,
            dpi=dpi,
        )
        target_points = self._get_target_points(num_samples=num_samples)

        import scipy

        return Calibrated2DImage(
            data=scipy.interpolate.griddata(
                points=source_points,
                values=padded_projection.image.data.ravel(),
                xi=target_points,
                method="nearest",
            ).reshape(num_samples, num_samples),
            spacing=(4000 / num_samples,) * 2,
        )

    def _get_target_points(self, num_samples: int):
        yy, xx = np.meshgrid(
            np.arange(num_samples) * 4000 / num_samples - 2000,
            np.arange(num_samples) * 4000 / num_samples - 2000,
            indexing="ij",
        )
        return np.stack([yy.ravel(), xx.ravel()], axis=-1)

    def _estimate_number_of_samples(self, spacing: Tuple[float, float], dpi: int):
        num_samples = int(np.min(spacing) * 10)
        while num_samples < 4.5 * dpi:
            num_samples += int(np.min(spacing) * 10)

        return num_samples

    def _draw_fwhm_annotations(
        self,
        axes: Axes,
        shape: Tuple[int, int],
        spacing: Tuple[float, float],
        fwhm_values: Tuple[float, float],
        origin_upper: bool,
    ) -> None:
        self._add_vertical_fwhm_annotation(
            axes=axes,
            fwhm_values=fwhm_values,
            shape=shape,
            spacing=spacing,
        )

        self._add_horizontal_fwhm_annotation(
            axes=axes,
            fwhm_values=fwhm_values,
            shape=shape,
            spacing=spacing,
            origin_upper=origin_upper,
        )

    def _add_horizontal_fwhm_annotation(
        self,
        axes: Axes,
        fwhm_values: Tuple[float, float],
        shape: Tuple[int, int],
        spacing: Tuple[float, float],
        origin_upper: bool,
    ):
        if origin_upper:
            shift_factor = 3
            start_factor = 1
            text_pos = shape[1] - shape[1] / 4.5
        else:
            shift_factor = 1
            start_factor = -1
            text_pos = shape[1] / 4.5

        cy = shape[0] / 2
        cx = shape[1] / 2
        y_fwhm, x_fwhm = fwhm_values

        if not np.isnan(y_fwhm) and not np.isnan(x_fwhm):
            dy = (y_fwhm / 2) / spacing[0]
            dx = (x_fwhm / 2) / spacing[1]

            axes.plot(
                [cx - dx, cx + dx],
                [
                    shift_factor * shape[1] / 4,
                ]
                * 2,
                linewidth=6,
                c="black",
                solid_capstyle="butt",
            )
            axes.plot(
                [cx - dx, cx + dx],
                [
                    shift_factor * shape[1] / 4,
                ]
                * 2,
                linewidth=4,
                c="white",
                solid_capstyle="butt",
            )
            axes.plot(
                [cx - dx, cx - dx],
                [cy + start_factor * dy, shift_factor * shape[1] / 4],
                "-",
                c="black",
            )
            axes.plot(
                [cx + dx, cx + dx],
                [cy + start_factor * dy, shift_factor * shape[1] / 4],
                "-",
                c="black",
            )
            axes.plot(
                [cx - dx, cx - dx],
                [cy + start_factor * dy, shift_factor * shape[1] / 4],
                "--",
                c="white",
            )
            axes.plot(
                [cx + dx, cx + dx],
                [cy + start_factor * dy, shift_factor * shape[1] / 4],
                "--",
                c="white",
            )

        axes.text(
            cx,
            text_pos,
            f"{self._get_fwhm_str(x_fwhm)}nm",
            ha="center",
            va="top",
            fontsize=15,
            bbox=dict(facecolor="white", alpha=0.8, linewidth=0),
        )

    def _get_fwhm_str(self, fwhm: float):
        if np.isnan(fwhm):
            return "NaN"
        else:
            return f"{int(np.round(fwhm))}"

    def _add_vertical_fwhm_annotation(
        self,
        axes: Axes,
        fwhm_values: Tuple[float, float],
        shape: Tuple[int, int],
        spacing: Tuple[float, float],
    ):
        cy = shape[0] / 2
        cx = shape[1] / 2
        y_fwhm, x_fwhm = fwhm_values

        if not np.isnan(y_fwhm) and not np.isnan(x_fwhm):
            dy = (y_fwhm / 2) / spacing[0]
            dx = (x_fwhm / 2) / spacing[1]

            axes.plot(
                [
                    shape[0] / 4,
                ]
                * 2,
                [cy - dy, cy + dy],
                linewidth=6,
                c="black",
                solid_capstyle="butt",
            )
            axes.plot(
                [
                    shape[0] / 4,
                ]
                * 2,
                [cy - dy, cy + dy],
                linewidth=4,
                c="white",
                solid_capstyle="butt",
            )
            axes.plot([shape[0] / 4, cx - dx], [cy - dy, cy - dy], "-", color="black")
            axes.plot([shape[0] / 4, cx - dx], [cy + dy, cy + dy], "-", color="black")
            axes.plot([shape[0] / 4, cx - dx], [cy - dy, cy - dy], "--", color="white")
            axes.plot([shape[0] / 4, cx - dx], [cy + dy, cy + dy], "--", color="white")

        axes.text(
            shape[1] / 4.5,
            cy,
            f"{self._get_fwhm_str(y_fwhm)}nm",
            ha="right",
            va="center",
            fontsize=15,
            bbox=dict(facecolor="white", alpha=0.8, linewidth=0),
        )

    def _has_nan_fwhm(self) -> bool:
        if np.isnan(self.psf_record.z_fit.z_fwhm):
            return True

        if np.isnan(self.psf_record.yx_fit.y_fwhm):
            return True

        if np.isnan(self.psf_record.yx_fit.x_fwhm):
            return True

        return False

    def _add_ellipsoids(self, centroid: Tuple[float, float, float]):
        self._configure_ticks_and_bounds()

        if not self._has_nan_fwhm():
            self._add_axis_aligned_ellipsoid() # Adds a grey ellipsoid from the fwhm of yx and z fits

        # TODO: Option in settings
        if self.settings["covariance_ellipsoid"]:
            self._add_cov_ellipsoid() # Adds a blue ellipsoid from covariance
        self._ax_3d_text.set_xlim(0, 100)
        self._ax_3d_text.set_ylim(0, 100)
        if centroid and self.settings["coordinate_annotation"]: # Disabled by request, TODO: Option in settings
            self._add_principal_components_annotons(centroid)

    def _add_color_ellipsoids(self, channel_offset_dict: dict = None):
        self._configure_ticks_and_bounds()

        self._add_fwhm_ellipsoids(channel_offset_dict)



    def _add_axis_aligned_ellipsoid(self):
        from psf_analysis_CFIM.psf_analysis.utils import sigma

        base_ell = self._get_simple_ellipsoid(
            xy_width=self.psf_record.yx_fit.y_fwhm, z_height=self.psf_record.z_fit.z_fwhm
        )
        self._ax_3d.plot_surface(
            *base_ell, rstride=2, cstride=2, color="grey", antialiased=True, alpha=1
        )
        self._ax_3d.plot_wireframe(
            *base_ell, rstride=3, cstride=3, color=self.ellipsoid_color, antialiased=True, alpha=0.5
        )

        self._ax_3d.contour(
            *base_ell,
            zdir="z",
            offset=self._ax_3d.get_zlim()[0],
            colors="white",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
        )
        self._ax_3d.contour(
            *base_ell,
            zdir="y",
            offset=self._ax_3d.get_ylim()[1],
            colors="white",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
        )
        self._ax_3d.contour(
            *base_ell,
            zdir="x",
            offset=self._ax_3d.get_xlim()[0],
            colors="white",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
        )
        self._ax_3d.contour(
            *base_ell,
            zdir="z",
            offset=self._ax_3d.get_zlim()[0],
            colors="black",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
            linestyles="--",
        )
        self._ax_3d.contour(
            *base_ell,
            zdir="y",
            offset=self._ax_3d.get_ylim()[1],
            colors="black",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
            linestyles="--",
        )
        self._ax_3d.contour(
            *base_ell,
            zdir="x",
            offset=self._ax_3d.get_xlim()[0],
            colors="black",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
            linestyles="--",
        )

    def _get_ellipsoid(
            self, covariance: ArrayLike, spacing: Tuple[float, float, float]
    ):
        bias = 0
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 30)

        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones_like(u), np.cos(v))
        cov_ = covariance / 2 * np.sqrt(2 * np.log(2))
        x, y, z = (cov_ @ np.stack((x, y, z), 0).reshape(3, -1) + bias).reshape(
            3, *x.shape
        )
        return x / spacing[2], y / spacing[1], z / spacing[0]

    def _get_simple_ellipsoid(self, xy_width: float | tuple[float, float], z_height: float, resolution: int = 30, zyx_offset: Tuple[float, float, float] = (0, 0, 0)):
        if isinstance(xy_width, float):
            a = xy_width / 2
            b = xy_width / 2
        else:
            a = xy_width[0] / 2
            b = xy_width[1] / 2


        c = z_height / 2

        # Create angular grids.
        u = np.linspace(0, 2 * np.pi, resolution)
        v = np.linspace(0, np.pi, resolution)

        # Parametric equations for the ellipsoid.
        x = a * np.outer(np.cos(u), np.sin(v))
        y = b * np.outer(np.sin(u), np.sin(v))
        z = c * np.outer(np.ones_like(u), np.cos(v))

        return x + zyx_offset[2], y + zyx_offset[1], z + zyx_offset[0]

    def _add_fwhm_ellipsoids(self, channel_offset_dict):

        import math


        # Sort channels based on the distance in (z, -y, x) space.
        sorted_keys = sorted(
            self.channels,
            key=lambda key: math.sqrt(
                (channel_offset_dict.get(key, (0, 0, 0))[0]) ** 2 +
                (-channel_offset_dict.get(key, (0, 0, 0))[1]) ** 2 +
                (channel_offset_dict.get(key, (0, 0, 0))[2]) ** 2
            ) if channel_offset_dict else 0,
        )

        channel_dim_prio_dict = {}
        dims = {"z": 0, "y": 1, "x": 2}
        for axis, idx in dims.items():
            sorted_keys = sorted(channel_offset_dict.keys(), key=lambda k: channel_offset_dict[k][idx], reverse=False)
            channel_dim_prio_dict[axis] = tuple(sorted_keys)

        ellipsoid_calc_dict = {}
        for key in sorted_keys:
            channel_dict = self.channels[key]
            zyx_fwhm = channel_dict.get("zyx")
            color = channel_dict["color"]
            if channel_offset_dict:
                channel_offset = channel_offset_dict.get(key, (0, 0, 0))
            else:
                channel_offset = (0, 0, 0)

            if channel_offset == (0, 0, 0):
                print(f"Found no offset for channel {key}")


            ellipsoid_calc = self._get_simple_ellipsoid(
                xy_width=(zyx_fwhm[2], zyx_fwhm[1]), z_height=zyx_fwhm[0], zyx_offset=channel_offset
            )

            self._ax_3d.plot_surface(
                *ellipsoid_calc, rstride=1, cstride=1, color=color, antialiased=True, alpha=0.3
            )
            self._ax_3d.plot_wireframe(
                *ellipsoid_calc, rstride=4, cstride=4, color=color, antialiased=True, alpha=0.2
            )

            ellipsoid_calc_dict[key] = ellipsoid_calc

        # We use the dim sorted dict to paint the ellipsoids in the correct order.
        # Kinda ugly, but thats what I could think of.
        zyx_args_dict = {
            "z": (self._ax_3d.get_zlim()[0], 0),
            "y": (self._ax_3d.get_ylim()[1], 1),
            "x": (self._ax_3d.get_xlim()[0], 2),
        }

        for dim_key in channel_dim_prio_dict:

            for channel_key in channel_dim_prio_dict[dim_key]:
                ellipsoid_calc = ellipsoid_calc_dict[channel_key]
                color = self.channels[channel_key]["color"]
                zyx_offset = channel_offset_dict.get(channel_key, (0, 0, 0))

                lim = zyx_args_dict[dim_key][0]
                dim_offset = zyx_offset[zyx_args_dict[dim_key][1]]


                self._ax_3d.contour(
                    *ellipsoid_calc,
                    zdir=dim_key,
                    offset=lim,
                    levels=[dim_offset],
                    colors=color,
                    linestyles="solid",
                )

                self._ax_3d.contourf(
                        *ellipsoid_calc,
                        zdir=dim_key,
                        offset=lim,
                        colors=color,
                        alpha=0.1,
                        levels=[dim_offset, dim_offset + 1000],
                    )


    def _add_cov_ellipsoid(self):
        fit = self.psf_record.zyx_fit
        covariance = np.array(
            [
                [fit.zyx_cxx, fit.zyx_cyx, fit.zyx_czx],
                [fit.zyx_cyx, fit.zyx_cyy, fit.zyx_czy],
                [fit.zyx_czx, fit.zyx_czy, fit.zyx_czz],
            ]
        )

        cv_ell = self._get_ellipsoid(
            covariance=covariance, spacing=self.psf_image.spacing
        )
        self._ax_3d.plot_surface(
            *cv_ell, rstride=1, cstride=1, color="navy", antialiased=True, alpha=0.15
        )
        self._ax_3d.plot_wireframe(
            *cv_ell, rstride=4, cstride=4, color="navy", antialiased=True, alpha=0.25
        )


        self._ax_3d.contour(
            *cv_ell,
            zdir="z",
            offset=self._ax_3d.get_zlim()[0],
            colors="navy",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
        )
        self._ax_3d.contour(
            *cv_ell,
            zdir="y",
            offset=self._ax_3d.get_ylim()[1],
            colors="navy",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
        )
        self._ax_3d.contour(
            *cv_ell,
            zdir="x",
            offset=self._ax_3d.get_xlim()[0],
            colors="navy",
            levels=1,
            vmin=-1,
            vmax=1,
            zorder=0,
        )

    def _configure_ticks_and_bounds(self, aspect_override: Tuple[float, float, float] = None):
        labels_list = [-1000, -750, -500, -250, 0, 250, 500, 750, 1000]
        if aspect_override:
            self._ax_3d.set_box_aspect(aspect_override)
        else:
            self._ax_3d.set_box_aspect((1.0, 1.0, 4.0 / 3.0))
        self._ax_3d.set_xticks(labels_list)
        self._ax_3d.set_xticklabels(
            labels_list, verticalalignment="bottom", horizontalalignment="right"
        )
        self._ax_3d.set_yticks(labels_list)
        self._ax_3d.set_yticklabels(
            labels_list, verticalalignment="bottom", horizontalalignment="left"
        )

        self._ax_3d.set_zticks(labels_list)
        self._ax_3d.set_zticklabels(
            labels_list,
            verticalalignment="top",
            horizontalalignment="left",
        )
        self._ax_3d.set_xlim(-800, 800)
        self._ax_3d.set_ylim(-800, 800)
        self._ax_3d.set_zlim(-1100, 1100)

    def _add_principal_components_annotons(self,centroid):

        self._ax_3d_text.text(
            -5,
            95,
            "Coordinates (nm)",
            fontsize=14,
            weight="bold",
            color="navy",
        )
        self._ax_3d_text.text(
            0,
            89,
            f"Z|{round(centroid[0],1)}",
            fontsize=14,
            color="navy",
        )
        self._ax_3d_text.text(
            0,
            83,
            f"Y|{round(centroid[1],1)}",
            fontsize=14,
            color="navy",
        )
        self._ax_3d_text.text(
            0,
            77,
            f"X|{round(centroid[2],1)}",
            fontsize=14,
            color="navy",
        )

    def _add_date(self, date: str) -> None:
        self._ax_3d_text.text(
            100,
            -4,
            f"Acquisition date: {date}",
            fontsize=11,
            horizontalalignment="right",
        )

    def _add_version(self, version: str) -> None: # Adds text to the bottom left with version number
        self._ax_3d_text.text(-110, -4, f"psf-analysis-CFIM: v{version}", fontsize=11)

    def _add_top_left_message(self, message: str) -> None:
        self._ax_3d_text.text(-110, 212, message, fontsize=14)

    def _fig_to_image(self):
        from matplotlib_inline.backend_inline import FigureCanvas

        canvas = FigureCanvas(self._figure)
        canvas.draw()
        image = np.frombuffer(canvas.tostring_rgb(), dtype="uint8").reshape(
            (self._figure.canvas.get_width_height()[::-1]) + (3,)
        )

        plt.close(self._figure)
        return image

    def render_multi_channel_summary(self, channel_offset_dict: dict, table_beads:dict,
                                     date: str = None, version: str = None, microscope: str = None, objective: str = None):
        """
            Renders a summary image with an ellipsoid for each color channel.
        """

        self._figure = plt.figure(figsize=(10, 10), dpi=150) # TODO:  use dpi from input, might need to be dpi / 2
        self._ax_3d = self._figure.add_subplot(111, projection="3d")
        table_ax = self._figure.add_axes((0.06, 0.750, 0.3, 0.16))


        # Allocate an additional axes for the distance table.
        self.create_distance_table_ax(table_beads, table_ax)

        self._add_color_ellipsoids(channel_offset_dict=channel_offset_dict)

        if date is not None:
            self._figure.text(0.99, 0.01, f"Acquisition date: {date}", ha="right", va="bottom", fontsize=12)


        # Adding text to the bottom left of the figure with two extra lines above
        if microscope:  self._figure.text(0.01, 0.059, f"Microscope: {microscope}", ha="left", va="bottom", fontsize=12)
        if objective:   self._figure.text(0.01, 0.04, f"Objective: {objective}", ha="left", va="bottom", fontsize=12)
        if version:     self._figure.text(0.01, 0.01, f"psf-analysis-CFIM: v{version}", ha="left", va="bottom", fontsize=12)



        return self._fig_to_image()

    def create_distance_table_ax(self, beads, ax):
        """
        Creates a table showing pairwise Euclidean distances between beads on an existing axes.
        Each bead is provided as a dictionary with:
           - 'bead': a tuple/list of zyx coordinates.
           - 'colormap': a string with a valid matplotlib color.
        """
        # Sort keys numerically for consistency.
        bead_keys_sorted = sorted(beads.keys(), key=lambda x: float(x))
        keys = [f"{wavelength}λ" for wavelength in bead_keys_sorted]
        n = len(keys)

        # Compute pairwise distance matrix.
        dist_matrix = np.zeros((n, n))
        for i, key_i in enumerate(bead_keys_sorted):
            coord_i = np.array(beads[key_i]["bead"])
            for j, key_j in enumerate(bead_keys_sorted):
                coord_j = np.array(beads[key_j]["bead"])
                dist_matrix[i, j] = np.linalg.norm(coord_i - coord_j)

        # Format the values for table cells.
        cell_text = [[f"{dist_matrix[i, j]:.0f}" for j in range(n)] for i in range(n)]

        # Create the table on the provided axes.
        table = ax.table(cellText=cell_text, rowLabels=keys, colLabels=keys, loc='upper center')
        table.scale(1, 1.5)

        # Color according to colormap
        cells = table.get_celld()
        for i, key in enumerate(bead_keys_sorted):
            row_cell = cells.get((0, i))
            col_cell = cells.get((i + 1, -1))
            for cell in (row_cell, col_cell):
                if cell:
                    cell.set_facecolor(beads[key]["colormap"])
                    cell.get_text().set_color("white")

        ax.set_title("Distances between centers in nm", color="black", fontsize=14)

        ax.axis('tight')
        ax.axis('off')



class PSF:
    image: Calibrated3DImage = None
    psf_record: PSFRecord = None
    error = False
    settings: dict = {}

    def __init__(self, image: Calibrated3DImage, psf_settings: dict):
        self.image = image
        self.settings = psf_settings

    def analyze(self) -> None:
        z_fitter = ZFitter(image=self.image)
        yx_fitter = YXFitter(image=self.image)
        zyx_fitter = ZYXFitter(image=self.image)
        try:
            z_fit_record: ZFitRecord = z_fitter.fit()
            yx_fit_record: YXFitRecord = yx_fitter.fit()
            zyx_fit_record: ZYXFitRecord = zyx_fitter.fit()
        except RuntimeError as e:
            print(f"Runtime error fitting point: {self.image.get_corner_coordinates()}")
            self.error = True
        except (TypeError, ValidationError) as e:
            print(f"Type error fitting point: {self.image.get_corner_coordinates()} | error: {e}")
            self.error = True
        else:
            self.psf_record = PSFRecord(
                z_fit=z_fit_record,
                yx_fit=yx_fit_record,
                zyx_fit=zyx_fit_record,
            )


    def get_record(self) -> PSFRecord:
        return self.psf_record

    def get_summary_image(
        self,
        date: str = None,
        version: str = None,
        dpi: int = 300,
        *,
        top_left_message: str = None,
        ellipsoid_color: str = "black",
        centroid = None,
    ) -> ArrayLike:
        engine = PSFRenderEngine(render_settings=self.settings.get("render_settings"),psf_image=self.image, psf_record=self.psf_record, ellipsoid_color=ellipsoid_color)
        return engine.render(date=date, version=version, dpi=dpi, top_left_message=top_left_message, centroid=centroid)

    def get_summary_dict(self) -> dict:
        return {
            **self.psf_record.z_fit.dict(),
            **self.psf_record.yx_fit.dict(),
            **self.psf_record.zyx_fit.dict(),
        }

    def get_fwhm(self):
        return self.psf_record.z_fit.z_fwhm,  self.psf_record.yx_fit.y_fwhm, self.psf_record.yx_fit.x_fwhm
