import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QWidget, QPushButton
from napari.utils.colormaps import Colormap

# TODO: Remove dependency on main widget being passed, instead get an event for image change
class ToggleRangeIndicator(QWidget):
    def __init__(self, main_widget,parent=None):
        super().__init__(parent)
        self._viewer = main_widget.viewer
        self.psf_analysis_widget = main_widget

    def init_ui(self):

        self.button = QPushButton("Toggle Range Indicator")
        self.button.clicked.connect(self.toggle_range_indicator)
        return self.button
    # TODO: Fix what is making the range indicator be applied to 0-64 and max-64 instead of 0 and max
    def toggle_range_indicator(self):
        layer = self.psf_analysis_widget.get_current_img_layer()
        # Check if the colormap ends with "_range_indicator"
        if layer.colormap.name.endswith("_range_indicator"):
            # Remove the "_range_indicator" suffix
            layer.colormap = layer.colormap.name.replace("_range_indicator", "")
        else:
            range_indicator_cmap = range_indicator_colormap_from_proxy(
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


def get_rgba_array(cmap, n_colors=256):
    """
    Attempt to extract an RGBA array from a colormap.
    Works with a matplotlib colormap or a napari colormap (even if wrapped in a PublicOnlyProxy).
    """
    # If cmap is callable, try calling it directly.
    if callable(cmap):
        return cmap(np.linspace(0, 1, n_colors))

    # If not callable, check for a __wrapped__ attribute (PublicOnlyProxy usually provides it)
    if hasattr(cmap, '__wrapped__'):
        underlying = cmap.__wrapped__
        if callable(underlying):
            return underlying(np.linspace(0, 1, n_colors))
        elif hasattr(underlying, 'colors'):
            return np.array(underlying.colors)

    # If still not, try to directly access a "colors" attribute.
    try:
        return np.array(cmap.colors)
    except Exception as e:
        raise ValueError("Unable to extract RGBA array from the provided colormap.") from e


def range_indicator_colormap_from_proxy(proxy_cmap,
                                        min_color=(0, 0, 1, 1),
                                        max_color=(1, 0, 0, 1),
                                        n_colors=65536):
    """
    Given a napari colormap proxy (which must have a 'name' attribute),
    this function retrieves the corresponding matplotlib colormap using that name,
    scales it to n_colors (e.g. 65,536 for 16-bit images) via linear interpolation,
    and forces the first (min) and last (max) entries to min_color and max_color.

    Parameters
    ----------
    proxy_cmap : napari colormap proxy
        A napari colormap object that provides a .name attribute.
    min_color : tuple
        RGBA tuple for the minimum color (default blue).
    max_color : tuple
        RGBA tuple for the maximum color (default red).
    n_colors : int
        The number of colors in the output colormap (default 65,536 for 16-bit images).

    Returns
    -------
    new_cmap : napari.utils.colormaps.Colormap
        A new napari Colormap with the range indicator modifications.
    """
    # Get the colormap name from the proxy.
    cmap_name = proxy_cmap.name
    # Retrieve the corresponding matplotlib colormap.
    mpl_cmap = plt.get_cmap(cmap_name)

    # First, sample the original colormap at a modest resolution (e.g. 256 points).
    base_colors = mpl_cmap(np.linspace(0, 1, n_colors))
    orig_N = base_colors.shape[0]

    # Create new positions for linear interpolation over [0, 1].
    x_old = np.linspace(0, 1, orig_N)
    x_new = np.linspace(0, 1, n_colors)

    # Interpolate each RGBA channel to create a new colormap with n_colors entries.
    new_colors = np.empty((n_colors, 4), dtype=base_colors.dtype)
    print(f"len new_colors: {len(new_colors)} | index 0: {new_colors[0]}")
    for channel in range(4):
        new_colors[:, channel] = np.interp(x_new, x_old, base_colors[:, channel])

    # Force only the extreme entries to be the desired colors.
    new_colors[0] = min_color
    new_colors[-1] = max_color
    # Create a new napari Colormap from the interpolated array.
    new_cmap = Colormap(name=f"{cmap_name}_range_indicator", colors=new_colors, interpolation = "zero")
    return new_cmap
