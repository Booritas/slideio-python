# Design: reference the slideio C++ library as a git submodule

Date: 2026-08-31

## Goal

Replace the Conan package `slideio/2.9.0@slideio/stable` as the standard way this
repository obtains the slideio C++ library with a git submodule at
`extern/slideio`, built from source into a local install prefix.

This ships as version **2.10.0** of the Python package, on branch `v2.10.0`.

The `SLIDEIO_INSTALL_DIR` environment override stays; the Conan path for slideio
itself goes away, together with the private Conan remote, the
`Booritas/conan-center-index` fork checkout and the scripts that drive them.

## Why this is feasible now

Three facts established while exploring both repositories:

1. **The C++ repository has already made the same migration.** Its `CLAUDE.md`
   records that every remaining dependency resolves from **conan center** — no
   private remote, no conan-center-index fork needed to bootstrap — and that the
   four dependencies that cannot come from conan center (`jpegxrcodec`, `pole`,
   `ndpi-tiff`, `ndpi-libjpeg-turbo`) are already git submodules under
   `slideio/extern/`.

2. **The binding layer's coupling to slideio is thin.** `src/*.cpp` includes only
   `<slideio/...>` public headers and pybind11 (`src/pybind.cpp:13`,
   `src/pyglobals.cpp:5`); no OpenCV, no third-party headers. It links four shared
   libraries — `slideio`, `slideio-converter`, `slideio-transformer`,
   `slideio-core`. None of slideio's ~15 Conan dependencies reach the Python
   extension's compile or link step.

3. **`SLIDEIO_INSTALL_DIR` already consumes exactly what the C++ repo installs.**
   `CMakeLists.txt:50-53` wants `include/`, `lib/` and `bin/`; the C++ repo's
   install rules produce precisely that layout, and its
   `install.py -a install -pr <prefix>` already accepts an external prefix.

`slideio/docker/manylinux_2_28_x86_64/Dockerfile` documents this usage directly:
mount a working copy, run `python3 install.py -a install -c release`, dependencies
are already in `~/.conan2`, and nothing needs a Conan remote or credentials.

## Decision: install prefix, not `add_subdirectory`

The submodule is built by its own build system into
`extern/slideio-install/`, and this repository consumes that prefix through the
existing prefix-based CMake path.

Rationale — two constraints rule out nesting slideio in this repository's CMake
graph:

- **The wheel loops wipe the build tree.** `build-wheels-macos.sh` and
  `build-wheels-manylinux.sh` both `rm -rf ./build` before each of ~7 Python
  versions. The C++ library is Python-version-independent, so it must be built
  once and live outside `./build`. `add_subdirectory` would recompile slideio and
  its whole Conan graph seven times per platform.
- **`setup.py` moves rather than copies.** `setup.py:186` does `shutil.move` on
  every shared library it finds under the build tree. With an in-tree build that
  evacuates freshly built artifacts from the CMake output directory. It works
  today only because a `PRE_BUILD` custom command re-copies them from the Conan
  package on each run.

Alternatives rejected:

- **`add_subdirectory(extern/slideio)`** — a single CMake graph, but on top of the
  two constraints above it needs upstream changes in the C++ repository (guards to
  skip `tests`/`tools`, which pull gtest and cli11), RPATH reconciliation
  (`@executable_path` in the C++ root vs `@loader_path` here) and a `setup.py`
  fix. More moving parts for no gain, since the extension needs nothing from
  slideio's dependency graph.
- **Submodule plus local `conan create`** — keeps Conan's binary cache and drops
  the conan-center-index fork, but requires writing a new recipe into the C++
  repository and keeps a Conan step in the flow. The C++ repository deliberately
  moved away from private packages; adding one back is the wrong direction.

## Dependency resolution order

`CMakeLists.txt` collapses from two branches to one prefix-based branch. Both
current branches already consume the same `include/ lib/ bin/` shape, so the Conan
branch (`find_package(slideio)`, `slideio::slideio`, the `slideio_BIN_DIRS_*`
globs) disappears entirely.

1. `SLIDEIO_INSTALL_DIR` environment variable, when set — wins, unchanged
   behaviour, so developing against an out-of-tree local slideio build keeps
   working.
2. Otherwise `${CMAKE_CURRENT_SOURCE_DIR}/extern/slideio-install`, when present.
3. Otherwise `FATAL_ERROR` naming `build-slideio.py` and the submodule init
   command.

## Build sequence

```
git submodule update --init --recursive     # slideio + its 4 nested extern/ submodules

python build-slideio.py                     # ONCE per platform
  |- extern/slideio/sync-toolchain.py
  '- extern/slideio/install.py -a install -c release
        -bd extern/slideio/build  -pr <repo>/extern/slideio-install
              -> include/  lib/  bin/

for py in 3.8 .. 3.14:                      # loop otherwise unchanged
  rm -rf ./build && python -m build
        -> cmake reads <prefix>/include, links <prefix>/lib
        -> PRE_BUILD copies <prefix>/bin/* beside slideiopybind
        -> setup.py collects them into slideio/core/libs
```

