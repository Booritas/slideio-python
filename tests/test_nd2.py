import unittest

import slideio
from testlib import get_test_image_path

# A Ver3.0 time lapse: 46 XY positions of 31 time points, two 16-bit channels.
FOLDER = "nd2/zenodo/bioformats"
IMAGE = "190821_L1_IRS-Akt_CS2003.nd2"


class TestND2(unittest.TestCase):
    def test_driver_is_registered(self):
        self.assertIn("ND2", slideio.get_driver_ids())

    def test_time_lapse_slide(self):
        # The same values Bio-Formats reports for this file (nd2-scenes.tsv in the C++
        # suite): one scene per XY position.
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            self.assertEqual(46, slide.num_scenes)
            self.assertEqual("Position 1", slide.get_scene(0).name)
            self.assertEqual("Position 46", slide.get_scene(45).name)
            scene = slide.get_scene(0)
            self.assertEqual((0, 0, 258, 258), scene.rect)
            self.assertEqual(2, scene.num_channels)
            self.assertEqual(1, scene.num_z_slices)
            self.assertEqual(31, scene.num_t_frames)
            self.assertEqual(1, scene.num_zoom_levels)
            self.assertEqual(60, scene.magnification)
            for channel in range(scene.num_channels):
                self.assertEqual("uint16", str(scene.get_channel_data_type(channel)))
            res_x, res_y = scene.resolution
            self.assertAlmostEqual(0.722288402520624e-6, res_x, delta=1e-15)
            self.assertAlmostEqual(0.722288402520624e-6, res_y, delta=1e-15)
            self.assertAlmostEqual(59.995475041666744, scene.t_resolution, delta=1e-9)

    def test_plane_timestamps(self):
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            scene = slide.get_scene(0)
            self.assertTrue(scene.has_plane_timestamps)
            self.assertGreater(scene.acquisition_time, 0)
            times = [scene.get_plane_timestamp(t, 0, 0) for t in range(scene.num_t_frames)]
            self.assertEqual(sorted(times), times)
            # One time point a minute, so the 31st is about half an hour in.
            self.assertAlmostEqual(1800, times[-1], delta=5)

    def test_plane_timestamp_out_of_range_is_zero(self):
        # The documented contract, which ND2 broke by raising (Booritas/slideio#98).
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            scene = slide.get_scene(0)
            self.assertEqual(0, scene.get_plane_timestamp(31, 0, 0))
            self.assertEqual(0, scene.get_plane_timestamp(-1, 0, 0))
            self.assertEqual(0, scene.get_plane_timestamp(0, 2, 0))
            self.assertEqual(0, scene.get_plane_timestamp(0, 0, 1))

    def test_time_series_read(self):
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            scene = slide.get_scene(0)
            last = scene.read_block(frames=(30, 31))
            self.assertEqual((258, 258, 2), last.shape)
            self.assertEqual("uint16", str(last.dtype))
            self.assertGreater(last.std(), 0)
            series = scene.read_block(channel_indices=[1], frames=(0, 31))
            self.assertEqual((31, 258, 258), series.shape)


if __name__ == "__main__":
    unittest.main()
