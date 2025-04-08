# python
from typing import overload
from uuid import UUID


class MultiKeyDict:
    def __init__(self, key_names: tuple = ("name", "unique_id", "wavelength")):
        self._by_name = {}
        self._by_uuid = {}
        self._by_wavelength = {}
        self._keys = key_names

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

    def get_all(self,key, value):
        # Return all dicts that have the key-value pair.

        return [entry for entry in self._by_name.values() if entry.get(key, None) == value]


    def has_id(self, uuid: UUID) -> bool:
        return uuid in self._by_uuid


    def to_dict(self):
        return self._by_uuid

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    @overload
    def remove(self, key: str | UUID | int):
        pass
    @overload
    def remove(self, key_list: list[str | UUID | int]):
        pass

    def remove(self, key):
        # If key is a list, remove each item in the list.
        if isinstance(key, list):
            for k in key:
                self.remove(k)
            return

        # Remove the entry from all 3 dictionaries.
        if key in self._by_name:
            uuid = self._by_name[key].get("unique_id")
            wavelength = self._by_name[key].get("wavelength")
            del self._by_name[key]
            del self._by_uuid[uuid]
            del self._by_wavelength[wavelength]
            return

        if key in self._by_uuid:
            name = self._by_uuid[key].get("name")
            wavelength = self._by_uuid[key].get("wavelength")
            del self._by_uuid[key]
            del self._by_name[name]
            del self._by_wavelength[wavelength]
            return

        if key in self._by_wavelength:
            name = self._by_wavelength[key].get("name")
            uuid = self._by_wavelength[key].get("unique_id")
            del self._by_wavelength[key]
            del self._by_name[name]
            del self._by_uuid[uuid]
            return



    def clear(self):
        self._by_name.clear()
        self._by_uuid.clear()
        self._by_wavelength.clear()

    def dump(self, key: UUID | str) -> str:
        # Check if the key is a str. Dump has 2 "modes" depending on key type.
        if isinstance(key, str):
            # In case the key is name, uuid or wavelength, return the corresponding dictionaries.
            result = f"{key} dict:\n"
            # Get the corresponding dictionary.
            _dict = {"name": self._by_name, "unique_id": self._by_uuid, "uuid": self._by_uuid, "wavelength": self._by_wavelength}[key]
            for key, inner_dict in _dict.items():
                # Make a copy so we don't alter the original dictionary.
                inner_copy = inner_dict.copy()
                result += f"{key}: {inner_copy}\n"
            return result


        # Retrieve the entry using the UUID.
        by_uuid_entry = self._by_uuid.get(key)
        if by_uuid_entry is None:
            return f"UUID {key} not found."

        # Get the associated name and wavelength.
        name = by_uuid_entry.get("name")
        wavelength = by_uuid_entry.get("wavelength")

        # Retrieve the corresponding dictionaries.
        by_name_entry = self._by_name.get(name, {})
        by_wavelength_entry = self._by_wavelength.get(wavelength, {})

        result = (
            f"UUID entry: {by_uuid_entry}\n"
            f"Name entry: {by_name_entry}\n"
            f"Wavelength entry: {by_wavelength_entry}\n"
        )
        return result

    def __repr__(self):
        # Return a representation based on one of the dictionaries.
        return f"MultiKeyDict({self._by_name})"

    def __len__(self):
        return len(self._by_name)

    def __next__(self):
        for key in self._by_name:
            yield key

    def __iter__(self):
        return self.__next__()



