import unittest
import slideio

class WheelTest(unittest.TestCase):
    def test_get_driver_ids(self):
        drivers = slideio.get_driver_ids()
        self.assertTrue(len(drivers) > 0)

if __name__ == '__main__':
    unittest.main()