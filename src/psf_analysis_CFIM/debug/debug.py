import numpy as np

default_path = "src/psf_analysis_CFIM/debug/saved_debug_info"

def save_np_array(array, name):
    np.save(default_path + "/" + name + ".npy", array)
