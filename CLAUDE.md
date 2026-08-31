# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Python bindings (via pybind11) for the **SlideIO** C++ library — a reader for medical/pathology whole-slide image formats (SVS, CZI, NDPI, DICOM, etc.) that returns image data as NumPy arrays. The C++ library itself lives in a separate repository ([Booritas/slideio](https://github.com/Booritas/slideio)) and is consumed here as the `extern/slideio` git submodule, built from source into `extern/slideio-install/` by `build-slideio.py`. Setting `SLIDEIO_INSTALL_DIR` overrides that and points the build at any other slideio install prefix.

Two git submodules: `pybind11` and `extern/slideio`. slideio carries four submodules of its own, so `--recursive` is required, not optional — clone with `--recurse-submodules` or run `git submodule update --init --recursive`.

There is no test suite in this repository; tests live in the main slideio C++ repository.

## Architecture: three layers

1. **`src/` — C++ binding layer.** pybind11 code compiled into the `slideiopybind` native module (target defined in `CMakeLists.txt`). `pybind.cpp` declares the module; `pyslide`/`pyscene`/`pyconverter`/`pytransformation` wrap the slideio C++ API and convert rasters to NumPy arrays.
2. **`slideio/core/` — raw import layer.** Imports symbols from `slideio/core/libs/slideiopybind` and aliases the low-level classes (`CoreSlide`, `CoreScene`, `core_*` functions). The `libs/` directory is populated at build time: `setup.py` copies the built `.pyd`/`.so`/`.dll` files (including the slideio shared libraries and, on Windows, MSVC runtime DLLs) into it.
3. **`slideio/wrappers/py_slideio.py` — public Python API.** Pythonic `Slide`/`Scene` classes and module functions (`open_slide`, `convert_scene`, `transform_scene`, ...) that delegate to the core layer. `slideio/__init__.py` re-exports this public surface.

When adding/changing API: a change usually touches `src/pybind.cpp` (binding), `slideio/core/__init__.py` (re-export), `slideio/wrappers/py_slideio.py` (wrapper), and `slideio/__init__.py` (public export).

## Build system

`setup.py` defines a `CMakeBuild` extension command that invokes CMake (Visual Studio 17 2022 / x64 on Windows, Makefiles elsewhere). CMake resolves the slideio C++ library from an install prefix — `include/`, `lib/`, `bin/` — in one of two ways:

- **`SLIDEIO_INSTALL_DIR` set** → that prefix is used, for developing against a slideio build outside this repository.
- **Otherwise** → `extern/slideio-install`, produced by `build-slideio.py` from the `extern/slideio` submodule. Configure fails with an actionable `FATAL_ERROR` if it is absent.

There is no Conan step in this repository: slideio is no longer a Conan package here, so no remote, no credentials and no `conanfile.txt`. The submodule's own build still uses Conan for slideio's dependencies — all of which resolve from conan center — but that is internal to `extern/slideio`.

The package version is read from `set(projectVersion MAJOR.MINOR ...)` in `CMakeLists.txt`, with the patch part taken from `CI_PIPELINE_IID` (defaults to `0`).

### Typical local build (any platform)

```bash
git submodule update --init --recursive   # pybind11 + extern/slideio + its four
python build-slideio.py                   # once per platform; --force to rebuild
python -m build
```

`build-slideio.py` runs the submodule's `install.py -a install` and installs into
`extern/slideio-install`. It is a no-op when that prefix already matches the
checked-out submodule commit, so it is safe to call from scripts. `--config debug`
builds the debug configuration.

### Conan profiles are hardcoded

The Conan profiles under `extern/slideio/conan/` are used exactly as committed.
**No build step ever rewrites them.** They are changed by hand, on demand, and the
change is reviewed and committed like any other.

The submodule ships `sync-toolchain.py`, which detects the host compiler and
rewrites `compiler.version` in every profile (and, on Windows, the CMake generator
string in its `install.py`). Treat it as a **setup tool, not a build step**: run it
manually when preparing a new machine or when a toolchain upgrade genuinely calls
for a different profile, then inspect the diff and commit it. `build-slideio.py`
deliberately never invokes it — a build that mutates tracked files leaves the
submodule dirty, and the script writes whatever the host reports, which the
installed Conan may reject (Apple clang 21 against Conan 2.10 fails with
`Invalid setting '21.0' is not a valid 'settings.compiler.version' value`).

One consequence to keep in mind: the CMake generator in the submodule's
`install.py` is whatever is committed there — currently `Visual Studio 17 2022`. If
a Windows machine or CI runner moves to a newer Visual Studio, that line has to be
updated in the submodule.

Linux wheel builds are intended to run inside the manylinux Docker containers
(`docker/`, images `booritas/slideio-manylinux_2_28_*`), which ship a prebuilt
Conan cache for slideio's dependencies.

### Multi-version wheel builds

- All three scripts call `build-slideio.py` once before their Python-version loop; the loop itself only ever rebuilds the extension, never the C++ library.
- `build-wheels-win.ps1` (helpers in `lib.ps1`): loops over Python 3.8–3.14 using conda envs, runs `python -m build`, then `Repair-Naming` fixes the `.pyd` name inside each wheel.
- `build-wheels-manylinux.sh`, `build-wheels-macos.sh` + `repair-wheels.sh`/`rename-macos-wheels.sh` for the other platforms.
- CI: `.github/workflows/{windows,linux,macos}-wheels.yml`, all `workflow_dispatch`-triggered; they check out submodules recursively, cache `~/.conan2`, build the C++ library with `build-slideio.py`, then run the platform's wheel script. No Conan remote and no credentials are involved.

## Version bumps

The slideio C++ version is the `extern/slideio` submodule pin — there is nothing
else to keep in sync. Bump it with:

```bash
git -C extern/slideio fetch origin
git -C extern/slideio checkout <tag-or-sha>
git add extern/slideio
python build-slideio.py --force
```

The Python package MAJOR.MINOR comes from `projectVersion` in `CMakeLists.txt`
and should track the C++ version it is pinned to.
