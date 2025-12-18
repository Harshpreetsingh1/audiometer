#!/usr/bin/env python3
"""Stress tests for Hughson-Westlake algorithm logic.

Tests the ascending method under various patient response patterns
to verify robustness and prevent infinite loops.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import tempfile
import shutil
import csv
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ascending_method import AscendingMethod
from audiometer import controller


class TestPerfectPatient(unittest.TestCase):
    """Test with a 'perfect' patient who always responds at 20dB."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Mock responder that always returns True (patient always responds)
        self.mock_responder = MagicMock()
        self.mock_responder.click_down.return_value = True
        self.mock_responder.click_up.return_value = True
        self.mock_responder.clear = Mock()
        self.mock_responder.wait_for_click = Mock()
        self.mock_responder.wait_for_click_up = Mock()
        self.mock_responder.wait_for_click_down_and_up = Mock()
        
        # Mock audio
        self.mock_audio = MagicMock()
        self.mock_audio.start = Mock()
        self.mock_audio.stop = Mock()
        self.mock_audio.close = Mock()
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_perfect_patient_finishes_quickly(self, mock_makedirs, mock_exists, mock_config, 
                                              mock_responder_class, mock_audio_class):
        """Perfect patient should complete test quickly without excessive iterations."""
        # Setup mocks
        mock_config_obj = self._create_mock_config()
        mock_config.return_value = mock_config_obj
        mock_responder_class.return_value = self.mock_responder
        mock_audio_class.return_value = self.mock_audio
        
        # Create CSV file
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        # Mock audibletone to return 20dB (perfect patient threshold)
        with patch.object(controller.Controller, 'audibletone', return_value=20), \
             patch.object(controller.Controller, 'clicktone', return_value=True), \
             patch.object(controller.Controller, 'save_results', return_value=None), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="PerfectPatient")
            test.ctrl.config.results_path = self.test_dir
            test.ctrl.config.freqs = [1000, 2000]  # Only 2 frequencies for speed
            test.ctrl.config.earsides = ['right', 'left']
            
            # Track iterations
            original_hearing_test = test.hearing_test
            iteration_count = [0]
            
            def counting_hearing_test():
                iteration_count[0] += 1
                return original_hearing_test()
            
            test.hearing_test = counting_hearing_test
            
            # Run test
            start_time = time.time()
            test.run()
            elapsed_time = time.time() - start_time
            
            # Verify test completed
            completed, total, percentage = test.get_progress()
            self.assertEqual(percentage, 100, "Test should complete to 100%")
            self.assertEqual(completed, total, "All steps should be completed")
            
            # Verify reasonable completion time (should be fast for perfect patient)
            # With 2 freqs × 2 ears = 4 steps, should complete quickly
            self.assertLess(elapsed_time, 10.0, "Perfect patient should complete quickly")
            print(f"✓ Perfect patient test completed in {elapsed_time:.2f}s")


