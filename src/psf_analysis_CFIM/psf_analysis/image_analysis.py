from typing import Dict

import numpy as np
import pandas as pd
from napari.utils.notifications import show_info

from psf_analysis_CFIM.error_widget.error_display_widget import ErrorDisplayWidget

# TODO: Rewrite this to a class
# TODO: A whole section for analysing quality after finding beads
def analyze_image(img_layer, error_widget: ErrorDisplayWidget, widget_settings: Dict[str, any], num_bins=8):

    img_data = img_layer.data
    settings = widget_settings

    if img_data is None:
        raise ValueError("Image data cannot be None")
    if not isinstance(img_data, np.ndarray):
        raise TypeError("Image data must be a NumPy array")

    # Determine max intensity value from image data type
    if np.issubdtype(img_data.dtype, np.integer):
        max_val = np.iinfo(img_data.dtype).max
    else:
        max_val = img_data.max()

    metadata = img_layer.metadata
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
    error_handling_intensity(min_percentage, max_percentage, max_val, error_widget, settings["intensity_settings"])
    # report_noise(img_data, error_widget, settings["noise_settings"]) # TODO: Make this work better before enabling

    try:
        expected_z_spacing = report_z_spacing(img_layer, error_widget, widget_settings)
    except ValueError as e:
        show_info(e)
        expected_z_spacing = None
    return expected_z_spacing

def error_handling_intensity(min_percentage, max_percentage, max_val, error_widget, settings):
    # TODO: make constants dependent on config file
    lower_warning_percent = settings["lower_warning_percent"]
    lower_error_percent = settings["lower_error_percent"]
    upper_warning_percent = settings["upper_warning_percent"]
    upper_error_percent = settings["upper_error_percent"]

    # Cast warnings / errors based on constants
    if min_percentage > lower_error_percent:
        error_widget.add_error(f"Too many pixels with min intensity | {round(min_percentage, 4)}% of pixels")
    elif min_percentage > lower_warning_percent:
        error_widget.add_warning(f"Many pixels with min intensity | {round(min_percentage, 4)}% of pixels")

    if max_percentage > upper_error_percent:
        error_widget.add_error(f"Too many pixels with max intensity ({max_val}) | {round(max_percentage, 4)}% of pixels")
    elif max_percentage > upper_warning_percent:
        error_widget.add_warning(f"Many pixels with max intensity ({max_val}) | {round(max_percentage, 4)}% of pixels")



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

def report_z_spacing(img_layer, error_widget: ErrorDisplayWidget, widget_settings: Dict[str, any]):
    """
    Calculate the expected bead z size and compare it to the z-spacing of the image.

    Formula: (2 * RI * λ) / NA^2 = expected_bead_z_size (in nm)

    Parameters:
        img_layer (napari.layers.): The image layer to analyze. Expected to have a `scale` attribute in micrometers (μm).
        error_widget (ErrorDisplayWidget): The widget to display errors and warnings.
        widget_settings (Dict[str, any]): Dictionary containing settings for the widget. Expected keys:
            - "RI_mounting_medium" (float): Refractive index of the mounting medium.
            - "Emission" (float): Emission wavelength in nanometers (nm).
            - "NA" (float): Numerical aperture of the objective.

    Raises:
        ValueError: If any of the required settings are missing from `widget_settings`.
    """
    reflective_index = widget_settings["RI_mounting_medium"]
    emission = widget_settings["Emission"]
    numeric_aparature = widget_settings["NA"]
    z_spacing = img_layer.scale[0] * 1000 # µn -> nm

    # Check if all required settings are present
    if None in (reflective_index, emission, numeric_aparature):
        raise ValueError("Missing required settings for calculating expected bead z size. \n reflective index | emission | numeric aparature")

    expected_bead_z_size = (2 * reflective_index * emission) / numeric_aparature ** 2

    if z_spacing > expected_bead_z_size / 2.5:
        error_widget.add_error(f"Z-spacing is too large | Z-spacing: {z_spacing:.2f} nm")
    elif z_spacing > expected_bead_z_size / 3.5:
        error_widget.add_warning(f"Z-spacing is larger than expected | Z-spacing: {z_spacing:.2f} nm")
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

def save_statistics_to_file(stats, filename="image_statistics.csv"):
    """
    Save image statistics to a CSV file.

    Parameters:
        stats (dict): A dictionary containing intensity ranges and percentages.
        filename (str): The file to save statistics to.
    """
    # Save as a CSV using Pandas
    df = pd.DataFrame(stats.items(), columns=["Intensity Range", "Percentage"])
    df.to_csv(filename, index=False)
    show_info("Statistics saved to file.")
