import unittest

import slideio
from testlib import get_test_image_path


class TestBIF(unittest.TestCase):
    def test_driver_is_registered(self):
        self.assertIn("BIF", slideio.get_driver_ids())

    def test_ventana_dp200_slide(self):
        # The same expectations as BIFCorpusOpen.Ventana1 in the C++ suite. The
        # label image can carry patient identifiers, so it is only listed, never read.
        path = get_test_image_path("bif/openslide", "Ventana-1.bif")
        with slideio.open_slide(path, "AUTO") as slide:
            self.assertEqual(1, slide.num_scenes)
            self.assertEqual(["Label", "Probability"], sorted(slide.get_aux_image_names()))
            scene = slide.get_scene(0)
            self.assertEqual("AOI0", scene.name)
            self.assertEqual((0, 0, 23432, 21504), scene.rect)
            self.assertEqual(3, scene.num_channels)
            self.assertEqual(1, scene.num_z_slices)
            self.assertEqual(40, scene.magnification)
            res_x, res_y = scene.resolution
            self.assertAlmostEqual(0.25e-6, res_x, delta=1e-12)
            self.assertAlmostEqual(0.25e-6, res_y, delta=1e-12)
            self.assertEqual(8, scene.num_zoom_levels)
            self.assertIsNotNone(scene.get_color_profile())

    def test_ventana_dp200_scaled_read(self):
        path = get_test_image_path("bif/openslide", "Ventana-1.bif")
        with slideio.open_slide(path, "AUTO") as slide:
            scene = slide.get_scene(0)
            raster = scene.read_block(size=(500, 0))
            self.assertEqual((459, 500, 3), raster.shape)
            self.assertGreater(raster.std(), 0)


if __name__ == "__main__":
    unittest.main()
