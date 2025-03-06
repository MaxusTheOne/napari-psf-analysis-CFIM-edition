import os

import numpy as np
from qtpy.QtCore import QObject, Signal

class DebugEmitter(QObject):
    save_debug = Signal(object, str)

def report_error_debug(message, msg_type="message"):
    debug_emitter.save_debug.emit(message, msg_type)

debug_emitter = DebugEmitter()

# TODO: Flush out the potential features for dedicated debug class
class DebugClass:
    def __init__(self, viewer):
        self.errors: list[tuple[any, str]] = []
        self.error_amount = 0
        self.viewer = viewer

        debug_emitter.save_debug.connect(self.save_debug)

    def get(self, index):
        return self.errors[index]

    def say_hello(self):
        return "Hello from Debug!"

    def save_debug(self, message, msg_type):
        self.error_amount += 1
        self.errors.append((message, msg_type))

    def show_3d_array(self, index):
        self.viewer.add_image(self.get(index))

    def test_type(self, index):
        # Language: python
        error = self.get(0)  # Get the error record
        data = error[0]       # Data to be saved

        print("Type of data:", type(data))
        if hasattr(data, "shape"):
            print("Shape of data:", data.shape)
        else:
            print("Data does not have a shape attribute")

        # Optionally, print first few elements if it is a sequence
        if hasattr(data, "__iter__"):
            print("Data sample:", list(data)[:5])
        else:
            print("Data is not iterable.")


    def save(self, index, *, overwrite_type=None):
        output_folder = "src/psf_analysis_CFIM/debug/saved_debug_info"
        error = self.get(index)
        data =  error[0]
        msg_type = overwrite_type if overwrite_type else error[1] # One-liner for overwrite

        # Ensure the "saved" folder exists
        os.makedirs(output_folder, exist_ok=True)

        if msg_type == "3d_array":
            np.save(f"{output_folder}/debug_{index}.npy", error[0])
        elif msg_type == "message":
            with open(f"{output_folder}/debug_{index}.txt", "w") as f:
                f.write(str(data))
        else:
            print(f"Unknown message type: {msg_type}")



# def save_np_array(array, name):
#     np.save(default_path + "/" + name + ".npy", array)
