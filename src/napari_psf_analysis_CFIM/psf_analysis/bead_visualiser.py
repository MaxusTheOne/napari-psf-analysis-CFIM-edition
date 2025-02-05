import matplotlib.pyplot as plt


def visualise_bead(bead_data):
    raw_data = bead_data.data  # `Calibrated3DImage` often has an attribute like `data`.
    print(raw_data.shape)  # Check if it is NumPy data.
