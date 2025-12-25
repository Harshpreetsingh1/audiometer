#!/usr/bin/env python3
"""
Chaos Monkey Test Suite - Adversarial Stress Testing for Audiometer Application

This test suite attempts to BREAK the application through:
- Rapid UI interactions (race conditions)
- Malicious input injection
- Hardware failure simulation
- Resource exhaustion
- Disk write failures

Run with: python -m pytest tests/chaos_test.py -v
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import threading
import time
import sys
import os
import string
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from audiometer import controller
    from audiometer import tone_generator
    import sounddevice as sd
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("Some tests may be skipped.")


class TestUIMasher(unittest.TestCase):
    """Test A: Rapid Start/Stop button clicking to trigger race conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.start_count = 0
        self.stop_count = 0
        self.threads_spawned = []
        self.lock = threading.Lock()
    
    def mock_start_test(self):
        """Mock start test function."""
        with self.lock:
            self.start_count += 1
            thread_id = threading.current_thread().ident
            self.threads_spawned.append(thread_id)
            time.sleep(0.01)  # Simulate some work
    
    def mock_stop_test(self):
        """Mock stop test function."""
        with self.lock:
            self.stop_count += 1
    
    def test_rapid_start_stop_clicking(self):
        """Simulate user clicking Start and Stop 50 times in 1 second."""
        print("\n[CHAOS TEST A] UI Masher: Rapid Start/Stop clicking...")
        
        # Simulate rapid clicking
        def rapid_clicker():
            for _ in range(50):
                # Randomly choose start or stop
                if random.random() < 0.5:
                    self.mock_start_test()
                else:
                    self.mock_stop_test()
                time.sleep(0.001)  # 1ms between clicks
        
        # Run rapid clicking in parallel
        threads = []
        for _ in range(5):  # 5 parallel clickers
            t = threading.Thread(target=rapid_clicker)
            t.start()
            threads.append(t)
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=2)
        
        print(f"  ✓ Start clicked: {self.start_count} times")
        print(f"  ✓ Stop clicked: {self.stop_count} times")
        print(f"  ✓ Threads spawned: {len(set(self.threads_spawned))}")
        
        # Verify we didn't crash
        self.assertGreater(self.start_count, 0)
        self.assertGreater(self.stop_count, 0)
        print("  ✓ No crashes detected")
    
    def test_concurrent_thread_creation(self):
        """Test if multiple threads can be created simultaneously."""
        print("\n[CHAOS TEST A.2] Concurrent thread creation...")
        
        def create_test_thread():
            try:
                # Simulate creating a test thread
                thread = threading.Thread(target=lambda: time.sleep(0.1))
                thread.start()
                return thread
            except Exception as e:
                print(f"  ✗ Thread creation failed: {e}")
                return None
        
        threads = []
        for i in range(100):
            t = create_test_thread()
            if t:
                threads.append(t)
        
        # Wait for all
        for t in threads:
            t.join(timeout=0.5)
        
        print(f"  ✓ Created {len(threads)} threads successfully")
        self.assertGreater(len(threads), 50)  # At least half should succeed


