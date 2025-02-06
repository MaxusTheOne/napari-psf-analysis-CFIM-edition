import numpy as np
import pandas as pd


def analyze_image(img_data, num_bins=8):
    if img_data is None:
        raise ValueError("Image data cannot be None")
    if not isinstance(img_data, np.ndarray):
        raise TypeError("Image data must be a NumPy array")

    # Convert color image to grayscale
    if len(img_data.shape) == 3:
        img_data = np.mean(img_data, axis=-1)

    # Determine max intensity value
    if np.issubdtype(img_data.dtype, np.integer):
        max_val = np.iinfo(img_data.dtype).max
    else:
        max_val = img_data.max()

    # Calculate pixel counts
    min_pixels = (img_data == 0).sum()
    max_pixels = (img_data == max_val).sum()
    total_pixels = img_data.size

    if total_pixels == 0:
        raise ValueError("Image contains no pixels to analyze.")

    # Filter out min and max values
    img_filtered = img_data[(img_data > 0) & (img_data < max_val)]

    # Compute histogram
    hist, bin_edges = np.histogram(img_filtered, bins=num_bins, range=(0, max_val))

    # Compute percentages
    percentages = (hist / total_pixels) * 100

    # Store statistics in dictionary
    stats = {
        f"0-{bin_edges[1]:.1f} (min)": f"{(min_pixels / total_pixels) * 100:.2f}%",
    }

    for i in range(len(hist)):
        stats[f"{bin_edges[i]:.1f}-{bin_edges[i + 1]:.1f}"] = f"{percentages[i]:.2f}%"

    stats[f"{max_val:.1f} (max)"] = f"{(max_pixels / total_pixels) * 100:.2f}%"

    return stats


def save_statistics_to_file(stats, filename="image_statistics.csv"):
    """
    Save image statistics to a CSV file.

    Parameters:
        stats (dict): A dictionary containing intensity ranges and percentages.
        filename (str): The file to save statistics to.
    """
    # Save as a CSV using Pandas
    df = pd.DataFrame(stats.items(), columns=["Intensity Range", "Percentage"])
    df.to_csv(filename, index=False)
    print(f"Statistics saved to {filename}")
