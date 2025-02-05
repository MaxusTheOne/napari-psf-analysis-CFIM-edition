import os
import subprocess


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


if __name__ == "__main__":
    install_plugin()
    launch_napari()