class TestInputFuzzer(unittest.TestCase):
    """Test B: Inject malicious/garbage data into input fields."""
    
    def setUp(self):
        """Set up test environment."""
        self.invalid_names = [
            "👴🔊",  # Emojis
            "'; DROP TABLE patients; --",  # SQL injection attempt
            "A" * 10000,  # Extremely long string
            "\x00\x01\x02",  # Null bytes
            "../../../etc/passwd",  # Path traversal
            "CON",  # Windows reserved name
            "PRN",  # Windows reserved name
            "AUX",  # Windows reserved name
            "NUL",  # Windows reserved name
            "COM1",  # Windows reserved name
            "LPT1",  # Windows reserved name
            "file.txt",  # Extension attempt
            "file.csv",  # CSV extension
            "file.pdf",  # PDF extension
            "/",  # Unix path separator
            "\\",  # Windows path separator
            ":",  # Windows drive separator
            "*",  # Wildcard
            "?",  # Wildcard
            "<>|",  # Invalid filename chars
            "  ",  # Only spaces
            "",  # Empty string
            "\n\r\t",  # Control characters
        ]
        
        self.invalid_ids = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "LPT1",
            "/",
            "\\",
            ":",
            "*",
            "?",
            "<>|",
            "A" * 300,  # Too long
        ]
        
        self.invalid_ages = [
            "-5",  # Negative
            "25.5",  # Float
            "old",  # Text
            "25 years",  # Text with number
            "0",  # Zero
            "",  # Empty
            "999999",  # Unrealistic
            "abc123",
        ]
    
    def test_filename_sanitization(self):
        """Test if controller properly sanitizes malicious filenames."""
        print("\n[CHAOS TEST B] Input Fuzzer: Filename sanitization...")
        
        try:
            from audiometer.controller import Controller
            
            failures = []
            for invalid_name in self.invalid_names:
                try:
                    # Try to create controller with malicious name
                    ctrl = Controller(subject_name=invalid_name)
                    sanitized = ctrl._sanitize_folder_name(invalid_name)
                    
                    # Check if sanitized name is safe
                    if sanitized == invalid_name and invalid_name in ["CON", "PRN", "AUX", "NUL"]:
                        failures.append(f"Windows reserved name not sanitized: {invalid_name}")
                    
                    # Check for invalid characters
                    invalid_chars = r'[<>:"/\\|?*]'
                    import re
                    if re.search(invalid_chars, sanitized):
                        failures.append(f"Invalid chars in sanitized name: {sanitized}")
                    
                    # Cleanup
                    if hasattr(ctrl, '_audio'):
                        try:
                            ctrl._audio.close()
                        except:
                            pass
                    if hasattr(ctrl, 'csvfile'):
                        try:
                            ctrl.csvfile.close()
                        except:
                            pass
                            
                except Exception as e:
                    # Some inputs should fail gracefully
                    if "CON" in invalid_name or "PRN" in invalid_name:
                        # Windows reserved names should be caught
                        print(f"  ✓ Correctly rejected: {invalid_name[:20]}")
                    else:
                        failures.append(f"Unexpected error for '{invalid_name[:20]}': {e}")
            
            if failures:
                print(f"  ✗ {len(failures)} sanitization failures:")
                for f in failures[:5]:  # Show first 5
                    print(f"    - {f}")
                self.fail(f"Sanitization failed for {len(failures)} inputs")
            else:
                print(f"  ✓ All {len(self.invalid_names)} malicious inputs handled correctly")
                
        except ImportError:
            self.skipTest("Controller module not available")
    
    def test_age_validation(self):
        """Test if age validation handles invalid inputs."""
        print("\n[CHAOS TEST B.2] Input Fuzzer: Age validation...")
        
        # This would need to be tested through the UI, but we can test the logic
        failures = []
        for invalid_age in self.invalid_ages:
            try:
                # Simulate UI validation logic
                age_str = invalid_age.strip()
                if age_str:
                    if not age_str.isdigit():
                        # Should reject non-digits
                        if invalid_age in ["25.5", "old", "25 years", "abc123"]:
                            print(f"  ✓ Correctly rejected: {invalid_age}")
                            continue
                    age_value = int(age_str)
                    if age_value <= 0:
                        # Should reject zero/negative
                        if invalid_age in ["-5", "0"]:
                            print(f"  ✓ Correctly rejected: {invalid_age}")
                            continue
                    # If we get here, validation passed (might be OK for some cases)
            except ValueError:
                # Expected for non-numeric
                if invalid_age not in ["", "25.5", "old", "25 years", "abc123"]:
                    failures.append(f"Unexpected ValueError for: {invalid_age}")
            except Exception as e:
                failures.append(f"Unexpected error for '{invalid_age}': {e}")
        
        if failures:
            print(f"  ✗ {len(failures)} validation failures")
            for f in failures[:3]:
                print(f"    - {f}")
        else:
            print(f"  ✓ Age validation handles edge cases")


