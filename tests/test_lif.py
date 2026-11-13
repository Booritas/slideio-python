import unittest

import slideio
from testlib import get_test_image_path

# A confocal project: seven Z stacks of four 8-bit channels, one of them a 2x2 tile scan.
FOLDER = "lif/bioformats/zenodo-6606445"
IMAGE = "Project007.lif"


class TestLIF(unittest.TestCase):
    def test_driver_is_registered(self):
        self.assertIn("LIF", slideio.get_driver_ids())

    def test_project_scenes(self):
        # The series Bio-Formats reports for this file (lif-scenes.tsv in the C++ suite):
        # one scene per image, and the tile scan expanded to one scene per field.
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            scenes = [slide.get_scene(i) for i in range(slide.num_scenes)]
            self.assertEqual(
                ["Cell 1 Dendrites zoom 1.5", "Cell 1 Dendrites zoom 2",
                 "Cell 1/Field 1", "Cell 1/Field 2", "Cell 1/Field 3", "Cell 1/Field 4",
                 "Cell 1 Merged"],
                [scene.name for scene in scenes])
            self.assertEqual([7, 7, 12, 12, 12, 12, 12], [scene.num_z_slices for scene in scenes])
            self.assertEqual((0, 0, 981, 975), scenes[6].rect)

    def test_z_stack_scene(self):
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            scene = slide.get_scene(0)
            self.assertEqual((0, 0, 512, 512), scene.rect)
            self.assertEqual(4, scene.num_channels)
            self.assertEqual(7, scene.num_z_slices)
            self.assertEqual(1, scene.num_t_frames)
            self.assertEqual(1, scene.num_zoom_levels)
            self.assertEqual(63, scene.magnification)
            for channel in range(scene.num_channels):
                self.assertEqual("uint8", str(scene.get_channel_data_type(channel)))
                self.assertEqual(8, scene.get_channel_significant_bits(channel))
            res_x, res_y = scene.resolution
            self.assertAlmostEqual(0.24073561643835617e-6, res_x, delta=1e-15)
            self.assertAlmostEqual(0.24073561643835617e-6, res_y, delta=1e-15)
            self.assertAlmostEqual(0.9999285e-6, scene.z_resolution, delta=1e-15)
            self.assertTrue(scene.has_plane_timestamps)
            self.assertGreater(scene.acquisition_time, 0)

    def test_z_stack_read(self):
        with slideio.open_slide(get_test_image_path(FOLDER, IMAGE), "AUTO") as slide:
            stack = slide.get_scene(0).read_block(slices=(0, 7))
            self.assertEqual((7, 512, 512, 4), stack.shape)
            self.assertEqual("uint8", str(stack.dtype))
            self.assertGreater(stack.std(), 0)


if __name__ == "__main__":
    unittest.main()
