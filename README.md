## Installation

You can install this package using one of the following options:

```bash
pip install git+https://github.com/MaxusTheOne/napari-psf-analysis-CFIM-edition
```

or

```bash
pip install psf-analysis-CFIM
```

---

## About

This is a **fork** of the [napari-psf-analysis](https://github.com/fmi-faim/napari-psf-analysis) project.

---

## Extra Features

This edition includes the following additional features:

- **CZI Reader**: Adds support for reading CZI image files.
- **Auto-Filling of Plugin Parameters**: Automatically populates parameters for the plugin.
- **Auto Analysis of Image for PSF**: Performs automatic image analysis to ascertain the quality.
- **Bead Detection**: Detects beads in the image.
- **Bead Averaging**: Adds an image of an averaged bead from all selected.
- **Error Handling**: Less likely to crash. errors points can be seen in viewer | Error UI
- **Bug fixes**: Fixes things like borders and other issues.
- Not made for file types other than .CZI for now


## Known Issues

- for autofilling, only .czi files are supported
- Paths including non-ASCII characters, like æøå cause unintended behavior
- The output.czv file is comma seperated with dot as decimal seperator, this might cause issue importing in Excel.