import numpy as np
import matplotlib.colors as mcolors
import napari

# Define a segmented colormap.
# Here we set a “plateau” for the low end (from 0 to a small fraction, e.g. 0.01, representing 0 and 1)
# and then a transition to red at the upper end (normalized intensity of 1).
cdict = {
    'red':   [(0.0, 0.0, 0.0),
              (0.01, 0.0, 0.0),
              (1.0, 1.0, 1.0)],
    'green': [(0.0, 0.0, 0.0),
              (0.01, 0.0, 0.0),
              (1.0, 0.0, 0.0)],
    'blue':  [(0.0, 1.0, 1.0),
              (0.01, 1.0, 1.0),
              (1.0, 0.0, 0.0)]
}

custom_cmap = mcolors.LinearSegmentedColormap('custom_cmap', segmentdata=cdict, N=256)

# Assume 'image' is your numpy array image data.
viewer = napari.Viewer()
viewer.add_image(image, colormap=custom_cmap, contrast_limits=[0, image.max()])