## Changes

**In this repository:**

1. **`.gitmodules` + `extern/slideio`** — new submodule,
   `https://github.com/Booritas/slideio.git`, pinned at a commit on the release
   branch matching this package's MAJOR.MINOR. HTTPS rather than the C++ repo's
   own SSH remote, so `actions/checkout` can fetch it without a key.

   Pinned at `bd112f8c3e531f5027f686fe7d98f01e15df9309`, the tip of
   `origin/v2.10.0` in the C++ repository. This migration ships as part of the
   2.10.0 release, so `projectVersion` in `CMakeLists.txt` moves from `2.9` to
   `2.10` in the same change.
2. **`CMakeLists.txt`** — single prefix branch per the resolution order above.
3. **`build-slideio.py`** — new root script: verify the submodule is initialised,
   run its `sync-toolchain.py`, then its `install.py -a install -c release` into
   the prefix. Idempotent; `--force` rebuilds. Accepts `--config debug`.
4. **`setup.py`** — `shutil.move` becomes `shutil.copy2`, so a rebuild in a warm
   tree is not left with an emptied CMake output directory.
5. **`.github/workflows/{windows,linux,macos}-wheels.yml`** — remove the
   `conan-center-index` checkout, `conan remote add`/`auth`, the package-upload
   steps and the `CONAN_*` secrets; set `submodules: recursive`; add the
   `build-slideio.py` step; cache `~/.conan2` keyed on the submodule SHA plus the
   submodule's Conan profiles; bump the Linux container from
   `booritas/slideio-manylinux_2_28_x86_64:2.8.0` to a tag built from the
   Dockerfile that ships the prebuilt Conan cache (the C++ repository's
   `docker-manylinux_2_28_x86_64.yml` currently defaults that tag to `2.10.0`;
   confirm the published tag before pinning it).
6. **`build-wheels-macos.sh`, `build-wheels-manylinux.sh`, `build-wheels-win.ps1`**
   — build slideio before the Python-version loop, never inside it.
7. **Deletions** — `conanfile.txt`, the `conan/` profile tree (the submodule
   carries its own), `conan.sh`, `conan.ps1`, `conan-one.sh`, `conan-one.ps1`,
   `build-dependencies.ps1`, `build-dependencies.sh`, `install.py` (its only
   remaining job is Conan generation for a conanfile that no longer exists), and
   `helper.cmake` — already dead code, since `FIX_MACOS_RPATH` is never invoked
   here and `NAME_TOOL_LIB_LIST` is never set in this repository.
8. **`CLAUDE.md`, `README.md`** — document the new flow. The "Version bumps"
   section becomes obsolete: the submodule pin is the version, so the
   `conanfile.txt` / `build-dependencies.ps1` / `conan.sh` drift it warns about
   (they are already drifted — 2.9.0 against 2.7.4) cannot recur.

**In the slideio C++ repository: no changes required.**

## Risks

- **Nested submodule fetch.** slideio's `extern/*` URLs carry a `Booritas@`
  userinfo prefix. `submodules: true` is proven at the first level by the C++
  repository's own `build-validation.yml`; recursive fetch from one level up is
  unproven and must be verified in CI early, before the rest of the workflow
  changes are written.
- **Cold CI build time.** The first run on a fresh runner compiles the whole Conan
  graph from source. Mitigated by the `~/.conan2` cache and, on Linux, by the
  newer manylinux image.
- **macOS RPATH.** The prefix path is the existing `SLIDEIO_INSTALL_DIR` code path
  and therefore known-good in principle, but CI currently exercises the Conan path
  instead, so both arm64 and x86_64 need explicit verification.
- **Regulatory.** Changing how a released component's binaries are produced is a
  build and configuration-management change under IEC 62304 clause 8. Depending on
  how slideio is classified in the device file it may count as a design change
  requiring re-validation and QMS documentation. This cannot be determined from the
  repository; confirm with GRC / Regulatory Affairs before release.

## Testing

There is no test suite in this repository — tests live in the C++ repository — so
acceptance is a build-and-smoke gate, run on all three platforms:

1. Build a wheel.
2. Install it into a clean virtualenv, `import slideio`, open a sample slide and
   read a block.
3. **Diff the wheel's `slideio/core/libs` file listing against a wheel built the
   current (Conan) way.** The file set must match, or every difference must be
   explained.

Step 3 is the substantive check: it is what catches a missing driver library or a
dropped runtime DLL, which an `import` alone would not.
