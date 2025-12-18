#!/usr/bin/env python3
"""Automated unit tests for audiometer logic.

Tests the core algorithms without requiring hardware:
- 10dB-down, 5dB-up Hughson-Westlake logic
- Progress calculation
- File generation with user folders
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
from audiometer import audiogram


class TestHughsonWestlakeLogic(unittest.TestCase):
    """Test the 10dB-down, 5dB-up Modified Hughson-Westlake algorithm."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test results
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Mock the audio and responder
        self.mock_audio = MagicMock()
        self.mock_responder = MagicMock()
        
        # Patch controller initialization
        with patch('audiometer.controller.tone_generator.AudioStream', return_value=self.mock_audio), \
             patch('audiometer.controller.responder.Responder', return_value=self.mock_responder), \
             patch('audiometer.controller.os.path.exists', return_value=True), \
             patch('audiometer.controller.os.makedirs'):
            
            # Mock config to use test directory
            with patch('audiometer.controller.config') as mock_config:
                mock_config_obj = MagicMock()
                mock_config_obj.results_path = self.test_dir
                mock_config_obj.filename = 'test_result.csv'
                mock_config_obj.device = None
                mock_config_obj.beginning_fam_level = 40
                mock_config_obj.tone_duration = 2.0
                mock_config_obj.small_level_increment = 5  # 5dB up
                mock_config_obj.small_level_decrement = 10  # 10dB down
                mock_config_obj.large_level_increment = 10
                mock_config_obj.large_level_decrement = 20
                mock_config_obj.freqs = [1000, 2000]
                mock_config_obj.earsides = ['right', 'left']
                mock_config_obj.conduction = 'air'
                mock_config_obj.masking = 'off'
                mock_config_obj.pause_time = [2, 3]
                mock_config_obj.carry_on = None
                mock_config_obj.cal_parameters = []
                mock_config.return_value = mock_config_obj
                
                # Create mock CSV file
                csv_path = os.path.join(self.test_dir, 'test_result.csv')
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Conduction', 'air', None])
                    writer.writerow(['Masking', 'off', None])
                    writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
                
                # Mock controller's CSV writer
                with open(csv_path, 'a', newline='') as f:
                    self.mock_csvfile = f
                    self.mock_writer = csv.writer(f)
    
    def test_10db_down_on_response(self):
        """Test that tone level decreases by 10dB when patient responds."""
        print("\n[TEST] 10dB-down on response")
        
        with patch('audiometer.controller.Controller') as MockController:
            mock_ctrl = MockController.return_value
            mock_ctrl.config.small_level_decrement = 10
            mock_ctrl.config.small_level_increment = 5
            mock_ctrl.config.beginning_fam_level = 40
            mock_ctrl.config.tone_duration = 2.0
            mock_ctrl.config.freqs = [1000]
            mock_ctrl.config.earsides = ['right']
            mock_ctrl.config.results_path = self.test_dir
            mock_ctrl.config.filename = 'test_result.csv'
            mock_ctrl.config.pause_time = [2, 3]
            mock_ctrl.config.large_level_increment = 10
            mock_ctrl.config.large_level_decrement = 20
            mock_ctrl.config.conduction = 'air'
            mock_ctrl.config.masking = 'off'
            mock_ctrl.config.carry_on = None
            mock_ctrl.config.cal_parameters = []
            mock_ctrl._audio = self.mock_audio
            mock_ctrl._rpd = self.mock_responder
            mock_ctrl.dBHL2dBFS = lambda f, d: -20  # Mock conversion
            mock_ctrl.save_results = Mock()
            mock_ctrl.audibletone = Mock(return_value=45)  # Familiarization returns 45dB
            mock_ctrl.clicktone = Mock()
            mock_ctrl.wait_for_click = Mock()
            mock_ctrl.__exit__ = Mock()
            
            # Create CSV file
            csv_path = os.path.join(self.test_dir, 'test_result.csv')
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Conduction', 'air', None])
                writer.writerow(['Masking', 'off', None])
                writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
            
            with open(csv_path, 'a', newline='') as f:
                mock_ctrl.csvfile = f
                mock_ctrl.writer = csv.writer(f)
            
            # Create test instance
            test = AscendingMethod(device_id=None, subject_name=None)
            test.ctrl = mock_ctrl
            test.freq = 1000
            test.earside = 'right'
            test.current_level = 45  # Start at 45dB
            
            # Simulate: Patient responds (click=True)
            # Expected: Level should decrease by 10dB to 35dB
            self.mock_responder.click_down.return_value = True
            mock_ctrl.clicktone.return_value = True  # Patient responds
            
            initial_level = test.current_level
            test.decrement_click(test.ctrl.config.small_level_decrement)
            
            # Verify level decreased by 10dB
            expected_level = initial_level - 10
            self.assertEqual(test.current_level, expected_level,
                           f"Expected level {expected_level}dB, got {test.current_level}dB")
            print(f"  ✓ Level correctly decreased from {initial_level}dB to {test.current_level}dB (-10dB)")
    
    def test_5db_up_on_no_response(self):
        """Test that tone level increases by 5dB when patient doesn't respond."""
        print("\n[TEST] 5dB-up on no response")
        
        with patch('audiometer.controller.Controller') as MockController:
            mock_ctrl = MockController.return_value
            mock_ctrl.config.small_level_increment = 5
            mock_ctrl.config.small_level_decrement = 10
            mock_ctrl.config.tone_duration = 2.0
            mock_ctrl._audio = self.mock_audio
            mock_ctrl._rpd = self.mock_responder
            mock_ctrl.dBHL2dBFS = lambda f, d: -20
            mock_ctrl.clicktone = Mock()
            
            test = AscendingMethod(device_id=None, subject_name=None)
            test.ctrl = mock_ctrl
            test.freq = 1000
            test.earside = 'right'
            test.current_level = 40  # Start at 40dB
            
            # Simulate: Patient doesn't respond (click=False)
            # Expected: Level should increase by 5dB to 45dB
            self.mock_responder.click_down.return_value = False
            mock_ctrl.clicktone.return_value = False  # No response
            
            initial_level = test.current_level
            test.increment_click(test.ctrl.config.small_level_increment)
            
            # Verify level increased by 5dB
            expected_level = initial_level + 5
            self.assertEqual(test.current_level, expected_level,
                           f"Expected level {expected_level}dB, got {test.current_level}dB")
            print(f"  ✓ Level correctly increased from {initial_level}dB to {test.current_level}dB (+5dB)")


