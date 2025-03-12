## Installation

You can install this package using one of the following options:

```bash
pip install git+https://github.com/MaxusTheOne/napari-psf-analysis-CFIM-edition
```
To install the latest version (not guaranteed to be stable)

or

```bash
pip install psf-analysis-CFIM
```
For the latest stable version (recommended)

---

## About

This is a **fork** of the [napari-psf-analysis](https://github.com/fmi-faim/napari-psf-analysis) project.

---

## Extra Features

This edition includes the following additional features:

- **Bead Averaging**: Adds an image of an averaged bead from all selected.
- **Visualisation**: Improves visualisation of the psf. Most notable color by wavelength.
  - **Range indicator** Button to mark the min and max values of the image.
- **PSF Report**: Adds a graded report on the quality of the PSF. <- WIP
- **Bead Detection**: Detects beads in the image.
- **Auto-Filling of Plugin Parameters**: Automatically populates parameters for the plugin.
  - At least 1 input also looks better
- **Auto Analysis of Image for PSF**: Performs automatic image analysis to ascertain the quality.
- **CZI Reader**: Adds support for reading CZI image files.
- **Debugging**: Adds a debug class to the IPython console. Small, but hey, we can show the psf box
- **Error Handling**: Less likely to crash. errors points can be seen in viewer | Error UI.
- **Bug fixes**: Fixes bugs involving zyx boxes, loading bar and other issues.

## Known Issues

- for autofilling, only .czi files are supported. Other issuses might also arise from not using .czi.
- Paths including non-ASCII characters, like "æøå" cause unintended behavior.
- The output.csv file is comma seperated with dot as decimal seperator, this might cause issue importing in Excel.
- Intensity for bead finder is hardcoded for now.
- Some images might still crash in the analysis.
- Hidden layer RaIn_label might show in newer versions of napari. (Only planned as of writing this)