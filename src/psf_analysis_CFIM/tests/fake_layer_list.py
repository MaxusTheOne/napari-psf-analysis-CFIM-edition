# File: tests/fake_layer_list.py
# A fake layer list that supports indexing by int and by name.
class FakeLayerList:
    def __init__(self, layers):
        self._layers = layers

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._layers[key]
        elif isinstance(key, str):
            for layer in self._layers:
                if layer.name == key:
                    return layer
            raise KeyError(f"No layer with name {key}")
        else:
            raise KeyError("Invalid key type. Must be int or str.")

    def __iter__(self):
        return iter(self._layers)

    def __len__(self):
        return len(self._layers)