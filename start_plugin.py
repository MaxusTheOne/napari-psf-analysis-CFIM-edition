import os
import subprocess
import napari
import numpy as np
import argparse
import faulthandler


def install_plugin():
    """Install the plugin using pip."""
    try:
        print("Installing the plugin...")
        subprocess.check_call(['pip', 'install', '.'])
        print("Plugin installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install the plugin. Error: {e}")
        exit(1)

def launch_napari():
    """Launch Napari."""
    try:
        print("Launching Napari...")
        subprocess.check_call(['napari'])
    except FileNotFoundError:
        print("Napari is not installed. Please install it by running 'pip install napari[all]'")
        exit(1)

def find_tif_file(folder_path):
    """
    Find the first TIF file in the given folder.
    :param folder_path: Path to the folder where TIF files are stored.
    :return: Path to the first TIF file found, or None if no files are found.
    """
    try:
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(".tif"):
                return os.path.join(folder_path, file_name)
        print(f"No .tif files found in {folder_path}.")
        return None
    except FileNotFoundError:
        print(f"Folder not found: {folder_path}")
        return None


def launch_napari_dev_mode(tif_folder):
    """
    Launch Napari in dev mode:
    - Load a TIF file from the specified folder
    - Create a Points layer
    - Activate the plugin 'napari_psf_analysis_CFIM'
    """
    print("Launching Napari in dev mode...")

    # Find a .tif file from the specified folder
    tif_file_path = find_tif_file(tif_folder)
    if not tif_file_path:
        print("No valid TIF file to load. Exiting dev mode.")
        return

    # Launch Napari viewer
    viewer = napari.Viewer()

    # Load the TIF file
    viewer.open(tif_file_path)
    print(f"Loaded TIF file: {tif_file_path}")

    points = np.array([
        [64, 170, 200],  # Center of the image
        [83, 360, 270],  # Another random point
        [16, 480, 100]  # Another random point
    ])

    viewer.add_points(points, name="Points", size=6, face_color='red')

    # Activate your plugin (napari_psf_analysis_CFIM)
    try:
        viewer.window.add_plugin_dock_widget("napari_psf_analysis_CFIM", widget_name="PSF Analysis - CFIM"
)
        print("Activated plugin 'napari_psf_analysis_CFIM'.")
    except ValueError:
        print("Plugin 'napari_psf_analysis_CFIM' not found or failed to load.")
    print(dir(napari.utils))
    napari.utils.config._set('application.debug')

    # Start the Napari event loop
    napari.run()


if __name__ == "__main__":
    # faulthandler.enable()
    # Setup argparse for handling dev mode
    parser = argparse.ArgumentParser(description="Start the Napari plugin with optional dev mode.")
    parser.add_argument(
        "--dev", action="store_true", help="Launch Napari in 'dev mode' for testing purposes."
    )
    parser.add_argument(
        "--folder", type=str, default="./tif_data",
        help="Folder containing TIF files to load in dev mode. Default is './tif_data'."
    )
    args = parser.parse_args()

    # Install the plugin
    install_plugin()

    # Launch the appropriate mode
    if args.dev:
        # Run the custom dev mode setup
        launch_napari_dev_mode(args.folder)
    else:
        # Run the standard Napari launch
        launch_napari()
