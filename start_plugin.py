import json
import os
import subprocess
import napari
import argparse
import faulthandler

import numpy as np


def install_plugin():
    """Install the plugin using pip."""
    try:
        print("Installing the plugin...")
        subprocess.check_call(['pip', 'install', '.'])
        print("Plugin installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install the plugin. Error: {e}")
        exit(1)

def load_czi_file(viewer, czi_file):
    """Load a .czi file into the Napari viewer."""
    print(f"Loading .czi file: {czi_file}")

    viewer.open(czi_file, plugin="psf-analysis-CFIM")

def launch_napari():
    """Launch Napari."""
    try:
        print("Launching Napari...")
        subprocess.check_call(['napari'])
    except FileNotFoundError:
        print("Napari is not installed. Please install it by running 'pip install napari[all]'")
        exit(1)


# TODO: Create a github actions script for deployment
def launch_napari_dev_mode(czi_file=None, points=None):
    """
        Launch Napari in dev mode:
        - czi: loads a .czi file with the given path
        - points: JSON string representing points coordinates e.g. "[[z,y,x],[z,y,x]]"

        Current issues:
        - dev mode messes with napari opening. Causing incorrect window size while the program still thinks it's full screen. Only visual.
        - points flag changes napari cord scale. Causing wrong focus after psf analysis. Only visual, the data is correct.
            - Likely due to the mismatch between the nm scale of the image and the pixel scale of the points.
        - Opening napari console with shortcut removes exposed variables. Makes the debug class unusable.
            - Works fine when opened with the console button.
    """
    print("Launching Napari in dev mode...")

    # Signal debug mode
    os.environ["PSF_ANALYSIS_CFIM_DEBUG"] = "1"
    is_debug = "1" == os.environ.get("PSF_ANALYSIS_CFIM_DEBUG")

    viewer = napari.Viewer(ndisplay=3, show= False)
    from psf_analysis_CFIM.debug.debug import DebugClass # Causes crash if imported before napari.Viewer() | Due to qt event loop


    if is_debug:
        debug = DebugClass(viewer)
        # globals.debug_instance = debug
        print(f"Debug class initialized. | {debug.say_hello()}")


    # Activate your plugin (psf_analysis_CFIM)
    try:
        viewer.window.add_plugin_dock_widget("psf-analysis-CFIM", widget_name="PSF Analysis - CFIM")
        print("Activated plugin 'psf-analysis-CFIM'.")
    except ValueError:
        print("Plugin 'psf-analysis-CFIM' not found or failed to load.")

    if czi_file or points:
        def on_status_change(event):
            viewer.events.disconnect(on_status_change)
            if czi_file:
                try:
                    load_czi_file(viewer, czi_file)

                except FileNotFoundError as e:
                    print(f"Failed to load czi file {czi_file}. Error: {e}")

            if points and czi_file:
                try:
                    print("Adding points")
                    czi_scale = viewer.layers[0].scale
                    points_list = json.loads(points)
                    viewer.add_points(points_list, name="Points Layer", scale=czi_scale)
                except json.JSONDecodeError:
                    print(
                        "Failed to decode the points argument. Please provide a valid JSON string, e.g. \"[[z,y,x],[z,y,x]]\".")

        viewer.events.connect(on_status_change)

    viewer.show()
    napari.run()


if __name__ == "__main__":
    faulthandler.enable()
    # Setup argparse for handling dev mode
    parser = argparse.ArgumentParser(description="Start the Napari plugin with optional dev mode. Expects the plugin to be installed.")
    parser.add_argument(
        "--dev", action="store_true", help="Launch Napari in 'dev mode' for testing purposes."
    )
    parser.add_argument(
        "--czi", type=str, help="Path to a .czi file to load into Napari."
    )
    parser.add_argument(
        "--points", type=str, help="Points coordinates in JSON format: \"[[z,y,x],[z,y,x]]\"."
    )

    args = parser.parse_args()


    # Launch the appropriate mode
    if args.dev:
        # Run the custom dev mode setup
        launch_napari_dev_mode(czi_file=args.czi, points=args.points)
    else:
        # Install the plugin
        install_plugin()
        # Run the standard Napari launch
        launch_napari()