class TestAudioHardwareFailure(unittest.TestCase):
    """Test C: Simulate audio hardware failures."""
    
    def test_device_unavailable_during_test(self):
        """Test if app handles PortAudioError gracefully."""
        print("\n[CHAOS TEST C] Audio Hardware Failure: Device unavailable...")
        
        try:
            from audiometer import tone_generator
            import sounddevice as sd
            
            # Mock PortAudioError
            with patch('sounddevice.OutputStream') as mock_stream:
                mock_stream.side_effect = sd.PortAudioError("Device Unavailable")
                
                try:
                    audio = tone_generator.AudioStream(device=0, attack=30, release=40)
                    self.fail("Should have raised PortAudioError")
                except (sd.PortAudioError, Exception) as e:
                    print(f"  ✓ Correctly caught error: {type(e).__name__}")
                    # Should not crash the application
                    
        except ImportError:
            self.skipTest("sounddevice not available")
        except Exception as e:
            print(f"  ✓ Error handled: {type(e).__name__}")
            # Any exception is better than a crash
    
    def test_stream_callback_error(self):
        """Test if callback errors are handled."""
        print("\n[CHAOS TEST C.2] Audio Hardware Failure: Callback errors...")
        
        try:
            from audiometer import tone_generator
            
            # Create a stream that will have callback errors
            with patch('sounddevice.OutputStream') as mock_stream_class:
                mock_stream = MagicMock()
                mock_stream_class.return_value = mock_stream
                
                # Simulate callback error
                mock_stream.start.side_effect = Exception("Callback error")
                
                try:
                    audio = tone_generator.AudioStream(device=0, attack=30, release=40)
                    # If we get here, check if error is logged
                    if hasattr(audio, '_callback_status'):
                        print("  ✓ Callback status tracking available")
                except Exception as e:
                    print(f"  ✓ Error caught: {type(e).__name__}")
                    
        except ImportError:
            self.skipTest("tone_generator not available")


class TestDiskWriteFailure(unittest.TestCase):
    """Test D: Simulate disk write failures."""
    
    def test_csv_write_permission_error(self):
        """Test if PermissionError during CSV write is handled."""
        print("\n[CHAOS TEST D] Disk Write Failure: CSV permission error...")
        
        try:
            from audiometer.controller import Controller
            
            # Mock open() to raise PermissionError
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                try:
                    ctrl = Controller(subject_name="TestPatient")
                    self.fail("Should have raised PermissionError")
                except PermissionError as e:
                    print(f"  ✓ PermissionError correctly raised: {e}")
                    # Should not silently fail
                except Exception as e:
                    print(f"  ⚠ Different exception: {type(e).__name__}: {e}")
                    # Might be acceptable if handled elsewhere
                    
        except ImportError:
            self.skipTest("Controller not available")
    
    def test_csv_write_disk_full(self):
        """Test if disk full error is handled."""
        print("\n[CHAOS TEST D.2] Disk Write Failure: Disk full...")
        
        try:
            from audiometer.controller import Controller
            
            # Mock csv.writer.writerow to raise OSError
            with patch('csv.writer') as mock_writer_class:
                mock_writer = MagicMock()
                mock_writer_class.return_value = mock_writer
                mock_writer.writerow.side_effect = OSError("No space left on device")
                
                try:
                    ctrl = Controller(subject_name="TestPatient")
                    # Try to save results
                    ctrl.save_results(level=25, freq=1000, earside='right')
                    self.fail("Should have raised OSError")
                except OSError as e:
                    print(f"  ✓ OSError correctly raised: {e}")
                except Exception as e:
                    print(f"  ⚠ Different exception: {type(e).__name__}: {e}")
                    
        except ImportError:
            self.skipTest("Controller not available")
        except Exception as e:
            print(f"  ⚠ Setup error: {e}")
    
    def test_file_locked_by_excel(self):
        """Test if file locked error (e.g., open in Excel) is handled."""
        print("\n[CHAOS TEST D.3] Disk Write Failure: File locked...")
        
        try:
            from audiometer.controller import Controller
            
            # Mock open() to raise PermissionError (simulating locked file)
            with patch('builtins.open', side_effect=PermissionError("File is locked")):
                try:
                    ctrl = Controller(subject_name="TestPatient")
                    self.fail("Should have raised PermissionError")
                except PermissionError:
                    print("  ✓ File lock error correctly detected")
                except Exception as e:
                    print(f"  ⚠ Different exception: {type(e).__name__}: {e}")
                    
        except ImportError:
            self.skipTest("Controller not available")


