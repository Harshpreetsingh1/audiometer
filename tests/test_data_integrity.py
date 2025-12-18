#!/usr/bin/env python3
"""Data integrity tests for file saving and CSV generation.

Tests that data is never lost and files are created correctly.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
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


class TestDirectoryCreation(unittest.TestCase):
    """Test that user folders are created correctly."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists')
    @patch('audiometer.controller.os.makedirs')
    def test_user_folder_creation(self, mock_makedirs, mock_exists, mock_config,
                                  mock_responder_class, mock_audio_class):
        """Verify user folder structure is created: Results/{SubjectName}/"""
        mock_config_obj = MagicMock()
        mock_config_obj.results_path = os.path.join(self.test_dir, 'audiometer', 'results')
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
        
        mock_exists.return_value = False  # Folder doesn't exist
        
        mock_responder_class.return_value = MagicMock()
        mock_audio_class.return_value = MagicMock()
        
        # Create controller with subject name
        subject_name = "TestUser_123"
        ctrl = controller.Controller(device_id=None, subject_name=subject_name)
        
        # Verify makedirs was called
        self.assertTrue(mock_makedirs.called, "makedirs should be called to create user folder")
        
        # Verify the path includes sanitized subject name
        call_args = mock_makedirs.call_args[0][0]
        self.assertIn('TestUser_123', call_args or '', "User folder path should contain subject name")
        print(f"✓ User folder creation verified: {call_args}")


class TestCSVFormat(unittest.TestCase):
    """Test CSV file format and headers."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_csv_headers_match_data(self, mock_makedirs, mock_exists, mock_config,
                                    mock_responder_class, mock_audio_class):
        """Verify CSV headers match the data columns."""
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
        mock_config_obj.freqs = [1000, 2000]
        mock_config_obj.earsides = ['right', 'left']
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
        
        # Track saved data
        saved_data = []
        
        def save_results_tracker(level, freq, earside):
            saved_data.append([level, freq, earside])
            mock_config_obj.writer.writerow([level, freq, earside])
        
        with patch.object(controller.Controller, 'audibletone', return_value=20), \
             patch.object(controller.Controller, 'clicktone', return_value=True), \
             patch.object(controller.Controller, 'save_results', side_effect=save_results_tracker), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="CSVTest")
            test.ctrl.config.results_path = self.test_dir
            
            # Run test
            test.run()
            
            # Read CSV file
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Verify headers
            self.assertEqual(rows[0], ['Conduction', 'air', ''], "Conduction header should match")
            self.assertEqual(rows[1], ['Masking', 'off', ''], "Masking header should match")
            self.assertEqual(rows[2], ['Level/dB', 'Frequency/Hz', 'Earside'], 
                           "Data header should match: Level/dB, Frequency/Hz, Earside")
            
            # Verify data rows match header format
            for i, data_row in enumerate(rows[3:], start=3):
                self.assertEqual(len(data_row), 3, f"Row {i} should have 3 columns")
                level, freq, earside = data_row
                # Verify types can be parsed
                try:
                    float(level)  # Level should be numeric
                    float(freq)    # Frequency should be numeric
                    self.assertIn(earside.lower(), ['left', 'right'], 
                                f"Earside should be 'left' or 'right', got '{earside}'")
                except ValueError as e:
                    self.fail(f"Row {i} contains invalid data: {e}")
            
            # Verify we have data
            self.assertGreater(len(saved_data), 0, "Should have saved some data")
            print(f"✓ CSV format verified: {len(saved_data)} data rows saved")
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_csv_contains_earside_column(self, mock_makedirs, mock_exists, mock_config,
                                        mock_responder_class, mock_audio_class):
        """Verify CSV contains 'Earside' column with correct values."""
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
        mock_config_obj.freqs = [1000, 2000]
        mock_config_obj.earsides = ['right', 'left']
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
        mock_audio_class.return_value = MagicMock()
        
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        saved_earsides = []
        
        def save_results_tracker(level, freq, earside):
            saved_earsides.append(earside)
            mock_config_obj.writer.writerow([level, freq, earside])
        
        with patch.object(controller.Controller, 'audibletone', return_value=20), \
             patch.object(controller.Controller, 'clicktone', return_value=True), \
             patch.object(controller.Controller, 'save_results', side_effect=save_results_tracker), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="EarsideTest")
            test.ctrl.config.results_path = self.test_dir
            
            test.run()
            
            # Verify earside column contains valid values
            self.assertIn('right', saved_earsides, "CSV should contain 'right' earside")
            self.assertIn('left', saved_earsides, "CSV should contain 'left' earside")
            
            # Verify all earsides are valid
            for earside in saved_earsides:
                self.assertIn(earside.lower(), ['left', 'right'], 
                            f"Invalid earside value: '{earside}'")
            
            print(f"✓ Earside column verified: {saved_earsides}")


class TestPartialResults(unittest.TestCase):
    """Test that partial results are saved when test is stopped mid-way."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    @patch('audiometer.controller.tone_generator.AudioStream')
    @patch('audiometer.controller.responder.Responder')
    @patch('audiometer.controller.config')
    @patch('audiometer.controller.os.path.exists', return_value=True)
    @patch('audiometer.controller.os.makedirs')
    def test_stop_mid_test_saves_partial_results(self, mock_makedirs, mock_exists, mock_config,
                                                mock_responder_class, mock_audio_class):
        """Stopping test mid-way should save partial results without corruption."""
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
        mock_config_obj.freqs = [1000, 2000, 3000, 4000, 5000]  # 5 frequencies
        mock_config_obj.earsides = ['right', 'left']
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
        
        csv_path = os.path.join(self.test_dir, 'test_result.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Conduction', 'air', ''])
            writer.writerow(['Masking', 'off', ''])
            writer.writerow(['Level/dB', 'Frequency/Hz', 'Earside'])
        
        with open(csv_path, 'a', newline='') as f:
            mock_config_obj.csvfile = f
            mock_config_obj.writer = csv.writer(f)
        
        saved_count = [0]
        
        def save_results_tracker(level, freq, earside):
            saved_count[0] += 1
            # Stop after 3 saves (partial completion)
            if saved_count[0] >= 3:
                raise KeyboardInterrupt("Test stopped")
            mock_config_obj.writer.writerow([level, freq, earside])
        
        with patch.object(controller.Controller, 'audibletone', return_value=20), \
             patch.object(controller.Controller, 'clicktone', return_value=True), \
             patch.object(controller.Controller, 'save_results', side_effect=save_results_tracker), \
             patch.object(controller.Controller, 'wait_for_click', return_value=None):
            
            test = AscendingMethod(device_id=None, subject_name="PartialTest")
            test.ctrl.config.results_path = self.test_dir
            
            # Run test - should stop mid-way
            try:
                test.run()
            except KeyboardInterrupt:
                pass  # Expected
            
            # Verify CSV file is not corrupted
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                
                # Should have headers + partial data
                self.assertGreaterEqual(len(rows), 4, "Should have headers + at least 1 data row")
                
                # Verify headers are intact
                self.assertEqual(rows[0], ['Conduction', 'air', ''], "Headers should be intact")
                self.assertEqual(rows[2], ['Level/dB', 'Frequency/Hz', 'Earside'], 
                               "Data header should be intact")
                
                # Verify data rows are valid
                for row in rows[3:]:
                    self.assertEqual(len(row), 3, "Data rows should have 3 columns")
                
                print(f"✓ Partial results saved correctly: {len(rows) - 3} data rows")
            except Exception as e:
                self.fail(f"CSV file should not be corrupted: {e}")


if __name__ == '__main__':
    unittest.main()