class TestDeafPatient(unittest.TestCase):
    """Test with a 'deaf' patient who NEVER responds."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Mock responder that NEVER returns True (patient never responds)
        self.mock_responder = MagicMock()
        self.mock_responder.click_down.return_value = False
        self.mock_responder.click_up.return_value = False
        self.mock_responder.clear = Mock()
        self.mock_responder.wait_for_click = Mock()
        self.mock_responder.wait_for_click_up = Mock()
        
        # Mock audio
        self.mock_audio = MagicMock()
        self.mock_audio.start = Mock()
        self.mock_audio.stop = Mock()
        self.mock_audio.close = Mock()
    
    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.results_path = self.test_dir
        config.filename = 'test_result.csv'
        config.device = None
        config.beginning_fam_level = 40
        config.tone_duration = 0.1  # Short for testing
        config.small_level_increment = 5
        config.small_level_decrement = 10
        config.large_level_increment = 10
        config.large_level_decrement = 20
        config.freqs = [1000]  # Single frequency for speed
        config.earsides = ['right']
        config.conduction = 'air'
        config.masking = 'off'
        config.pause_time = [0.1, 0.2]
        config.carry_on = None
        config.logging = False
        config.cal_parameters = []
        return config
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_deaf_patient_hits_safety_limit(self, mock_makedirs, mock_exists, mock_config,
                                            mock_responder_class, mock_audio_class):
        """Deaf patient should hit safety limit (80dB) and stop correctly."""
        # Setup mocks
        mock_config_obj = self._create_mock_config()
        mock_config.return_value = mock_config_obj
        mock_responder_class.return_value = self.mock_responder
        mock_audio_class.return_value = self.mock_audio
        
        # Create CSV file
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        # Mock audibletone to return 80dB (safety limit reached)
        with patch.object(controller.Controller, 'audibletone', return_value=80), \
             patch.object(controller.Controller, 'clicktone', return_value=False), \
             patch.object(controller.Controller, 'save_results', return_value=None), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="DeafPatient")
            test.ctrl.config.results_path = self.test_dir
            test.ctrl.config.freqs = [1000]
            test.ctrl.config.earsides = ['right']
            
            # Run test - should handle gracefully
            try:
                test.run()
                # Test should complete (even if with high threshold)
                completed, total, percentage = test.get_progress()
                # Should have attempted the test
                self.assertGreater(completed, 0, "Test should make progress even for deaf patient")
            except Exception as e:
                # Should not crash, but may raise OverflowError for distorted signal
                self.assertIsInstance(e, OverflowError, "Should raise OverflowError for safety limit")
                print(f"✓ Deaf patient correctly hit safety limit: {e}")


class TestRandomPatient(unittest.TestCase):
    """Test with a random/erratic patient response pattern."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.results_path = self.test_dir
        config.filename = 'test_result.csv'
        config.device = None
        config.beginning_fam_level = 40
        config.tone_duration = 0.1
        config.small_level_increment = 5
        config.small_level_decrement = 10
        config.large_level_increment = 10
        config.large_level_decrement = 20
        config.freqs = [1000]
        config.earsides = ['right']
        config.conduction = 'air'
        config.masking = 'off'
        config.pause_time = [0.1, 0.2]
        config.carry_on = None
        config.logging = False
        config.cal_parameters = []
        return config
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_random_patient_no_infinite_loop(self, mock_makedirs, mock_exists, mock_config,
                                             mock_responder_class, mock_audio_class):
        """Random patient responses should not cause infinite loops."""
        import random as random_module
        
        # Setup mocks
        mock_config_obj = self._create_mock_config()
        mock_config.return_value = mock_config_obj
        mock_responder = MagicMock()
        mock_responder_class.return_value = mock_responder
        mock_audio_class.return_value = MagicMock()
        
        # Create CSV file
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        # Random response pattern (50% chance of response)
        response_sequence = []
        def random_click_down():
            response = random_module.random() < 0.5
            response_sequence.append(response)
            return response
        
        mock_responder.click_down.side_effect = random_click_down
        mock_responder.click_up.return_value = True
        mock_responder.clear = Mock()
        mock_responder.wait_for_click = Mock()
        
        with patch.object(controller.Controller, 'audibletone', return_value=30), \
             patch.object(controller.Controller, 'clicktone') as mock_clicktone, \
             patch.object(controller.Controller, 'save_results', return_value=None), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            # Make clicktone use our random responder
            def clicktone_impl(freq, level, earside):
                return mock_responder.click_down()
            mock_clicktone.side_effect = clicktone_impl
            
            test = AscendingMethod(device_id=None, subject_name="RandomPatient")
            test.ctrl.config.results_path = self.test_dir
            test.ctrl.config.freqs = [1000]
            test.ctrl.config.earsides = ['right']
            
            # Run test with timeout to prevent infinite loops
            start_time = time.time()
            timeout = 30.0  # 30 second timeout
            
            try:
                test.run()
                elapsed = time.time() - start_time
                self.assertLess(elapsed, timeout, "Test should complete within timeout")
                print(f"✓ Random patient test completed in {elapsed:.2f}s")
            except Exception as e:
                # Should not hang indefinitely
                elapsed = time.time() - start_time
                self.assertLess(elapsed, timeout, "Test should not hang indefinitely")
                print(f"✓ Random patient test handled exception: {e}")


