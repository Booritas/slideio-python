# Scene Native Handle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Scene._native_handle()` hands the slideio-processor extension the `slideio::Scene` behind a Python scene, built from the same SlideIO commit slideio-processor pins.

**Architecture:** One pybind11 method on the `Scene` class in `src/pybind.cpp` returns a `PyCapsule` owning a heap-allocated aliasing `std::shared_ptr<slideio::Scene>` that also owns the `PyScene` (and so the slide). The public wrapper forwards to it. The `extern/slideio` submodule moves to `edda013a` first.

**Tech Stack:** C++17, pybind11, CPython capsule API, pytest + ctypes, Pillow (test-only).

**Spec:** `docs/superpowers/specs/2026-11-22-native-handle-design.md` (this repository). Parent design: slideio-processor repository, `docs/superpowers/specs/2026-11-22-python-bindings-design.md`, D2/D3.

## Global Constraints

- Contract, verbatim: method `_native_handle`, capsule name `"slideio.Scene"`, pointee `std::shared_ptr<slideio::Scene>` allocated with `new`, freed by the capsule destructor with `delete`.
- Ownership: the pointer is built with the aliasing constructor from the `std::shared_ptr<PyScene>` the method is called on: `std::shared_ptr<slideio::Scene>(self, extractScene(self).get())`.
- `PyScene` must keep holding no Python objects (only C++ shared pointers), so the last owner can release it without the interpreter lock.
- SlideIO submodule pin: `edda013a` (full SHA starts `edda013a`), the commit slideio-processor pins. `projectVersion` stays `2.11`.
- CHANGELOG: one new top section `## [Unreleased]`; the release tag sets the patch number later. Do not tag, push tags, or publish.
- No slide paths or image content in test names, messages or logs beyond the corpus-free temp files the tests create.
- Follow `CLAUDE.md`: an API change touches `src/pybind.cpp`, `slideio/core/__init__.py` (only if a new name is exported — none is here), `slideio/wrappers/py_slideio.py`, `slideio/__init__.py` (same).

### Build and test (Windows, local)

Run in PowerShell. `<S>` is a scratch directory outside the checkout; `<R>` is the repository root.

```powershell
conda run -n slideio python build-slideio.py            # add --force after a submodule move
conda run -n slideio python -m build --wheel --outdir <S>\dist
Push-Location <S>; . <R>\lib.ps1; Repair-Naming; Pop-Location   # Repair-Naming works on .\dist of the cwd
conda run -n slideio python -m venv <S>\venv
& <S>\venv\Scripts\python.exe -m pip install pytest pillow numpy pyyaml
& <S>\venv\Scripts\python.exe -m pip install --force-reinstall --no-deps --no-index --find-links <S>\dist slideio
Set-Location <S>; & <S>\venv\Scripts\python.exe -m pytest <R>\tests
```

Never run `Repair-Naming` from `<R>`: `<R>\dist` holds old release wheels it would rewrite. `SLIDEIO_IMAGES_PATH` is set in the user environment; leave `SLIDEIO_SKIP_MISSING_IMAGES` unset.

## Review Focus

