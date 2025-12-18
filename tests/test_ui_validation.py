#!/usr/bin/env python3
"""UI validation and input sanitation tests.

Tests that the UI properly validates inputs and handles edge cases
without crashing the backend.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import shutil
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ascending_method import AscendingMethod
from audiometer import controller


class TestInputValidation(unittest.TestCase):
    """Test input validation and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_empty_patient_id_handled_gracefully(self, mock_makedirs, mock_exists, mock_config,
                                                 mock_responder_class, mock_audio_class):
        """Empty patient ID should be handled gracefully."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = [1000]
        mock_config_obj.earsides = ['right']
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder_class.return_value = MagicMock()
        mock_audio_class.return_value = MagicMock()
        
        # Test with empty subject name (should use default folder)
        try:
            test = AscendingMethod(device_id=None, subject_name="")
            # Should not raise exception
            self.assertIsNotNone(test)
            print("✓ Empty patient ID handled gracefully")
        except Exception as e:
            self.fail(f"Empty patient ID should not raise exception: {e}")
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_none_patient_id_handled_gracefully(self, mock_makedirs, mock_exists, mock_config,
                                                mock_responder_class, mock_audio_class):
        """None patient ID should be handled gracefully."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = [1000]
        mock_config_obj.earsides = ['right']
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder_class.return_value = MagicMock()
        mock_audio_class.return_value = MagicMock()
        
        # Test with None subject name
        try:
            test = AscendingMethod(device_id=None, subject_name=None)
            self.assertIsNotNone(test)
            print("✓ None patient ID handled gracefully")
        except Exception as e:
            self.fail(f"None patient ID should not raise exception: {e}")
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_invalid_characters_in_patient_id(self, mock_makedirs, mock_exists, mock_config,
                                              mock_responder_class, mock_audio_class):
        """Patient ID with invalid filesystem characters should be sanitized."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = [1000]
        mock_config_obj.earsides = ['right']
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder_class.return_value = MagicMock()
        mock_audio_class.return_value = MagicMock()
        
        # Test with invalid characters (should be sanitized by controller)
        invalid_name = "Patient/Name\\With|Invalid*Chars?"
        try:
            test = AscendingMethod(device_id=None, subject_name=invalid_name)
            # Should not raise exception - controller should sanitize
            self.assertIsNotNone(test)
            # Verify sanitization happened
            sanitized = test.ctrl._sanitize_folder_name(invalid_name)
            self.assertNotIn('/', sanitized, "Invalid chars should be removed")
            self.assertNotIn('\\', sanitized, "Invalid chars should be removed")
            print(f"✓ Invalid characters sanitized: '{invalid_name}' -> '{sanitized}'")
        except Exception as e:
            self.fail(f"Invalid characters should be sanitized, not raise exception: {e}")


class TestThreadSafety(unittest.TestCase):
    """Test thread safety and race conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_stop_immediately_after_start(self, mock_makedirs, mock_exists, mock_config,
                                          mock_responder_class, mock_audio_class):
        """Calling stop_test() immediately after start should not cause race condition."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = [1000]
        mock_config_obj.earsides = ['right']
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder = MagicMock()
        mock_responder.click_down.return_value = False
        mock_responder.click_up.return_value = True
        mock_responder.clear = Mock()
        mock_responder.wait_for_click = Mock()
        mock_responder_class.return_value = mock_responder
        
        mock_audio = MagicMock()
        mock_audio.start = Mock()
        mock_audio.stop = Mock()
        mock_audio.close = Mock()
        mock_audio_class.return_value = mock_audio
        
        import csv
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        # Create test instance
        test = AscendingMethod(device_id=None, subject_name="ThreadTest")
        test.ctrl.config.results_path = self.test_dir
        test.ctrl.config.freqs = [1000]
        test.ctrl.config.earsides = ['right']
        
        # Start test in thread
        test_thread = threading.Thread(target=test.run, daemon=True)
        test_thread.start()
        
        # Immediately stop (race condition test)
        time.sleep(0.01)  # Tiny delay to let thread start
        try:
            test.stop_test()
            # Should not raise exception
            print("✓ Stop immediately after start handled correctly")
        except Exception as e:
            self.fail(f"Stop immediately after start should not raise exception: {e}")
        
        # Wait a bit and verify stop event is set
        time.sleep(0.1)
        self.assertTrue(test.stop_event.is_set(), "Stop event should be set")
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_multiple_stop_calls_safe(self, mock_makedirs, mock_exists, mock_config,
                                     mock_responder_class, mock_audio_class):
        """Multiple calls to stop_test() should be safe (idempotent)."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = [1000]
        mock_config_obj.earsides = ['right']
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder_class.return_value = MagicMock()
        mock_audio_class.return_value = MagicMock()
        
        import csv
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        test = AscendingMethod(device_id=None, subject_name="MultiStopTest")
        
        # Call stop multiple times
        try:
            test.stop_test()
            test.stop_test()
            test.stop_test()
            # Should not raise exception
            self.assertTrue(test.stop_event.is_set(), "Stop event should be set")
            print("✓ Multiple stop calls handled safely")
        except Exception as e:
            self.fail(f"Multiple stop calls should be safe: {e}")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_single_frequency_single_ear(self, mock_makedirs, mock_exists, mock_config,
                                         mock_responder_class, mock_audio_class):
        """Test with minimal configuration (1 freq, 1 ear)."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = [1000]  # Single frequency
        mock_config_obj.earsides = ['right']  # Single ear
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder = MagicMock()
        mock_responder.click_down.return_value = True
        mock_responder.click_up.return_value = True
        mock_responder.clear = Mock()
        mock_responder.wait_for_click = Mock()
        mock_responder_class.return_value = mock_responder
        
        mock_audio = MagicMock()
        mock_audio.start = Mock()
        mock_audio.stop = Mock()
        mock_audio.close = Mock()
        mock_audio_class.return_value = mock_audio
        
        import csv
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        with patch.object(controller.Controller, 'audibletone', return_value=20), \
             patch.object(controller.Controller, 'clicktone', return_value=True), \
             patch.object(controller.Controller, 'save_results', return_value=None), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="MinimalTest")
            test.ctrl.config.results_path = self.test_dir
            
            # Run test
            test.run()
            
            # Verify progress
            completed, total, percentage = test.get_progress()
            self.assertEqual(percentage, 100, "Minimal test should complete to 100%")
            self.assertEqual(total, 1, "Total should be 1 (1 freq × 1 ear)")
            print("✓ Minimal configuration (1 freq, 1 ear) works correctly")
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_empty_frequencies_list(self, mock_makedirs, mock_exists, mock_config,
                                    mock_responder_class, mock_audio_class):
        """Test with empty frequencies list should handle gracefully."""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = self.test_dir
        mock_config_obj.filename = 'test_result.csv'
        mock_config_obj.device = None
        mock_config_obj.beginning_fam_level = 40
        mock_config_obj.tone_duration = 0.1
        mock_config_obj.small_level_increment = 5
        mock_config_obj.small_level_decrement = 10
        mock_config_obj.large_level_increment = 10
        mock_config_obj.large_level_decrement = 20
        mock_config_obj.freqs = []  # Empty list
        mock_config_obj.earsides = ['right']
        mock_config_obj.conduction = 'air'
        mock_config_obj.masking = 'off'
        mock_config_obj.pause_time = [0.1, 0.2]
        mock_config_obj.carry_on = None
        mock_config_obj.logging = False
        mock_config_obj.cal_parameters = []
        mock_config.return_value = mock_config_obj
        
        mock_responder_class.return_value = MagicMock()
        mock_audio_class.return_value = MagicMock()
        
        import csv
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        test = AscendingMethod(device_id=None, subject_name="EmptyFreqTest")
        test.ctrl.config.results_path = self.test_dir
        
        # Run test - should handle gracefully
        test.run()
        
        # Should complete with 0% progress (no steps to complete)
        completed, total, percentage = test.get_progress()
        self.assertEqual(total, 0, "Total should be 0 with empty frequencies")
        self.assertEqual(percentage, 0, "Progress should be 0% with no steps")
        print("✓ Empty frequencies list handled gracefully")


if __name__ == '__main__':
    unittest.main()

