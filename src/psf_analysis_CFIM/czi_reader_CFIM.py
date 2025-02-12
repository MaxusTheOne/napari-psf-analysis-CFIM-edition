from psf_analysis_CFIM.czi_metadata_processor import extract_key_metadata


def read_czi(path):
    """Load a .czi file and return the data in a proper callable format."""
    from aicsimageio.readers import CziReader
    import numpy as np

    # Read the .czi file using the appropriate library
    reader = CziReader(path)
    data = reader.data  # or reader.get_image_data("CZYX")


    # Removing the scene, time, channels. psf can only take 3. extra info can be in metadata
    squeezed_data = np.squeeze(data)

    # If additional metadata is required
    metadata = extract_key_metadata(reader)
    # Napari expects a callable function, so we wrap the returned data
    def _reader_callable(_path=None):
        return [
            (squeezed_data, metadata, "image")  # A tuple -> (data, metadata, layer_type)
        ]

    return _reader_callable