from aicsimageio.readers import CziReader
from napari.utils.notifications import show_warning

from psf_analysis_CFIM.czi_reader.czi_metadata_processor import extract_key_metadata
import numpy as np

from psf_analysis_CFIM.library_workarounds.RangeDict import RangeDict

wavelength_to_color = RangeDict(
            [(380, 450, "Violet"),
             (450, 485, "Blue"),
             (485, 500, "Cyan"),
             (500, 565, "Green"),
             (565, 590, "Yellow"),
             (590, 625, "Orange"),
             (625, 740, "Red")])

def find_in_xml_tree(xml_tree, tag):
    """
        Finds all occurrences of a tag in an XML tree.
    """
    elements = xml_tree.findall(f".//{tag}")
    print(f"Found {len(elements)} occurrences of {tag}")
    return elements


def read_czi(path):
    """
        Loads a .czi file and return the data in a proper callable format.
        Made because I could not get a direct reader to work with napari.

        Parameters:
            path: str -> Path to the .czi file.

        Returns:
            callable -> A callable that returns a list of tuples with the data, metadata and layer type.
                        Required format for napari readers.
    """
    reader = CziReader(path)

    channels = reader.dims.C
    reader_metadata = reader.metadata
    emissions = find_in_xml_tree(reader_metadata, "EmissionWavelength")

    data_list = []
    for channel in range(channels):
        print(channel)

        data = reader.get_image_data("ZYX", T=0, C=channel)




        metadata = extract_key_metadata(reader_metadata, reader)
        wavelength = emissions[channel].text


        metadata["colormap"] = wavelength_to_color[int(wavelength)]

        if not isinstance(metadata, dict):
            print(f"Metadata is not a dictionary: {metadata.__class__}")
            metadata = {"metadata": metadata}  # Wrap in dictionary if necessary
        data_list.append((data, metadata, "image"))

    def _reader_callable(_path=None):
        # A tuple -> (data, metadata, layer_type)
        return data_list


    return _reader_callable