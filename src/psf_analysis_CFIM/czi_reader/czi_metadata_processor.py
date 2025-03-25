import warnings
import xml.etree.ElementTree as ET

import numpy as np
import pint
from scipy.interpolate import interp1d

from psf_analysis_CFIM.library_workarounds.RangeDict import RangeDict


def recursive_find(element, tag, num):
    """
    Recursively searches for the first occurrence of an element with the given tag.
    """
    number = num
    if element.tag == tag:
        return element
    for child in element:
        result = recursive_find(child, tag, number)
        if result is not None:
            print(f"/{element.tag}", end="")
            return result
    return None

def find_in_xml_tree(xml_tree, tag):
    """
        Finds all occurrences of a tag in an XML tree.
        Returns a list of elements.
    """
    elements = xml_tree.findall(f".//{tag}")
    return elements

# region Wavelength and color
wavelength_to_color = RangeDict(
            [(380, 450, "Violet"),
             (450, 485, "Blue"),
             (485, 500, "Cyan"),
             (500, 565, "Green"),
             (565, 590, "Yellow"),
             (590, 625, "Orange"),
             (625, 740, "Red")])

def generate_gamma_dict():
    # Tabulated wavelengths (nm) and corresponding V(λ) values
    wavelengths = np.array([380, 400, 420, 440, 460, 480, 500, 520, 540, 555, 580, 600, 620, 640, 660, 680, 700, 780])
    V_values = np.array(
        [0.00004, 0.0004, 0.0040, 0.0230, 0.0600, 0.1390, 0.3230, 0.7100, 0.9540, 1.0000, 0.8700, 0.6310, 0.3810,
         0.1750, 0.0610, 0.0170, 0.0041, 0.0000])

    range_dict_list = [(wavelengths[i], wavelengths[i + 1], V_values[i]) for i in range(len(wavelengths) - 1)]
    wave_length_to_value = RangeDict(
        range_dict_list
    )

    # Create an interpolation function
    V_interp = interp1d(wavelengths, V_values, kind='linear', fill_value="extrapolate")

    # Define the wavelengths for your channels
    channel_wavelengths = {"red": 625, "orange": 590, "yellow": 565, "green": 500, "cyan": 485, "blue": 480, "violet": 450}

    # Create a dictionary with the computed V(λ) for each channel
    V_dict = {channel: float(V_interp(wl)) for channel, wl in channel_wavelengths.items()}
    print(V_dict)

wavelength_luminous_dict = {'red': 0.3, 'orange': 0.7, 'yellow': 0.9, 'green': 0.4, 'cyan': 0.3, 'blue': 0.2, 'violet': 0.1}

def compute_napari_gamma(color_name_list, gamma_default=1.0, correction_weight=0.05):
    """
    Computes a napari gamma dict.

    Napari gamma is defined in the range 0 - 2, with 0 being the brightest and 2 the darkest.
    This function uses a luminous efficiency dictionary (wavelength_luminous_dict) and treats the channel with
    the highest luminous value as the reference (its gamma will be gamma_default).

    Parameters:
      color_name_list: list of color names (e.g., ["red", "green", "blue"]).
      gamma_default: Gamma value for the reference channel (default brightness setting).
      correction_weight: Scaling factor for how strongly to adjust other channels.
         Lower values bring the gamma values closer together.

    Returns:
      A dictionary mapping each color in color_name_list to its computed gamma.
    """
    napari_gamma_dict = {}
    max_color = max(wavelength_luminous_dict, key=wavelength_luminous_dict.get)
    max_luminous = wavelength_luminous_dict[max_color]

    for color in color_name_list:
        try:
            # Get luminous efficiency for the current channel.
            current_luminous = wavelength_luminous_dict[color.lower()]
            # Avoid division by zero.
            if current_luminous == 0:
                ratio = 1.0
            else:
                ratio = max_luminous / current_luminous
            # For the channel with the maximum luminous value, ratio = 1, so gamma remains gamma_default.
            gamma = gamma_default - correction_weight * (ratio - 1)
        except KeyError:
            warnings.warn(f"Unknown channel {color}. Using default gamma value.")
            gamma = gamma_default

        # Clamp gamma to the allowed range [0, 2]
        gamma = max(0, min(gamma, 2))
        napari_gamma_dict[color] = gamma
    return napari_gamma_dict

