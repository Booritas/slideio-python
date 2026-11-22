# Scene native handle — design

Approved 2026-11-22. Project 2 of the slideio-processor Python bindings design
(slideio-processor repository,
`docs/superpowers/specs/2026-11-22-python-bindings-design.md`, decisions D2 and
D3).

## Intent

The slideio-processor Python bindings (a separate wheel, `slideio-processor`)
must run a pipeline on a scene the caller opened with this package. Both
wheels share one copy of the SlideIO C++ library: the one this wheel ships
(D2). The processor's extension therefore needs the `slideio::Scene` behind a
Python `Scene`, and it cannot reach it through C++ symbols or pybind11 types:
extension modules export neither, and sharing a pybind11 type across modules
would tie both wheels to one pybind11 version, compiler and flag set.

## Goals

- `Scene._native_handle()` returns a `PyCapsule` named `"slideio.Scene"` whose
  pointer is a heap-allocated `std::shared_ptr<slideio::Scene>`.
- The capsule owns that shared pointer and deletes it in its destructor.
- The shared pointer keeps the scene's slide alive too, so the scene stays
  valid for as long as anyone holds the pointer, after Python has dropped
  every `Slide` and `Scene` object.
- The method exists on both the core class (`slideio.core.CoreScene`) and the
  public wrapper (`slideio.Scene`), including auxiliary-image scenes.
- This package and slideio-processor are built from the same SlideIO commit.

## Non-goals

- No documented user API. The leading underscore keeps the method out of it.
- No way to build a Python `Scene` from a native one.
- No change to how slides or scenes are opened or read.

## Anti-goals

- A capsule whose pointer outlives the objects it points into.
- A capsule whose destruction needs the Python interpreter lock beyond what
  CPython already holds when it runs a capsule destructor.
- Two SlideIO builds in one process.

## Decisions

**N1. Contract.** Method name `_native_handle`, capsule name `"slideio.Scene"`,
pointee `std::shared_ptr<slideio::Scene>`. Changing any of the three is a
breaking change for both packages.

**N2. Ownership (aliasing shared pointer).** The capsule's shared pointer is
built with the aliasing constructor from the `std::shared_ptr<PyScene>` the
method is called on and the raw `slideio::Scene*` that `extractScene` returns:

```cpp
std::shared_ptr<slideio::Scene>(self, extractScene(self).get())
```

It points at the scene and owns the `PyScene`, which holds both the scene and
its slide. `PyScene` holds only C++ shared pointers, no Python objects, so the
last owner may release it on any thread without the interpreter lock.

*Why not the plain `extractScene(self)` of D3:* that pointer keeps the scene
but not the slide. The processor would have to hold the Python `Scene` object
for as long as it uses the scene, and a mistake there is a use-after-free
rather than an error.

**N3. SlideIO version.** The `extern/slideio` submodule moves from `e2ceb224`
(slideio 2.11.0) to `edda013a`, the commit slideio-processor pins: 2.11.0 plus
the OME-TIFF one-tile-level fix (Booritas/slideio PR #102). `projectVersion`
stays `2.11`; the release carrying this change is a 2.11 patch release, and the
processor bindings pin that exact version.

## Left to the builder

- The docstring wording.
- How the tests reach the capsule API (`ctypes.pythonapi` is sufficient).

Publishing to PyPI is the maintainer's step, outside this work.
