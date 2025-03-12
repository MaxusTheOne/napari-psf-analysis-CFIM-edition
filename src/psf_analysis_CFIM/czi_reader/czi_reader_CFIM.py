from aicsimageio.readers import CziReader
from napari.utils.notifications import show_warning

from psf_analysis_CFIM.czi_reader.czi_metadata_processor import extract_key_metadata
import numpy as np


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
    if len(reader.scenes) > 1:
        show_warning("Multiple scenes found | Only the first scene will be loaded.")
        data = reader.data[0]
    else:
        data = reader.data[0]

    # Removing the scene, time, channels. psf can only take 3. extra info can be in metadata
    # This might give an error later
    squeezed_data = np.squeeze(data)
    metadata = extract_key_metadata(reader)

    def _reader_callable(_path=None):
        return [
            (squeezed_data, metadata, "image")  # A tuple -> (data, metadata, layer_type)
        ]

    return _reader_callable