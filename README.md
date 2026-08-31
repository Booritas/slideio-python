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

## Building from source

The C++ **SlideIO** library is not downloaded as a prebuilt package. It is the
`extern/slideio` git submodule and is compiled from source into a local install
prefix, which the Python extension then links against. No Conan remote, account or
credentials are needed: every C++ dependency resolves from
[conan center](https://conan.io/center), and the few that do not live there are
submodules of the slideio repository.

### Prerequisites

| Requirement | Notes |
|---|---|
| Git | Submodules are required, see below |
| CMake 3.10+ | |
| A C++17 compiler | GCC, Clang, or Visual Studio 2022 on Windows |
| Python 3.7+ | Wheels are published for 3.8–3.14 |
| [Conan 2](https://conan.io) | `pip install conan` — used only to build the C++ library |
| `distro` | Linux only: `pip install distro` |
| `build` | `pip install build` — only if you want a wheel rather than an install |

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/Booritas/slideio-python.git
cd slideio-python
```

`--recurse-submodules` is not optional. There are two submodules — `pybind11` and
`extern/slideio` — and slideio carries four of its own. In an existing clone:

```bash
git submodule update --init --recursive
```

### 2. Build the C++ library

```bash
python build-slideio.py
```

This builds the `extern/slideio` submodule and installs it into
`extern/slideio-install/` (`include/`, `lib/`, `bin/`). The first run compiles the
whole dependency graph from source and takes a while; later runs reuse the Conan
cache.

| Option | Effect |
|---|---|
| *(none)* | Release build; does nothing if the prefix already matches the checked-out submodule commit |
| `--force` | Rebuild and reinstall even when the prefix is up to date |
| `--config debug` | Build the debug configuration instead |
| `--prefix PATH` | Install somewhere other than `extern/slideio-install` |

Because the library does not depend on the Python version, it only has to be built
once per machine — the wheel scripts below call this script themselves and it is a
no-op after the first time.

### 3. Build the Python package

To install into the current environment:

```bash
pip install .
```

To produce a wheel in `dist/` instead:

```bash
python -m build --wheel
```

Either way CMake compiles the `slideiopybind` extension, and the slideio shared
libraries are copied into the package as `slideio/core/libs/`, so the resulting
wheel is self-contained.

### Building wheels for every supported Python version

Each platform has a script that loops over a range of Python versions, building one
wheel per version — 3.8–3.14 on macOS and Windows (3.13 is the cap on macOS Intel),
3.7–3.14 on manylinux. They build the C++ library once up front, then rebuild only
the extension per version.

```bash
./build-wheels-macos.sh        # macOS, needs conda
./build-wheels-manylinux.sh    # Linux, intended for the manylinux container
```

```powershell
.\build-wheels-win.ps1         # Windows, needs conda
```

macOS wheels are then renamed with `./rename-macos-wheels.sh ./dist`; Linux wheels
are repaired by `auditwheel` inside `build-wheels-manylinux.sh` and land in
`wheelhouse/`.

### Building on Linux with the manylinux Docker container

The container already carries the toolchain and a prebuilt Conan cache, so the
build goes straight to compiling slideio itself.

```bash
git clone --recurse-submodules https://github.com/Booritas/slideio-python.git

docker run --name slideio -it \
  -v "$(pwd)/slideio-python:/slideio-python" \
  booritas/slideio-manylinux_2_28_x86_64:2.10.0 bash

cd /slideio-python
./build-wheels-manylinux.sh
```

The wheels end up in the `wheelhouse` subdirectory.

### Building against a slideio checkout outside this repository

To develop against your own slideio build rather than the submodule, point
`SLIDEIO_INSTALL_DIR` at its install prefix. It takes precedence over
`extern/slideio-install`, and `build-slideio.py` is then not needed at all.

```bash
export SLIDEIO_INSTALL_DIR=/path/to/slideio/install    # must contain include/ lib/ bin/
pip install .
```

### Conan profiles

The Conan profiles live in the submodule, under `extern/slideio/conan/<platform>/`,
and are used exactly as committed — **no build step rewrites them**. If your
compiler is not the one a profile names, edit the profile deliberately and commit
the change.

The slideio repository ships `sync-toolchain.py`, which detects the host compiler
and rewrites `compiler.version` in every profile (and, on Windows, the CMake
generator in its `install.py`). It is a setup tool for preparing a new machine, not
part of the build: run it by hand from `extern/slideio`, check the diff, and commit
it.

```bash
cd extern/slideio && python sync-toolchain.py && git diff conan/
```

---

## Contributing
Please submit pull requests or open issues if you have any suggestions or find any bugs. We welcome contributions from the community to improve the library and its Python bindings.

---

**Enjoy using SlideIO for your medical and digital pathology workflows!**