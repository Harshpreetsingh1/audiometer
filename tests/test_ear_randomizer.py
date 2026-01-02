import unittest
from collections import Counter

from audiometer.ascending_method import AscendingMethod


class TestEarRandomizer(unittest.TestCase):
    def test_random_start_ear_occurs(self):
        # Run multiple instantiations and record the first ear observed
        starts = []
        for i in range(50):
            am = AscendingMethod(device_id=None)
            # The controller config is set during init; record the first ear
            starts.append(am.ctrl.config.earsides[0])
        counter = Counter(starts)
        # Both ears should appear at least once as starting ear
        self.assertTrue(counter['right'] > 0 and counter['left'] > 0,
                        f"Expected both ears to appear as start ear, got: {counter}")


if __name__ == '__main__':
    unittest.main()
