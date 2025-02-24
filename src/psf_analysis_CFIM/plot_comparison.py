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