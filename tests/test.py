import unittest
from tests.test import Test
import slideio

class TestTest(unittest.TestCase):
    def test_get_driver_ids(self):
        drivers = slideio.get_driver_ids()
        self.assertTrue(len(drivers) > 0)

if __name__ == '__main__':
    unittest.main()