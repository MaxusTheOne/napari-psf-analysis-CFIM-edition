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

def find_file(folder_path):
    """
    Find the first file in the given folder.
    :param folder_path: Path to the folder containing files.
    :return: Path to the first file found, or None if no files are found.
    """
    try:
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                return file_path
        print(f"No valid files found in {folder_path}.")
        return None
    except FileNotFoundError:
        print(f"Folder not found: {folder_path}")
        return None


def launch_napari_dev_mode():
    """
    Launch Napari in dev mode:
    - Currently a stub, just opens the plugin
    """
    print("Launching Napari in dev mode...")


    # Launch Napari viewer
    viewer = napari.Viewer()

    # Activate your plugin (psf_analysis_CFIM)
    try:
        viewer.window.add_plugin_dock_widget("psf-analysis-CFIM", widget_name="PSF Analysis - CFIM")
        print("Activated plugin 'psf-analysis-CFIM'.")
    except ValueError:
        print("Plugin 'psf-analysis-CFIM' not found or failed to load.")

    # Start the Napari event loop
    napari.run()

if __name__ == "__main__":
    faulthandler.enable()
    # Setup argparse for handling dev mode
    parser = argparse.ArgumentParser(description="Start the Napari plugin with optional dev mode.")
    parser.add_argument(
        "--dev", action="store_true", help="Launch Napari in 'dev mode' for testing purposes."
    )

    args = parser.parse_args()

    # Install the plugin
    install_plugin()

    # Launch the appropriate mode
    if args.dev:
        # Run the custom dev mode setup
        launch_napari_dev_mode()
    else:
        # Run the standard Napari launch
        launch_napari()
