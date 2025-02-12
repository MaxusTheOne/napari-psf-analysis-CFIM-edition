import os
import shutil
import subprocess

# List of directory names to delete
directories_to_delete = ['build', 'dist']
# Directory name pattern to delete (e.g., folders ending with .egg-info)
directory_extension_to_delete = '.egg-info'

# Package name for uninstalling
package_name = "psf-analysis-CFIM"

def delete_items(base_path='.'):
    """
    Deletes specified directories and directories matching patterns,
    excluding virtual environments (like .venv).

    Args:
        base_path (str): The base directory to start searching from. Defaults to the current directory.
    """
    venv_dir = os.path.join(base_path, '.venv')  # Customize this if your venv is named differently

    for root, dirs, files in os.walk(base_path):
        # Avoid descending into the .venv directory
        if root.startswith(venv_dir):
            continue

        # Delete specific directories like "build" and "dist"
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)

            # Skip .venv even if accidentally picked up
            if dir_path.startswith(venv_dir):
                # print(f"Skipping virtual environment folder: {dir_path}")
                continue

            # Delete exact directory names
            if dir_name in directories_to_delete:
                print(f"Deleting directory: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)

            # Delete directories ending with `.egg-info`
            if dir_name.endswith(directory_extension_to_delete):
                print(f"Deleting .egg-info folder: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)


def reinstall_package():
    """
    Uninstalls and then reinstalls the package.
    """
    try:
        # Uninstall the package
        print(f"Uninstalling package: {package_name}")
        subprocess.check_call(["pip", "uninstall", "-y", package_name])

        # Reinstall from the current directory
        print("Reinstalling package from the current directory")
        subprocess.check_call(["pip", "install", "."])

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while reinstalling the package: {e}")


if __name__ == "__main__":
    # Run the cleanup
    print("Cleaning up build files...")
    delete_items()

    # Reinstall the package
    print("\nReinstalling the package...")
    reinstall_package()

    print("\nProcess completed!")