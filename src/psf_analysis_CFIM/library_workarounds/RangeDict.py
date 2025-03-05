
class RangeDict:
    def __init__(self, range_map: list[tuple]):
        self.range_map = range_map

    def __getitem__(self, key):
        for lower, upper, value in self.range_map:
            if lower <= key < upper:
                return value
        raise KeyError(f"{key} not found in any range")