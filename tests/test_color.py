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


    def test_source_profile_override_makes_an_unprofiled_scene_convertible(self):
        # The spec declines to ship a vendor fallback profile table on the
        # grounds that source_profile_override "is the honest substitute: a lab
        # that has actually characterised its scanner supplies the profile and
        # owns the claim". That substitute has to exist in Python, which is
        # where the ML pipelines this feature is for actually live.
        path = get_test_image_path("gdal", "img_2448x2448_3x8bit_SRC_RGB_ducks.png")
        profiled = get_test_image_path("gdal", "colors.png")
        with slideio.open_slide(profiled, "AUTO") as donor:
            icc = donor.get_scene(0).get_color_profile()
        self.assertIsInstance(icc, bytes)

        with slideio.open_slide(path, "AUTO") as slide:
            scene = slide.get_scene(0)
            self.assertIsNone(scene.get_color_profile())

            # Without an override, FAIL is the whole point: no colorimetry.
            strict = slideio.ColorManagement()
            strict.target = slideio.ColorTarget.LAB
            strict.missing_profile_policy = slideio.MissingProfilePolicy.FAIL
            with self.assertRaises(RuntimeError):
                slideio.transform_scene(scene, [strict])

            # With one, the same strict policy converts, because a real profile
            # was supplied rather than assumed.
            supplied = slideio.ColorManagement()
            supplied.target = slideio.ColorTarget.LAB
            supplied.missing_profile_policy = slideio.MissingProfilePolicy.FAIL
            supplied.source_profile_override = icc
            self.assertEqual(supplied.source_profile_override, icc)
            managed = slideio.transform_scene(scene, [supplied])
            info = managed.get_color_profile_info()
            self.assertTrue(info.present)
            self.assertEqual(info.source, slideio.ColorProfileSource.EMBEDDED)
            self.assertEqual(info.size, len(icc))
            tile = managed.read_block((0, 0, 16, 16), size=(16, 16))
            self.assertEqual(tile.dtype.name, "float32")

    def test_source_profile_override_round_trips_and_clears(self):
        cm = slideio.ColorManagement()
        self.assertIsNone(cm.source_profile_override)
        cm.source_profile_override = b"not a real profile"
        self.assertEqual(cm.source_profile_override, b"not a real profile")
        cm.source_profile_override = None
        self.assertIsNone(cm.source_profile_override)
        with self.assertRaises(TypeError):
            cm.source_profile_override = "a str is not ICC bytes"

    def test_new_enums_do_not_shadow_colorspace_in_the_extension_namespace(self):
        # export_values() drops every member into the extension module's own
        # namespace. IccColorSpace exports GRAY/RGB/XYZ and ColorTarget exports
        # XYZ, which silently rebound the names the pre-existing ColorSpace
        # enum had already put there -- so a bare GRAY meant IccColorSpace.Gray,
        # not ColorSpace.GRAY. The new enums are reachable through their own
        # type instead, which is the clearer form anyway.
        from slideio.core.libs import slideiopybind as ext

        self.assertIs(ext.GRAY, ext.ColorSpace.GRAY)
        self.assertIs(ext.XYZ, ext.ColorSpace.XYZ)
        for name in ("SRGB", "LINEAR_RGB", "EMBEDDED", "ASSUMED", "PERCEPTUAL",
                     "CMYK", "YCBCR", "ASSUME_SRGB", "PASS_THROUGH", "FAIL"):
            self.assertFalse(hasattr(ext, name),
                             f"{name} leaked into the extension namespace")
        self.assertIsNotNone(slideio.IccColorSpace.RGB)
        self.assertIsNotNone(slideio.ColorTarget.XYZ)
        self.assertIsNotNone(slideio.MissingProfilePolicy.FAIL)


if __name__ == "__main__":
    unittest.main()
