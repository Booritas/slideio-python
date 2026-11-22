"""Scene._native_handle(): the capsule shared with slideio-processor.

The contract is a PyCapsule named "slideio.Scene" whose pointer is a heap-allocated
std::shared_ptr<slideio::Scene> that also keeps the scene's slide alive. Most tests
write a small PNG into tmp_path, so they need no image corpus.
"""
import ctypes
import gc

import pytest
from PIL import Image

import slideio
from testlib import get_test_image_path

_NAME = b"slideio.Scene"

_api = ctypes.pythonapi
_api.PyCapsule_IsValid.argtypes = [ctypes.py_object, ctypes.c_char_p]
_api.PyCapsule_IsValid.restype = ctypes.c_int
_api.PyCapsule_GetName.argtypes = [ctypes.py_object]
_api.PyCapsule_GetName.restype = ctypes.c_char_p
_api.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
_api.PyCapsule_GetPointer.restype = ctypes.c_void_p


def _capsule_name(capsule):
    return _api.PyCapsule_GetName(capsule)


def _capsule_valid(capsule, name):
    return bool(_api.PyCapsule_IsValid(capsule, name))


def _capsule_pointer(capsule, name):
    return _api.PyCapsule_GetPointer(capsule, name)


def _png(tmp_path):
    path = tmp_path / "scene.png"
    Image.new("RGB", (64, 48), (10, 20, 30)).save(path)
    return str(path)


def _open_scene(tmp_path):
    slide = slideio.open_slide(_png(tmp_path), "GDAL")
    return slide.get_scene(0)


def test_capsule_name_and_pointer(tmp_path):
    scene = _open_scene(tmp_path)
    handle = scene._native_handle()
    assert type(handle).__name__ == "PyCapsule"
    assert _capsule_name(handle) == _NAME
    assert _capsule_valid(handle, _NAME)
    assert _capsule_pointer(handle, _NAME)  # non-null


def test_core_scene_has_the_method(tmp_path):
    scene = _open_scene(tmp_path)
    assert _capsule_name(scene.scene._native_handle()) == _NAME  # CoreScene


def test_handle_outlives_slide_and_scene(tmp_path):
    slide = slideio.open_slide(_png(tmp_path), "GDAL")
    scene = slide.get_scene(0)
    handle = scene._native_handle()
    del scene, slide
    gc.collect()
    assert _capsule_valid(handle, _NAME)
    del handle
    gc.collect()  # capsule destructor releases the last owner; must not crash


def test_each_call_returns_an_independent_capsule(tmp_path):
    scene = _open_scene(tmp_path)
    a, b = scene._native_handle(), scene._native_handle()
    assert a is not b
    assert _capsule_pointer(a, _NAME) != _capsule_pointer(b, _NAME)
    del a
    gc.collect()
    assert _capsule_valid(b, _NAME)


def test_closed_scene_has_no_handle(tmp_path):
    scene = _open_scene(tmp_path)
    scene.close()
    with pytest.raises(AttributeError):
        scene._native_handle()


def test_aux_image_scene_has_a_handle():
    path = get_test_image_path("bif/openslide", "Ventana-1.bif")
    slide = slideio.open_slide(path, "AUTO")
    aux = slide.get_aux_image(slide.get_aux_image_names()[0])
    handle = aux._native_handle()
    del aux, slide
    gc.collect()
    assert _capsule_valid(handle, _NAME)
    assert _capsule_pointer(handle, _NAME)
