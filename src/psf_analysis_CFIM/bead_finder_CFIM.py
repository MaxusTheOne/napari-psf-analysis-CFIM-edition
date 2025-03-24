from typing import Tuple, List

import numpy as np
from scipy.ndimage import median_filter
from skimage.feature import peak_local_max


class BeadFinder:
    def __init__(self, image_layers, scale: tuple, bounding_box: tuple):
        self._debug = True

        self.bounding_box_px = np.array(bounding_box) / np.array(scale)
        self.max_bead_dist = np.linalg.norm(np.array(self.bounding_box_px)) / 2

        self.images_list = image_layers
        self.scale = scale

        self.yx_border_padding = 2 # TODO: Add to settings
        self.z_border_padding = 0

        self.maxima_rel = 0.3
        self.maxima_abs = 0

        self.passed_bead_count = [0, 0, 0]
        self.discarded_bead_count = [0, 0, 0]


    """
       A class for finding approximate bead positions in a 3D image stack.
       
        Parameters:
        - images_list: A list of napari image layers. 
            Multiple layers are assumed to be different channels / wavelengths.
            Single layers don't get a wavelength assigned.
        - scale: A tuple of 3 floats representing the pixel size for display in napari.
        - bounding_box: tuple[int, int, int] -> represent the psf box in nm.
        
        Returns:
        - A list of dicts, 
            points: list[tuple(z, y, x) for found beads, 
            discarded: list[tuple(z, y, x) for discarded beads,
            wavelength: an int, for identifying the channel.
    """

    def find_beads(self):
        total_beads = []
        total_discarded_beads = []
        channels_beads_dicts = []


        for image_layer in self.images_list:
            try:
                wavelength = image_layer.metadata["EmissionWavelength"]
            except KeyError:
                wavelength = None

            beads, discarded_beads = self.find_beads_for_channel(image_layer.data)

            total_beads += beads
            total_discarded_beads += discarded_beads

            channel_beads_dict = {
                "points": beads,
                "discarded": discarded_beads,
                "wavelength": wavelength
            }

            channels_beads_dicts.append(channel_beads_dict)

        if self._debug: # It was really important to color code the output, trust me...
            green = '\033[92m'
            yellow = '\033[93m'
            endc = '\033[0m'

            print(
                f"Beads {green}passed{endc} / {yellow}discarded{endc} of {len(self.images_list)} color channel{"s" if len(self.images_list) > 1 else ""} \nxy border: {green}{self.passed_bead_count[0]}{endc} / {yellow}{self.discarded_bead_count[0]}{endc} "
                f"| z border: {green}{self.passed_bead_count[1]}{endc} / {yellow}{self.discarded_bead_count[1]}{endc} | neighbor dist: {green}{self.passed_bead_count[2]}{endc} / {yellow}{self.discarded_bead_count[2]}{endc}")
            print(f"Total: {green}{len(total_beads)}{endc} / {yellow}{len(total_discarded_beads)}{endc}")
        return channels_beads_dicts

    def find_beads_for_channel(self, channel_image):
        median_image = self._median_filter(self._max_projection(channel_image))

        yx_beads, discarded_xy = self._maxima(median_image, channel_image)
        zyx_beads, zyx_discarded_beads = self._find_bead_positions(channel_image, yx_beads)

        beads, discarded_beads_by_neighbor_dist = self.filter_beads_by_neighbour_distance(zyx_beads, zyx_discarded_beads)
        yx_discarded_beads, x = self._find_bead_positions(channel_image, discarded_xy, no_filter=True) # Convert discarded yx beads to zyx

        # Combine discarded beads TODO: Add lines to visualize discarded beads from neighbor distance

        if self._debug:
            self.passed_bead_count = [len(zyx_beads), len(yx_beads), len(beads)]
            self.discarded_bead_count = [len(discarded_xy), len(zyx_discarded_beads), len(discarded_beads_by_neighbor_dist)]

        discarded_beads = zyx_discarded_beads + yx_discarded_beads + discarded_beads_by_neighbor_dist
        return beads, discarded_beads

    def get_image(self):
        return self.image

    def get_scale(self):
        return self.scale

    def _max_projection(self, image=None):
        return np.max(image, axis=0)

    def _median_filter(self, image, size=3):
        return median_filter(image, size=size)

    # TODO: Make threshold a setting with option for rel/abs
    def _maxima(self, image, channel_image) -> (List[Tuple], List[Tuple]):

        yx_border = (self.bounding_box_px[1] / 2) + self.yx_border_padding
        image_size = channel_image.shape
        xy_bead_positions = peak_local_max(image, min_distance=2, threshold_rel=self.maxima_rel, threshold_abs=self.maxima_abs, exclude_border=0)
        xy_bead_positions = [(y, x) for (y, x) in xy_bead_positions]
        in_border_xy_bead_positions = [bead for bead in xy_bead_positions if yx_border < bead[0] < image_size[1] - yx_border and yx_border < bead[1] < image_size[2] - yx_border]
        discarded_beads = [bead for bead in xy_bead_positions if bead not in in_border_xy_bead_positions]

        return in_border_xy_bead_positions, discarded_beads

    def _find_bead_positions(self, image, xy_beads, no_filter=False):
        bead_pos = []
        discarded_beads = []
        z_border = self.bounding_box_px[0] / 2
        for (y, x) in xy_beads:
            z_profile = image[:, y, x]

            z_profile_median = self._median_filter(z_profile, size=2)

            z = np.argmax(z_profile_median)
            if 0 + z_border < z < image.shape[0] - z_border or no_filter:
                bead_pos.append((z, y, x))
            else:
                discarded_beads.append((z, y, x))

        return bead_pos, discarded_beads

    def filter_beads_by_neighbour_distance(self, beads, discarded_beads):
        discarded_beads = []
        valid_beads = []
        half_box = self.bounding_box_px / 2.0

        all_beads = beads + discarded_beads
        for bead in beads:
            is_valid = True
            for neighbour in all_beads:
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


    def set_settings(self, settings_dict):
        self.yx_border_padding = settings_dict['yx_border_padding']
        self.z_border_padding = settings_dict['z_border_padding']
        self.maxima_rel = settings_dict['maxima_relative']
        self.maxima_abs = settings_dict['maxima_absolute']
        self.max_bead_dist = settings_dict['max_bead_distance']
