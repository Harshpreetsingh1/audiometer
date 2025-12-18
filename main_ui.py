#!/usr/bin/env python3
"""
PC Audiometer GUI - Professional hearing test interface using ttkbootstrap
Requires USB headphones connected to the PC
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox as tk_messagebox
import threading
import sounddevice as sd
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from ascending_method import AscendingMethod


class AudiometerUI(ttk.Window):
    """Main GUI application for PC Audiometer."""
    
    def __init__(self):
        """Initialize the GUI with Superhero (dark) theme."""
        super().__init__(themename="superhero", title="PC Audiometer", resizable=(False, False))
        
        # Window configuration
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # Test state
        self.current_test = None
        self.test_thread = None
        self.is_running = False
        self.test_stop_requested = False
        self.test_lock = threading.Lock()
        self.last_progress = 0
        self.button_flash_active = False
        
        # Build UI
        self._create_widgets()
        self._setup_layout()
        self._load_audio_devices()
        
        # Start UI update polling
        self._poll_ui_updates()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # === SIDEBAR (Left - 30%) ===
        self.sidebar_frame = ttk.Frame(self, padding=20)
        
        # Title
        title_label = ttk.Label(
            self.sidebar_frame,
            text="PC AUDIOMETER",
            font=("Helvetica", 18, "bold"),
            bootstyle="primary"
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            self.sidebar_frame,
            text="Hearing Assessment System",
            font=("Helvetica", 10),
            bootstyle="secondary"
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Patient Details Section
        patient_frame = ttk.Labelframe(
            self.sidebar_frame,
            text="Patient Details",
            padding=15,
            bootstyle="info"
        )
        patient_frame.pack(fill=X, pady=(0, 15))
        
        # Name
        ttk.Label(patient_frame, text="Name:", font=("Helvetica", 9)).pack(anchor=W, pady=(0, 5))
        self.name_entry = ttk.Entry(patient_frame, width=25, font=("Helvetica", 10))
        self.name_entry.pack(fill=X, pady=(0, 10))
        
        # Age
        ttk.Label(patient_frame, text="Age:", font=("Helvetica", 9)).pack(anchor=W, pady=(0, 5))
        self.age_entry = ttk.Entry(patient_frame, width=25, font=("Helvetica", 10))
        self.age_entry.pack(fill=X, pady=(0, 10))
        
        # ID with Generate button
        id_label_frame = ttk.Frame(patient_frame)
        id_label_frame.pack(fill=X, pady=(0, 5))
        ttk.Label(id_label_frame, text="Patient ID:", font=("Helvetica", 9)).pack(side=LEFT, anchor=W)
        
        id_input_frame = ttk.Frame(patient_frame)
        id_input_frame.pack(fill=X)
        self.id_entry = ttk.Entry(id_input_frame, width=18, font=("Helvetica", 10))
        self.id_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        self.generate_id_button = ttk.Button(
            id_input_frame,
            text="Generate",
            command=self._generate_patient_id,
            bootstyle="secondary",
            width=8
        )
        self.generate_id_button.pack(side=RIGHT)
        
        # Device Setup Section
        device_frame = ttk.Labelframe(
            self.sidebar_frame,
            text="Device Setup",
            padding=15,
            bootstyle="info"
        )
        device_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(device_frame, text="USB Headset:", font=("Helvetica", 9)).pack(anchor=W, pady=(0, 5))
        self.device_var = ttk.StringVar()
        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            width=23,
            state="readonly",
            font=("Helvetica", 10)
        )
        self.device_combo.pack(fill=X)
        
        # Test Config Section
        config_frame = ttk.Labelframe(
            self.sidebar_frame,
            text="Test Configuration",
            padding=15,
            bootstyle="info"
        )
        config_frame.pack(fill=X, pady=(0, 20))
        
        self.right_ear_first_var = ttk.BooleanVar(value=True)
        right_ear_check = ttk.Checkbutton(
            config_frame,
            text="Test Right Ear First",
            variable=self.right_ear_first_var,
            bootstyle="success-round-toggle"
        )
        right_ear_check.pack(anchor=W, pady=(0, 10))
        
        # Action Button
        self.start_button = ttk.Button(
            self.sidebar_frame,
            text="START TEST",
            command=self._start_test,
            bootstyle="success",
            width=25,
            padding=10
        )
        self.start_button.pack(fill=X, pady=(0, 10))
        
        self.stop_button = ttk.Button(
            self.sidebar_frame,
            text="STOP TEST",
            command=self._stop_test,
            bootstyle="danger",
            width=25,
            padding=10,
            state=DISABLED
        )
        self.stop_button.pack(fill=X)
        
        # === MAIN DISPLAY (Right - 70%) ===
        self.main_frame = ttk.Frame(self, padding=30)
        
        # Status Banner
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=X, pady=(0, 20))
        
        self.status_label = ttk.Label(
            status_frame,
            text="Ready to start test",
            font=("Helvetica", 16, "bold"),
            bootstyle="primary",
            anchor=CENTER
        )
        self.status_label.pack(fill=X, pady=(15, 5))
        
        # Current Ear Indicator (Task 3)
        self.ear_indicator_label = ttk.Label(
            status_frame,
            text="",
            font=("Helvetica", 20, "bold"),
            bootstyle="warning",
            anchor=CENTER
        )
        self.ear_indicator_label.pack(fill=X, pady=(0, 10))
        
        # Progress Bar
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            progress_frame,
            text="Test Progress:",
            font=("Helvetica", 11),
            bootstyle="secondary"
        ).pack(anchor=W, pady=(0, 5))
        
        self.progress_var = ttk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=600,
            bootstyle="success-striped",
            mode="determinate"
        )
        self.progress_bar.pack(fill=X, pady=(0, 5))
        
        self.progress_text = ttk.Label(
            progress_frame,
            text="0%",
            font=("Helvetica", 10),
            bootstyle="secondary"
        )
        self.progress_text.pack(anchor=E)
        
        # Live Feedback Section
        feedback_frame = ttk.Labelframe(
            self.main_frame,
            text="Live Feedback",
            padding=20,
            bootstyle="info"
        )
        feedback_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Light Bulb Indicator
        indicator_frame = ttk.Frame(feedback_frame)
        indicator_frame.pack(pady=20)
        
        self.light_bulb_label = ttk.Label(
            indicator_frame,
            text="💡",
            font=("Helvetica", 48),
            bootstyle="warning"
        )
        self.light_bulb_label.pack()
        
        self.feedback_label = ttk.Label(
            indicator_frame,
            text="Waiting for patient response...",
            font=("Helvetica", 12),
            bootstyle="secondary"
        )
        self.feedback_label.pack(pady=(10, 0))
        
        # Patient Response Button
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=X)
        
        self.patient_button = ttk.Button(
            button_frame,
            text="I HEAR IT",
            command=self._on_patient_button_press,
            bootstyle="primary",
            width=30,
            padding=15,
            state=DISABLED
        )
        self.patient_button.pack(pady=10)
        
        # Bind button release
        self.patient_button.bind("<ButtonPress-1>", lambda e: self._on_patient_button_press())
        self.patient_button.bind("<ButtonRelease-1>", lambda e: self._on_patient_button_release())
        
        # Bind spacebar as alternative
        self.bind("<KeyPress-space>", lambda e: self._on_patient_button_press())
        self.bind("<KeyRelease-space>", lambda e: self._on_patient_button_release())
        self.focus_set()
    
    def _setup_layout(self):
        """Configure the main layout with sidebar and main display."""
        self.sidebar_frame.pack(side=LEFT, fill=Y, padx=(0, 2))
        self.main_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(2, 0))
    
    def _load_audio_devices(self):
        """Load available audio output devices."""
        try:
            devices = sd.query_devices()
            device_list = []
            default_device = None
            
            for i, d in enumerate(devices):
                if d['max_output_channels'] > 0:
                    device_str = f"{i}: {d['name']}"
                    device_list.append(device_str)
                    # Prefer USB devices
                    if 'USB' in d['name'] and default_device is None:
                        default_device = device_str
            
            if device_list:
                self.device_combo['values'] = device_list
                if default_device:
                    self.device_var.set(default_device)
                else:
                    self.device_var.set(device_list[0])
            else:
                self.device_var.set("No devices found")
                self.start_button.config(state=DISABLED)
        except Exception as e:
            self.status_label.config(text=f"Error loading devices: {e}", bootstyle="danger")
    
    def _start_test(self):
        """Start the hearing test in a background thread.
        
        This function performs comprehensive validation, updates UI state,
        and launches the test in a separate thread to prevent UI freezing.
        """
        # ============================================================
        # 1. INPUT VALIDATION (Before Starting)
        # ============================================================
        
        # Validate Audio Device selection
        device_str = self.device_var.get()
        if not device_str or device_str == "No devices found":
            self._show_error("Please select an audio device first!")
            return
        
        # Validate Patient ID (required)
        patient_id = self.id_entry.get().strip()
        if not patient_id:
            self._show_error("Please enter a Patient ID!")
            return
        
        # Validate Age (must be positive integer if provided)
        age_str = self.age_entry.get().strip()
        if age_str:  # Age is optional, but if provided must be valid
            if not age_str.isdigit() or int(age_str) <= 0:
                self._show_error("Age must be a positive integer (e.g., 25) or leave blank.")
                return
        
        # Validate Patient Name (required)
        subject_name = self.name_entry.get().strip()
        if not subject_name:
            self._show_error("Please enter patient name!")
            return
        
        # Extract device ID from selection string
        try:
            device_id = int(device_str.split(':')[0])
        except (ValueError, IndexError):
            self._show_error("Invalid device selection! Please select a valid audio device.")
            return
        
        # Check device channel capability (warn if mono only)
        try:
            devinfo = sd.query_devices(device_id)
            max_out = int(devinfo.get('max_output_channels', 2))
            if max_out < 2:
                response = self._show_warning(
                    "Selected device only supports mono output.\n"
                    "Ear-specific testing may not be possible. Continue?"
                )
                if not response:
                    return
        except Exception as e:
            # If we can't query device, log but continue
            print(f"Warning: Could not query device capabilities: {e}")
        
        # ============================================================
        # 2. UI STATE MANAGEMENT (Immediate Updates)
        # ============================================================
        
        # Disable Start button immediately to prevent double-clicking
        self.start_button.config(state=DISABLED)
        
        # Enable Stop button
        self.stop_button.config(state=NORMAL)
        
        # Enable Response button
        self.patient_button.config(state=NORMAL, bootstyle="success")
        
        # Disable input controls during test
        self._set_test_controls_state(DISABLED)
        
        # Update status label
        self.status_label.config(text="Starting Test...", bootstyle="info")
        self.ear_indicator_label.config(text="", bootstyle="warning")
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_text.config(text="0% (0/0)")
        
        # ============================================================
        # 3. PREPARE TEST DATA
        # ============================================================
        
        # Get patient info
        age = self.age_entry.get().strip()
        
        # Combine name with ID for results folder
        full_name = f"{subject_name} (ID: {patient_id})"
        
        # ============================================================
        # 4. THREADED EXECUTION (With Error Handling)
        # ============================================================
        
        try:
            # Reset test state
            self.is_running = True
            self.test_stop_requested = False
            self.last_progress = 0
            
            # Launch test in separate thread (CRITICAL: prevents UI freezing)
            self.test_thread = threading.Thread(
                target=self._run_test_thread,
                args=(device_id, full_name, self._update_progress_bar, self._on_ear_change),
                daemon=True,  # Thread dies when main program exits
                name="AudiometerTestThread"
            )
            self.test_thread.start()
            
            # Update status after thread starts
            self.status_label.config(text="Test Running...", bootstyle="info")
            
        except Exception as e:
            # Error handling wrapper: catch any exception during thread launch
            error_msg = f"Failed to start test: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Show error to user
            self._show_error(error_msg)
            
            # Re-enable Start button so user isn't stuck
            self.start_button.config(state=NORMAL)
            self.stop_button.config(state=DISABLED)
            self.patient_button.config(state=DISABLED, bootstyle="primary")
            self._set_test_controls_state(NORMAL)
            
            # Reset status
            self.status_label.config(text="Ready to start test", bootstyle="primary")
            self.is_running = False
    
    def _run_test_thread(self, device_id, subject_name, progress_callback, ear_change_callback):
        """Run the hearing test in background thread.
        
        Args:
            device_id: Audio device ID
            subject_name: Patient name
            progress_callback: Callback function for progress updates (receives float 0-100)
            ear_change_callback: Callback function for ear changes (receives 'left' or 'right')
        """
        try:
            # Reset stop flag
            self.test_stop_requested = False
            
            # Create test instance with progress callback and ear change callback (Task 2 & 3)
            test = AscendingMethod(
                device_id=device_id,
                subject_name=subject_name,
                progress_callback=progress_callback,
                ear_change_callback=ear_change_callback
            )
            
            with self.test_lock:
                self.current_test = test
            
            # Run test
            test.run()
            
            # Check if stop was requested
            if self.test_stop_requested or test.stop_event.is_set():
                self.after(0, self._on_test_stopped)
            else:
                # Test completed successfully
                self.is_running = False
                self.after(0, self._on_test_completed, test)
            
        except Exception as e:
            self.is_running = False
            if not self.test_stop_requested:
                self.after(0, self._on_test_error, str(e))
            else:
                self.after(0, self._on_test_stopped)
    
    def _stop_test(self):
        """Stop the currently running test (Task 1)."""
        if self.is_running:
            self.test_stop_requested = True
            self.status_label.config(text="Stopping test...", bootstyle="warning")
            
            # Call stop_test() on the test instance (Task 1)
            with self.test_lock:
                if self.current_test:
                    try:
                        # Set the stop event FIRST
                        self.current_test.stop_event.set()
                        # Then call stop_test() which also stops audio
                        self.current_test.stop_test()
                        print("DEBUG: stop_test() called, stop_event is set")
                    except Exception as e:
                        print(f"Error stopping test: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("DEBUG: current_test is None, cannot stop")
            
            # Don't reset UI immediately - let the test thread clean up
            # The UI will be reset when _on_test_completed or _on_test_stopped is called
            # But we can disable the stop button to prevent double-clicks
            self.stop_button.config(state=DISABLED)
    
    def _on_test_stopped(self):
        """Handle test stop."""
        self._set_test_controls_state(NORMAL)
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.patient_button.config(state=DISABLED, bootstyle="primary")
        
        self.status_label.config(text="Test Stopped", bootstyle="warning")
        self.ear_indicator_label.config(text="", bootstyle="warning")
        self.test_stop_requested = False
        
        # Clean up test reference
        with self.test_lock:
            self.current_test = None
    
    def _on_test_completed(self, test):
        """Handle test completion."""
        self._set_test_controls_state(NORMAL)
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.patient_button.config(state=DISABLED, bootstyle="primary")
        
        self.status_label.config(text="Test Completed!", bootstyle="success")
        self.ear_indicator_label.config(text="", bootstyle="warning")
        self.progress_var.set(100)
        self.progress_text.config(text="100%")
        
        # Open audiogram automatically
        try:
            csv_path = os.path.join(test.ctrl.config.results_path, test.ctrl.config.filename)
            pdf_path = csv_path + '.pdf'
            if os.path.exists(pdf_path):
                self._open_file(pdf_path)
        except Exception as e:
            print(f"Could not open audiogram: {e}")
        
        # Show completion message
        self._show_info(
            "Hearing test completed!\n\n"
            f"Results saved to:\n{test.ctrl.config.results_path}"
        )
    
    def _on_test_error(self, error_msg):
        """Handle test error."""
        self._set_test_controls_state(NORMAL)
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.patient_button.config(state=DISABLED, bootstyle="primary")
        
        self.status_label.config(text=f"Error: {error_msg}", bootstyle="danger")
        self.ear_indicator_label.config(text="", bootstyle="warning")
        self._show_error(f"Test Error:\n{error_msg}")
    
    def _on_ear_change(self, ear_name):
        """Handle ear change callback (Task 3).
        
        Called from test thread when ear changes. Updates UI thread-safely.
        
        Args:
            ear_name: 'left' or 'right'
        """
        self.after(0, lambda: self._on_ear_change_safe(ear_name))
    
    def _on_ear_change_safe(self, ear_name):
        """Thread-safe ear indicator update (Task 3)."""
        try:
            ear_display = ear_name.upper() + " EAR"
            self.ear_indicator_label.config(
                text=f"Testing: {ear_display}",
                bootstyle="warning"
            )
            # Logging is optional - remove if not needed
            # logging.info(f"Ear changed to: {ear_name}")
        except Exception as e:
            print(f"Error updating ear indicator: {e}")
    
    def _on_patient_button_press(self):
        """Handle patient response button press."""
        if self.is_running and self.current_test:
            with self.test_lock:
                if self.current_test and hasattr(self.current_test.ctrl, '_rpd'):
                    self.current_test.ctrl._rpd.ui_button_pressed()
                    self._flash_button_indicator()
    
    def _on_patient_button_release(self):
        """Handle patient response button release."""
        if self.is_running and self.current_test:
            with self.test_lock:
                if self.current_test and hasattr(self.current_test.ctrl, '_rpd'):
                    self.current_test.ctrl._rpd.ui_button_released()
    
    def _flash_button_indicator(self):
        """Flash the light bulb indicator when button is pressed."""
        if self.button_flash_active:
            return
        
        self.button_flash_active = True
        original_text = self.light_bulb_label.cget("text")
        original_style = "warning"
        
        # Flash yellow
        self.light_bulb_label.config(text="💡", bootstyle="warning")
        self.feedback_label.config(text="Response detected!", bootstyle="success")
        
        # Reset after 500ms
        self.after(500, lambda: self._reset_button_indicator(original_text, original_style))
    
    def _reset_button_indicator(self, original_text, original_style):
        """Reset button indicator to normal state."""
        self.light_bulb_label.config(text=original_text, bootstyle=original_style)
        self.feedback_label.config(text="Waiting for patient response...", bootstyle="secondary")
        self.button_flash_active = False
    
    def _update_progress_bar(self, percentage):
        """Update progress bar from callback (Task 2).
        
        This is called directly from the test thread via the progress_callback.
        We use after() to ensure thread-safe UI updates.
        
        Args:
            percentage: Progress percentage as float (0.0-100.0)
        """
        # Use functools.partial to avoid lambda closure issues
        from functools import partial
        self.after(0, partial(self._update_progress_bar_safe, percentage))
    
    def _update_progress_bar_safe(self, percentage):
        """Thread-safe progress bar update (called from main thread)."""
        try:
            self.progress_var.set(percentage)
            # Get completed/total from test if available
            if self.current_test:
                with self.test_lock:
                    if self.current_test:
                        completed, total, _ = self.current_test.get_progress()
                        self.progress_text.config(text=f"{percentage:.1f}% ({completed}/{total})")
            else:
                self.progress_text.config(text=f"{percentage:.1f}%")
        except Exception as e:
            print(f"Error updating progress bar: {e}")
    
    def _poll_ui_updates(self):
        """Poll for status updates (progress is now handled by callback)."""
        if self.is_running and self.current_test:
            try:
                with self.test_lock:
                    if self.current_test:
                        # Update status with current test info
                        if hasattr(self.current_test, '_current_earside') and hasattr(self.current_test, '_current_freq'):
                            ear = self.current_test._current_earside or "Unknown"
                            freq = self.current_test._current_freq or "Unknown"
                            if ear != "Unknown" and freq != "Unknown":
                                self.status_label.config(
                                    text=f"Testing {ear.upper()} Ear - {freq}Hz",
                                    bootstyle="info"
                                )
                        elif hasattr(self.current_test, 'earside') and hasattr(self.current_test, 'freq'):
                            # Fallback to direct attributes
                            ear = getattr(self.current_test, 'earside', 'Unknown')
                            freq = getattr(self.current_test, 'freq', 'Unknown')
                            if ear and freq:
                                self.status_label.config(
                                    text=f"Testing {ear.upper()} Ear - {freq}Hz",
                                    bootstyle="info"
                                )
                
                # Enable patient button during test
                if self.patient_button.cget("state") == DISABLED and self.is_running:
                    self.patient_button.config(state=NORMAL)
            
            except Exception as e:
                print(f"Error polling UI updates: {e}")
        
        # Schedule next poll (every 100ms)
        self.after(100, self._poll_ui_updates)
    
    def _generate_patient_id(self):
        """Generate a unique patient ID (Task 4).
        
        Format: P-YYYYMMDD-XXXX where XXXX is a short UUID segment.
        """
        # Generate date prefix
        date_prefix = datetime.now().strftime("%Y%m%d")
        
        # Generate short unique suffix (first 4 chars of UUID)
        unique_suffix = str(uuid.uuid4())[:4].upper()
        
        # Combine: P-20241015-X9A2
        patient_id = f"P-{date_prefix}-{unique_suffix}"
        
        # Insert into ID field
        self.id_entry.delete(0, 'end')
        self.id_entry.insert(0, patient_id)
    
    def _set_test_controls_state(self, state):
        """Enable/disable test configuration controls."""
        self.name_entry.config(state=state)
        self.age_entry.config(state=state)
        self.id_entry.config(state=state)
        self.device_combo.config(state=state)
        # Note: Checkbox state management if needed
    
    def _show_error(self, message):
        """Show error message dialog."""
        tk_messagebox.showerror("Error", message, parent=self)
    
    def _show_warning(self, message):
        """Show warning message dialog and return True if user confirms."""
        result = tk_messagebox.askyesno("Warning", message, parent=self)
        return result
    
    def _show_info(self, message):
        """Show info message dialog."""
        tk_messagebox.showinfo("Test Complete", message, parent=self)
    
    def _open_file(self, filepath):
        """Open a file with the default OS application."""
        try:
            if sys.platform == 'win32':
                os.startfile(filepath)
            elif sys.platform == 'darwin':
                os.system(f'open "{filepath}"')
            else:
                os.system(f'xdg-open "{filepath}"')
        except Exception as e:
            print(f"Could not open file: {e}")


def main():
    """Main entry point."""
    try:
        app = AudiometerUI()
        app.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        tk_messagebox.showerror(
            "Error",
            f"Fatal application error:\n{e}\n\nCheck console for details."
        )


if __name__ == '__main__':
        main()
