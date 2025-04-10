from pydantic import BaseModel, Field, conint, confloat, conlist
from typing import List
import os

def get_default_output_folder() -> str:
    base = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    return os.path.join(base, "psf-analysis-cfim", "output")

class RenderSettings(BaseModel):
    covariance_ellipsoid: bool = False
    coordinate_annotation: bool = False

class PSFSettings(BaseModel):
    render_settings: RenderSettings = RenderSettings()

class AnalyzerSettings(BaseModel):
    psf_settings: PSFSettings = PSFSettings()

class IntensitySettings(BaseModel):
    lower_warning_percent: float = Field(0.08, ge=0, le=1)
    lower_error_percent: float = Field(0.12, ge=0, le=1)
    upper_warning_percent: float = Field(0.01, ge=0, le=1)
    upper_error_percent: float = Field(0.08, ge=0, le=1)


class NoiseSettings(BaseModel):
    high_noise_threshold: conint(ge=0) = 120
    low_snr_threshold: conint(ge=0) = 10

class ImageAnalysisSettings(BaseModel):
    intensity_settings: IntensitySettings = IntensitySettings()
    noise_settings: NoiseSettings = NoiseSettings()


class UISettings(BaseModel):
    bead_size: conint(gt=0) = 100
    box_size_xy: conint(gt=0) = 2000
    box_size_z: conint(gt=0) = 2500
    ri_mounting_medium: confloat(gt=0.9, lt=2) = 1.4

class PSFAnalysisPluginSettings(BaseModel):
    __version__: str = "1.3.2"

    debug: bool = Field(default=False)
    version: str = Field(default=__version__)
    microscopes: List[str] = ["TIRF", "Zeiss Z1"]
    output_folder: str = Field(default_factory=get_default_output_folder)
    ui_settings: UISettings = UISettings()
    image_analysis_settings: ImageAnalysisSettings = ImageAnalysisSettings()
    analyzer_settings: AnalyzerSettings = AnalyzerSettings()