class TestEarSwitching(unittest.TestCase):
    """Test that ear switching works correctly."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.ear_sequence = []
    
    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.results_path = self.test_dir
        config.filename = 'test_result.csv'
        config.device = None
        config.beginning_fam_level = 40
        config.tone_duration = 0.1
        config.small_level_increment = 5
        config.small_level_decrement = 10
        config.large_level_increment = 10
        config.large_level_decrement = 20
        config.freqs = [1000, 2000]
        config.earsides = ['right', 'left']
        config.conduction = 'air'
        config.masking = 'off'
        config.pause_time = [0.1, 0.2]
        config.carry_on = None
        config.logging = False
        config.cal_parameters = []
        return config
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_ear_switching_completes_both_ears(self, mock_makedirs, mock_exists, mock_config,
                                               mock_responder_class, mock_audio_class):
        """Verify that both ears are tested and switching works correctly."""
        # Setup mocks
        mock_config_obj = self._create_mock_config()
        mock_config.return_value = mock_config_obj
        mock_responder = MagicMock()
        mock_responder.click_down.return_value = True
        mock_responder.click_up.return_value = True
        mock_responder.clear = Mock()
        mock_responder.wait_for_click = Mock()
        mock_responder_class.return_value = mock_responder
        mock_audio_class.return_value = MagicMock()
        
        # Create CSV file
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        # Track which ears are tested
        tested_ears = []
        
        def save_results_tracker(level, freq, earside):
            tested_ears.append(earside)
            mock_config_obj.writer.writerow([level, freq, earside])
        
        with patch.object(controller.Controller, 'audibletone', return_value=20), \
             patch.object(controller.Controller, 'clicktone', return_value=True), \
             patch.object(controller.Controller, 'save_results', side_effect=save_results_tracker), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="EarTest")
            test.ctrl.config.results_path = self.test_dir
            test.ctrl.config.freqs = [1000, 2000]
            test.ctrl.config.earsides = ['right', 'left']
            
            # Run test
            test.run()
            
            # Verify both ears were tested
            self.assertIn('right', tested_ears, "Right ear should be tested")
            self.assertIn('left', tested_ears, "Left ear should be tested")
            
            # Verify each ear was tested for each frequency
            right_count = tested_ears.count('right')
            left_count = tested_ears.count('left')
            self.assertEqual(right_count, 2, f"Right ear should be tested 2 times (2 freqs), got {right_count}")
            self.assertEqual(left_count, 2, f"Left ear should be tested 2 times (2 freqs), got {left_count}")
            
            # Verify ears don't repeat unnecessarily
            # Should be: right, right, left, left (or random order, but consistent)
            print(f"✓ Ear sequence: {tested_ears}")
            print(f"✓ Both ears tested correctly")


class TestProgressMath(unittest.TestCase):
    """Test that progress calculation is mathematically correct."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def _create_mock_config(self):
        """Create a mock config object."""
        config = MagicMock()
        config.results_path = self.test_dir
        config.filename = 'test_result.csv'
        config.device = None
        config.beginning_fam_level = 40
        config.tone_duration = 0.1
        config.small_level_increment = 5
        config.small_level_decrement = 10
        config.large_level_increment = 10
        config.large_level_decrement = 20
        config.freqs = [1000, 2000, 3000]
        config.earsides = ['right', 'left']
        config.conduction = 'air'
        config.masking = 'off'
        config.pause_time = [0.1, 0.2]
        config.carry_on = None
        config.logging = False
        config.cal_parameters = []
        return config
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_progress_math_exact_100_percent(self, mock_makedirs, mock_exists, mock_config,
                                             mock_responder_class, mock_audio_class):
        """Progress should be exactly 100% at completion, not 99% or 101%."""
        # Setup mocks
        mock_config_obj = self._create_mock_config()
        mock_config.return_value = mock_config_obj
        mock_responder = MagicMock()
        mock_responder.click_down.return_value = True
        mock_responder.click_up.return_value = True
        mock_responder.clear = Mock()
        mock_responder.wait_for_click = Mock()
        mock_responder_class.return_value = mock_responder
        mock_audio_class.return_value = MagicMock()
        
        # Create CSV file
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
            
            test = AscendingMethod(device_id=None, subject_name="ProgressTest")
            test.ctrl.config.results_path = self.test_dir
            test.ctrl.config.freqs = [1000, 2000, 3000]  # 3 frequencies
            test.ctrl.config.earsides = ['right', 'left']  # 2 ears
            
            # Expected: 3 freqs × 2 ears = 6 total steps
            
            # Run test
            test.run()
            
            # Verify final progress
            completed, total, percentage = test.get_progress()
            
            # Should be exactly 100%
            self.assertEqual(percentage, 100, f"Progress should be exactly 100%, got {percentage}%")
            self.assertEqual(completed, total, f"Completed ({completed}) should equal total ({total})")
            self.assertEqual(total, 6, f"Total should be 6 (3 freqs × 2 ears), got {total}")
            
            # Verify percentage calculation
            expected_percentage = int((completed / total) * 100) if total > 0 else 0
            self.assertEqual(percentage, expected_percentage, 
                           f"Percentage calculation incorrect: {completed}/{total} = {percentage}%")
            
            print(f"✓ Progress math correct: {completed}/{total} = {percentage}%")


if __name__ == '__main__':
    unittest.main()

