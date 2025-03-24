# File: tests/test_image_interaction_manager.py
import unittest
import uuid
from PyQt5.QtWidgets import QApplication
import napari

# Import the ImageInteractionManager from your project.
from psf_analysis_CFIM.image_selector_dropdown import ImageInteractionManager
from psf_analysis_CFIM.tests.fake_image import FakeImage
from psf_analysis_CFIM.tests.fake_viewer import FakeViewer

# Instantiate QApplication if not already created.
app = QApplication.instance() or QApplication([])

class TestImageInteractionManager(unittest.TestCase):

    def setUp(self):
        # Create three fake image layers.
        self.image1 = FakeImage("Image 1")
        self.image2 = FakeImage("Image 2")
        self.image3 = FakeImage("Image 3")

        # Create a fake viewer with these layers.
        self.viewer = FakeViewer([self.image1, self.image2, self.image3])

        # Create an instance of ImageInteractionManager with our fake viewer.
        self.manager = ImageInteractionManager(viewer=self.viewer)

        # Manually trigger the layers_change event to update references.
        self.viewer.events.layers_change.emit()

    def test_update_image_references(self):
        self.manager.update_image_references()
        # Check that image_selection_reference has been populated for each image.
        self.assertEqual(len(self.manager.image_selection_reference), 3)
        ref = self.manager.image_selection_reference[0]
        self.assertIn("name", ref)
        self.assertIn("unique_id", ref)
        self.assertIn("index", ref)
        self.assertEqual(ref["name"], "Image 1")

    def test_get_image_by_index_and_name(self):
        # Test get_image using an integer index.
        img = self.manager.get_image(1)
        self.assertEqual(img.name, "Image 2")
        # Test get_image using a name.
        img = self.manager.get_image("Image 3")
        self.assertEqual(img.name, "Image 3")
        # Test invalid type returns ValueError.
        with self.assertRaises(ValueError):
            self.manager.get_image(3.14)

    def test_get_image_index(self):
        self.manager.update_image_references()
        index = self.manager.get_image_index("Image 2")
        self.assertEqual(index, 1)
        index = self.manager.get_image_index("Nonexistent")
        self.assertEqual(index, -1)

    def test_get_images(self):
        # Test get_images with a list of names.
        test_images = ["Image 1", "Image 3"]
        images = self.manager.get_images(test_images)
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].name, "Image 1")
        self.assertEqual(images[1].name, "Image 3")
        # Test get_images with a list of indexes.
        images = self.manager.get_images([0, 2])
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].name, "Image 1")
        self.assertEqual(images[1].name, "Image 3")
        # Test invalid argument type.
        with self.assertRaises(ValueError):
            self.manager.get_images("Image 1")

if __name__ == "__main__":
    unittest.main()