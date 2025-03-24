# File: tests/fake_viewer.py
from psf_analysis_CFIM.tests.fake_event import FakeEvents
from psf_analysis_CFIM.tests.fake_layer_list import FakeLayerList


# A fake viewer with a layers attribute and events.
class FakeViewer:
    def __init__(self, layers):
        self.layers = FakeLayerList(layers)
        self.events = FakeEvents()

    def add_layer(self, layer):
        self.layers._layers.append(layer)
        self.events.layers_change.emit()