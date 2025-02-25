import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

def ensure_3d(image, point):
    # Ensure the image is 3D
    if image.ndim == 1:
        image = np.expand_dims(np.expand_dims(image, axis=0), axis=0)
    elif image.ndim == 2:
        image = np.expand_dims(image, axis=0)

    # Ensure the point is 3D
    if len(point) == 1:
        point = (0, 0, point[0])
    elif len(point) == 2:
        point = (0, point[0], point[1])

    return image, point

def plot_point_in_image(image, point):
    image, point = ensure_3d(image, point)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.voxels(image, edgecolor='k')
    ax.scatter(point[2], point[1], point[0], c='r', s=100)
    plt.show()

def plot_points_in_image(image, point_list):
    image, _ = ensure_3d(image, point_list[0])

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.voxels(image, edgecolor='k')
    for point in point_list:
        _, point = ensure_3d(image, point)
        ax.scatter(point[2], point[1], point[0], c='r', s=100)
    plt.show()

def compare_by_index(list1, list2):
    # Create an index for each parameter
    indices = range(len(list1))

    # Plot the values as scatter points
    plt.figure(figsize=(10, 6))
    plt.scatter(indices, list1, color='red', label='Guessed p0', marker='o')
    plt.scatter(indices, list2, color='blue', label='Optimal parameters', marker='x')

    plt.xlabel('Parameter Index')
    plt.ylabel('Parameter Value')
    plt.title('Scatter Plot of Guessed p0 vs Optimal Parameters')
    plt.legend()
    plt.grid(True)
    plt.show()

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def plot_correlation_matrix(corr_matrix):
    """
    Plots a heatmap of the correlation matrix with the given variable names.

    Parameters:
    - corr_matrix: 2D array-like, the correlation matrix to plot.
    - var_names: list of str, the variable names corresponding to the matrix dimensions.
    """
    var_names = [
        'zyx_bg', 'zyx_amp', 'zyx_z_mu', 'zyx_y_mu', 'zyx_x_mu',
        'zyx_czz', 'zyx_czy', 'zyx_czx', 'zyx_cyy', 'zyx_cyx', 'zyx_cxx'
    ]
    # Create a DataFrame from the correlation matrix for better labeling
    df = pd.DataFrame(corr_matrix, index=var_names, columns=var_names)

    # Set up the matplotlib figure
    plt.figure(figsize=(10, 8))

    # Draw the heatmap with the mask and correct aspect ratio
    sns.heatmap(df, annot=True, fmt=".2f", cmap='coolwarm', vmin=-1, vmax=1, linewidths=0.5)

    # Add titles and labels
    plt.title('Correlation Matrix Heatmap', fontsize=16)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()

    # Display the plot
    plt.show()

if __name__ == "__main__":
    corr_matrix = [
        [1.000, 0.038, -0.008, 0.001, -0.0003, -0.093, 0.010, -0.006, -0.098, 0.013, -0.098],
        [0.038, 1.000, -0.053, 0.005, -0.002, -0.412, 0.045, -0.026, -0.456, 0.062, -0.457],
        [-0.008, -0.053, 1.000, -0.086, 0.049, 0.103, -0.011, 0.006, 0.001, -0.001, 0.001],
        [0.001, 0.005, -0.086, 1.000, -0.097, -0.009, -0.015, 0.001, 0.002, -0.001, 0.00006],
        [-0.0003, -0.002, 0.049, -0.097, 1.000, 0.005, 0.001, -0.016, -0.0001, 0.001, -0.001],
        [-0.093, -0.412, 0.103, -0.009, 0.005, 1.000, -0.109, 0.063, 0.016, -0.007, 0.011],
        [0.010, 0.045, -0.011, -0.015, 0.001, -0.109, 1.000, -0.099, -0.121, 0.057, -0.008],
        [-0.006, -0.026, 0.006, 0.001, -0.016, 0.063, -0.099, 1.000, 0.012, -0.090, 0.070],
        [-0.098, -0.456, 0.001, 0.002, -0.0001, 0.016, -0.121, 0.012, 1.000, -0.136, 0.019],
        [0.013, 0.062, -0.001, -0.001, 0.001, -0.007, 0.057, -0.090, -0.136, 1.000, -0.137],
        [-0.098, -0.457, 0.001, 0.00006, -0.001, 0.011, -0.008, 0.070, 0.019, -0.137, 1.000]
    ]

    plot_correlation_matrix(corr_matrix)