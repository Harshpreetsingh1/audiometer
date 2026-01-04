#!/usr/bin/env python3
"""
PyWebView-based Audiometer Pro Interface

This module provides a modern web-based UI for the PC Audiometer using PyWebView.
It bridges the HTML/JS frontend with the Python audio engine.
"""

import webview
import threading
import logging
import os
import sys
import time
import json
import re
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sounddevice as sd
from ascending_method import AscendingMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


class AudiometerAPI:
    """
    Python API exposed to JavaScript via PyWebView.
    
    This class provides methods that can be called from the frontend JavaScript
    to control the audiometer test and get status updates.
    """
    
    def __init__(self):
        self.window: Optional[webview.Window] = None
        self.test_instance: Optional[AscendingMethod] = None
        self.test_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.test_completed = False
        self.lock = threading.Lock()
        
        # Current test state (updated by callbacks)
        self.current_ear: Optional[str] = None
        self.current_freq: Optional[int] = None
        self.current_level: Optional[float] = None
        self.current_progress: float = 0.0
        
        # Responder simulation for button press
        self._button_pressed = False
        
        # Task 4: Storage for test results (for CSV export)
        self.test_results: Dict[str, Dict[int, float]] = {'left': {}, 'right': {}}
    
    def set_window(self, window: webview.Window):
        """Set the webview window reference for JS calls."""
        self.window = window
    
    # ============================================================
    # Device Management
    # ============================================================
    
    def get_audio_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of available audio output devices.
        
        Returns:
            List of device dictionaries with id, name, and is_default fields.
        """
        try:
            # Force refresh audio devices
            try:
                sd._terminate()
                sd._initialize()
            except Exception:
                pass
            
            devices = sd.query_devices()
            device_list = []
            default_device_id = None
            
            for i, d in enumerate(devices):
                if d.get('max_output_channels', 0) > 0:
                    name = d.get('name', 'Unknown Device')
                    is_usb = 'USB' in name.upper()
                    device_list.append({
                        'id': i,
                        'name': f"{i}: {name}",
                        'is_default': is_usb and default_device_id is None
                    })
                    if is_usb and default_device_id is None:
                        default_device_id = i
            
            # If no USB device, mark first as default
            if device_list and default_device_id is None:
                device_list[0]['is_default'] = True
            
            logging.info(f"Found {len(device_list)} audio output devices")
            return device_list
            
        except Exception as e:
            logging.error(f"Failed to query audio devices: {e}")
            return []
    
    # ============================================================
    # Test Control
    # ============================================================
    
    def start_test(self, device_id: int, patient_name: str, patient_age: str, 
                   patient_id: str, quick_mode: bool = True, mini_mode: bool = False) -> Dict[str, Any]:
        """
        Start the hearing test.
        
        Args:
            device_id: Audio device ID
            patient_name: Patient's name
            patient_age: Patient's age
            patient_id: Patient's ID
            quick_mode: Use quick mode (4 frequencies)
            mini_mode: Use mini mode (2 frequencies)
            
        Returns:
            Dict with success status and optional error message.
        """
        # Guard clause: prevent double-start
        with self.lock:
            if self.is_running:
                return {'success': False, 'error': 'Test already running'}
        
        # Input validation
        try:
            # Validate and sanitize patient name
            if not patient_name or not patient_name.strip():
                return {'success': False, 'error': 'Patient name is required'}
            
            patient_name = patient_name.strip()
            
            # Validate age (optional but must be positive if provided)
            if patient_age and patient_age.strip():
                try:
                    age_val = int(patient_age.strip())
                    if age_val <= 0 or age_val > 150:
                        return {'success': False, 'error': 'Age must be between 1 and 150'}
                except ValueError:
                    return {'success': False, 'error': 'Age must be a valid number'}
            
            # Sanitize patient name for filesystem
            subject_name = self._sanitize_filename(patient_name)
            if patient_id:
                subject_name += f" (ID: {self._sanitize_filename(patient_id)})"
            
            logging.info(f"Starting test for {subject_name} on device {device_id}")
            logging.info(f"Mode: {'mini' if mini_mode else 'quick' if quick_mode else 'full'}")
            
            # Reset state
            self.test_completed = False
            self.current_ear = None
            self.current_freq = None
            self.current_level = None
            self.current_progress = 0.0
            
            # Task 4: Reset results storage
            self.test_results = {'left': {}, 'right': {}}
            
            # Start test in background thread
            self.test_thread = threading.Thread(
                target=self._run_test_thread,
                args=(device_id, subject_name, quick_mode, mini_mode),
                daemon=True,
                name="AudiometerTestThread"
            )
            
            with self.lock:
                self.is_running = True
            
            self.test_thread.start()
            
            return {'success': True}
            
        except Exception as e:
            logging.error(f"Failed to start test: {e}")
            return {'success': False, 'error': str(e)}
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string for use in filesystem paths.
        
        Removes/replaces characters that are invalid in Windows filenames
        and handles Windows reserved names (CON, PRN, AUX, NUL, etc.).
        """
        if not name:
            return 'Unknown'
        
        # Remove/replace invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
        
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip('_. ')
        
        # Check for Windows reserved names
        windows_reserved = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        if sanitized.upper() in windows_reserved:
            sanitized = f"User_{sanitized}"
        
        # Ensure name is not empty after sanitization
        if not sanitized:
            sanitized = 'Unknown'
        
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        
        return sanitized
    
    def _run_test_thread(self, device_id: int, subject_name: str, 
                          quick_mode: bool, mini_mode: bool):
        """Background thread that runs the hearing test."""
        try:
            logging.info("Test thread started")
            
            # Create test instance
            self.test_instance = AscendingMethod(
                device_id=device_id,
                subject_name=subject_name,
                progress_callback=self._on_progress_update,
                ear_change_callback=self._on_ear_change,
                freq_change_callback=self._on_freq_change,
                quick_mode=quick_mode,
                mini_mode=mini_mode
            )
            
            # Run the test
            self.test_instance.run()
            
            # Test completed successfully
            logging.info("Test completed successfully")
            self.test_completed = True
            
            # Task 4: Read results from CSV file for export
            self._collect_results_from_csv()
            
            self._push_update({'progress': 100, 'stopped': True})
            
        except Exception as e:
            logging.error(f"Test thread error: {e}")
            import traceback
            traceback.print_exc()
            self._push_update({'stopped': True, 'error': str(e)})
            
        finally:
            with self.lock:
                self.is_running = False
                self.test_instance = None
    
    def _collect_results_from_csv(self):
        """Read test results from the CSV file after test completion (Task 4)."""
        try:
            if not self.test_instance or not hasattr(self.test_instance, 'ctrl'):
                return
            
            import csv
            
            config = self.test_instance.ctrl.config
            csv_path = os.path.join(config.results_path, config.filename)
            
            if not os.path.exists(csv_path):
                logging.warning(f"CSV file not found: {csv_path}")
                return
            
            # Try/except for file access - handles Excel lock scenario
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        # Skip header rows (Conduction, Masking, Level/dB header)
                        if len(row) >= 3 and row[2] in ['left', 'right']:
                            try:
                                level = float(row[0])
                                freq = int(float(row[1]))
                                ear = row[2]
                                
                                with self.lock:
                                    if ear in self.test_results:
                                        self.test_results[ear][freq] = level
                                        logging.info(f"Collected result: {ear} ear, {freq} Hz = {level} dB")
                            except (ValueError, IndexError) as e:
                                logging.debug(f"Skipping row: {row} - {e}")
            except PermissionError:
                logging.error(f"Cannot read CSV file - it may be open in another program (e.g., Excel): {csv_path}")
            except IOError as e:
                logging.error(f"IO error reading CSV file: {e}")
            
            logging.info(f"Collected results: {self.test_results}")
            
        except Exception as e:
            logging.error(f"Failed to collect results from CSV: {e}")
    
    def stop_test(self) -> Dict[str, Any]:
        """Stop the currently running test."""
        with self.lock:
            if not self.is_running or not self.test_instance:
                return {'success': False, 'error': 'No test running'}
        
        try:
            logging.info("Stop test requested")
            self.test_instance.stop_test()
            
            # Wait briefly for thread to finish
            if self.test_thread and self.test_thread.is_alive():
                self.test_thread.join(timeout=1.0)
            
            return {'success': True}
            
        except Exception as e:
            logging.error(f"Failed to stop test: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_test_state(self) -> Dict[str, Any]:
        """
        Get current test state for UI polling.
        
        Returns:
            Dict with current ear, frequency, level, progress, and running status.
        """
        with self.lock:
            return {
                'is_running': self.is_running,
                'completed': self.test_completed,
                'ear': self.current_ear,
                'frequency': self.current_freq,
                'level': self.current_level,
                'progress': self.current_progress
            }
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get collected test results for CSV export (Task 4).
        
        Returns:
            Dict with success status and data containing results per ear/frequency.
            Also includes 'complete' flag indicating if all frequencies were tested.
        """
        try:
            with self.lock:
                if not self.test_results or (not self.test_results.get('left') and not self.test_results.get('right')):
                    return {'success': False, 'error': 'No results available'}
                
                # Check completeness
                expected_freqs = {125, 250, 500, 1000, 2000, 4000, 8000}
                left_freqs = set(self.test_results.get('left', {}).keys())
                right_freqs = set(self.test_results.get('right', {}).keys())
                
                is_complete = (left_freqs == expected_freqs and right_freqs == expected_freqs)
                
                return {
                    'success': True,
                    'complete': is_complete,
                    'data': {
                        'left': dict(self.test_results.get('left', {})),
                        'right': dict(self.test_results.get('right', {}))
                    }
                }
        except Exception as e:
            logging.error(f"Failed to get results: {e}")
            return {'success': False, 'error': str(e)}
    
    # ============================================================
    # Patient Response
    # ============================================================
    
    def patient_response(self, pressed: bool) -> Dict[str, Any]:
        """
        Handle patient button press/release.
        
        This simulates a keyboard press for the responder system.
        """
        try:
            if self.test_instance and hasattr(self.test_instance, 'ctrl'):
                rpd = self.test_instance.ctrl._rpd
                if pressed:
                    rpd._click_down = True
                else:
                    rpd._click_down = False
                    rpd._click_up = True
            return {'success': True}
        except Exception as e:
            logging.debug(f"Patient response error: {e}")
            return {'success': False}
    
    # ============================================================
    # Callbacks from Test Engine
    # ============================================================
    
    def _on_progress_update(self, progress: float):
        """Called when test progress updates."""
        self.current_progress = progress
        self._push_update({'progress': progress})
    
    def _on_ear_change(self, ear: str):
        """Called when testing ear changes."""
        self.current_ear = ear
        logging.info(f"Testing ear: {ear}")
        self._push_update({'ear': ear})
    
    def _on_freq_change(self, freq: int):
        """Called when testing frequency changes."""
        self.current_freq = freq
        logging.info(f"Testing frequency: {freq} Hz")
        self._push_update({'frequency': freq})
    
    def _on_threshold_determined(self, ear: str, freq: int, level: float):
        """Called when a threshold is determined for a frequency/ear (Task 4)."""
        with self.lock:
            if ear in self.test_results:
                self.test_results[ear][freq] = level
                logging.info(f"Stored result: {ear} ear, {freq} Hz = {level} dB")
        
        # Push result to frontend for real-time storage
        self._push_update({'result': {'ear': ear, 'frequency': freq, 'level': level}})
    
    def _push_update(self, data: Dict[str, Any]):
        """Push state update to JavaScript frontend."""
        if self.window:
            try:
                js_data = json.dumps(data)
                self.window.evaluate_js(f'window.updateFromPython({js_data})')
            except Exception as e:
                logging.debug(f"Failed to push update to JS: {e}")


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for both development and PyInstaller.
    
    When running as a PyInstaller executable, assets are extracted to a
    temporary folder referenced by sys._MEIPASS. In development, we use
    the script's directory as the base path.
    
    Args:
        relative_path: Path relative to the application root.
        
    Returns:
        Absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        base_path = sys._MEIPASS
    else:
        # Running in normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_html_path() -> str:
    """Get the path to the HTML UI file."""
    # Use resource_path for PyInstaller compatibility
    html_path = resource_path('audiometer_ui.html')
    
    if os.path.exists(html_path):
        return html_path
    
    # Fallback to current directory (development)
    if os.path.exists('audiometer_ui.html'):
        return os.path.abspath('audiometer_ui.html')
    
    raise FileNotFoundError("Could not find audiometer_ui.html")


def main():
    """Main entry point for the PyWebView Audiometer application."""
    print("=" * 60)
    print("  Audiometer Pro - PyWebView Edition")
    print("=" * 60)
    
    # Create the API instance
    api = AudiometerAPI()
    
    # Get HTML file path
    try:
        html_path = get_html_path()
        print(f"Loading UI from: {html_path}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    # Create the webview window
    window = webview.create_window(
        title='Audiometer Pro',
        url=html_path,
        js_api=api,
        width=450,
        height=900,
        min_size=(400, 700),
        resizable=True,
        background_color='#050a07'  # Match the dark theme
    )
    
    # Store window reference in API for JS calls
    api.set_window(window)
    
    # Start the webview (this blocks until window is closed)
    print("Starting PyWebView window...")
    webview.start(debug=False)
    
    print("Application closed.")


if __name__ == '__main__':
    main()
