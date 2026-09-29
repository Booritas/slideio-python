"""Scene acquisition time, plane timestamps and channel significant bits.

These four getters exist on the C++ Scene and are exercised thoroughly there;
what is tested here is only what a Python caller sees -- that the values arrive
with the right names, types and indexing. The expected values are the ones the
C++ suite pins (src/tests/main/test_svs_driver.cpp and test_czi_driver.cpp), so
a disagreement means the binding lost or mangled something on the way across.
"""
import unittest

import slideio
from testlib import get_test_image_path


class TestAcquisitionTime(unittest.TestCase):
    def test_svs_scene_reports_its_scan_time(self):
        # 1262080755 == 2009-12-29T13:59:15Z, the scan time in the Aperio header.
        path = get_test_image_path("svs", "CMU-1-Small-Region.svs")
        with slideio.open_slide(path, "SVS") as slide:
            scene = slide.get_scene(0)
            self.assertEqual(scene.acquisition_time, 1262080755)
            self.assertIsInstance(scene.acquisition_time, int)

    def test_unknown_acquisition_time_is_zero_not_none(self):
        # The contract is 0 for "unknown", so a caller can do arithmetic without
        # a None check. colors.png carries no acquisition time at all.
        path = get_test_image_path("gdal", "colors.png")
        with slideio.open_slide(path, "AUTO") as slide:
            self.assertEqual(slide.get_scene(0).acquisition_time, 0)


class TestChannelSignificantBits(unittest.TestCase):
    def test_reports_the_acquisition_bit_depth(self):
        # 16 bit samples carrying 10 bits of camera data: Aperio states
        # "Acquisition Bit Depth = 10" in the image description.
        path = get_test_image_path("svs", "jp2k_1chnl.svs")
        with slideio.open_slide(path, "SVS") as slide:
            scene = slide.get_scene(0)
            self.assertEqual(scene.num_channels, 1)
            self.assertEqual(scene.get_channel_significant_bits(0), 10)

    def test_out_of_range_channel_is_zero(self):
        path = get_test_image_path("svs", "jp2k_1chnl.svs")
        with slideio.open_slide(path, "SVS") as slide:
            scene = slide.get_scene(0)
            self.assertEqual(scene.get_channel_significant_bits(-1), 0)
            self.assertEqual(scene.get_channel_significant_bits(1), 0)


class TestPlaneTimestamps(unittest.TestCase):
    def test_scene_without_timestamps_says_so(self):
        path = get_test_image_path("svs", "CMU-1-Small-Region.svs")
        with slideio.open_slide(path, "SVS") as slide:
            scene = slide.get_scene(0)
            self.assertFalse(scene.has_plane_timestamps)
            # Documented fallback: 0 rather than an exception.
            self.assertEqual(scene.get_plane_timestamp(0, 0, 0), 0)

    def test_czi_time_series_reports_every_plane(self):
        # Three time frames by two channels. The stated start is
        # 2021-02-10T09:18:18Z; each plane's offset is the sub-second remainder.
        path = get_test_image_path("czi", "T_3_CH_2.czi")
        with slideio.open_slide(path, "CZI") as slide:
            scene = slide.get_scene(0)
            self.assertEqual(scene.num_t_frames, 3)
            self.assertEqual(scene.num_channels, 2)
            self.assertTrue(scene.has_plane_timestamps)
            self.assertEqual(scene.acquisition_time, 1612948698)

            expected = {
                (0, 0): 0.1395793,
                (0, 1): 0.1795789,
                (1, 0): 0.2055902,
                (1, 1): 0.2365808,
                (2, 0): 0.2625829,
                (2, 1): 0.2925791,
            }
            for (t_frame, channel), value in expected.items():
                self.assertAlmostEqual(
                    scene.get_plane_timestamp(t_frame, channel, 0), value,
                    places=6, msg=f"t_frame={t_frame} channel={channel}")

    def test_timestamps_are_ordered_within_a_time_frame(self):
        # The binding must not transpose the (t_frame, channel, z_slice)
        # arguments: if it did, these two would come back swapped.
        path = get_test_image_path("czi", "T_3_CH_2.czi")
        with slideio.open_slide(path, "CZI") as slide:
            scene = slide.get_scene(0)
            first = scene.get_plane_timestamp(0, 0, 0)
            later = scene.get_plane_timestamp(2, 0, 0)
            self.assertLess(first, later)


if __name__ == '__main__':
    unittest.main()
