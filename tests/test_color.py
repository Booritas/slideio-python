import io
import os
import unittest

import slideio
from testlib import get_test_image_path


class TestColor(unittest.TestCase):
    def test_absent_profile_is_none(self):
        # img_2448x2448_3x8bit_SRC_RGB_ducks.png carries no ICC profile at all,
        # unlike gdal/colors.png (see test_profile_bytes_round_trip_to_pillow),
        # which embeds a real one.
        path = get_test_image_path("gdal", "img_2448x2448_3x8bit_SRC_RGB_ducks.png")
        with slideio.open_slide(path, "AUTO") as slide:
            scene = slide.get_scene(0)
            self.assertIsNone(scene.get_color_profile())
            info = scene.get_color_profile_info()
            self.assertFalse(info.present)
            self.assertEqual(info.source, slideio.ColorProfileSource.NONE)

    def test_profile_bytes_round_trip_to_pillow(self):
        # colors.png embeds a real 672-byte GIMP sRGB profile, so this
        # actually exercises the round trip through an external consumer
        # rather than skipping every run.
        path = get_test_image_path("gdal", "colors.png")
        with slideio.open_slide(path, "AUTO") as slide:
            icc = slide.get_scene(0).get_color_profile()
            self.assertIsNotNone(icc)
            self.assertIsInstance(icc, bytes)
            from PIL import ImageCms
            profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            self.assertTrue(ImageCms.getProfileDescription(profile))

    def test_source_distinguishes_embedded_from_assumed(self):
        # The whole point of ColorProfileSource is that a pipeline can tell a
        # real correction (Embedded) from a guess (Assumed) apart. Exercise
        # both ends of that distinction from Python.
        profiled_path = get_test_image_path("gdal", "colors.png")
        with slideio.open_slide(profiled_path, "AUTO") as slide:
            info = slide.get_scene(0).get_color_profile_info()
            self.assertTrue(info.present)
            self.assertEqual(info.source, slideio.ColorProfileSource.EMBEDDED)

        unprofiled_path = get_test_image_path("gdal", "img_2448x2448_3x8bit_SRC_RGB_ducks.png")
        with slideio.open_slide(unprofiled_path, "AUTO") as slide:
            scene = slide.get_scene(0)
            cm = slideio.ColorManagement()
            cm.target = slideio.ColorTarget.SRGB
            managed = slideio.transform_scene(scene, [cm])
            info = managed.get_color_profile_info()
            self.assertTrue(info.present)
            self.assertEqual(info.source, slideio.ColorProfileSource.ASSUMED)

    def test_lab_transform_returns_float32(self):
        path = get_test_image_path("gdal", "colors.png")
        with slideio.open_slide(path, "AUTO") as slide:
            scene = slide.get_scene(0)
            cm = slideio.ColorManagement()
            cm.target = slideio.ColorTarget.LAB
            managed = slideio.transform_scene(scene, [cm])
            tile = managed.read_block((0, 0, 16, 16), size=(16, 16))
            self.assertEqual(tile.dtype.name, "float32")
            self.assertEqual(tile.shape[2], 3)
            self.assertTrue((tile[:, :, 0] >= -0.5).all())
            self.assertTrue((tile[:, :, 0] <= 100.5).all())

    def test_fail_policy_raises(self):
        # Must be a scene with no embedded profile: Fail only fires when the
        # missing-profile policy is actually consulted.
        path = get_test_image_path("gdal", "img_2448x2448_3x8bit_SRC_RGB_ducks.png")
        with slideio.open_slide(path, "AUTO") as slide:
            scene = slide.get_scene(0)
            cm = slideio.ColorManagement()
            cm.target = slideio.ColorTarget.LAB
            cm.missing_profile_policy = slideio.MissingProfilePolicy.FAIL
            with self.assertRaises(RuntimeError):
                slideio.transform_scene(scene, [cm])


if __name__ == "__main__":
    unittest.main()
