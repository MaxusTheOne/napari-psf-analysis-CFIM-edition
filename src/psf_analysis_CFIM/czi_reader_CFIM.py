from aicsimageio.readers import CziReader
from psf_analysis_CFIM.czi_metadata_processor import extract_key_metadata
import numpy as np


def read_czi(path):
    """Load a .czi file and return the data in a proper callable format."""

    reader = CziReader(path)
    data = reader.data

    # Removing the scene, time, channels. psf can only take 3. extra info can be in metadata
    # This might give an error later
    squeezed_data = np.squeeze(data)

    metadata = extract_key_metadata(reader)

    def _reader_callable(_path=None):
        return [
            (squeezed_data, metadata, "image")  # A tuple -> (data, metadata, layer_type)
        ]

    return _reader_callable