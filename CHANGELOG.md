# Changelog

All notable changes to the slideio Python package are recorded here. Changes
inside the C++ library are summarised as they affect a Python caller; the full
history is in the [slideio repository](https://github.com/Booritas/slideio).

## [2.11.0] - 2026-11-14

### slideio C++ library

The `extern/slideio` submodule moves from `b054e5ac` (slideio 2.10.0) to
`73ea70ab` (slideio 2.11.0).

### New image drivers

| Driver | Format | Extensions |
|---|---|---|
| **MRXS** | 3DHISTECH MIRAX | `*.mrxs` |
| **BIF** | Ventana BIF (iScan Coreo/HT, VENTANA DP 200) | `*.bif` |
| **LIF** | Leica LIF | `*.lif` |
| **ND2** | Nikon ND2 | `*.nd2` |

All four are picked up by `open_slide` with the default `driver="AUTO"`.

- **MRXS** — a MIRAX slide is a bundle: the `.mrxs` file plus a data directory
  of the same name. Pass the `.mrxs` file to `open_slide`, or the bundle's
  `Slidedat.ini` when the data directory was copied without it. Label and
  macro images are exposed as auxiliary images, and reads may run concurrently.
- **BIF** — one scene per scanned area (`AOI0`, `AOI1`, ...), as QuPath shows
  them. The label, thumbnail and probability-map images are auxiliary images of
  the slide. Z-stack BIF files are refused with an error for now.
- **LIF** — a LIF project opens with one scene per image, named by its folder
  path inside the project (`TileScan 1/Merged`); a tile scan gives one scene per
  field. An image the driver cannot read is left out of the scene list with a
  warning rather than failing the whole project. Each scene has a single level
  (no zoom pyramid); downscaled reads are computed from it.
- **ND2** — one scene per XY position, with Z slices and time frames taken from
  the experiment loops. Both chunked and legacy JPEG 2000
  files are read, including legacy files with 9- to 15-bit codestreams. A file
  missing its chunk-map trailer is recovered by scanning instead of being
  refused. Each scene has a single level.

LIF and ND2 report per-plane timestamps where the file records them
(`Scene.has_plane_timestamps`, `Scene.get_plane_timestamp`). For ND2, an
out-of-range index returns `0` rather than raising.

### Fixes in existing drivers

- Reads that run past the edge of an image fill the overhang with background in
  every driver, rather than leaving it undefined.
- NDPI, CZI and GDAL scenes stay readable after their `Slide` object is
  released.
- NDPI: all open files share one striped-raster cache budget, and a
  single-stripe directory is decoded once per read sequence instead of on every
  read.
- VSI: missing dimensions are inferred, and ETS files are paired with their
  scene by stack id.
- JPEG 2000: strips are decoded as well as tiles, and a strip that decodes larger
  than the rows it carries is cropped.
- A negative scene index is rejected by every driver.
- A negative block size, or a block read over channels of mixed data types,
  raises `RuntimeError` instead of producing undefined output.
- `transform_scene` rejects transformation types defined outside slideio.
- Converter: OME-XML pixel types and the JPEG 2000 tile buffer are typed by the
  channels actually written.

### Build and CI

- macOS arm64 wheels are built on the `macos-15` runner; GitHub retired the
  `macos-14` label. The wheels' platform floor is unchanged at macOS 12.0.
- Python-side tests for the new drivers: `tests/test_mrxs.py`,
  `tests/test_bif.py`, `tests/test_lif.py` and `tests/test_nd2.py`.

## [2.10.0] - 2026-10-01

Baseline for this changelog.

[2.11.0]: https://github.com/Booritas/slideio-python/compare/v2.10.0...v2.11.0
[2.10.0]: https://github.com/Booritas/slideio-python/releases/tag/v2.10.0
