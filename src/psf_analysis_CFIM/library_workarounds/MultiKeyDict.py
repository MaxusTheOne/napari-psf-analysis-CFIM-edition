# python
class MultiKeyDict:
    def __init__(self):
        self._by_name = {}
        self._by_uuid = {}
        self._by_wavelength = {}

    def __setitem__(self, keys, value):
        # Expecting keys as a tuple of (name, unique_id, wavelength)
        name, unique_id, wavelength = keys
        if isinstance(value, dict):
            value["name"] = name
            value["unique_id"] = unique_id
            value["wavelength"] = wavelength
        self._by_name[name] = value
        self._by_uuid[unique_id] = value
        self._by_wavelength[wavelength] = value


    def __getitem__(self, key):
        # Try to look up the key in all dictionaries.
        if key in self._by_name:
            return self._by_name[key]
        if key in self._by_uuid:
            return self._by_uuid[key]
        if key in self._by_wavelength:
            return self._by_wavelength[key]
        raise KeyError(f"Key {key} not found.")

    def clear(self):
        self._by_name.clear()
        self._by_uuid.clear()
        self._by_wavelength.clear()

    def __repr__(self):
        # Return a representation based on one of the dictionaries.
        return f"MultiKeyDict({self._by_name})"