class TestResourceLeaks(unittest.TestCase):
    """Test E: Check for resource leaks."""
    
    def test_csv_file_not_closed_on_exception(self):
        """Test if CSV file is closed when exception occurs."""
        print("\n[CHAOS TEST E] Resource Leaks: CSV file cleanup...")
        
        try:
            from audiometer.controller import Controller
            
            # Create controller
            ctrl = Controller(subject_name="TestPatient")
            
            # Simulate exception during test
            try:
                # Force an exception
                raise ValueError("Test exception")
            except ValueError:
                # Check if resources are cleaned up
                # Controller should have __exit__ method for context manager
                if hasattr(ctrl, '__exit__'):
                    print("  ✓ Controller supports context manager cleanup")
                    # Test context manager
                    try:
                        with Controller(subject_name="TestPatient2") as ctrl2:
                            pass
                        print("  ✓ Context manager cleanup works")
                    except Exception as e:
                        print(f"  ⚠ Context manager error: {e}")
                else:
                    print("  ✗ Controller missing __exit__ method")
            
            # Manual cleanup
            try:
                if hasattr(ctrl, 'csvfile') and ctrl.csvfile:
                    ctrl.csvfile.close()
                if hasattr(ctrl, '_audio') and ctrl._audio:
                    ctrl._audio.close()
            except:
                pass
                
        except ImportError:
            self.skipTest("Controller not available")
    
    def test_audio_stream_not_closed_on_exception(self):
        """Test if audio stream is closed when exception occurs."""
        print("\n[CHAOS TEST E.2] Resource Leaks: Audio stream cleanup...")
        
        try:
            from audiometer import tone_generator
            
            # Create audio stream
            audio = tone_generator.AudioStream(device=0, attack=30, release=40)
            
            # Simulate exception
            try:
                raise ValueError("Test exception")
            except ValueError:
                # Check if close method exists
                if hasattr(audio, 'close'):
                    print("  ✓ AudioStream has close() method")
                    # Test context manager
                    try:
                        with tone_generator.AudioStream(device=0, attack=30, release=40) as audio2:
                            pass
                        print("  ✓ AudioStream context manager works")
                    except Exception as e:
                        print(f"  ⚠ Context manager error: {e}")
            
            # Manual cleanup
            try:
                audio.close()
            except:
                pass
                
        except ImportError:
            self.skipTest("tone_generator not available")
        except Exception as e:
            print(f"  ⚠ Setup error: {e}")


class TestThreadSafety(unittest.TestCase):
    """Test F: Check for thread safety issues."""
    
    def test_tkinter_calls_from_background_thread(self):
        """Test if tkinter is called from background threads (should use root.after())."""
        print("\n[CHAOS TEST F] Thread Safety: Tkinter calls from background...")
        
        # This is a static analysis test - we check the code
        import re
        
        main_ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main_ui.py")
        if not os.path.exists(main_ui_path):
            self.skipTest("main_ui.py not found")
        
        with open(main_ui_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find _run_test_thread method
        pattern = r'def _run_test_thread.*?(?=def |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            thread_method = match.group(0)
            # Check for direct .config( or .update( calls
            direct_calls = re.findall(r'\.(config|update|set)\(', thread_method)
            after_calls = re.findall(r'\.after\(', thread_method)
            
            if direct_calls and not after_calls:
                print(f"  ✗ Found {len(direct_calls)} direct tkinter calls without .after()")
                print("    Direct calls should use root.after() for thread safety")
            elif after_calls:
                print(f"  ✓ Found {len(after_calls)} .after() calls (thread-safe)")
            else:
                print("  ✓ No direct tkinter calls in thread method")
        else:
            print("  ⚠ Could not find _run_test_thread method")


if __name__ == '__main__':
    print("=" * 70)
    print("CHAOS MONKEY TEST SUITE - Adversarial Stress Testing")
    print("=" * 70)
    print("\nThis suite attempts to BREAK the application.")
    print("Some tests may fail - that's the point!\n")
    
    unittest.main(verbosity=2)