# endregion

# TODO: Fix pint warning
def extract_key_metadata(reader, channels):
    """
    Extracts specified metadata from reader.metadata and returns it as a list of dictionaries.
    With index being a dictionary for each channel.

    Parameters:
        reader: A CziReader instance that already has its metadata loaded.
        channels: int -> The number of channels in the image.

    Returns:
        dict_list -> A list of dictionaries with the metadata for each channel.
    """
    # Defining the keys to extract from the metadata; TODO: Add to settings, to allow user to select which keys for UI.
    keys = ["LensNA", "CameraName", "NominalMagnification", "PinholeSizeAiry", "ExcitationWavelength", "EmissionWavelength", "ObjectiveName", "DefaultScalingUnit"]

    # Get the xml metadata from the reader
    xml_metadata = reader.metadata
    key_dict = {}
    for key in keys:
        data = find_in_xml_tree(xml_metadata, key)
        if data:
            key_dict[key] = data
        else:
            print(f"No metadata found for {key}")
            key_dict[key] = None

    # region scaling
    try:
        default_scaling_unit = key_dict["DefaultScalingUnit"]
        if not default_scaling_unit:
            raise KeyError(f"Default scaling unit is {default_scaling_unit}")
        original_units = default_scaling_unit[0].text
    except KeyError:
        warnings.warn("No OriginalUnits found. Assuming micrometre(µm)")
        original_units = "micrometre"

    pint_unit_register = pint.UnitRegistry()
    if original_units == "micrometre" or original_units == "µm":
        nm_scale = (reader.physical_pixel_sizes.Z, reader.physical_pixel_sizes.Y, reader.physical_pixel_sizes.X)
        scale = [s * 1000 for s in nm_scale]
        pint_units = pint_unit_register("nm")
        units = (pint_units, pint_units, pint_units)
    else:
        scale = reader.physical_pixel_sizes
        pint_units = pint_unit_register(original_units)
        units = (pint_units, pint_units, pint_units)
    # endregion

    # Here reformat the metadata into a dictionary with a list size of channels.
    channel_metadata = {}
    for key, data in key_dict.items():
        if data:
            if len(data) == 1:
                channel_metadata[key] = [data[0].text for _ in range(channels)]
                continue
            elif len(data) != channels:
                raise ValueError(f"Expected {channels} values for {key}, got {len(data)}")
                # This is mostly to filter out the weird Airy scans.

            channel_metadata[key] = [data[i].text for i in range(channels)]

    # Fun side project. # TODO: Add to settings. And take max channel from the max wavelength.
    try:
        wavelength_colors = [wavelength_to_color[round(float(color),0)] for color in channel_metadata["EmissionWavelength"]]
        napari_gamma_dict = compute_napari_gamma(wavelength_colors, correction_weight=0.1, gamma_default=1.3)
    except KeyError:
        napari_gamma_dict = None
        wavelength_colors = None

    channel_metadata_list = []
    for channel in range(channels):
        metadata_metadata = {}
        for key in channel_metadata:
            metadata_metadata[key] = channel_metadata[key][channel]

        if napari_gamma_dict:
            colormap = wavelength_colors[channel]
            gamma = napari_gamma_dict[colormap]
        else:
            colormap = None
            gamma = 1.0

        metadata = {"scale": scale, "units": units, "metadata": metadata_metadata, "blending": "additive", "colormap": colormap, "gamma": gamma}
        channel_metadata_list.append(metadata)

    return channel_metadata_list
