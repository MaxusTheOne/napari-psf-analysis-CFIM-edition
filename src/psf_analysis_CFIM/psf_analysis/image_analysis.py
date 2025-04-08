from typing import Dict

import numpy as np
import pandas as pd
from napari.utils.notifications import show_info

from psf_analysis_CFIM.error_widget.error_display_widget import ErrorDisplayWidget, report_validation_error, \
    report_validation_warning


# TODO: Rewrite this to a class
# TODO: A whole section for analysing quality after finding beads
def analyze_image(img_layer, widget_settings: Dict[str, any], num_bins=8):

    img_data = img_layer.data
    settings = widget_settings

    channel = get_first_existing_key(settings, ("wavelength", "Emission", "EmissionWavelength"), 0)

    print(f"Dev | Analysing image for: {channel}")

    if img_data is None:
        raise ValueError("Image data cannot be None")
    if not isinstance(img_data, np.ndarray):
        raise TypeError("Image data must be a NumPy array")

    # Determine max intensity value from image data type
    if np.issubdtype(img_data.dtype, np.integer):
        max_val = np.iinfo(img_data.dtype).max
    else:
        max_val = img_data.max()

    # Calculate pixel counts
    min_pixels = (img_data == 0).sum()
    max_pixels = (img_data == max_val).sum()
    total_pixels = img_data.size

    if total_pixels == 0:
        raise ValueError("Image contains no pixels to analyze.")


    # Filter out min and max values
    img_filtered = img_data[(img_data > 0) & (img_data < max_val)]

    # Compute histogram
    hist, bin_edges = np.histogram(img_filtered, bins=num_bins, range=(0, max_val))

    # Compute percentages
    percentages = (hist / total_pixels) * 100
    min_percentage = min_pixels / total_pixels * 100
    max_percentage = max_pixels / total_pixels * 100

    # Error handling
    error_handling_intensity(min_percentage, max_percentage, max_val, settings["intensity_settings"],channel)
    # report_noise(img_data, error_widget, settings["noise_settings"]) # TODO: Make this work better before enabling

    try:
        expected_z_spacing = report_z_spacing(img_layer, widget_settings, channel)
    except ValueError as e:
        print(f"Error calculating expected z spacing: {e}")
        expected_z_spacing = None
    return expected_z_spacing

def error_handling_intensity(min_percentage, max_percentage, max_val, settings, channel):
    # TODO: make constants dependent on config file
    lower_warning_percent = settings["lower_warning_percent"]
    lower_error_percent = settings["lower_error_percent"]
    upper_warning_percent = settings["upper_warning_percent"]
    upper_error_percent = settings["upper_error_percent"]

    # Cast warnings / errors based on constants
    if min_percentage > lower_error_percent:
        report_validation_error(f"Too many pixels with min intensity | {round(min_percentage, 4)}% of pixels",channel)
    elif min_percentage > lower_warning_percent:
        report_validation_warning(f"Many pixels with min intensity | {round(min_percentage, 4)}% of pixels",channel)

    if max_percentage > upper_error_percent:
        report_validation_error(f"Too many pixels with max intensity ({max_val}) | {round(max_percentage, 4)}% of pixels",channel)
    elif max_percentage > upper_warning_percent:
        report_validation_warning(f"Many pixels with max intensity ({max_val}) | {round(max_percentage, 4)}% of pixels",channel)



def report_noise(img_data, error_widget, settings):
    standard_deviation = np.std(img_data)
    snr = _calculate_snr(img_data)

    # TODO: config file
    high_noise_threshold = settings["high_noise_threshold"]  # Example threshold for high noise
    low_snr_threshold = settings["low_snr_threshold"]  # Example threshold for low SNR in dB

    print(f"Standard deviation: {standard_deviation:.2f} | SNR: {snr:.2f} dB")
    # Imagine not using elif. SMH.
    if snr < low_snr_threshold:
        error_widget.add_warning(f"Low SNR detected. Image quality might suffer | SNR: {snr:.2f} dB")
    elif standard_deviation > high_noise_threshold:
            error_widget.add_error(f"High noise detected, image might be unusable | Standard deviation: {standard_deviation:.2f}")

def report_z_spacing(img_layer, widget_settings: Dict[str, any], channel=0):
    """
    Calculate the expected bead z size and compare it to the z-spacing of the image.

    Formula: (2 * RI * λ) / NA^2 = expected_bead_z_size (in nm)

    Parameters:
        img_layer (napari.layers.): The image layer to analyze. Expected to have a `scale` attribute in nanometers (nm).
        widget_settings (Dict[str, any]): Dictionary containing settings for the widget. Expected keys:
            - "RI_mounting_medium" (float): Refractive index of the mounting medium.
            - "Emission" (float): Emission wavelength in nanometers (nm).
            - "NA" (float): Numerical aperture of the objective.

    Raises:
        ValueError: If any of the required settings are missing from `widget_settings`.
    """
    reflective_index = float(widget_settings["RI_mounting_medium"])
    emission = float(widget_settings["Emission"])
    numeric_aparature = float(widget_settings["NA"])
    z_spacing = img_layer.scale[0] # We now expect the scale to be for nanometers

    # Check if all required settings are present
    if None in (reflective_index, emission, numeric_aparature):
        raise ValueError(f"Missing required settings for calculating expected bead z size. \n reflective index | emission | numeric aparature\nGot: {widget_settings}")

    expected_bead_z_size = (2 * reflective_index * emission) / numeric_aparature ** 2

    if z_spacing > expected_bead_z_size / 2.5:
        report_validation_error(f"Z-spacing is too large | Z-spacing: {z_spacing:.2f} nm", int(channel))
    elif z_spacing > expected_bead_z_size / 3.5:
        report_validation_warning(f"Z-spacing is larger than expected | Z-spacing: {z_spacing:.2f} nm", int(channel))
    return expected_bead_z_size


