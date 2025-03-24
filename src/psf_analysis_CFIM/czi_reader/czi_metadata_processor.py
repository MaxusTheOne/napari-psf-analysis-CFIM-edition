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

def compute_napari_gamma(V, V_max, gamma_default=1.0, correction_weight=0.05):
    """
    Compute a napari gamma value for a channel.

    Parameters:
      V: Sensitivity for the channel.
      V_max: Maximum sensitivity among channels (reference).
      gamma_default: Gamma value for the reference channel.
      correction_weight: Strength of the correction.
          Lower values make the channels' gamma values closer to each other.

    Returns:
      A gamma value in the range [0, 2], where lower means brighter.
    """
    # Compute the ratio: for the channel with maximum sensitivity, ratio = 1.
    ratio = V_max / V
    # We want the reference channel (ratio==1) to have gamma_default.
    # For channels with lower sensitivity (ratio > 1), we subtract a scaled difference.
    gamma = gamma_default - correction_weight * (ratio - 1)
    # Ensure gamma stays within napari's allowed range.
    return max(0, min(gamma, 2))


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

    try:
        original_units = key_dict["DefaultScalingUnit"][0].text
    except KeyError:
        warnings.warn("No OriginalUnits found. Assuming micrometre(µm)")
        original_units = "micrometre"

    pint_ureg = pint.UnitRegistry()
    if original_units == "micrometre" or original_units == "µm":
        nm_scale = (reader.physical_pixel_sizes.Z, reader.physical_pixel_sizes.Y, reader.physical_pixel_sizes.X)
        scale = [s * 1000 for s in nm_scale]
        pint_units = pint_ureg("nm")
        units = (pint_units, pint_units, pint_units)
    else:
        scale = reader.physical_pixel_sizes
        pint_units = pint_ureg(original_units)
        units = (pint_units, pint_units, pint_units)


    # Fun side project. # TODO: Add to settings. And take max channel from the max wavelength.
    max_channel = wavelength_luminous_dict["red"]
    napari_gamma_dict = {
        channel: compute_napari_gamma(value, max_channel, 1, 0.30)
        for channel, value in wavelength_luminous_dict.items()
    }

    dict_list = []

    for channel in range(channels):
        metadata_metadata = {}
        for key, data in key_dict.items():
            if data:
                if len(data) == 1:
                    metadata_metadata[key] = data[0].text
                    continue
                if len(data) < channels:
                    raise ValueError(f"Number of entries should be 1 or equal(or more) to the number of channels. Found {len(data)} entries for {key}")
                metadata_metadata[key] = data[channel].text
            else:
                metadata_metadata[key] = None
        colormap = wavelength_to_color[int(metadata_metadata["EmissionWavelength"])]
        try:
            gamma = napari_gamma_dict[colormap.lower()]
        except KeyError:
            gamma = 1
        metadata = {"scale": scale, "units": units, "metadata": metadata_metadata, "blending": "additive", "colormap": colormap, "gamma": gamma}
        dict_list.append(metadata)

    return dict_list