1. A capsule outliving every Python `Slide`/`Scene` object: the slide must still be alive — the aliasing constructor in N2 is the only thing that guarantees this; a plain `extractScene(self)` copy compiles and passes every Python-visible test.
2. An auxiliary-image scene (`CoreScene.get_aux_image`; the public wrapper's `Scene.get_aux_image` returns an ndarray) returns a working handle too (it is a `PyScene` like any other).
3. Two calls return two independent capsules; deleting one leaves the other valid.
4. A closed public `slideio.Scene` (after `close()`) fails the same way every other method on a closed scene fails; no capsule with a null pointer.
5. A wheel test run that silently uses the source tree instead of the installed wheel (see CLAUDE.md): tests must run from `<S>`.

---

### Task 1: Move SlideIO to the processor's pin

**Files:**
- Modify: `extern/slideio` (gitlink) → `edda013a`
- Modify: `CHANGELOG.md` (new `## [Unreleased]` section at the top, below the intro)

**Interfaces:**
- Produces: a local `extern/slideio-install` built from `edda013a`, used by Task 2.

- [ ] **Step 1: Move the submodule**

```bash
git -C extern/slideio fetch origin
git -C extern/slideio checkout edda013a
git -C extern/slideio submodule update --init --recursive
git add extern/slideio
```

Check: `git -C extern/slideio log --oneline -1` starts with `edda013a`; `git -C extern/slideio merge-base --is-ancestor e2ceb224 HEAD` exits 0.

- [ ] **Step 2: Rebuild SlideIO and the wheel; run the whole suite**

Run the Build-and-test block with `build-slideio.py --force`. Expected: build exits 0; pytest reports no failures and no errors (record the pass/skip counts in the report).

- [ ] **Step 3: CHANGELOG entry**

Add `## [Unreleased]` with a `### slideio C++ library` subsection in the style of the 2.11.0 entry: the submodule moves from `e2ceb224` (slideio 2.11.0) to `edda013a`; a one-paragraph caller-facing note that an OME-TIFF pyramid level fitting in a single tile smaller than the tile size is now read cropped instead of stretched (Booritas/slideio PR #102).

- [ ] **Step 4: Commit**

```bash
git add extern/slideio CHANGELOG.md
git commit -m "Bump extern/slideio to edda013a (OME-TIFF one-tile level fix)"
```

---

### Task 2: `Scene._native_handle()`

**Files:**
- Modify: `src/pybind.cpp` (the `py::class_<PyScene, std::shared_ptr<PyScene>>(m, "Scene")` chain)
- Modify: `slideio/wrappers/py_slideio.py` (class `Scene`)
- Modify: `src/pyscene.hpp` (one comment on the `private:` members: `PyScene` must hold no Python objects; `_native_handle` relies on it)
- Modify: `CHANGELOG.md` (`## [Unreleased]`: a `### Python API` note)
- Modify: `CLAUDE.md` (a short "Native scene handle" paragraph: the contract in Global Constraints, that it is shared with slideio-processor, and that changing it breaks both packages)
- Create: `tests/test_native_handle.py`

**Interfaces:**
- Consumes: `std::shared_ptr<slideio::Scene> extractScene(std::shared_ptr<PyScene>)` (`src/pyscene.hpp`).
- Produces: `CoreScene._native_handle() -> PyCapsule` and `slideio.Scene._native_handle() -> PyCapsule`; contract in Global Constraints.

- [ ] **Step 1: Write the failing tests** in `tests/test_native_handle.py`

The tests need no image corpus: each writes a small RGB PNG with Pillow into pytest's `tmp_path` (e.g. 64×48, uint8) and opens it with `slideio.open_slide(path, "GDAL")`. Reach the capsule API through `ctypes.pythonapi` (`PyCapsule_IsValid`, `PyCapsule_GetName`, `PyCapsule_GetPointer`, with `argtypes`/`restype` set; capsule passed as `ctypes.py_object`).

```python
def test_capsule_name_and_pointer(tmp_path):
    scene = _open_scene(tmp_path)
    handle = scene._native_handle()
    assert type(handle).__name__ == "PyCapsule"
    assert _capsule_name(handle) == b"slideio.Scene"
    assert _capsule_valid(handle, b"slideio.Scene")
    assert _capsule_pointer(handle, b"slideio.Scene")  # non-null

def test_core_scene_has_the_method(tmp_path):
    scene = _open_scene(tmp_path)
    assert _capsule_name(scene.scene._native_handle()) == b"slideio.Scene"   # CoreScene

def test_handle_outlives_slide_and_scene(tmp_path):
    slide = slideio.open_slide(_png(tmp_path), "GDAL")
    scene = slide.get_scene(0)
    handle = scene._native_handle()
    del scene, slide
    gc.collect()
    assert _capsule_valid(handle, b"slideio.Scene")
    del handle
    gc.collect()   # capsule destructor releases the last owner; must not crash

def test_each_call_returns_an_independent_capsule(tmp_path):
    scene = _open_scene(tmp_path)
    a, b = scene._native_handle(), scene._native_handle()
    assert a is not b
    assert _capsule_pointer(a, b"slideio.Scene") != _capsule_pointer(b, b"slideio.Scene")
    del a
    gc.collect()
    assert _capsule_valid(b, b"slideio.Scene")

def test_closed_scene_has_no_handle(tmp_path):
    scene = _open_scene(tmp_path)
    scene.close()
    with pytest.raises(AttributeError):
        scene._native_handle()
```

(`_open_scene`, `_png`, `_capsule_*` are small module helpers. Review Focus 2: if a corpus-free image with an auxiliary image is not available, add `test_aux_image_scene_has_a_handle` using `get_test_image_path` on a corpus slide that has aux images — pick one already used by an existing test — so it skips only under `SLIDEIO_SKIP_MISSING_IMAGES`.)

- [ ] **Step 2: Run to verify they fail**

Build-and-test block, then `pytest <R>\tests\test_native_handle.py -v` from `<S>`. Expected: FAIL with `AttributeError: ... '_native_handle'`.

- [ ] **Step 3: Implement**

- `src/pybind.cpp`: `.def("_native_handle", ...)` on the `Scene` class taking `std::shared_ptr<PyScene> self`, returning `py::capsule` named `"slideio.Scene"` around `new std::shared_ptr<slideio::Scene>(self, extractScene(self).get())`, with a destructor that `delete`s it. Docstring states the contract and that it is internal (for slideio-processor).
- `slideio/wrappers/py_slideio.py`: `Scene._native_handle(self)` returns `self.scene._native_handle()`; docstring: internal, for slideio-processor; a closed scene raises as every other method does.
- `src/pyscene.hpp`, `CHANGELOG.md`, `CLAUDE.md` as listed under Files.

- [ ] **Step 4: Run the whole suite**

Build-and-test block (no `--force`). Expected: the new tests pass; no other failures or errors.

- [ ] **Step 5: Commit**

```bash
git add src/pybind.cpp src/pyscene.hpp slideio/wrappers/py_slideio.py tests/test_native_handle.py CHANGELOG.md CLAUDE.md
git commit -m "feat: Scene._native_handle() capsule for slideio-processor"
```

## Not in this plan

- Tagging, publishing to PyPI, or updating slideio-processor's pin (already `edda013a`).
- The processor-side consumer (project 3).
