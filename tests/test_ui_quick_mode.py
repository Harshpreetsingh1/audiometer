import unittest

from audiometer.ascending_method import AscendingMethod


class TestUIQuickMode(unittest.TestCase):
    def test_ascending_method_honors_quick_mode(self):
        # When quick_mode=True, the controller should be configured to use the
        # quick screening frequency set [1000, 2000, 4000, 500]
        am = AscendingMethod(quick_mode=True)
        self.assertEqual(am.ctrl.config.freqs, [1000, 2000, 4000, 500])

    def test_ascending_method_default_is_not_quick_by_flag(self):
        # By default (quick_mode=False) the config should still contain freq
        # values (we check it's not empty), but may not be the quick set.
        am = AscendingMethod(quick_mode=False)
        self.assertTrue(len(am.ctrl.config.freqs) >= 1)

    def test_ascending_method_honors_mini_mode(self):
        # When mini_mode=True, the controller should use the 2-frequency set
        am = AscendingMethod(mini_mode=True)
        self.assertEqual(am.ctrl.config.freqs, [1000, 4000])


if __name__ == '__main__':
    unittest.main()
