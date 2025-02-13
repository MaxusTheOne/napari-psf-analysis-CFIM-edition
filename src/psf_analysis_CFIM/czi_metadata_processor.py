import xml.etree.ElementTree as ET


def recursive_find(element, tag):
    """
    Recursively searches for the first occurrence of an element with the given tag.
    """
    if element.tag == tag:
        return element
    for child in element:
        result = recursive_find(child, tag)
        if result is not None:
            return result
    return None


def extract_key_metadata(reader):
    """
    Extracts a few key metadata fields from the reader's XML metadata and returns a
    metadata dictionary that nests these values under 'metadataToStore'.

    Expected mapping:
        "NA"             <- value from XML tag "LensNA"
        "MicroscopeType" <- value from XML tag "CameraName"
        "Magnification"  <- value from XML tag "NominalMagnification"

    Parameters:
        reader: A CziReader instance that already has its metadata loaded.

    Returns:
        dict: A dictionary with allowed keys for Napari and a nested custom metadata.
    """
    # Start with keys that Napari is expecting.
    metadata = {
        "scale": reader.physical_pixel_sizes,
        "units": "nanometer"
        # You can add any other top-level keys Napari supports, e.g. "name", "colormap", etc.
    }

    # Define the mapping between our desired custom keys and the XML tag names.
    key_mapping = {
        "NA": "LensNA",
        "MicroscopeType": "CameraName",
        "Magnification": "NominalMagnification",
        "AiryUnit": "PinholeSizeAiry",
        "Excitation": "ExcitationWavelength",
        "Emission": "EmissionWavelength",
        "objectiveID": "ObjectiveName",
    }

    custom_meta = {}
    xml_meta = reader.metadata

    # If the metadata is already an XML element, search for each tag.
    if isinstance(xml_meta, ET.Element):
        for custom_key, xml_tag in key_mapping.items():
            found = recursive_find(xml_meta, xml_tag)
            if found is not None and found.text:
                custom_meta[custom_key] = found.text.strip()
            else:
                custom_meta[custom_key] = None  # Or a default value like "Not available"
    else:
        # If it's not an XML Element, store a string version for each.
        for custom_key in key_mapping:
            custom_meta[custom_key] = str(xml_meta)

    # Nest the custom metadata under a single key.
    metadata["metadata"] = custom_meta
    return metadata
