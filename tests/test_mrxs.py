import unittest

import slideio
from testlib import get_test_image_path


class TestMRXS(unittest.TestCase):
    def test_driver_is_registered(self):
        self.assertIn("MRXS", slideio.get_driver_ids())

    def test_cmu_slide(self):
        # Geometry as OpenSlide reports it for the bundle (mirax/reference/manifest.json,
        # which MRXSCorpusGeometry in the C++ suite compares against). The label image
        # can carry patient identifiers, so it is only listed, never read.
        path = get_test_image_path("mirax/openslide/CMU-1-Saved-1_16", "CMU-1-Saved-1_16.mrxs")
        with slideio.open_slide(path, "AUTO") as slide:
            self.assertEqual(1, slide.num_scenes)
            self.assertEqual(["Label", "Macro", "Thumbnail"], sorted(slide.get_aux_image_names()))
            scene = slide.get_scene(0)
            self.assertEqual("CMU-1-Saved-1_16", scene.name)
            self.assertEqual((0, 0, 7436, 15494), scene.rect)
            self.assertEqual(3, scene.num_channels)
            self.assertEqual(1, scene.num_z_slices)
            self.assertEqual(20, scene.magnification)
            levels = [scene.get_zoom_level_info(i).size for i in range(scene.num_zoom_levels)]
            self.assertEqual(
                [(7436, 15494), (3718, 7747), (1859, 3873), (929, 1936), (464, 968), (232, 484)],
                [(size.width, size.height) for size in levels])

    def test_cmu_scaled_read(self):
        path = get_test_image_path("mirax/openslide/CMU-1-Saved-1_16", "CMU-1-Saved-1_16.mrxs")
        with slideio.open_slide(path, "AUTO") as slide:
            raster = slide.get_scene(0).read_block(size=(200, 0))
            self.assertEqual((417, 200, 3), raster.shape)
            self.assertGreater(raster.std(), 0)

    def test_slidedat_ini_opens_the_same_slide(self):
        # A bundle whose data directory was copied without its .mrxs opens through
        # Slidedat.ini, and AUTO still picks the MRXS driver for it.
        folder = "mirax/openslide/CMU-1-Saved-1_16"
        by_entry = get_test_image_path(folder, "CMU-1-Saved-1_16.mrxs")
        by_ini = get_test_image_path(folder, "CMU-1-Saved-1_16/Slidedat.ini")
        with slideio.open_slide(by_entry, "AUTO") as entry_slide, \
                slideio.open_slide(by_ini, "AUTO") as ini_slide:
            entry_scene = entry_slide.get_scene(0)
            ini_scene = ini_slide.get_scene(0)
            self.assertEqual(entry_scene.rect, ini_scene.rect)
            block = (1444, 4294, 256, 256)
            self.assertTrue((entry_scene.read_block_from_level(1, block)
                             == ini_scene.read_block_from_level(1, block)).all())


if __name__ == "__main__":
    unittest.main()
