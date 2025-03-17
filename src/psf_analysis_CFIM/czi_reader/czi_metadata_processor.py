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
            return result
    return None



wavelength_to_color = RangeDict(
            [(380, 450, "Violet"),
             (450, 485, "Blue"),
             (485, 500, "Cyan"),
             (500, 565, "Green"),
             (565, 590, "Yellow"),
             (590, 625, "Orange"),
             (625, 740, "Red")])


def extract_key_metadata(xml_metadata, reader):
    """
    Extracts a few key metadata fields from the reader's XML metadata and stores them in the metadata property.

    Parameters:
        reader: A CziReader instance that already has its metadata loaded.

    Returns:
        dict: A dictionary with allowed keys for Napari and a nested custom metadata.
    """

    # List the keys of the root element's attributes
    print("All attributes of the XML element:")
    for key in xml_metadata:
        print(f"{key}")
    # Start with keys that Napari is expecting.

    # image_document = xml_metadata["ImageDocument"]
    # _metadata = image_document["Metadata"]
    # display_settings = _metadata["DisplaySettings"]
    # channels = display_settings["Channels"]
    # channel = channels["Channel"]
    # information = _metadata["Information"]
    # image = information["Image"]
    # print(f"Channel: {channel} | Channels: {channels}")

    # Define the mapping between our desired custom keys and the XML tag names.
    key_mapping = {
        "LensNA": "LensNA",
        "CameraName": "CameraName",
        "NominalMagnification": "NominalMagnification",
        "PinholeSizeAiry": "PinholeSizeAiry",
        "ExcitationWavelength": "ExcitationWavelength",
        "EmissionWavelength": "EmissionWavelength",
        "ObjectiveName": "ObjectiveName",
        "OriginalUnits": "DefaultScalingUnit",
    }

    custom_meta = {}


    # If the metadata is already an XML element, search for each tag.
    if isinstance(xml_metadata, ET.Element):
        for custom_key, xml_tag in key_mapping.items():
            print(f"{custom_key} path:", end="")
            found = recursive_find(xml_metadata, xml_tag, 0)
            print("")
            if found is not None and found.text:
                custom_meta[custom_key] = found.text.strip()
            else:
                custom_meta[custom_key] = None  # Or a default value like "Not available"
    else:
        # If it's not an XML Element, store a string version for each.
        for custom_key in key_mapping:
            custom_meta[custom_key] = str(xml_metadata)

    # Convert the scale to nanometers if it's in micrometers.
    try:
        # /Scaling/Items/Distance/DefaultUnitFormat
        # original_units = _metadata["Scaling"]["Items"]["Distance"]["DefaultUnitFormat"]
        original_units = custom_meta["OriginalUnits"]
        print(f"Original units: {original_units}")
        emission_wavelength = int(custom_meta["EmissionWavelength"])
    except KeyError:
        original_units = None
        emission_wavelength = None

    if original_units == "micrometre" or original_units == "µm":
        scale_nm = (reader.physical_pixel_sizes.Z, reader.physical_pixel_sizes.Y, reader.physical_pixel_sizes.X)
        scale = [s * 1000 for s in scale_nm]
        units = "nm"
    else:
        scale = reader.physical_pixel_sizes
        units = original_units



    metadata = {"scale": scale, "units": units, "metadata": custom_meta, "blending": "additive"}

    # Nest the custom metadata under a single key.
    return metadata
