from typing import Tuple

from numpy._typing import ArrayLike
from pydantic import BaseModel, PositiveFloat, validator, field_validator


class CalibratedImage(BaseModel):
    data: ArrayLike
    spacing: Tuple[PositiveFloat, ...]
    offset: Tuple[int, ...]

    class Config:
        arbitrary_types_allowed = True

    def shape(self):
        return self.data.shape

    def get_corner_coordinates(self):
        return tuple(self.offset)

    def get_middle_coordinates(self):
        return tuple(o + s / 2 for o, s in zip(self.offset, self.data.shape))

# TODO: Make Calibrated3DImage.mean() method
class Calibrated3DImage(CalibratedImage):
    offset: Tuple[int, int, int] = (0,) * 3

    @field_validator("data")
    def check_ndims(data: ArrayLike):
        assert data.ndim == 3, "Data must be 3D."
        return data


    class Config:
        arbitrary_types_allowed = True

    def get_box(self) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """
        Returns a tuple of two 3D tuples:
        - The first is the minimum coordinate (offset).
        - The second is the maximum coordinate computed as offset + data.shape.
        """
        min_coord = self.offset
        max_coord = tuple(o + s for o, s in zip(self.offset, self.data.shape))
        return (min_coord, max_coord)


class Calibrated2DImage(CalibratedImage):
    offset: Tuple[int, int] = (0,) * 2

    @field_validator("data")
    def check_ndims(data: ArrayLike):
        assert data.ndim == 2, "Data must be 2D."
        return data

    class Config:
        arbitrary_types_allowed = True


class Calibrated1DImage(CalibratedImage):
    offset: Tuple[int] = (0,)

    @field_validator("data")
    def check_ndims(data: ArrayLike):
        assert data.ndim == 1, "Data must be 1D."
        return data

    class Config:
        arbitrary_types_allowed = True
