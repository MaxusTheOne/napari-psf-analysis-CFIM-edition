import napari
import numpy as np
from qtpy.QtWidgets import QWidget, QPushButton, QVBoxLayout
from aicsimageio.readers import CziReader
from matplotlib import pyplot as plt
from napari.utils import Colormap
import matplotlib

# TODO: Remove dependency on main widget being passed, instead get an event for image change
class ToggleRangeIndicator(QWidget):
    def __init__(self, main_widget,parent=None):
        super().__init__(parent)
        self._viewer = main_widget._viewer
        self.psf_analysis_widget = main_widget

    def init_ui(self):

        self.button = QPushButton("Toggle Range Indicator")
        self.button.clicked.connect(self.toggle_range_indicator)
        return self.button

    def toggle_range_indicator(self):
        layer = self.psf_analysis_widget.get_current_img_layer()
        # Check if the colormap ends with "_range_indicator"
        if layer.colormap.name.endswith("_range_indicator"):
            # Remove the "_range_indicator" suffix
            layer.colormap = layer.colormap.name.replace("_range_indicator", "")
        else:
            range_indicator_cmap = add_range_indicator_to_colormap(
                layer.colormap, min_color=(0, 0, 1, 1), max_color=(1, 0, 0, 1)
            )
            layer.colormap = range_indicator_cmap

def plot_mpl_colormap(mpl_cmap, n=256):
    """
    Displays a horizontal gradient of a matplotlib colormap.
    """
    # Make a 2D gradient from 0..1
    gradient = np.linspace(0, 1, n)
    gradient = np.vstack((gradient, gradient))  # shape (2, n)

    fig, ax = plt.subplots(figsize=(6, 1))
    ax.imshow(gradient, aspect='auto', cmap=mpl_cmap)
    ax.set_axis_off()
    plt.show()

def plot_napari_colormap(napari_cmap):
    """
    Displays a horizontal gradient of a napari Colormap by converting it
    to a matplotlib ListedColormap.
    """
    # napari_cmap.colors is an Nx4 array of RGBA
    arr = np.array(napari_cmap.colors)
    mpl_cmap = matplotlib.colors.ListedColormap(arr, name=napari_cmap.name)
    plot_mpl_colormap(mpl_cmap)  # use the function from above


def plot_mpl_colormap(mpl_cmap, n=256):
    """
    Displays a horizontal gradient of a matplotlib colormap.
    """
    # Make a 2D gradient from 0..1
    gradient = np.linspace(0, 1, n)
    gradient = np.vstack((gradient, gradient))  # shape (2, n)

    fig, ax = plt.subplots(figsize=(6, 1))
    ax.imshow(gradient, aspect='auto', cmap=mpl_cmap)
    ax.set_axis_off()
    plt.show()

def add_range_indicator_to_colormap(
    cmap,
    min_color=(0, 0, 1, 1),  # RGBA for "blue"
    max_color=(1, 0, 0, 1),  # RGBA for "red"
    n_colors=65536
):
    """
    Returns a new napari Colormap that is identical to the input colormap,
    except the minimum value is forced to `min_color` and the maximum value
    is forced to `max_color`.

    Parameters
    ----------
    cmap : str, matplotlib.colors.Colormap, or napari.utils.Colormap
        The input colormap. Can be a named matplotlib colormap (e.g. "viridis"),
        a matplotlib.colors.Colormap object, or a napari.utils.Colormap object.
    min_color : tuple of float
        RGBA values for the minimum color. Defaults to pure blue (0, 0, 1, 1).
    max_color : tuple of float
        RGBA values for the maximum color. Defaults to pure red (1, 0, 0, 1).
    n_colors : int
        Number of color samples to take from the original colormap. Defaults to 256.

    Returns
    -------
    napari_cmap : napari.utils.Colormap
        A new napari Colormap object with forced min/max colors.
    """
    print(f"Original type: {type(cmap)}")

    # 1. Convert the input `cmap` to a matplotlib.colors.Colormap if necessary
    if isinstance(cmap, str):
        # Treat `cmap` as a named matplotlib colormap
        mpl_cmap = plt.get_cmap(cmap)
    elif isinstance(cmap, matplotlib.colors.Colormap):
        mpl_cmap = cmap
    elif isinstance(cmap, Colormap):
        # Already a napari Colormap: let's extract its RGBA array and rebuild as a mpl colormap
        arr = np.array(cmap.colors)
        mpl_cmap = matplotlib.colors.ListedColormap(arr, name=cmap.name)
    else:
        raise TypeError(
            "cmap must be a string, a matplotlib.colors.Colormap, or a napari.utils.Colormap."
        )

    # 2. Sample the original colormap in [0..1] range
    rgba_array = mpl_cmap(np.linspace(0, 1, n_colors))
    plot_napari_colormap(mpl_cmap)

    # 3. Force the first color (min) and last color (max)
    rgba_array[0] = min_color
    rgba_array[-1] = max_color

    # 4. Convert the modified RGBA array into a napari Colormap
    napari_cmap_rain = Colormap(name=f"{mpl_cmap.name}_range_indicator", colors=rgba_array)

    plot_napari_colormap(napari_cmap_rain)
    print(f"Colormap length: {len(napari_cmap_rain.colors)}")

    return napari_cmap_rain
