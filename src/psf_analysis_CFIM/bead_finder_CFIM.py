from typing import Tuple, List

import numpy as np
from scipy.ndimage import median_filter
from skimage.feature import peak_local_max

from psf_analysis_CFIM.error_display_widget import report_warning


class BeadFinder:
    def __init__(self, image, scale: tuple, bounding_box: tuple):
        self._debug = False
        self.image = image
        self.scale = scale
        self._border = 5
        self._bounding_box = bounding_box / np.array(scale)
        self.max_bead_dist = np.linalg.norm(np.array(bounding_box))
        print(f"Max bead distance: {self.max_bead_dist}")
    def find_beads(self):
        image = self._max_projection()
        image = self._median_filter(image)

        xy_beads, discarded_xy = self._maxima(image)
        beads, discarded_beads = self._find_bead_positions(xy_beads)
        xy_discarded_beads, x = self._find_bead_positions(discarded_xy, no_filter=True)
        discarded_beads = discarded_beads + xy_discarded_beads

        beads, discarded_beads_by_neighbor_dist = self.filter_beads_by_neighbour_distance(beads)

        if self._debug: print(f"Beads inside border: {len(beads)} | Discarded beads: {len(discarded_beads)} | Total beads: {len(beads) + len(discarded_beads)} ")

        return beads, discarded_beads

    def get_image(self):
        return self.image

    def get_scale(self):
        return self.scale

    def _max_projection(self):
        return np.max(self.image, axis=0)

    def _median_filter(self, image, size=3):
        return median_filter(image, size=size)

    # TODO: Dynamically find threshold or make it a parameter/config
    def _maxima(self, image) -> (List[Tuple], List[Tuple]):
        xy_bead_positions = peak_local_max(image, min_distance=2, threshold_abs=3000, exclude_border=0)
        xy_bead_positions = [(y, x) for (y, x) in xy_bead_positions]
        in_border_xy_bead_positions = [bead for bead in xy_bead_positions if self._border < bead[0] < self.image.shape[1] - self._border and self._border < bead[1] < self.image.shape[2] - self._border]
        discarded_beads = [bead for bead in xy_bead_positions if bead not in in_border_xy_bead_positions]
        return in_border_xy_bead_positions, discarded_beads

    def _find_bead_positions(self, xy_beads, no_filter=False):
        bead_pos = []
        discarded_beads = []
        for (y, x) in xy_beads:
            z_profile = self.image[:, y, x]

            z_profile_median = self._median_filter(z_profile, size=2)

            z = np.argmax(z_profile_median)
            if 0 + self._border < z < self.image.shape[0] - self._border or no_filter:
                bead_pos.append((z, y, x))
            else:
                discarded_beads.append((z, y, x))

        return bead_pos, discarded_beads

    def filter_beads_by_neighbour_distance(self, beads):
        discarded_beads = []
        valid_beads = []
        for bead in beads:
            smallest_distance = np.inf
            for neighbour in beads:
                if bead == neighbour:
                    continue
                distance = np.linalg.norm(np.array(bead) - np.array(neighbour))
                if distance < smallest_distance:
                    smallest_distance = distance
            if smallest_distance > 5:
                valid_beads.append(bead)
            else:
                discarded_beads.append(bead)
        return valid_beads, discarded_beads


    def close(self):
        self.image = None
