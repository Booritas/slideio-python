"""Open options: the dict open_slide and Slide pass to the driver.

Corpus-free: the conversion to strings is checked directly, and a bad key is
rejected before any file is touched, so a path that does not exist is enough.
"""
import unittest

import slideio
from slideio.wrappers.py_slideio import _option_strings


class TestOpenOptions(unittest.TestCase):
    def test_values_become_strings(self):
        self.assertEqual(
            {"mrxs.crop_to_content": "true", "x.n": "3", "x.s": "s", "x.f": "false", "x.r": "0.5"},
            _option_strings({"mrxs.crop_to_content": True, "x.n": 3, "x.s": "s", "x.f": False, "x.r": 0.5}))

    def test_none_is_no_options(self):
        self.assertEqual({}, _option_strings(None))

    def test_unsupported_value_type_raises_type_error(self):
        with self.assertRaises(TypeError) as ctx:
            _option_strings({"a.b": [1]})
        self.assertIn("a.b", str(ctx.exception))

    def test_unknown_driver_prefix_is_reported_before_the_file(self):
        with self.assertRaises(Exception) as ctx:
            slideio.open_slide("no/such/file.mrxs", "AUTO", {"nosuch.x": True})
        self.assertIn("unknown driver 'nosuch'", str(ctx.exception))

    def test_slide_takes_options_too(self):
        with self.assertRaises(Exception) as ctx:
            slideio.Slide("no/such/file.mrxs", "AUTO", options={"nosuch.x": True})
        self.assertIn("unknown driver 'nosuch'", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
