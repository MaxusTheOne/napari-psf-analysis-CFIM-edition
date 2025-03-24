# File: tests/fake_event.py
# A simple fake event to allow connecting callbacks.
class FakeEvent:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in self.callbacks:
            callback()

# Aggregated events, holding the layers_change event.
class FakeEvents:
    def __init__(self):
        self.layers_change = FakeEvent()