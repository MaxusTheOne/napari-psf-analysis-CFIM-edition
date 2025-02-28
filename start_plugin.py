import subprocess
import napari
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



def launch_napari_dev_mode(czi_file=None):
    """
    Launch Napari in dev mode:
    - czi: loads a .czi file with the given path
    """
    print("Launching Napari in dev mode...")
    viewer = napari.Viewer()


    # Activate your plugin (psf_analysis_CFIM)
    try:
        viewer.window.add_plugin_dock_widget("psf-analysis-CFIM", widget_name="PSF Analysis - CFIM")
        print("Activated plugin 'psf-analysis-CFIM'.")
    except ValueError:
        print("Plugin 'psf-analysis-CFIM' not found or failed to load.")

    # Improvement would be a better event here. Can't find a better one
    if czi_file:
        def on_status_change(event):
            viewer.events.disconnect(on_status_change)
            load_czi_file(viewer, czi_file)

        viewer.events.connect(on_status_change)

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

    args = parser.parse_args()


    # Launch the appropriate mode
    if args.dev:
        # Run the custom dev mode setup
        launch_napari_dev_mode(args.czi)
    else:
        # Install the plugin
        install_plugin()
        # Run the standard Napari launch
        launch_napari()
