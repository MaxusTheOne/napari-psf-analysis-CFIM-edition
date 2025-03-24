# File: tests/fake_image.py
import uuid
import napari

# A simple fake image layer to simulate napari.layers.Image.
class FakeImage:
    def __init__(self, name):
        self.name = name
        self.unique_id = uuid.uuid4()
        self.selected = False

# For testing purposes, assign FakeImage to napari.layers.Image.
napari.layers.Image = FakeImage