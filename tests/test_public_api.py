"""The names the slideio package exposes, and the enums its properties return.

A type handed back by a public property has to be reachable from the public
package, otherwise a caller cannot compare against it without importing the
private extension module. Two enums were registered on one side of that line but
not the other:

  * TransformationType was never registered with pybind11 at all, so reading
    Transformation.type raised "Unregistered type : slideio::TransformationType".
  * MetadataFormat was registered in the binding but re-exported by neither
    slideio.core nor slideio, so Slide.metadata_format returned a value with no
    public constant to compare it to.

Both are regression tests: they fail against 2.10.0.
"""
import unittest

import slideio
from testlib import get_test_image_path


class TestTransformationType(unittest.TestCase):
    """Every transformation must be able to name its own type."""

    # Transformation class -> the TransformationType member it must report.
    TRANSFORMATIONS = [
        "ColorTransformation",
        "ColorManagement",
        "GaussianBlurFilter",
        "MedianBlurFilter",
        "SobelFilter",
        "ScharrFilter",
        "LaplacianFilter",
        "BilateralFilter",
        "CannyFilter",
    ]

    def test_enum_is_exported(self):
        self.assertTrue(hasattr(slideio, "TransformationType"))

    def test_enum_members(self):
        self.assertEqual(
            set(slideio.TransformationType.__members__),
            {"Unknown"} | set(self.TRANSFORMATIONS))

    def test_each_transformation_reports_its_own_type(self):
        for name in self.TRANSFORMATIONS:
            with self.subTest(transformation=name):
                transformation = getattr(slideio, name)()
                self.assertEqual(transformation.type,
                                 getattr(slideio.TransformationType, name))


class TestMetadataFormat(unittest.TestCase):

    def test_enum_is_exported(self):
        self.assertTrue(hasattr(slideio, "MetadataFormat"))

    def test_enum_members(self):
        self.assertEqual(set(slideio.MetadataFormat.__members__),
                         {"None", "Unknown", "XML", "JSON", "TEXT"})

    def test_slide_metadata_format_compares_against_the_public_enum(self):
        """The point of the export: comparing a returned value to a constant.

        Slide and Scene describe different metadata -- for Aperio the slide
        carries the TEXT image description and the scene a JSON tree -- so they
        are checked against their own constants rather than against each other.
        """
        path = get_test_image_path("svs", "CMU-1-Small-Region.svs")
        with slideio.open_slide(path, "SVS") as slide:
            self.assertIsInstance(slide.metadata_format, slideio.MetadataFormat)
            self.assertEqual(slide.metadata_format, slideio.MetadataFormat.TEXT)
            scene_format = slide.get_scene(0).metadata_format
            self.assertIsInstance(scene_format, slideio.MetadataFormat)
            self.assertEqual(scene_format, slideio.MetadataFormat.JSON)


class TestStarImport(unittest.TestCase):
    """__all__ must list the names the package imports for callers to use."""

    def test_every_name_in_all_exists(self):
        missing = [name for name in slideio.__all__ if not hasattr(slideio, name)]
        self.assertEqual(missing, [])

    def test_star_import_brings_the_enums(self):
        namespace = {}
        exec("from slideio import *", namespace)
        for name in ("Compression", "DataType", "MetadataFormat",
                     "TransformationType", "ColorManagement", "ColorTarget"):
            with self.subTest(name=name):
                self.assertIn(name, namespace)


if __name__ == "__main__":
    unittest.main()
