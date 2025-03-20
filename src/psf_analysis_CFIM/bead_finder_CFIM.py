from typing import Tuple, List

import numpy as np
from scipy.ndimage import median_filter
from skimage.feature import peak_local_max


class BeadFinder:
    def __init__(self, image, scale: tuple, bounding_box: tuple):
        self._debug = True

        self.bounding_box_px = np.array(bounding_box) / np.array(scale)
        self.max_bead_dist = np.linalg.norm(np.array(self.bounding_box_px)) / 2

        self.image = image
        self.scale = scale

        self.yx_border_padding = 2

    """
    A class to find beads in a 3D image stack.

    Attributes:
        image (np.ndarray): The 3D image stack (z, y, x) in pixel units.
        scale (Tuple[float, float, float]): The scale of the image (µm/px).
        bounding_box (Tuple[float, float, float]): The bounding box dimensions (nm).
    """

    def find_beads(self):
        image = self._max_projection()
        image = self._median_filter(image)

        yx_beads, discarded_xy = self._maxima(image)
        zyx_beads, zyx_discarded_beads = self._find_bead_positions(yx_beads)
        # TODO: OPTIMIZE Use a better algorithm for neighbor distance. This one is O(n^2). VERY SLOW.
        # TODO: Keep previously discarded beads to check neighbors
        beads, discarded_beads_by_neighbor_dist = self.filter_beads_by_neighbour_distance(zyx_beads)
        yx_discarded_beads, x = self._find_bead_positions(discarded_xy, no_filter=True) # Convert discarded yx beads to zyx

        # Combine discarded beads TODO: Add lines to visualize discarded beads from neighbor distance
        discarded_beads = zyx_discarded_beads + yx_discarded_beads + discarded_beads_by_neighbor_dist

        if self._debug: # It was really important to color code the output, trust me...
            green = '\033[92m'
            yellow = '\033[93m'
            endc = '\033[0m'

            print(
                f"Beads {green}passed{endc} / {yellow}discarded{endc} \nxy border: {green}{len(yx_beads)}{endc} / {yellow}{len(discarded_xy)}{endc} "
                f"| z border: {green}{len(zyx_beads)}{endc} / {yellow}{len(zyx_discarded_beads)}{endc} | neighbor dist: {green}{len(beads)}{endc} / {yellow}{len(discarded_beads_by_neighbor_dist)}{endc}")
            print(f"Total: {green}{len(beads)}{endc} / {yellow}{len(discarded_beads)}{endc}")

        return beads, discarded_beads

    def get_image(self):
        return self.image

    def get_scale(self):
        return self.scale

    def _max_projection(self):
        return np.max(self.image, axis=0)

    def _median_filter(self, image, size=3):
        return median_filter(image, size=size)

    # TODO: Make threshold a setting with option for rel/abs
    def _maxima(self, image) -> (List[Tuple], List[Tuple]):

        yx_border = (self.bounding_box_px[1] / 2) + self.yx_border_padding
        xy_bead_positions = peak_local_max(image, min_distance=2, threshold_rel=0.3, exclude_border=0)
        xy_bead_positions = [(y, x) for (y, x) in xy_bead_positions]
        in_border_xy_bead_positions = [bead for bead in xy_bead_positions if yx_border < bead[0] < self.image.shape[1] - yx_border and yx_border < bead[1] < self.image.shape[2] - yx_border]
        discarded_beads = [bead for bead in xy_bead_positions if bead not in in_border_xy_bead_positions]

        return in_border_xy_bead_positions, discarded_beads

    def _find_bead_positions(self, xy_beads, no_filter=False):
        bead_pos = []
        discarded_beads = []
        z_border = self.bounding_box_px[0] / 2
        for (y, x) in xy_beads:
            z_profile = self.image[:, y, x]

            z_profile_median = self._median_filter(z_profile, size=2)

            z = np.argmax(z_profile_median)
            if 0 + z_border < z < self.image.shape[0] - z_border or no_filter:
                bead_pos.append((z, y, x))
            else:
                discarded_beads.append((z, y, x))

        return bead_pos, discarded_beads

    def filter_beads_by_neighbour_distance(self, beads):
        discarded_beads = []
        valid_beads = []
        half_box = self.bounding_box_px / 2.0

        for bead in beads:
            is_valid = True
            for neighbour in beads:
                if bead == neighbour:
                    continue
                # Check if each coordinate of neighbour is within bead \+\/\- half_box
                if (bead[0] - half_box[0] <= neighbour[0] <= bead[0] + half_box[0] and
                        bead[1] - half_box[1] <= neighbour[1] <= bead[1] + half_box[1] and
                        bead[2] - half_box[2] <= neighbour[2] <= bead[2] + half_box[2]):
                    is_valid = False
                    break
            if is_valid:
                valid_beads.append(bead)
            else:
                discarded_beads.append(bead)
        return valid_beads, discarded_beads


    def close(self):
        self.image = None
