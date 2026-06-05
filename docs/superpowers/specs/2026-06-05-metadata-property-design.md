# Design: expose `getMetadata` as `metadata` property on Slide and Scene

Date: 2026-06-05

## Goal

Expose `slideio::Slide::getMetadata()` and `slideio::Scene::getMetadata()` (added in
slideio C++ 2.8.1, returning a lazy `const Metadata&` tree view) to Python as a
read-only `metadata` property on both `Slide` and `Scene`.

## Decision: representation in Python

The `Metadata` tree is converted to **native Python objects** at the binding
boundary: `Object` → `dict`, `Array` → `list`, `String` → `str`, `Int` → `int`,
`Double` → `float`, `Bool` → `bool`, `Null` → `None`.

Rationale: most Pythonic (iteration, indexing, `json.dumps` work directly), no new
Python class to maintain. The cost — the whole tree is converted per property
access — is negligible next to slide I/O; the C++ side already caches the parsed
tree (`std::call_once`). No caching in the Python wrapper (YAGNI).

Alternatives rejected:
- Binding the `Metadata` class 1:1 (`as_string()`, `find()`, ...): non-Pythonic,
  more surface to maintain.
- JSON round-trip via `toJson()` + `json.loads()`: extra serialize/parse pass,
  NaN/Inf edge cases, awkward layering.
- pybind11 `type_caster`: overkill for two call sites.

## Changes

1. **`src/pymetadata.hpp` / `src/pymetadata.cpp`** — helper
   `pybind11::object metadataToPyObject(const slideio::Metadata&)`: recursive
   switch on `Metadata::Type`.
2. **`src/pyslide.hpp` / `src/pyslide.cpp`** — `pybind11::object getMetadata() const`
   delegating to `m_slide->getMetadata()` + conversion.
3. **`src/pyscene.hpp` / `src/pyscene.cpp`** — same for `m_scene`.
4. **`src/pybind.cpp`** — `.def_property_readonly("metadata", ...)` on both
   `Slide` and `Scene`, next to the existing `raw_metadata`/`metadata_format` defs.
5. **`slideio/wrappers/py_slideio.py`** — `metadata` property on wrapper `Slide`
   and `Scene` classes delegating to the core objects.
6. **`slideio/core/__init__.py`** — no change needed (properties come with
   `CoreSlide`/`CoreScene`).

## Error handling

Existing pattern: slideio C++ exceptions propagate through pybind11 as Python
exceptions. Nothing new.

## Testing

No test suite in this repo (tests live in the C++ repo). Verification = successful
build of the extension + smoke check (`slide.metadata` / `scene.metadata` on a
sample file if available).
