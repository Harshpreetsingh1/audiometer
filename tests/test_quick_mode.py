"""Tests for Quick vs Diagnostic mode preference and Controller integration."""
import unittest
from unittest.mock import patch
import os, tempfile, shutil
from audiometer import config

class TestQuickModePreference(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.environ['AUDIO_METER_CONFIG_DIR'] = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.environ.pop('AUDIO_METER_CONFIG_DIR', None)

    def test_quick_mode_persistence(self):
        prefs = {'theme': 'darkly', 'quick_mode': True}
        config.save_prefs(prefs)
        loaded = config.load_prefs()
        self.assertTrue(loaded.get('quick_mode'))

    def test_controller_honors_quick_mode_flag(self):
        # When passing --quick-mode to controller.config, it should set freqs accordingly
        from audiometer.audiometer import controller as ctrlmod
        parsed = ctrlmod.config(args=['--quick-mode'])
        self.assertEqual(parsed.freqs, [1000, 2000, 4000, 500])

if __name__ == '__main__':
    unittest.main()
