# SlideIO Python Wrapper

This repository provides a Python interface to the **SlideIO** library, a high-performance C++ image-reading framework designed for medical and biological slides. With SlideIO, you can read whole-slide images, extract specific regions, and scale large slides efficiently. The Python wrapper integrates these capabilities into a convenient API, returning image data as NumPy arrays.

License:  BSD-3-Clause.

---

## References
- [**SlideIO** GitHub Repository](https://github.com/Booritas/slideio)
- [**SlideIO** Tutorial](https://github.com/Booritas/slideio-tutorial)
- [**SlideIO** Website](https://www.slideio.com)
- [**SlideIO** Python Documentation](https://www.slideio.com/sphinx/)
- [*Using SlideIO Python Library for Image Analysis in Digital Pathology*](https://blog.gopenai.com/using-slideio-python-library-for-image-analysis-in-digital-pathology-ea9e71a4b430)
- [*SlideIO: A New Python Library for Reading Medical Images*](https://towardsdatascience.com/slideio-a-new-python-library-for-reading-medical-images-11858a522059)

---

## Overview

**SlideIO** is available as:
- A **C++ library** for efficient reading of whole-slide images, with support for multi-dimensional data (2D, 3D, and time series).
- A **Python module** that leverages the same C++ codebase, providing a Pythonic interface for reading images into NumPy arrays.

Key features include:
- **Whole-slide reading**: Load entire slides or specific regions of interest.  
- **Efficient scaling**: Rapidly generate scaled images from large slides using internal zoom pyramids.  
- **Format flexibility**: Handle diverse medical and biological imaging formats through an extensible driver system.
- **Explicit zoom level access**: Read a region from a pyramid level you name, in that level's own coordinate
  system, with `Scene.read_block_from_level` - useful for tiled viewers and tile caches that already know which
  level they want.
- **Structured metadata**: Access slide and scene metadata as a navigable tree through the `metadata` property.

### Supported Image Formats

The following table lists the currently implemented drivers and their corresponding file formats:

| **Driver** | **File Format** | **Extensions** | **Developer** | **Scanners** |
|------------|-----------------|----------------|---------------|--------------|
| **SVS**    | [Aperio SVS](https://www.leicabiosystems.com/en-de/digital-pathology/manage/aperio-imagescope/) | *.svs | [Leica Microsystems](https://www.leicabiosystems.com/) | [Aperio GT 450 and Aperio GT 450 DX](https://www.leicabiosystems.com/en-de/digital-pathology/scan/) |
| **AFI**    | [Aperio AFI (Fluorescent)](https://www.pathologynews.com/fileformats/leica-afi/) | *.afi | [Leica Microsystems](https://www.leicabiosystems.com/) |  |
| **SCN**    | [Leica SCN](https://www.leica-microsystems.com/) | *.scn | [Leica Microsystems](https://www.leicabiosystems.com/) | [Leica SCN400](https://www.leicabiosystems.com/en-de/news-events/leica-microsystems-launches-scn400-f-combined-fluorescence-and-brightfield-slide/) |
| **CZI**    | [Zeiss CZI](https://www.zeiss.com/microscopy/en/products/software/zeiss-zen/czi-image-file-format.html) | *.czi | [Zeiss Microscopy](https://www.zeiss.com/microscopy/en/home.html?vaURL=www.zeiss.com/microscopy) | [ZEISS Axioscan 7](https://www.zeiss.com/microscopy/en/products/imaging-systems/axioscan-for-biology.html) |
| **ZVI**    | Zeiss ZVI | *.zvi | [Zeiss Microscopy](https://www.zeiss.com/microscopy/en/home.html?vaURL=www.zeiss.com/microscopy) |  |
| **DCM**    | DICOM | *.dcm / no extension | - | - |
| **NDPI**   | [Hamamatsu NDPI](https://www.hamamatsu.com/eu/en/product/life-science-and-medical-systems/digital-slide-scanner/U12388-01.html) | *.ndpi | [Hamamatsu](https://www.hamamatsu.com/eu/en.html) |  |
| **VSI**    | Olympus VSI | *.vsi | - | - |
| **QPTIFF** | PerkinElmer Vectra QPTIFF | *.qptiff | [Akoya Biosciences](https://www.akoyabio.com/software-data-analysis/) | [PerkinElmer Vectra](https://www.akoyabio.com/phenoimager/instruments/vectra-3-0/) |
| **OMETIFF** | [OME-TIFF](https://ome-model.readthedocs.io/en/stable/ome-tiff/) | *.ome.tif, *.ome.tiff, *.ome.tf2, *.ome.tf8, *.ome.btf | [Open Microscopy Environment](https://www.openmicroscopy.org/) | - |
| **PHTIFF** | Philips TIFF | *.tif, *.tiff | [Philips](https://www.philips.com/healthcare) | [Philips IntelliSite Pathology Solution](https://www.usa.philips.com/healthcare/resources/feature-detail/intellisite-pathology-solution) |
| **GDAL**   | Common image formats (JPEG, PNG, TIFF, etc.) | *.jpeg, *.jpg, *.tif, *.tiff, *.png | - | - |

Philips TIFF files use the generic `*.tif`/`*.tiff` extensions, so the PHTIFF driver identifies them by their
embedded metadata. `open_slide` with the default `driver="AUTO"` therefore selects the right driver, while plain
TIFF files continue to be read by GDAL and OME-TIFF files by the OMETIFF driver.

To learn more about the library and additional features, visit the [SlideIO Website](https://booritas.github.io/slideio/).

---

## Building on Linux with the Manylinux Docker Container

1. **Clone the repository with its submodules**
   ```bash
   git clone --recurse-submodules https://github.com/Booritas/slideio-python.git
   ```
   The `--recurse-submodules` is required: the C++ library is the `extern/slideio`
   submodule and carries four submodules of its own.

2. **Run the Docker container**
   ```bash
   docker run --name slideio -it \
     -v /path-to-slideio-python:/slideio-python \
     booritas/slideio-manylinux_2_28_x86_64:2.10.0 bash
   ```

3. **Build the wheels**
   ```bash
   cd /slideio-python
   ./build-wheels-manylinux.sh
   ```
   The script builds the C++ library once with `build-slideio.py`, then builds one
   wheel per Python version. No Conan remote or credentials are needed — every
   dependency resolves from conan center, and the image ships them prebuilt.

4. **Locate the wheel packages**
   They are in the `wheelhouse` subdirectory.

---

## Contributing
Please submit pull requests or open issues if you have any suggestions or find any bugs. We welcome contributions from the community to improve the library and its Python bindings.

---

**Enjoy using SlideIO for your medical and digital pathology workflows!**