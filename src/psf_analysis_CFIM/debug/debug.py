import os
from typing import overload

import numpy as np
from napari.utils.theme import opacity
from qtpy.QtCore import QObject, Signal
from scipy import spatial
from vispy.visuals import LineVisual

from psf_analysis_CFIM.debug import global_vars


class DebugEmitter(QObject):
    save_debug = Signal(object, str)

def report_error_debug(message, msg_type="message"):
    debug_emitter.save_debug.emit(message, msg_type)

debug_emitter = DebugEmitter()

# TODO: Flush out the potential features for dedicated debug class
class DebugClass:
    """
        Holds methods for debugging and visualizing data and processes.

        Is instantiated in napari console when PSF_ANALYSIS_CFIM_DEBUG == "1"
        Because of this, all methods should be callable from the console.

    """
    # region Initialization
    def __init__(self, viewer):
        self.errors: list[tuple[any, str]] = []
        self.error_amount = 0
        self._viewer = viewer
        self._widget = None
        self._bead_layer = None
        self._shape_layer = None
        self._surface_layer = None

        global_vars.debug_instance = self

        debug_emitter.save_debug.connect(self.save_debug)

    def set_PSFAnalysis_instance(self, widget):
        self._widget = widget

    def save_debug(self, message, msg_type):
        self.error_amount += 1
        self.errors.append((message, msg_type))

    # endregion
    # region Visualization | 3D

    def show_3d_array(self, index):
        self._viewer.add_image(self.get(index))

    @overload
    def add_nm_point(self, point: tuple[float, float, float]):
        pass

    @overload
    def add_nm_point(self, z: float, y: float, x: float):
        pass


    def add_nm_point(self, *args):
        if len(args) == 1:
            point = args[0]
        else:
            point = (args[0], args[1], args[2])
        scaled_point = point / self._widget.get_scale()
        self._viewer.add_points(scaled_point, size=10, face_color='violet', name="nm_point", scale=self._widget.get_scale())

    def show_psf_box(self, index):
        if self._set_bead_point_layer():
            point = self._bead_layer.data[index]
            self._add_bounding_box(point)

    def _add_bounding_box(self, point: tuple[float, float, float], *, bounding_box_dims=None):
        if bounding_box_dims is None:
            bounding_box_dims = self._widget.get_bounding_box_px()

        # surface_layer = self._get_surface_layer()

        half_bbox = (bounding_box_dims[0] / 2, bounding_box_dims[1] / 2, bounding_box_dims[2] / 2)

        # Adjust vertices to be centered around the given point and scale them
        vertices = np.array([
            [point[0] - half_bbox[0], point[1] - half_bbox[1], point[2] - half_bbox[2]],
            [point[0] - half_bbox[0], point[1] - half_bbox[1], point[2] + half_bbox[2]],
            [point[0] - half_bbox[0], point[1] + half_bbox[1], point[2] - half_bbox[2]],
            [point[0] - half_bbox[0], point[1] + half_bbox[1], point[2] + half_bbox[2]],
            [point[0] + half_bbox[0], point[1] - half_bbox[1], point[2] - half_bbox[2]],
            [point[0] + half_bbox[0], point[1] - half_bbox[1], point[2] + half_bbox[2]],
            [point[0] + half_bbox[0], point[1] + half_bbox[1], point[2] - half_bbox[2]],
            [point[0] + half_bbox[0], point[1] + half_bbox[1], point[2] + half_bbox[2]]
        ]) * self._widget.get_scale()

        hull = spatial.ConvexHull(vertices)
        surface = (hull.points, hull.simplices)

        if self._surface_layer is None:
            self._surface_layer = self._viewer.add_surface(surface, opacity=0, name="bbox_surface", wireframe={'visible': True, 'color': 'red'})
        else:
            self._surface_layer.data = surface
        # else: # TODO: Figure out how to add multiple surfaces to the same layer
        #     data = self._surface_layer.data
        #     data = np.array(data[0])
        #     data = np.concatenate((data, surface), axis=0)
        #     self._surface_layer.data = data


    def _draw_bounding_box(self, min_coord, max_coord):
        """
            Returns a list of line visuals representing the edges of a bounding box.
        """
        box = [
            [min_coord, [min_coord[0], min_coord[1], max_coord[2]]],
            [min_coord, [min_coord[0], max_coord[1], min_coord[2]]],
            [min_coord, [max_coord[0], min_coord[1], min_coord[2]]],
            [max_coord, [max_coord[0], max_coord[1], min_coord[2]]],
            [max_coord, [max_coord[0], min_coord[1], max_coord[2]]],
            [max_coord, [min_coord[0], max_coord[1], max_coord[2]]],
            [[max_coord[0], min_coord[1], min_coord[2]], [max_coord[0], max_coord[1], min_coord[2]]],
            [[max_coord[0], min_coord[1], min_coord[2]], [max_coord[0], min_coord[1], max_coord[2]]],
            [[min_coord[0], max_coord[1], min_coord[2]], [min_coord[0], max_coord[1], max_coord[2]]],
            [[min_coord[0], min_coord[1], max_coord[2]], [min_coord[0], max_coord[1], max_coord[2]]],
            [[min_coord[0], min_coord[1], max_coord[2]], [max_coord[0], min_coord[1], max_coord[2]]],
            [[min_coord[0], max_coord[1], min_coord[2]], [max_coord[0], max_coord[1], min_coord[2]]]
        ]
        return box

    def _draw_vertices_box(self, min_coord, max_coord):
        # vertices are generated according to the following scheme:
        #    5-------7
        #   /|      /|
        #  1-------3 |
        #  | |     | |
        #  | 4-----|-6
        #  |/      |/
        #  0-------2
        vertices = [
            min_coord,
            [max_coord[0], min_coord[1], min_coord[2]],
            [min_coord[0], min_coord[1], max_coord[2]],
            [max_coord[0], min_coord[1], max_coord[2]],
            [min_coord[0], max_coord[1], min_coord[2]],
            [max_coord[0], max_coord[1], min_coord[2]],
            [min_coord[0], max_coord[1], max_coord[2]],
            max_coord
        ]
        return vertices


    def _add_wireframe(self, min_coord, max_coord):
        """
            Add a wireframe box to the viewer.

            Parameters:
                min_coord (tuple): The minimum coordinates of the box (x, y, z)
                max_coord (tuple): The maximum coordinates of the box (x, y, z)
        """

        # Define the 8 vertices of the box using the min and max coordinates
        vertices = np.array([
            [min_coord[0], min_coord[1], min_coord[2]],
            [max_coord[0], min_coord[1], min_coord[2]],
            [max_coord[0], max_coord[1], min_coord[2]],
            [min_coord[0], max_coord[1], min_coord[2]],
            [min_coord[0], min_coord[1], max_coord[2]],
            [max_coord[0], min_coord[1], max_coord[2]],
            [max_coord[0], max_coord[1], max_coord[2]],
            [min_coord[0], max_coord[1], max_coord[2]],
        ])

        # Define the edges of the box as pairs of vertex indices
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # bottom face
            [4, 5], [5, 6], [6, 7], [7, 4],  # top face
            [0, 4], [1, 5], [2, 6], [3, 7]  # vertical edges
        ]

        # Create segments for each edge (each segment is a pair of coordinates)
        segments = np.array([[vertices[i], vertices[j]] for i, j in edges])


        # Add the segments as a shapes layer (using 'line' type for wireframe)
        self._viewer.add_shapes(
            segments,
            shape_type='line',
            edge_color='red',
            face_color='transparent',
            scale=self._scale
        )
    # endregion
    # region Helper methods
    def get(self, index):
        return self.errors[index]

    def _get_shape_layer(self):
        layer_name = "Shapes"
        scale = self._widget.get_scale()

        if self._shape_layer is None:
            self._shape_layer = self._viewer.add_shapes(np.empty((0, 3)), ndim=3, name=layer_name, scale=scale)

        return self._shape_layer

    def _get_shape_points_layer(self):
        layer_name = "Shape Points"
        scale = self._widget.get_scale()

        if self._shape_points_layer is None:
            self._shape_points_layer = self._viewer.add_points(np.empty((0, 3)), ndim=3, name=layer_name, scale=scale
                                                               ,face_color='blue', border_color = "blue" ,size=2)

        return self._shape_points_layer

    def _get_surface_layer(self):
        layer_name = "bbox_surface"

        if self._shape_layer is None:
            self._shape_layer = self._viewer.add_surface(np.empty((0, 3)), name=layer_name)

        return self._shape_layer

    def _set_bead_point_layer(self):
        """
            Gets the selected bead layer from PSFAnalysis widget and sets it to self._bead_layer
        """
        layer = self._widget.get_current_points_layer()
        if layer is None:
            print("No bead layer selected.")
            return None
        if layer == self._bead_layer:
            return True
        self._bead_layer = layer
        return True

    def say_hello(self):
        return "Hello from Debug!"
    # endregion

    # region tests
    def test_type(self, index):
        # Language: python
        error = self.get(0)  # Get the error record
        data = error[0]       # Data to be saved

        print("Type of data:", type(data))
        if hasattr(data, "shape"):
            print("Shape of data:", data.shape)
        else:
            print("Data does not have a shape attribute")

        # Optionally, print first few elements if it is a sequence
        if hasattr(data, "__iter__"):
            print("Data sample:", list(data)[:5])
        else:
            print("Data is not iterable.")

    # endregion
    def save(self, index, *, overwrite_type=None):
        output_folder = "saved_debug"
        error = self.get(index)
        data =  error[0]
        msg_type = overwrite_type if overwrite_type else error[1] # One-liner for overwrite

        # Make directory if needed
        os.makedirs(output_folder, exist_ok=True)

        if msg_type == "3d_array":
            np.save(f"{output_folder}/debug_{index}.npy", error[0])
        elif msg_type == "message":
            with open(f"{output_folder}/debug_{index}.txt", "w") as f:
                f.write(str(data))
        else:
            print(f"Unknown message type: {msg_type}")


