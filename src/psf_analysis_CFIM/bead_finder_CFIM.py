import numpy as np
from scipy.ndimage import median_filter
from skimage.feature import peak_local_max


class BeadFinder():
    def __init__(self, image, scale):
        self.image = image
        self.scale = scale

        self._border = 10

    def get_image(self):
        return self.image

    def get_scale(self):
        return self.scale

    def _max_projection(self):
        return np.max(self.image, axis=0)

    def _median_filter(self, image):
        return median_filter(image, size=3)

    # TODO: Dynamically find threshold or make it a parameter/config
    def _maxima(self, image):
        return peak_local_max(image, min_distance=2, threshold_abs=3000, exclude_border=self._border)

    def _find_bead_positions(self, xy_beads):
        bead_pos = []
        for (y, x) in xy_beads:
            z_profile = self.image[:, y, x]

            z_profile_median = self._median_filter(z_profile)

            z = np.argmax(z_profile_median)
            if 0 + self._border < z < self.image.shape[0] - self._border:
                bead_pos.append((z, y, x))
        return bead_pos


    def find_beads(self):
        image = self._max_projection()
        image = self._median_filter(image)
        xy_beads = self._maxima(image)
        print("Found xy_beads:", len(xy_beads))
        beads = self._find_bead_positions(xy_beads)
        print("Found beads:", len(beads))
        return beads

    def close(self):
        self.image = None
