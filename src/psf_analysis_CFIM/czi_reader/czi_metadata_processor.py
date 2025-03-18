import warnings
import xml.etree.ElementTree as ET

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
    # Define the keys to extract from the metadata
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
        original_units = "µm"

    if original_units == "micrometre" or original_units == "µm":
        nm_scale = (reader.physical_pixel_sizes.Z, reader.physical_pixel_sizes.Y, reader.physical_pixel_sizes.X)
        scale = [s * 1000 for s in nm_scale]
        units = "nm"
    else:
        scale = reader.physical_pixel_sizes
        units = original_units


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
        metadata = {"scale": scale, "units": units, "metadata": metadata_metadata, "blending": "additive", "colormap": colormap}
        print(f"Metadata for channel {channel}: {metadata}")
        dict_list.append(metadata)

    return dict_list