class TestProgressCalculation(unittest.TestCase):
    """Test progress tracking and calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def test_progress_calculation_25_percent(self):
        """Test that progress is 25% after completing 1 of 4 total steps."""
        print("\n[TEST] Progress calculation: 1/4 = 25%")
        
        with patch('audiometer.controller.Controller') as MockController:
            mock_ctrl = MockController.return_value
            mock_ctrl.config.freqs = [1000, 2000]  # 2 frequencies
            mock_ctrl.config.earsides = ['right', 'left']  # 2 ears
            mock_ctrl.config.results_path = self.test_dir
            mock_ctrl.config.filename = 'test_result.csv'
            mock_ctrl.config.beginning_fam_level = 40
            mock_ctrl.config.tone_duration = 2.0
            mock_ctrl.config.small_level_increment = 5
            mock_ctrl.config.small_level_decrement = 10
            mock_ctrl.config.large_level_increment = 10
            mock_ctrl.config.large_level_decrement = 20
            mock_ctrl.config.pause_time = [2, 3]
            mock_ctrl.config.conduction = 'air'
            mock_ctrl.config.masking = 'off'
            mock_ctrl.config.carry_on = None
            mock_ctrl.config.cal_parameters = []
            mock_ctrl._audio = MagicMock()
            mock_ctrl._rpd = MagicMock()
            mock_ctrl.dBHL2dBFS = lambda f, d: -20
            mock_ctrl.save_results = Mock()
            mock_ctrl.audibletone = Mock(return_value=40)
            mock_ctrl.clicktone = Mock(return_value=True)
            mock_ctrl.wait_for_click = Mock()
            mock_ctrl.__exit__ = Mock()
            
            # Create CSV file
            csv_path = os.path.join(self.test_dir, 'test_result.csv')
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Conduction', 'air', None])
                writer.writerow(['Masking', 'off', None])
                writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
            
            with open(csv_path, 'a', newline='') as f:
                mock_ctrl.csvfile = f
                mock_ctrl.writer = csv.writer(f)
            
            # Create test instance
            test = AscendingMethod(device_id=None, subject_name=None)
            test.ctrl = mock_ctrl
            
            # Initialize progress tracking
            # Total steps = 2 frequencies × 2 ears = 4
            test._total_steps = len(mock_ctrl.config.freqs) * len(mock_ctrl.config.earsides)
            test._completed_steps = 0
            
            # Simulate completing 1 frequency (1 step)
            test._completed_steps = 1
            
            # Get progress
            completed, total, percentage = test.get_progress()
            
            # Verify calculations
            self.assertEqual(total, 4, "Total steps should be 4 (2 freqs × 2 ears)")
            self.assertEqual(completed, 1, "Completed steps should be 1")
            self.assertEqual(percentage, 25, "Progress should be 25% (1/4)")
            print(f"  ✓ Progress: {completed}/{total} = {percentage}%")
    
    def test_progress_calculation_50_percent(self):
        """Test that progress is 50% after completing 2 of 4 total steps."""
        print("\n[TEST] Progress calculation: 2/4 = 50%")
        
        with patch('audiometer.controller.Controller') as MockController:
            mock_ctrl = MockController.return_value
            mock_ctrl.config.freqs = [1000, 2000]
            mock_ctrl.config.earsides = ['right', 'left']
            mock_ctrl.config.results_path = self.test_dir
            mock_ctrl.config.filename = 'test_result.csv'
            mock_ctrl.config.beginning_fam_level = 40
            mock_ctrl.config.tone_duration = 2.0
            mock_ctrl.config.small_level_increment = 5
            mock_ctrl.config.small_level_decrement = 10
            mock_ctrl.config.large_level_increment = 10
            mock_ctrl.config.large_level_decrement = 20
            mock_ctrl.config.pause_time = [2, 3]
            mock_ctrl.config.conduction = 'air'
            mock_ctrl.config.masking = 'off'
            mock_ctrl.config.carry_on = None
            mock_ctrl.config.cal_parameters = []
            mock_ctrl._audio = MagicMock()
            mock_ctrl._rpd = MagicMock()
            mock_ctrl.dBHL2dBFS = lambda f, d: -20
            mock_ctrl.save_results = Mock()
            mock_ctrl.audibletone = Mock(return_value=40)
            mock_ctrl.clicktone = Mock(return_value=True)
            mock_ctrl.wait_for_click = Mock()
            mock_ctrl.__exit__ = Mock()
            
            csv_path = os.path.join(self.test_dir, 'test_result.csv')
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Conduction', 'air', None])
                writer.writerow(['Masking', 'off', None])
                writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
            
            with open(csv_path, 'a', newline='') as f:
                mock_ctrl.csvfile = f
                mock_ctrl.writer = csv.writer(f)
            
            test = AscendingMethod(device_id=None, subject_name=None)
            test.ctrl = mock_ctrl
            
            test._total_steps = len(mock_ctrl.config.freqs) * len(mock_ctrl.config.earsides)
            test._completed_steps = 2  # Completed 2 steps (e.g., all RIGHT ear frequencies)
            
            completed, total, percentage = test.get_progress()
            
            self.assertEqual(percentage, 50, "Progress should be 50% (2/4)")
            print(f"  ✓ Progress: {completed}/{total} = {percentage}%")


class TestFileGeneration(unittest.TestCase):
    """Test file generation with user folder structure."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def test_user_folder_creation(self):
        """Test that user folder is created when subject_name is provided."""
        print("\n[TEST] User folder creation")
        
        subject_name = "TestUser"
        sanitized_name = "TestUser"  # Should be sanitized by controller
        
        with patch('audiometer.controller.config') as mock_config, \
             patch('audiometer.controller.tone_generator.AudioStream') as mock_audio_class, \
             patch('audiometer.controller.responder.Responder') as mock_responder_class, \
             patch('os.path.exists') as mock_exists, \
             patch('os.makedirs') as mock_makedirs:
            
            # Setup mocks
            mock_config_obj = MagicMock()
            mock_config_obj.results_path = os.path.join(self.test_dir, 'audiometer', 'results')
            mock_config_obj.filename = f'result_{time.strftime("%Y-%m-%d_%H-%M-%S")}.csv'
            mock_config_obj.device = None
            mock_config_obj.beginning_fam_level = 40
            mock_config_obj.tone_duration = 2.0
            mock_config_obj.small_level_increment = 5
            mock_config_obj.small_level_decrement = 10
            mock_config_obj.large_level_increment = 10
            mock_config_obj.large_level_decrement = 20
            mock_config_obj.freqs = [1000]
            mock_config_obj.earsides = ['right']
            mock_config_obj.conduction = 'air'
            mock_config_obj.masking = 'off'
            mock_config_obj.pause_time = [2, 3]
            mock_config_obj.carry_on = None
            mock_config_obj.cal_parameters = []
            mock_config.return_value = mock_config_obj
            
            mock_exists.return_value = False  # Folder doesn't exist yet
            
            mock_audio = MagicMock()
            mock_audio_class.return_value = mock_audio
            
            mock_responder = MagicMock()
            mock_responder_class.return_value = mock_responder
            
            # Create controller with subject name
            ctrl = controller.Controller(device_id=None, subject_name=subject_name)
            
            # Verify makedirs was called to create user folder
            user_folder_path = os.path.join(mock_config_obj.results_path, sanitized_name)
            mock_makedirs.assert_called_with(user_folder_path)
            print(f"  ✓ User folder creation called: {user_folder_path}")
            
            # Verify results_path was updated
            self.assertEqual(ctrl.config.results_path, user_folder_path,
                           "Results path should point to user folder")
            print(f"  ✓ Results path updated to: {ctrl.config.results_path}")
    
    def test_csv_file_generation(self):
        """Test that CSV file is created in user folder."""
        print("\n[TEST] CSV file generation in user folder")
        
        subject_name = "TestUser"
        results_base = os.path.join(self.test_dir, 'audiometer', 'results')
        user_folder = os.path.join(results_base, subject_name)
        os.makedirs(user_folder, exist_ok=True)
        
        with patch('audiometer.controller.config') as mock_config, \
             patch('audiometer.controller.tone_generator.AudioStream') as mock_audio_class, \
             patch('audiometer.controller.responder.Responder') as mock_responder_class, \
             patch('os.path.exists', return_value=True):
            
            mock_config_obj = MagicMock()
            mock_config_obj.results_path = user_folder
            mock_config_obj.filename = 'test_result.csv'
            mock_config_obj.device = None
            mock_config_obj.beginning_fam_level = 40
            mock_config_obj.tone_duration = 2.0
            mock_config_obj.small_level_increment = 5
            mock_config_obj.small_level_decrement = 10
            mock_config_obj.large_level_increment = 10
            mock_config_obj.large_level_decrement = 20
            mock_config_obj.freqs = [1000]
            mock_config_obj.earsides = ['right']
            mock_config_obj.conduction = 'air'
            mock_config_obj.masking = 'off'
            mock_config_obj.pause_time = [2, 3]
            mock_config_obj.carry_on = None
            mock_config_obj.cal_parameters = []
            mock_config.return_value = mock_config_obj
            
            mock_audio_class.return_value = MagicMock()
            mock_responder_class.return_value = MagicMock()
            
            ctrl = controller.Controller(device_id=None, subject_name=subject_name)
            
            # Verify CSV file was created
            csv_path = os.path.join(user_folder, 'test_result.csv')
            self.assertTrue(os.path.exists(csv_path), f"CSV file should exist at {csv_path}")
            print(f"  ✓ CSV file created: {csv_path}")
            
            # Verify CSV content
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                self.assertEqual(rows[0], ['Conduction', 'air', ''])
                self.assertEqual(rows[1], ['Masking', 'off', ''])
                self.assertEqual(rows[2], ['Level/dB', 'Frequency/Hz', 'Earside'])
            print("  ✓ CSV file has correct header structure")
    
    @patch('audiometer.audiogram.make_audiogram')
    def test_audiogram_generation(self, mock_make_audiogram):
        """Test that audiogram PDF is generated after test completion."""
        print("\n[TEST] Audiogram PDF generation")
        
        subject_name = "TestUser"
        results_base = os.path.join(self.test_dir, 'audiometer', 'results')
        user_folder = os.path.join(results_base, subject_name)
        os.makedirs(user_folder, exist_ok=True)
        
        csv_filename = 'test_result.csv'
        csv_path = os.path.join(user_folder, csv_filename)
        
        # Create test CSV file
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
            writer.writerow(['25', '1000', 'right'])
            writer.writerow(['30', '2000', 'right'])
        
        with patch('audiometer.controller.Controller') as MockController:
            mock_ctrl = MockController.return_value
            mock_ctrl.config.results_path = user_folder
            mock_ctrl.config.filename = csv_filename
            mock_ctrl.config.freqs = [1000]
            mock_ctrl.config.earsides = ['right']
            mock_ctrl.config.beginning_fam_level = 40
            mock_ctrl.config.tone_duration = 2.0
            mock_ctrl.config.small_level_increment = 5
            mock_ctrl.config.small_level_decrement = 10
            mock_ctrl.config.large_level_increment = 10
            mock_ctrl.config.large_level_decrement = 20
            mock_ctrl.config.pause_time = [2, 3]
            mock_ctrl.config.conduction = 'air'
            mock_ctrl.config.masking = 'off'
            mock_ctrl.config.carry_on = None
            mock_ctrl.config.cal_parameters = []
            mock_ctrl._audio = MagicMock()
            mock_ctrl._rpd = MagicMock()
            mock_ctrl.dBHL2dBFS = lambda f, d: -20
            mock_ctrl.save_results = Mock()
            mock_ctrl.audibletone = Mock(return_value=40)
            mock_ctrl.clicktone = Mock(return_value=True)
            mock_ctrl.wait_for_click = Mock()
            mock_ctrl.__exit__ = Mock()
            
            with open(csv_path, 'a', newline='') as f:
                mock_ctrl.csvfile = f
                mock_ctrl.writer = csv.writer(f)
            
            test = AscendingMethod(device_id=None, subject_name=subject_name)
            test.ctrl = mock_ctrl
            
            # Simulate test completion (__exit__ is called)
            test.__exit__(None, None, None)
            
            # Verify make_audiogram was called with correct parameters
            mock_make_audiogram.assert_called_once()
            call_args = mock_make_audiogram.call_args
            self.assertEqual(call_args[0][0], csv_filename)
            self.assertEqual(call_args[0][1], user_folder)
            print(f"  ✓ make_audiogram called with: {call_args[0][0]}, {call_args[0][1]}")


def run_tests():
    """Run all automated tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestHughsonWestlakeLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestProgressCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestFileGeneration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())


