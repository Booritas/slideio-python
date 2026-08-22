# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Python bindings (via pybind11) for the **SlideIO** C++ library — a reader for medical/pathology whole-slide image formats (SVS, CZI, NDPI, DICOM, etc.) that returns image data as NumPy arrays. The C++ library itself lives in a separate repository ([Booritas/slideio](https://github.com/Booritas/slideio)) and is consumed here as a prebuilt Conan package (see `conanfile.txt`, currently `slideio/2.9.0@slideio/stable`) or from a local install via the `SLIDEIO_INSTALL_DIR` environment variable.

`pybind11` is a git submodule — clone with `--recursive` or run `git submodule update --init`.

There is no test suite in this repository; tests live in the main slideio C++ repository.

## Architecture: three layers

1. **`src/` — C++ binding layer.** pybind11 code compiled into the `slideiopybind` native module (target defined in `CMakeLists.txt`). `pybind.cpp` declares the module; `pyslide`/`pyscene`/`pyconverter`/`pytransformation` wrap the slideio C++ API and convert rasters to NumPy arrays.
2. **`slideio/core/` — raw import layer.** Imports symbols from `slideio/core/libs/slideiopybind` and aliases the low-level classes (`CoreSlide`, `CoreScene`, `core_*` functions). The `libs/` directory is populated at build time: `setup.py` copies the built `.pyd`/`.so`/`.dll` files (including the slideio shared libraries and, on Windows, MSVC runtime DLLs) into it.
3. **`slideio/wrappers/py_slideio.py` — public Python API.** Pythonic `Slide`/`Scene` classes and module functions (`open_slide`, `convert_scene`, `transform_scene`, ...) that delegate to the core layer. `slideio/__init__.py` re-exports this public surface.

When adding/changing API: a change usually touches `src/pybind.cpp` (binding), `slideio/core/__init__.py` (re-export), `slideio/wrappers/py_slideio.py` (wrapper), and `slideio/__init__.py` (public export).

## Build system

`setup.py` defines a `CMakeBuild` extension command that invokes CMake (Visual Studio 17 2022 / x64 on Windows, Makefiles elsewhere). CMake resolves the slideio C++ library in one of two ways:

- **`SLIDEIO_INSTALL_DIR` set** → headers/libs/binaries are taken from that local slideio install (used for developing against a locally built slideio).
- **Otherwise** → Conan: `find_package(slideio)` with the toolchain at `cmake/conan_toolchain.cmake` (generated into `cmake/` by `install.py -a conan`).

The package version is read from `set(projectVersion MAJOR.MINOR ...)` in `CMakeLists.txt`, with the patch part taken from `CI_PIPELINE_IID` (defaults to `1`).

### Typical local build (Windows)

```powershell
# 1. (Once, if the slideio conan package is not available) build it from the
#    Booritas/conan-center-index fork. Requires $env:CONAN_INDEX_HOME and
#    $env:SLIDEIO_PYTHON_HOME pointing at the respective repo roots.
.\build-dependencies.ps1 release   # or: debug

# 2. Install conan dependencies / generate cmake toolchain into .\cmake
python install.py -a conan -c release

# 3. Build the extension + wheel
python -m build
```

On Linux/macOS use `./conan.sh` and `python3 install.py -a conan -c release` instead; Linux builds are intended to run inside the manylinux Docker containers (`docker/`, images `booritas/slideio-manylinux_2_28_*`).

`install.py` also supports `-a configure|build|install|clean`; `--clean` wipes the build dir plus generated `CMakeUserPresets.json`/`cmake` dirs.

### Multi-version wheel builds

- `build-wheels-win.ps1` (helpers in `lib.ps1`): loops over Python 3.8–3.14 using conda envs, runs `python -m build`, then `Repair-Naming` fixes the `.pyd` name inside each wheel.
- `build-wheels-manylinux.sh`, `build-wheels-macos.sh` + `repair-wheels.sh`/`rename-macos-wheels.sh` for the other platforms.
- CI: `.github/workflows/{windows,linux,macos}-wheels.yml`, all `workflow_dispatch`-triggered; they optionally rebuild the conan packages from the conan-center-index fork and upload to a private Conan remote.

### Conan profiles

Per-platform profiles live in `conan/{Windows,Linux,OSX}/...` (Windows: `x86_64_release`/`x86_64_debug`; Linux: `ubuntu`/`manylinux`/`s390x`; OSX: `arm`/`x86-64`). `install.py` picks the profile directory automatically from the platform (and `distro`/processor on Linux/macOS).

## Version bumps

The slideio C++ package version appears in several places that must stay in sync: `conanfile.txt` (the `[requires]` line), `build-dependencies.ps1` / `conan.sh` (conan create version; these two are easy to miss and have drifted apart before), and the release branch name (e.g. `2.9.0`). The Python package MAJOR.MINOR comes from `projectVersion` in `CMakeLists.txt`.