def _calculate_snr(img_data: np.ndarray) -> float:
    """Calculate the Signal-to-Noise Ratio (SNR) of an image."""
    signal_power = np.mean(img_data ** 2)
    noise_power = np.var(img_data)
    print(f"Signal power: {signal_power:.2f} | Noise power: {noise_power:.2f}")
    return 10 * np.log10(signal_power / noise_power)

def error_handling_flat(img_data, error_widget):
    """Check if the image is flat based on the standard deviation of pixel intensities."""
    # TODO: config file | Make this function more useful
    flat_threshold = 1.0
    standard_deviation = np.std(img_data)
    if standard_deviation < flat_threshold:
        error_widget.add_warning(f"Flat image detected. Standard deviation: {standard_deviation:.2f}")

def filter_psf_beads_by_box(result_dict, bead_figures, psf_bbox):
    """
        Filter out beads based on whether they have a visual PSF in their image.
        Image size is the same as psf_bbox. The visual bbox is found using result_dict: "FWHM_3D_Z", "FWHM_3D_Y" and "FWHM_3D_X".
        Bead positions are found from result_dict: "z_pos", "y_pos" and "x_pos".

        Parameters:
            result_dict (Dict[str, List[float]]): Dictionary containing the results from the PSF analysis.
            bead_figures (List[np.ndarray]): List of 3D images containing summary figures.
            psf_bbox (Tuple[int, int, int]): The bounding box for the PSF analysis. z, y, x size.

        Returns:
            np.array(Figure): A List of summary figures that contain a visual PSF.
    """
    print(f"Dict length: {len(result_dict["z_pos"])} | Bead figures: {len(bead_figures)}")

    if len(result_dict["z_pos"]) != len(result_dict["y_pos"]):
        raise ValueError("Z and Y positions do not match in length.")

    psf_bbox_positions = []
    visual_bbox_positions = []
    for i in range(len(result_dict["z_pos"])):
        z = result_dict["z_pos"][i]
        y = result_dict["y_pos"][i]
        x = result_dict["x_pos"][i]
        visual_bbox = (result_dict["FWHM_3D_Z"][i], result_dict["FWHM_3D_Y"][i], result_dict["FWHM_3D_X"][i])
        psf_bbox_positions.append( _get_psf_bbox(psf_bbox, z, y, x))
        visual_bbox_positions.append( _get_psf_bbox(visual_bbox, z, y, x))

    return filter_beads(psf_bbox_positions, visual_bbox_positions, bead_figures)


def _get_psf_bbox(psf_bbox, z, y, x):
    """
        Translate the bbox size to max, min coordinates based on the bead position.
    """
    z_min = z - psf_bbox[0] // 2
    z_max = z + psf_bbox[0] // 2
    y_min = y - psf_bbox[1] // 2
    y_max = y + psf_bbox[1] // 2
    x_min = x - psf_bbox[2] // 2
    x_max = x + psf_bbox[2] // 2
    return [z_min, z_max, y_min, y_max, x_min, x_max]


def filter_beads(psf_bboxes, visual_psf_bboxes, beads):
    """
    Filter out beads whose PSF_bbox intersects any visual_PSF_bbox.

    Parameters:
      psf_bboxes: List of 3D bounding boxes.
      visual_psf_bboxes: List of 3D bounding boxes (both bboxes formatted as
                                                    List[min_z, min_y, min_x, max_z, max_y, max_x])
      beads: List of beads. Expected to be a list of summary figures, but can be any list.

    Returns:
      A list of beads that do not have an intersecting PSF_bbox with any visual_PSF_bbox.
    """
    filtered = []
    for i in range(len(beads)):
        bead_box = psf_bboxes[i]
        # Skip bead if its PSF_bbox intersects any visual_PSF_bbox
        if any(intersects_3d(bead_box, vbox) for vbox in visual_psf_bboxes):
            continue
        filtered.append(beads[i])
    return filtered


def intersects_3d(box1, box2):
    """
    Check if two 3D bounding boxes intersect.

    Each box is in the format:
      [min_z, min_y, min_x, max_z, max_y, max_x]
    """
    return not (
            box1[3] < box2[0] or  # box1 is entirely before box2 in z
            box1[0] > box2[3] or  # box1 is entirely after box2 in z
            box1[4] < box2[1] or  # box1 is entirely below box2 in y
            box1[1] > box2[4] or  # box1 is entirely above box2 in y
            box1[5] < box2[2] or  # box1 is entirely left of box2 in x
            box1[2] > box2[5]  # box1 is entirely right of box2 in x
    )
def get_first_existing_key(d, keys, default=None):
    for key in keys:
        if key in d:
            return d[key]
    return default