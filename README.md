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
- **PSF Report**: Adds a graded report on the quality of the PSF. <- WIP
- **Bead Detection**: Detects beads in the image.
- **Auto-Filling of Plugin Parameters**: Automatically populates parameters for the plugin.
- **Auto Analysis of Image for PSF**: Performs automatic image analysis to ascertain the quality.
- **CZI Reader**: Adds support for reading CZI image files.
- **Error Handling**: Less likely to crash. errors points can be seen in viewer | Error UI.
- **Bug fixes**: Fixes bugs involving zyx boxes, loading bar and other issues.
- Not made for file types other than .CZI for now


## Known Issues

- for autofilling, only .czi files are supported.
- Paths including non-ASCII characters, like "æøå" cause unintended behavior.
- The output.csv file is comma seperated with dot as decimal seperator, this might cause issue importing in Excel.
- Intensity for bead finder is hardcoded for now.
- Some images might still crash in the analysis.