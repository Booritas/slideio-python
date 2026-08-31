# SlideIO Submodule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Conan package `slideio/2.9.0@slideio/stable` with a git submodule at `extern/slideio`, built into a local install prefix, and ship it as version 2.10.0.

**Architecture:** The submodule is built by its *own* build system (`extern/slideio/install.py`) into `extern/slideio-install/`, which this repository consumes through the prefix-based CMake path that `SLIDEIO_INSTALL_DIR` already exercises. The Python extension links four slideio shared libraries and includes only slideio public headers, so none of slideio's Conan dependencies reach this repository's compile or link step. The C++ library is built **once per platform**, outside `./build`, because the wheel loops `rm -rf ./build` before each of ~7 Python versions.

**Tech Stack:** CMake 3.10+, pybind11 (submodule), setuptools + `python -m build`, Conan 2 (used only inside the submodule's own build), GitHub Actions, manylinux Docker.

**Spec:** `docs/superpowers/specs/2026-08-31-slideio-submodule-design.md`

## Global Constraints

- Branch: **`v2.10.0`** (already created). All work lands here, never on `main`.
- Submodule pin: `https://github.com/Booritas/slideio.git` at commit **`bd112f8c3e531f5027f686fe7d98f01e15df9309`** (tip of `origin/v2.10.0`).
- Package version: `projectVersion` in `CMakeLists.txt` becomes **`2.10`**. The patch component still comes from `CI_PIPELINE_IID`, defaulting to `0` (`setup.py`).
- Install prefix: **`extern/slideio-install`**, relative to the repository root. It must live outside `./build`.
- Dependency resolution order in `CMakeLists.txt`: `SLIDEIO_INSTALL_DIR` env → `extern/slideio-install` → `FATAL_ERROR`.
- Python versions supported by the wheel loops are unchanged: 3.8–3.14 (3.13 max on macOS Intel).
- **Do not modify the `pybind11` submodule pointer.** The working tree currently has it checked out at an older commit than the recorded one; that is pre-existing and out of scope.
- **Do not modify the slideio C++ repository.** This plan requires no upstream changes.
- There is no test suite in this repository. Verification is build + smoke + wheel-manifest diff, defined in Task 10.

---

### Task 1: Capture the current wheel manifest as the comparison baseline

The acceptance gate in the spec is a diff of the wheel's `slideio/core/libs` file listing against a wheel built the current (Conan) way. That baseline must be captured **before** anything changes, because after the migration the Conan path no longer exists.

**Files:**
- Create: `docs/superpowers/plans/baseline-wheel-manifest.txt`

- [ ] **Step 1: Find an existing wheel to read the baseline from**

Look for a previously built wheel in `dist/` or `wheelhouse/`:

```bash
ls -la dist/*.whl wheelhouse/*.whl 2>/dev/null
```

If one exists, skip to Step 3. If none exists, build one at Step 2.

- [ ] **Step 2: Build one wheel the current (Conan) way, if no wheel exists**

This requires the private Conan remote and is expected to be possible only on a machine already set up for it. Run:

```bash
python install.py -a conan -c release
python -m build
```

If this cannot be run (no Conan remote access, no `slideio/2.9.0@slideio/stable` in the local cache), **do not block**: write the file with the single line `BASELINE UNAVAILABLE` plus a one-line reason, and note in Task 10 that the manifest diff degrades to a manual review of the library list against `extern/slideio-install/bin/`.

- [ ] **Step 3: Extract the library manifest**

```bash
WHL=$(ls -t dist/*.whl wheelhouse/*.whl 2>/dev/null | head -1)
echo "# baseline from: $(basename "$WHL")" > docs/superpowers/plans/baseline-wheel-manifest.txt
unzip -l "$WHL" | awk '{print $4}' | grep 'slideio/core/libs/' | sed 's|.*/||' | sort \
  >> docs/superpowers/plans/baseline-wheel-manifest.txt
cat docs/superpowers/plans/baseline-wheel-manifest.txt
```

Expected: a sorted list of shared library filenames — on macOS `libslideio.dylib`, `libslideio-core.dylib`, `libslideio-svs.dylib`, and so on for all 11 drivers plus `imagetools`, `converter`, `transformer`, plus `slideiopybind*.so`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/baseline-wheel-manifest.txt
git commit -m "chore: capture pre-migration wheel library manifest as baseline"
```

---

### Task 2: Add the slideio submodule and prove the recursive fetch works

The spec flags recursive submodule fetch as the highest-uncertainty item: slideio's own `extern/*` submodule URLs carry a `Booritas@` userinfo prefix, and nothing has yet proven those resolve when fetched one level down. Prove it first, before any other change depends on it.

**Files:**
- Modify: `.gitmodules`
- Create: `extern/slideio` (submodule pointer)
- Modify: `.gitignore`

**Interfaces:**
- Produces: the submodule at `extern/slideio`, whose `install.py`, `sync-toolchain.py` and `conan/` profile tree Task 3 invokes.

- [ ] **Step 1: Add the submodule**

```bash
git submodule add https://github.com/Booritas/slideio.git extern/slideio
git -C extern/slideio checkout bd112f8c3e531f5027f686fe7d98f01e15df9309
```

- [ ] **Step 2: Fetch the nested submodules — this is the risk being tested**

```bash
git submodule update --init --recursive
```

Expected: four nested submodules populate under `extern/slideio/extern/`. Verify:

```bash
git submodule status --recursive
```

Expected output includes all five, none prefixed with `-` (uninitialised):

```
 bd112f8c...  extern/slideio (heads/v2.10.0)
 152b7064...  extern/slideio/extern/jpegxrcodec (v1.0.3-2-g152b706)
 6bb4790c...  extern/slideio/extern/ndpi-libjpeg-turbo (v2.1.2)
 d23311c3...  extern/slideio/extern/ndpi-tiff (v4.3.0)
 3e64e5ae...  extern/slideio/extern/pole (v1.0.4-3-g3e64e5a)
 7c33cdc2...  pybind11 (v2.11.0-172-g7c33cdc2)
```

If any nested submodule fails to clone because of the `Booritas@` prefix, the fix is a URL rewrite rather than editing the upstream `.gitmodules`:

```bash
git config --global url."https://github.com/".insteadOf "https://Booritas@github.com/"
```

Record which of the two happened — the CI workflows in Task 7 need the rewrite step only if it was required here.

**Result on macOS/arm64, 2026-08-31: the plain recursive fetch succeeded. No URL
rewrite was needed, so Task 7 Step 4 does not apply.** Note that `--recursive`
additionally clones a googletest copy nested inside each of `jpegxrcodec` and
`pole`; slideio's own build forces their tests off and does not need them, but
there is no way to exclude them from a recursive fetch. The cost is download time
only.

- [ ] **Step 3: Confirm the CMakeLists the submodule ships is the expected one**

```bash
grep -n 'set(projectVersion' extern/slideio/CMakeLists.txt
```

Expected: `set(projectVersion 2.9.0)`.

This is not a mistake and not the wrong SHA: `bd112f8c` is the tip of
`origin/v2.10.0` (verify with `git ls-remote --heads https://github.com/Booritas/slideio.git`),
but the C++ repository has not yet bumped its own `projectVersion` string on that
branch. The branch identity is what pins the version here. Bumping the C++ repo's
version string is that repository's concern and out of scope for this plan.

Confirm the pin by branch rather than by version string:

```bash
git ls-remote --heads https://github.com/Booritas/slideio.git v2.10.0
```

Expected: `bd112f8c3e531f5027f686fe7d98f01e15df9309	refs/heads/v2.10.0`.

- [ ] **Step 4: Ignore the install prefix**

Append to `.gitignore`:

```
# Local install prefix produced by build-slideio.py from the extern/slideio
# submodule. Generated, never committed.
extern/slideio-install/
```

- [ ] **Step 5: Commit**

```bash
git add .gitmodules extern/slideio .gitignore
git commit -m "build: add slideio C++ library as extern/slideio submodule at 2.10.0"
```

---

### Task 3: Add `build-slideio.py`

The script that builds the submodule into the install prefix. It is the single entry point developers and CI both call.

**Files:**
- Create: `build-slideio.py`

**Interfaces:**
- Consumes: `extern/slideio` from Task 2.
- Produces: `extern/slideio-install/{include,lib,bin}`, which Task 4's `CMakeLists.txt` reads. Command-line surface later tasks call: `python build-slideio.py [--config release|debug] [--force] [--prefix PATH]`.

- [ ] **Step 1: Write the script**

Create `build-slideio.py`:

```python
#!/usr/bin/env python3
"""Build the slideio C++ library from the extern/slideio submodule.

The submodule is built by its own build system into a local install prefix
(extern/slideio-install by default), which CMakeLists.txt then consumes the same
way it consumes SLIDEIO_INSTALL_DIR. The prefix deliberately sits outside ./build,
which the wheel scripts delete once per Python version -- the C++ library does not
depend on the Python version and must be built only once per platform.

    python build-slideio.py                  # release, skip if already built
    python build-slideio.py --force          # rebuild even if the prefix exists
    python build-slideio.py --config debug
"""

import argparse
import os
import shutil
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SUBMODULE_DIR = os.path.join(REPO_DIR, 'extern', 'slideio')
DEFAULT_PREFIX = os.path.join(REPO_DIR, 'extern', 'slideio-install')

# Written into the prefix after a successful build so a later run can tell
# whether the prefix matches the currently checked-out submodule commit.
STAMP_NAME = '.slideio-build-stamp'


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def check_submodule():
    """Stop with an actionable message if the submodule was never initialised."""
    if not os.path.exists(os.path.join(SUBMODULE_DIR, 'CMakeLists.txt')):
        fail(
            "extern/slideio is empty. Run:\n"
            "    git submodule update --init --recursive\n"
            "in the repository root and try again."
        )
    nested = os.path.join(SUBMODULE_DIR, 'extern', 'jpegxrcodec', 'CMakeLists.txt')
    if not os.path.exists(nested):
        fail(
            "extern/slideio/extern/jpegxrcodec is empty -- the nested submodules\n"
            "were not fetched. Run:\n"
            "    git submodule update --init --recursive\n"
            "Note the --recursive: slideio carries four submodules of its own."
        )


def submodule_commit():
    """The commit extern/slideio is currently checked out at."""
    return subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=SUBMODULE_DIR
    ).decode().strip()


def read_stamp(prefix):
    path = os.path.join(prefix, STAMP_NAME)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return f.read().strip()


def write_stamp(prefix, value):
    with open(os.path.join(prefix, STAMP_NAME), 'w', encoding='utf-8') as f:
        f.write(value + '\n')


def run(command, cwd):
    print('+ ' + ' '.join(command), flush=True)
    subprocess.check_call(command, cwd=cwd)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--config', choices=['release', 'debug'], default='release',
                        help='Build configuration (default: release).')
    parser.add_argument('-p', '--prefix', default=DEFAULT_PREFIX,
                        help='Install prefix (default: extern/slideio-install).')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Rebuild even when the prefix is already up to date.')
    parser.add_argument('--skip-toolchain-sync', action='store_true',
                        help="Do not run the submodule's sync-toolchain.py.")
    args = parser.parse_args()

    check_submodule()

    prefix = os.path.abspath(args.prefix)
    commit = submodule_commit()
    stamp = f"{commit} {args.config}"

    if not args.force and read_stamp(prefix) == stamp:
        print(f"slideio {commit[:12]} ({args.config}) already installed in {prefix}.")
        print("Pass --force to rebuild.")
        return

    if args.force and os.path.exists(prefix):
        print(f"Removing {prefix}")
        shutil.rmtree(prefix)

    build_dir = os.path.join(SUBMODULE_DIR, 'build')

    print(f"Building slideio {commit[:12]} ({args.config}) into {prefix}")

    if not args.skip_toolchain_sync:
        # Aligns the submodule's conan profiles with the host compiler. On
        # Windows it also rewrites the CMake generator string in its install.py.
        run([sys.executable, 'sync-toolchain.py'], cwd=SUBMODULE_DIR)

    run([sys.executable, 'install.py',
         '-a', 'install',
         '-c', args.config,
         '-bd', build_dir,
         '-pr', prefix], cwd=SUBMODULE_DIR)

    for required in ('include', 'lib', 'bin'):
        if not os.path.isdir(os.path.join(prefix, required)):
            fail(f"{prefix} has no {required}/ directory -- the install did not "
                 f"produce the expected layout.")

    write_stamp(prefix, stamp)
    print(f"slideio installed into {prefix}")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify the guard fires when the submodule is missing**

Temporarily move the submodule aside and confirm the error is the actionable one:

```bash
mv extern/slideio /tmp/slideio-stash && python build-slideio.py ; mv /tmp/slideio-stash extern/slideio
```

Expected: exits non-zero with `ERROR: extern/slideio is empty. Run: git submodule update --init --recursive`.

- [ ] **Step 3: Run the real build**

```bash
python build-slideio.py --config release
```

Expected: Conan resolves the graph from conan center (no remote, no credentials), CMake configures, the library builds, and the run ends with `slideio installed into .../extern/slideio-install`. This is a cold full build of the whole dependency graph and can take a long time on a fresh machine.

- [ ] **Step 4: Verify the produced layout**

```bash
ls extern/slideio-install
ls extern/slideio-install/include/slideio
ls extern/slideio-install/bin | head -30
```

Expected: `bin  include  lib` (plus the stamp file); `include/slideio` contains `core converter imagetools slideio transformer`; `bin` contains the slideio shared libraries including all 11 drivers.

- [ ] **Step 5: Verify the idempotence check**

```bash
python build-slideio.py --config release
```

Expected: prints `already installed` and exits immediately without rebuilding.

- [ ] **Step 6: Commit**

```bash
git add build-slideio.py
git commit -m "build: add build-slideio.py to build the submodule into a local prefix"
```

---

### Task 4: Rewrite the dependency resolution in `CMakeLists.txt`

Collapse the two dependency branches into one. Both current branches already consume the same `include/ lib/ bin/` shape, so the Conan branch disappears entirely.

**Files:**
- Modify: `CMakeLists.txt` (`projectVersion` at line 6; the env/prefix block at lines 9-15; the include/link-dir block at lines 50-55; `include(helper.cmake)` at line 86; the link block at lines 88-97; the binary-copy block at lines 107-127)
- Delete: `helper.cmake`

**Interfaces:**
- Consumes: `extern/slideio-install` from Task 3, or `SLIDEIO_INSTALL_DIR` from the environment.
- Produces: a `slideiopybind` target whose build directory contains the slideio shared libraries, which `setup.py` then collects.

- [ ] **Step 1: Bump the project version**

Replace line 6 of `CMakeLists.txt`:

```cmake
set(projectVersion 2.9)
```

with:

```cmake
set(projectVersion 2.10)
```

- [ ] **Step 2: Replace the resolution block**

Replace lines 9-15 (the `if(DEFINED ENV{SLIDEIO_INSTALL_DIR}) ... endif()` block near the top that also sets `CMAKE_PREFIX_PATH`/`CMAKE_MODULE_PATH`) with:

```cmake
# The slideio C++ library is resolved from an install prefix -- include/, lib/
# and bin/ -- in one of two ways:
#
#   1. SLIDEIO_INSTALL_DIR in the environment, for developing against a slideio
#      build that lives outside this repository. It always wins when set.
#   2. Otherwise extern/slideio-install, produced by build-slideio.py from the
#      extern/slideio submodule. This is the standard path.
#
# There is no longer a conan branch: slideio itself is no longer consumed as a
# conan package, so this repository needs no conan remote and no conanfile. The
# submodule's own build still uses conan for slideio's dependencies, but that is
# entirely internal to extern/slideio.
if(DEFINED ENV{SLIDEIO_INSTALL_DIR})
    set(SLIDEIO_INSTALL_DIR $ENV{SLIDEIO_INSTALL_DIR})
    message(STATUS "slideio from SLIDEIO_INSTALL_DIR: ${SLIDEIO_INSTALL_DIR}")
else()
    set(SLIDEIO_INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/extern/slideio-install)
    message(STATUS "slideio from submodule prefix: ${SLIDEIO_INSTALL_DIR}")
endif()

if(NOT EXISTS ${SLIDEIO_INSTALL_DIR}/include/slideio)
    message(FATAL_ERROR
        "No slideio installation at ${SLIDEIO_INSTALL_DIR}.\n"
        "Build it from the submodule:\n"
        "    git submodule update --init --recursive\n"
        "    python build-slideio.py\n"
        "or point SLIDEIO_INSTALL_DIR at an existing slideio install prefix.")
endif()
```

- [ ] **Step 3: Simplify the include/link directory block**

Replace lines 50-55 (the second `if(DEFINED SLIDEIO_INSTALL_DIR) ... find_package(slideio) ... endif()`) with the unconditional form:

```cmake
include_directories(${SLIDEIO_INSTALL_DIR}/include)
link_directories(${SLIDEIO_INSTALL_DIR}/lib)
```

- [ ] **Step 4: Simplify the link libraries block**

Replace lines 88-97 (`if(DEFINED SLIDEIO_INSTALL_DIR) ... slideio::slideio ... endif()`) with:

```cmake
target_link_libraries(${LIBRARY_NAME} PRIVATE
    slideio
    slideio-converter
    slideio-transformer
    slideio-core
)
```

- [ ] **Step 5: Simplify the binary-copy block**

Replace the whole trailing `if(DEFINED SLIDEIO_INSTALL_DIR) ... else() ... endif()` block (lines 107-127, to the end of the file) with:

```cmake
# Stage the slideio runtime next to the extension so setup.py can collect both
# into slideio/core/libs. Globbed at configure time: re-run cmake after
# rebuilding the submodule if the set of libraries changed.
file(GLOB SLIDEIO_BIN_FILES ${SLIDEIO_INSTALL_DIR}/bin/*.*)
add_custom_command(TARGET ${LIBRARY_NAME} PRE_BUILD
   COMMAND ${CMAKE_COMMAND} -E copy
   ${SLIDEIO_BIN_FILES}
   "$<TARGET_FILE_DIR:${LIBRARY_NAME}>"
   COMMAND_EXPAND_LISTS
   VERBATIM
)
```

Note the change from `$ENV{SLIDEIO_INSTALL_DIR}` to `${SLIDEIO_INSTALL_DIR}` — the old code read the environment variable directly here, which would glob nothing on the submodule path.

- [ ] **Step 6: Remove the dead helper**

`helper.cmake` defines `FIX_MACOS_RPATH`, which is never invoked in this repository, and which reads `NAME_TOOL_LIB_LIST`, which is never set here.

```bash
git rm helper.cmake
```

Then delete the `include(helper.cmake)` line (line 86) from `CMakeLists.txt`.

- [ ] **Step 7: Verify the FATAL_ERROR path**

```bash
mv extern/slideio-install /tmp/prefix-stash
rm -rf /tmp/cmake-probe && cmake -S . -B /tmp/cmake-probe 2>&1 | tail -20
mv /tmp/prefix-stash extern/slideio-install
```

Expected: configure fails with `No slideio installation at .../extern/slideio-install` followed by the `build-slideio.py` instructions.

- [ ] **Step 8: Verify a real configure and build**

```bash
rm -rf /tmp/cmake-probe
cmake -S . -B /tmp/cmake-probe -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/cmake-probe --target slideiopybind -j4
```

Expected: `slideio from submodule prefix: .../extern/slideio-install` in the configure output, then a successful build producing `slideiopybind*.so` with the slideio libraries copied beside it. Verify:

```bash
find /tmp/cmake-probe -name 'slideiopybind*' -o -name 'libslideio*' | head -20
```

- [ ] **Step 9: Commit**

```bash
git add CMakeLists.txt
git commit -m "build: resolve slideio from the submodule prefix, drop the conan branch"
```

`helper.cmake` was already staged for deletion by the `git rm` in Step 6.

---

### Task 5: Fix `setup.py` to copy rather than move

Two changes. First, `setup.py` currently `shutil.move`s every shared library out of the CMake output directory into the wheel staging directory. That works today only because the `PRE_BUILD` custom command re-copies them on each run — a second `python -m build` against a warm tree where CMake considers the target up to date would produce a wheel missing its libraries. Copying is correct regardless.

**Files:**
- Modify: `setup.py:113-116` (dead conan toolchain block), `setup.py:177` (the move)

- [ ] **Step 1: Remove the dead conan toolchain block**

After Task 4 there is no `cmake/conan_toolchain.cmake` in this repository, and a stale one left over in a developer's tree would now be picked up and applied to a build that must not use it. Delete lines 113-116 of `setup.py`:

```python
        # Only use conan toolchain if SLIDEIO_INSTALL_DIR is not defined
        if not os.environ.get('SLIDEIO_INSTALL_DIR'):
            toolchain_path = './cmake/conan_toolchain.cmake'
            if os.path.exists(os.path.join(ext.source_dir, toolchain_path)):
                cmake_args.append('-DCMAKE_TOOLCHAIN_FILE=' + toolchain_path)
```

Leave the surrounding `cmake_args` construction intact.

- [ ] **Step 2: Change the move to a copy**

In `setup.py`, in the loop that stages `extra_files` into `wheel_lib_dir`, replace:

```python
        for fl in extra_files:
            file_name = os.path.basename(fl)
            destination = os.path.join(wheel_lib_dir, file_name)
            print("Copy", fl, "->", destination)
            shutil.move(fl, destination)
```

with:

```python
        for fl in extra_files:
            file_name = os.path.basename(fl)
            destination = os.path.join(wheel_lib_dir, file_name)
            print("Copy", fl, "->", destination)
            # copy2, not move: the libraries must stay in the CMake output
            # directory. A second build in a warm tree does not re-run the
            # PRE_BUILD staging command when the target is already up to date,
            # and a moved library would leave the next wheel without it.
            shutil.copy2(fl, destination)
```

- [ ] **Step 3: Verify a wheel builds and contains the libraries**

```bash
rm -rf build dist && python -m build --wheel
unzip -l dist/*.whl | grep 'slideio/core/libs/' | head -30
```

Expected: the extension module plus the slideio shared libraries.

- [ ] **Step 4: Verify the second build in a warm tree also works — this is the regression being fixed**

```bash
rm -rf dist && python -m build --wheel   # note: ./build is NOT removed
unzip -l dist/*.whl | grep -c 'slideio/core/libs/'
```

Expected: the same non-zero count as Step 3. Before this change, the count would drop.

- [ ] **Step 5: Commit**

```bash
git add setup.py
git commit -m "build: copy staged libraries and drop the dead conan toolchain hook"
```

---

### Task 6: Delete the Conan machinery and update the packaging manifest

Everything that existed only to obtain `slideio/*@slideio/stable` from the private remote.

**Files:**
- Delete: `conanfile.txt`, `conan/` (whole tree), `conan.sh`, `conan.ps1`, `conan-one.sh`, `conan-one.ps1`, `build-dependencies.ps1`, `build-dependencies.sh`, `install.py`
- Modify: `MANIFEST.in`

- [ ] **Step 1: Confirm nothing else references what is being deleted**

```bash
grep -rn "conanfile\|install\.py\|helper\.cmake\|conan-one\|build-dependencies\|SLIDEIO_PYTHON_HOME\|CONAN_INDEX_HOME" \
  --include='*.py' --include='*.sh' --include='*.ps1' --include='*.yml' --include='*.in' \
  --include='*.toml' --include='*.cmake' --include='*.txt' --include='*.md' \
  . | grep -v '^./extern/' | grep -v '^./pybind11/' | grep -v '^./docs/superpowers/'
```

Expected remaining hits are only in the files this task and Task 7 and Task 9 modify: `MANIFEST.in`, the three workflow files, `README.md`, `CLAUDE.md`. Anything else is an unplanned dependency — stop and reassess.

Note `install.py` here is *this repository's* copy. The submodule's `extern/slideio/install.py` is a different file and stays.

- [ ] **Step 2: Delete the files**

```bash
git rm conanfile.txt conan.sh conan.ps1 conan-one.sh conan-one.ps1 \
       build-dependencies.ps1 build-dependencies.sh install.py
git rm -r conan
```

- [ ] **Step 3: Update `MANIFEST.in`**

It currently references two deleted files (`helper.cmake`, `conanfile.txt`) and a directory that no longer holds anything tracked (`cmake/`, which is gitignored and only ever contained Conan-generated files). Replace the whole file with:

```
include CMakeLists.txt
include build-slideio.py
recursive-include src *.cpp *.hpp *.h
recursive-include pybind11 *.h *.hpp *.cmake CMakeLists.txt
```

The sdist deliberately does not carry `extern/slideio`: an sdist could not build the C++ library from its own contents before this change either, and vendoring the full slideio source tree into every sdist is not the intent.

- [ ] **Step 4: Verify the extension still builds from a clean tree**

```bash
rm -rf build dist && python -m build --wheel
unzip -l dist/*.whl | grep -c 'slideio/core/libs/'
```

Expected: a successful build with the same library count as Task 5.

- [ ] **Step 5: Commit**

```bash
git add -A MANIFEST.in
git commit -m "build: remove the conan machinery for the slideio package"
```

---

### Task 7: Update the three CI workflows

**Files:**
- Modify: `.github/workflows/linux-wheels.yml`
- Modify: `.github/workflows/macos-wheels.yml`
- Modify: `.github/workflows/windows-wheels.yml`

Each workflow gets the same five changes:

1. Remove the `build-conan-packages` and `upload-conan-packages` `workflow_dispatch` inputs.
2. Remove the `CONAN_LOGIN_USERNAME`, `CONAN_PASSWORD`, `CONAN_SERVER` and `CONAN_INDEX_HOME` env entries. Keep `CONAN_REVISIONS_ENABLED` and `CONAN_DISABLE_CHECK_COMPILER` — the submodule's build still uses Conan. Keep `SLIDEIO_HOME`.
3. Change `submodules: 'true'` to `submodules: 'recursive'`, and remove the `conan-center-index` checkout step.
4. Remove the `conan remote add` / `conan remote auth` steps, the "Install conan packages from conan-center-index" steps and the "Upload conan packages" steps.
5. Replace the `python install.py -a conan -c release` step with a `~/.conan2` cache step plus `python build-slideio.py -c release`.

- [ ] **Step 1: Rewrite `.github/workflows/linux-wheels.yml`**

```yaml
name: Linux Wheels

on:
  workflow_dispatch:

env:
  CONAN_REVISIONS_ENABLED: 1
  CONAN_DISABLE_CHECK_COMPILER: 1
  SLIDEIO_HOME: ${{ github.workspace }}/slideio

jobs:
  build-linux:
    runs-on: ubuntu-latest
    container:
      image: booritas/slideio-manylinux_2_28_x86_64:2.10.0

    steps:
    - name: checkout the repository
      uses: actions/checkout@v4
      with:
        submodules: 'recursive'
        path: slideio

    - name: cache conan packages
      uses: actions/cache@v4
      with:
        path: ~/.conan2
        key: conan-manylinux-${{ hashFiles('slideio/.git/modules/extern/slideio/HEAD') }}
        restore-keys: |
          conan-manylinux-

    - name: build the slideio C++ library
      shell: bash -el {0}
      working-directory: slideio
      run: |
        python3 build-slideio.py -c release

    - name: build wheels
      shell: bash -el {0}
      working-directory: slideio
      run: |
        ./build-wheels-manylinux.sh

    - uses: actions/upload-artifact@v4
      with:
          name: wheels
          path: ./slideio/wheelhouse
```

The container tag moves from `2.8.0` to `2.10.0` — the image that ships a prebuilt Conan cache, which is what makes a from-source slideio build in CI affordable. **Before committing, confirm that tag is published:**

```bash
docker manifest inspect booritas/slideio-manylinux_2_28_x86_64:2.10.0 >/dev/null && echo PUBLISHED || echo MISSING
```

If it reports `MISSING`, keep `2.8.0` and add a `# TODO` comment naming the missing tag — the older image still has the toolchain, it just builds the Conan graph from source the first time.

- [ ] **Step 2: Rewrite `.github/workflows/macos-wheels.yml`**

```yaml
name: Build Macos Wheels

on:
  workflow_dispatch:
    inputs:
      os:
        description: 'Operating System'
        required: true
        default: 'macos-14'
        type: choice
        options:
          - macos-14
          - macos-15-intel

env:
  CONAN_REVISIONS_ENABLED: 1
  CONAN_DISABLE_CHECK_COMPILER: 1
  SLIDEIO_HOME: ${{ github.workspace }}/slideio

jobs:
  build-mac-wheels:
    runs-on: ${{ github.event.inputs.os }}
    steps:
    - name: Setup cmake
      uses: jwlawson/actions-setup-cmake@v2
      with:
        cmake-version: '3.31.9'

    - name: display cmake version
      run: cmake --version

    - name: checkout the repository
      uses: actions/checkout@v4
      with:
        submodules: 'recursive'
        path: slideio

    - uses: conda-incubator/setup-miniconda@v3
      with:
        auto-activate-base: true
        activate-environment: ""

    - name: Create conan2 conda environment
      shell: bash -el {0}
      run: |
        conda create -n conan2 python=3.12 -y
        conda activate conan2
        python -m pip install conan distro
        conan --version
        conda deactivate

    - name: cache conan packages
      uses: actions/cache@v4
      with:
        path: ~/.conan2
        key: conan-${{ runner.os }}-${{ runner.arch }}-${{ hashFiles('slideio/.git/modules/extern/slideio/HEAD') }}
        restore-keys: |
          conan-${{ runner.os }}-${{ runner.arch }}-

    - name: build the slideio C++ library
      shell: bash -el {0}
      working-directory: slideio
      run: |
        conda activate conan2
        python build-slideio.py -c release
        conda deactivate

    - name: Build wheels
      working-directory: slideio
      shell: bash -el {0}
      run: |
        ./build-wheels-macos.sh
        ./rename-macos-wheels.sh ./dist

    - uses: actions/upload-artifact@v4
      with:
        path: ./slideio/dist/*.whl
```

Note `distro` added to the pip install: the submodule's `install.py` imports it on Linux and its absence is a silent behaviour change rather than an error, so installing it everywhere is the safe form.

- [ ] **Step 3: Rewrite `.github/workflows/windows-wheels.yml`**

```yaml
name: Build Windows Wheels

on:
  workflow_dispatch:

env:
  CONAN_REVISIONS_ENABLED: 1
  CONAN_DISABLE_CHECK_COMPILER: 1
  SLIDEIO_HOME: ${{ github.workspace }}/slideio

jobs:
  build-win:
    runs-on: windows-2022

    steps:
    - name: Setup cmake
      uses: jwlawson/actions-setup-cmake@v2

    - name: display cmake version
      run: cmake --version

    - name: checkout the repository
      uses: actions/checkout@v4
      with:
        submodules: 'recursive'
        path: slideio

    - uses: conda-incubator/setup-miniconda@v3
      with:
        auto-activate-base: true
        activate-environment: ""

    - name: Create conan2 conda environment
      shell: pwsh
      run: |
        conda create -n conan2 python=3.12 -y
        conda activate conan2
        python -m pip install conan distro
        conan --version
        conda deactivate

    - name: cache conan packages
      uses: actions/cache@v4
      with:
        path: ~/.conan2
        key: conan-windows-${{ hashFiles('slideio/.git/modules/extern/slideio/HEAD') }}
        restore-keys: |
          conan-windows-

    - name: build the slideio C++ library
      shell: pwsh
      working-directory: slideio
      run: |
        conda activate conan2
        python build-slideio.py -c release
        conda deactivate

    - name: Build python wheels
      shell: pwsh
      working-directory: slideio
      run: |
        ./build-wheels-win.ps1

    - uses: actions/upload-artifact@v4
      with:
        path: ./slideio/dist/*.whl
```

- [ ] **Step 4: If Task 2 Step 2 needed the URL rewrite, add it to all three workflows**

Only if the nested submodule fetch failed without it. Insert *before* each checkout step:

```yaml
    - name: rewrite submodule URLs
      run: git config --global url."https://github.com/".insteadOf "https://Booritas@github.com/"
```

- [ ] **Step 5: Validate the YAML parses**

```bash
python3 -c "
import yaml, glob
for f in sorted(glob.glob('.github/workflows/*.yml')):
    yaml.safe_load(open(f))
    print('OK', f)
"
```

Expected: `OK` for all three.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows
git commit -m "ci: build slideio from the submodule, drop the private conan remote"
```

---

### Task 8: Build the C++ library once, outside the Python-version loop

The three wheel scripts each `rm -rf ./build` per Python version. They must not rebuild slideio each time — and after Task 4 they cannot, since the prefix is outside `./build`. This task makes each script build the prefix once up front so a developer running the script directly gets a working build without a separate manual step.

**Files:**
- Modify: `build-wheels-manylinux.sh`
- Modify: `build-wheels-macos.sh`
- Modify: `build-wheels-win.ps1`

- [ ] **Step 1: `build-wheels-manylinux.sh`**

After `set -e` and before `rm -rf ./dist`, insert:

```bash
# The C++ library does not depend on the Python version. Build it once, into
# extern/slideio-install, before the loop below starts deleting ./build.
# No-op when the prefix already matches the checked-out submodule commit.
python3 build-slideio.py -c release
```

- [ ] **Step 2: `build-wheels-macos.sh`**

After the `eval "$(conda shell.bash hook)"` line and before the `for version in ...` loop, insert the same block:

```bash
# The C++ library does not depend on the Python version. Build it once, into
# extern/slideio-install, before the loop below starts deleting ./build.
# No-op when the prefix already matches the checked-out submodule commit.
python3 build-slideio.py -c release
```

- [ ] **Step 3: `build-wheels-win.ps1`**

After the `. .\lib.ps1` line and before `Remove-Item -Path .\dist ...`, insert:

```powershell
# The C++ library does not depend on the Python version. Build it once, into
# extern\slideio-install, before Build-Wheels starts deleting .\build.
# No-op when the prefix already matches the checked-out submodule commit.
python build-slideio.py -c release
if ($LASTEXITCODE -ne 0) { throw "build-slideio.py failed" }
```

- [ ] **Step 4: Remove the now-pointless `conan` pip installs from the wheel loops**

The per-Python-version environments no longer run Conan — only `build-slideio.py` does, and it runs outside them.

In `build-wheels-macos.sh`, delete the line `python -m pip install conan` inside the loop.
In `lib.ps1`, in `Build-Wheels`, delete the line `python -m pip install conan`.

- [ ] **Step 5: Verify the loop is a no-op on the second entry**

```bash
python3 build-slideio.py -c release && python3 build-slideio.py -c release
```

Expected: the first may build, the second prints `already installed` and returns immediately. This is what makes the per-version loop cheap.

- [ ] **Step 6: Commit**

```bash
git add build-wheels-manylinux.sh build-wheels-macos.sh build-wheels-win.ps1 lib.ps1
git commit -m "build: build the C++ library once, before the python-version loop"
```

---

### Task 9: Update the documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: `CLAUDE.md` — replace the dependency sentence in "What this repository is"**

Replace:

```
The C++ library itself lives in a separate repository ([Booritas/slideio](https://github.com/Booritas/slideio)) and is consumed here as a prebuilt Conan package (see `conanfile.txt`, currently `slideio/2.9.0@slideio/stable`) or from a local install via the `SLIDEIO_INSTALL_DIR` environment variable.

`pybind11` is a git submodule — clone with `--recursive` or run `git submodule update --init`.
```

with:

```
The C++ library itself lives in a separate repository ([Booritas/slideio](https://github.com/Booritas/slideio)) and is consumed here as the `extern/slideio` git submodule, built from source into `extern/slideio-install/` by `build-slideio.py`. Setting `SLIDEIO_INSTALL_DIR` overrides that and points the build at any other slideio install prefix.

Two git submodules: `pybind11` and `extern/slideio`. slideio carries four submodules of its own, so `--recursive` is required, not optional — clone with `--recurse-submodules` or run `git submodule update --init --recursive`.
```

- [ ] **Step 2: `CLAUDE.md` — replace the whole "Build system" section body**

Replace the paragraph beginning `setup.py defines a CMakeBuild extension command...` and the two bullets under it with:

```
`setup.py` defines a `CMakeBuild` extension command that invokes CMake (Visual Studio 17 2022 / x64 on Windows, Makefiles elsewhere). CMake resolves the slideio C++ library from an install prefix — `include/`, `lib/`, `bin/` — in one of two ways:

- **`SLIDEIO_INSTALL_DIR` set** → that prefix is used, for developing against a slideio build outside this repository.
- **Otherwise** → `extern/slideio-install`, produced by `build-slideio.py` from the `extern/slideio` submodule. Configure fails with an actionable `FATAL_ERROR` if it is absent.

There is no Conan step in this repository: slideio is no longer a Conan package here, so no remote, no credentials and no `conanfile.txt`. The submodule's own build still uses Conan for slideio's dependencies — all of which resolve from conan center — but that is internal to `extern/slideio`.

The package version is read from `set(projectVersion MAJOR.MINOR ...)` in `CMakeLists.txt`, with the patch part taken from `CI_PIPELINE_IID` (defaults to `0`).
```

- [ ] **Step 3: `CLAUDE.md` — replace the "Typical local build (Windows)" block**

Replace the PowerShell block and the paragraph after it with:

````
### Typical local build (any platform)

```bash
git submodule update --init --recursive   # pybind11 + extern/slideio + its four
python build-slideio.py                   # once per platform; --force to rebuild
python -m build
```

`build-slideio.py` runs the submodule's own `sync-toolchain.py` and
`install.py -a install`, installing into `extern/slideio-install`. It is a no-op
when that prefix already matches the checked-out submodule commit, so it is safe
to call from scripts. `--config debug` builds the debug configuration.

Linux wheel builds are intended to run inside the manylinux Docker containers
(`docker/`, images `booritas/slideio-manylinux_2_28_*`), which ship a prebuilt
Conan cache for slideio's dependencies.
````

- [ ] **Step 4: `CLAUDE.md` — update the multi-version wheel bullets and delete two sections**

In "Multi-version wheel builds", add as the first bullet:

```
- All three scripts call `build-slideio.py` once before their Python-version loop; the loop itself only ever rebuilds the extension, never the C++ library.
```

In the CI bullet, replace the text after `all `workflow_dispatch`-triggered;` with:

```
they check out submodules recursively, cache `~/.conan2`, build the C++ library with `build-slideio.py`, then run the platform's wheel script. No Conan remote and no credentials are involved.
```

Delete the **"Conan profiles"** section entirely — the profiles now live in the submodule.

Replace the whole **"Version bumps"** section with:

```
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
```

- [ ] **Step 5: `README.md` — replace the manylinux build instructions**

Replace the whole "Building on Linux with the Manylinux Docker Container" section (steps 1-7) with:

````
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
````

Use the same image tag decided in Task 7 Step 1.

- [ ] **Step 6: Verify no stale references remain**

```bash
grep -rn "conanfile\|conan-center-index\|CONAN_INDEX_HOME\|SLIDEIO_PYTHON_HOME\|conan\.sh\|install\.py -a conan" \
  README.md CLAUDE.md
```

Expected: no output. (`extern/slideio/install.py` may legitimately appear; the pattern above targets this repository's removed script specifically.)

- [ ] **Step 7: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: describe the submodule-based slideio dependency"
```

---

### Task 10: End-to-end acceptance

The gate defined in the spec. Run on the current platform in full; the other two platforms are verified by dispatching their workflows.

**Files:**
- Modify: `docs/superpowers/plans/baseline-wheel-manifest.txt` (append the post-migration comparison)

- [ ] **Step 1: Clean-tree build from scratch**

```bash
rm -rf build dist extern/slideio-install
python build-slideio.py -c release
python -m build --wheel
ls -la dist/
```

Expected: one wheel.

- [ ] **Step 2: Install into a clean virtualenv and smoke test**

```bash
rm -rf /tmp/slideio-venv && python3 -m venv /tmp/slideio-venv
/tmp/slideio-venv/bin/pip install --quiet numpy dist/*.whl
/tmp/slideio-venv/bin/python -c "
import slideio
print('version:', slideio.__version__ if hasattr(slideio, '__version__') else 'n/a')
print('drivers:', slideio.get_driver_ids())
"
```

Expected: the driver list contains all 12 format ids (SVS, AFI, SCN, CZI, ZVI, DCM, NDPI, VSI, PKE/QPTIFF, OMETIFF, PHTIFF, GDAL). A short list means driver libraries did not make it into the wheel — the `bin/` glob in `CMakeLists.txt` is the place to look.

- [ ] **Step 3: Open a slide and read a block**

Any image the C++ repository's test corpus provides works. If `SLIDEIO_TEST_DATA_PATH` is set:

```bash
/tmp/slideio-venv/bin/python -c "
import glob, os, slideio
root = os.environ['SLIDEIO_TEST_DATA_PATH']
path = sorted(glob.glob(os.path.join(root, '**', '*.svs'), recursive=True))[0]
print('opening', path)
s = slideio.open_slide(path, 'AUTO')
sc = s.get_scene(0)
print('scene:', sc.name, sc.rect, sc.num_channels)
block = sc.read_block(size=(200, 0))
print('block:', block.shape, block.dtype)
"
```

Expected: a slide opens and a NumPy array of the requested width comes back. If no test corpus is available, say so explicitly in the completion report rather than skipping silently.

- [ ] **Step 4: Diff the wheel manifest against the baseline**

```bash
unzip -l dist/*.whl | awk '{print $4}' | grep 'slideio/core/libs/' | sed 's|.*/||' | sort > /tmp/new-manifest.txt
grep -v '^#' docs/superpowers/plans/baseline-wheel-manifest.txt | sort > /tmp/old-manifest.txt
diff /tmp/old-manifest.txt /tmp/new-manifest.txt && echo "IDENTICAL"
```

Expected: `IDENTICAL`, or a difference explainable by the 2.9.0 → 2.10.0 library change. Append the result to the baseline file under a `## post-migration` heading, with an explanation for every difference. **An unexplained missing library is a failure, not a note** — a dropped driver produces a wheel that imports fine and then cannot open that format.

If Task 1 recorded `BASELINE UNAVAILABLE`, compare against `extern/slideio-install/bin/` instead:

```bash
ls extern/slideio-install/bin | sort > /tmp/prefix-libs.txt
diff /tmp/prefix-libs.txt /tmp/new-manifest.txt
```

Every library in the prefix's `bin/` should appear in the wheel; the wheel additionally holds `slideiopybind*`.

- [ ] **Step 5: Verify `SLIDEIO_INSTALL_DIR` still overrides**

The spec keeps this path working; verify it explicitly rather than assuming.

```bash
rm -rf /tmp/cmake-override
SLIDEIO_INSTALL_DIR=$(pwd)/extern/slideio-install cmake -S . -B /tmp/cmake-override \
  -DCMAKE_BUILD_TYPE=Release 2>&1 | grep 'slideio from'
```

Expected: `slideio from SLIDEIO_INSTALL_DIR: .../extern/slideio-install` — the env-var branch, not the submodule branch.

- [ ] **Step 6: Commit the acceptance record**

```bash
git add docs/superpowers/plans/baseline-wheel-manifest.txt
git commit -m "test: record post-migration wheel manifest comparison"
```

- [ ] **Step 7: Push the branch and dispatch the other two platforms**

```bash
git push -u origin v2.10.0
```

Then dispatch each workflow against the branch and confirm all three go green:

```bash
gh workflow run linux-wheels.yml --ref v2.10.0
gh workflow run macos-wheels.yml --ref v2.10.0 -f os=macos-14
gh workflow run windows-wheels.yml --ref v2.10.0
gh run list --branch v2.10.0 --limit 5
```

Download each artifact and repeat Step 4's manifest check per platform. Do not report the migration complete until all three platforms have produced a wheel whose library set is accounted for.

---

## Regulatory note

Changing how a released component's binaries are produced is a build and configuration-management change under IEC 62304 clause 8, and depending on how slideio is classified in the device file it may count as a design change requiring re-validation and QMS documentation. This cannot be determined from the repository — confirm with GRC / Regulatory Affairs before release. This plan does not include that step because it is not a code change.


---

## Execution deviations

Recorded during execution on macOS/arm64, 2026-08-31. Three things the plan did not
anticipate; each was verified before moving on.

1. **`build-slideio.py` never runs `sync-toolchain.py`.** The plan had it run on
   every build. On a host with Apple clang 21 and Conan 2.10.2 that rewrites the
   profiles to `compiler.version=21.0` and the first `conan install` dies with
   `Invalid setting '21.0' is not a valid 'settings.compiler.version' value`
   (Conan's `settings.yml` stops at 16). It also leaves four tracked profile files
   modified inside the submodule on every build.

   Per the project owner's decision: **the Conan profiles are hardcoded in the
   repository and changed manually, on demand.** No build step may rewrite them.
   `sync-toolchain.py` is a setup tool — useful for producing a profile on a new
   machine — and is run by hand, with its diff reviewed and committed like any other
   change. There is no opt-in flag; the capability is simply not part of the build.

   Skipping it is safe for `compiler.version`, which labels package IDs rather than
   selecting a compiler: with `-b missing` every dependency is compiled by the real
   host toolchain either way. The one thing it leaves manual is the CMake generator
   in the submodule's `install.py` (committed as `Visual Studio 17 2022`), which must
   be updated in the submodule if a Windows machine or runner moves to a newer
   Visual Studio.

2. **The submodule's `install.py` always appends the configuration to the prefix.**
   It installs into `<prefix>/release` or `<prefix>/debug` regardless of `-c` — this
   repository's own (now deleted) `install.py` behaved differently, which is where
   the plan's assumption came from. `build-slideio.py` now installs into a staging
   directory inside the submodule build tree and moves the one configuration up, so
   `extern/slideio-install` stays a plain install prefix with `include/`, `lib/` and
   `bin/` at its root. `CMakeLists.txt` needed no change.

3. **`setup.py` needed a third fix: exclude the staging directory from the library
   scan.** `find_shared_libs` walks `build_temp`, which *contains* `wheel_lib_dir`,
   so a warm-tree rebuild rediscovers the libraries the previous run staged and tries
   to copy each onto itself — `shutil.SameFileError`. The old `shutil.move` hid this
   because renaming a path onto itself is a silent no-op; switching to `copy2`
   surfaced it. Files already under `wheel_lib_dir` are now skipped when collecting.
   This was a latent bug in the existing code, not one the migration introduced.

Also confirmed during execution:

- The recursive submodule fetch works with slideio's `Booritas@` URLs unchanged, so
  **Task 7 Step 4 (URL rewrite) was not needed**.
- `booritas/slideio-manylinux_2_28_x86_64:2.10.0` is published, so the Linux
  container tag was bumped as planned.
- `bd112f8c` carries `projectVersion 2.9.0` in the C++ repository's own
  `CMakeLists.txt` even though it is the tip of `origin/v2.10.0`. That is an unbumped
  version string upstream, not a wrong pin.
