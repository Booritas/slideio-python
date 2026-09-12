"""Test image path resolution shared by the Python test suite.

Mirrors TestTools::getTestImagePath in the C++ repository's test library
(extern/slideio/src/tests/testlib): the same SLIDEIO_IMAGES_PATH environment
variable, and the same SLIDEIO_SKIP_MISSING_IMAGES escape hatch so a rotated-out
image corpus skips the tests that need it instead of turning the whole run red.
Leaving SLIDEIO_SKIP_MISSING_IMAGES unset -- as CI must -- keeps a missing image
a hard failure, so coverage cannot quietly disappear.
"""
import os

import pytest

_IMAGES_PATH_VAR = "SLIDEIO_IMAGES_PATH"
_SKIP_MISSING_VAR = "SLIDEIO_SKIP_MISSING_IMAGES"


def _skips_missing_images():
    value = os.environ.get(_SKIP_MISSING_VAR)
    return bool(value) and value != "0"


def get_test_image_path(subfolder, image):
    """Resolve `<SLIDEIO_IMAGES_PATH>/<subfolder>/<image>`.

    Raises RuntimeError if SLIDEIO_IMAGES_PATH is not set. If the resolved path
    does not exist and SLIDEIO_SKIP_MISSING_IMAGES is set, skips the current
    test instead of handing back a path that will fail deeper inside slideio.
    """
    root = os.environ.get(_IMAGES_PATH_VAR)
    if root is None:
        raise RuntimeError(f"Undefined environment variable: {_IMAGES_PATH_VAR}")
    path = os.path.normpath(os.path.join(root, subfolder, image))
    if not os.path.exists(path) and _skips_missing_images():
        pytest.skip(f"test image not found: {path}")
    return path
