"""Tests for preference persistence (audiometer.config)."""
import unittest
import tempfile
import os
import shutil
from audiometer import config


class TestUIPrefsPersistence(unittest.TestCase):
    def setUp(self):
        # Create a temp dir and override env var
        self.tmpdir = tempfile.mkdtemp()
        os.environ['AUDIO_METER_CONFIG_DIR'] = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.environ.pop('AUDIO_METER_CONFIG_DIR', None)

    def test_save_and_load_prefs(self):
        prefs = {'theme': 'litera', 'win_focus': False, 'high_contrast': True}
        config.save_prefs(prefs)
        loaded = config.load_prefs()
        self.assertEqual(loaded['theme'], 'litera')
        self.assertFalse(loaded['win_focus'])
        self.assertTrue(loaded['high_contrast'])

    def test_defaults_when_missing(self):
        # Delete any config file and ensure defaults are returned
        p = config.get_config_path()
        if p.exists():
            p.unlink()
        loaded = config.load_prefs()
        self.assertIn('theme', loaded)
        self.assertIn('win_focus', loaded)
        self.assertIn('high_contrast', loaded)


if __name__ == '__main__':
    unittest.main()
