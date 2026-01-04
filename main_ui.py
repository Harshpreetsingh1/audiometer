#!/usr/bin/env python3
"""
PC Audiometer GUI - Professional hearing test interface using ttkbootstrap
Requires USB headphones connected to the PC
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import (
    NORMAL, DISABLED, CENTER, LEFT, RIGHT, W, E, X, Y, BOTH
)
from tkinter import messagebox as tk_messagebox
import threading
import sounddevice as sd
import os
import sys
import time
import uuid
import logging
import atexit
import signal
from datetime import datetime
from typing import List
from pathlib import Path
from ascending_method import AscendingMethod
from audiometer.config import load_prefs, save_prefs

# Load persisted preferences early so theme can be applied consistently
_PREFERENCES = load_prefs()

# Choose a theme; prefer dark on Windows
DEFAULT_THEME = _PREFERENCES.get('theme', 'darkly') if sys.platform == 'win32' else _PREFERENCES.get('theme', 'superhero')

# Wrap common ttk constructors to gracefully handle environments where
# the theme/layout does not support the `bootstyle` option or certain
# layout elements. This shim will strip `bootstyle` on construction if
# it causes errors, and will store a lightweight `_bootstyle` attribute
# so tests can still query `cget('bootstyle')` without a TclError.
def _wrap_ttk_constructor(name):
    try:
        orig = getattr(ttk, name)
    except Exception:
        return

    def wrapped(*args, **kwargs):
        boot = None
        if 'bootstyle' in kwargs:
            boot = kwargs.get('bootstyle')
        try:
            widget = orig(*args, **kwargs)
        except Exception:
            # Retry without bootstyle
            if 'bootstyle' in kwargs:
                kwargs2 = dict(kwargs)
                kwargs2.pop('bootstyle', None)
                widget = orig(*args, **kwargs2)
            else:
                raise

        # Store bootstyle for tests and provide tolerant config/cget
        if boot is not None:
            try:
                setattr(widget, '_bootstyle', boot)
            except Exception:
                pass

        # Wrap config/configure to accept bootstyle without raising
        try:
            orig_config = widget.config
        except Exception:
            orig_config = None

        def _safe_config(**cnf):
            b = None
            if 'bootstyle' in cnf:
                b = cnf.pop('bootstyle')
            if orig_config:
                orig_config(**cnf)
            if b is not None:
                try:
                    setattr(widget, '_bootstyle', b)
                except Exception:
                    pass

        def _safe_cget(key):
            if key == 'bootstyle':
                return getattr(widget, '_bootstyle', '')
            try:
                return widget.tk.call(widget._w, 'cget', '-' + key)
            except Exception:
                # Fallback to tkinter's cget if direct call fails
                try:
                    return widget.__getattribute__('cget')(key)
                except Exception:
                    return None

        # Attach wrappers (both names used in tkinter)
        try:
            widget.config = lambda **cnf: _safe_config(**cnf)
            widget.configure = lambda **cnf: _safe_config(**cnf)
            widget.cget = lambda key: _safe_cget(key)
        except Exception:
            pass

        return widget

    try:
        setattr(ttk, name, wrapped)
    except Exception:
        pass

# Wrap commonly used widget types
for _name in ('Label', 'Labelframe', 'Frame', 'Button', 'Combobox', 'Entry',
               'Checkbutton', 'Progressbar', 'Scale', 'Radiobutton', 'Spinbox'):
    _wrap_ttk_constructor(_name)


class AudiometerUI(ttk.Window):
    """Main GUI application for PC Audiometer."""
    
    def __init__(self):
        """Initialize the GUI with Superhero (dark) theme."""
        super().__init__(themename=DEFAULT_THEME, title="PC Audiometer", resizable=(False, False))
        
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
        # Flag indicating whether the Tk mainloop is active (set by main())
        self._mainloop_running = False
        
        # Register cleanup handlers for graceful shutdown
        self._register_cleanup_handlers()
        
        # Build UI
        self._create_widgets()
        self._setup_layout()
        self._load_audio_devices()
        
        # Start UI update polling
        self._poll_ui_updates()
    
    def _register_cleanup_handlers(self):
        """Register signal handlers and atexit callbacks for graceful shutdown."""
        # Register atexit handler for cleanup on normal exit
        atexit.register(self._cleanup_resources)
        
        # Register signal handlers for graceful shutdown (Unix/Linux/Mac)
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        else:
            # Windows: Register handler for Ctrl+C (SIGINT)
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self._cleanup_resources()
        # Close the window
        self.destroy()
        sys.exit(0)
    
    def _cleanup_resources(self):
        """Clean up resources (audio streams, files, etc.) on shutdown."""
        try:
            logging.info("Cleaning up resources...")
            
            # Stop any running test
            if self.is_running:
                self.test_stop_requested = True
                with self.test_lock:
                    if self.current_test:
                        try:
                            self.current_test.stop_test()
                        except Exception as e:
                            logging.warning(f"Error stopping test during cleanup: {e}")
            
            # Clean up audio resources
            with self.test_lock:
                if self.current_test and hasattr(self.current_test, 'ctrl'):
                    try:
                        if hasattr(self.current_test.ctrl, '_audio'):
                            self.current_test.ctrl._audio.close()
                        if hasattr(self.current_test.ctrl, 'csvfile') and self.current_test.ctrl.csvfile:
                            self.current_test.ctrl.csvfile.close()
                    except Exception as e:
                        logging.warning(f"Error closing audio/file resources: {e}")
            
            logging.info("Resource cleanup complete")
        except Exception as e:
            logging.error(f"Error during resource cleanup: {e}")
    
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
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(
            self.sidebar_frame,
            text="Hearing Assessment System",
            font=("Helvetica", 10),
            bootstyle="secondary"
        )
        subtitle_label.pack(pady=(0, 10))
        
        # Patient Details Section
        patient_frame = ttk.Labelframe(
            self.sidebar_frame,
            text="Patient Details",
            padding=15,
            bootstyle="info"
        )
        patient_frame.pack(fill=X, pady=(0, 5))
        
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
        device_frame.pack(fill=X, pady=(0, 5))
        
        device_input_frame = ttk.Frame(device_frame)
        device_input_frame.pack(fill=X)
        
        ttk.Label(device_input_frame, text="Audio Output:", font=("Helvetica", 9)).pack(anchor=W, pady=(0, 5))
        self.device_var = ttk.StringVar()
        self.device_combo = ttk.Combobox(
            device_input_frame,
            textvariable=self.device_var,
            state="readonly",
            font=("Helvetica", 10)
        )
        self.device_combo.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        self.refresh_devices_button = ttk.Button(
            device_input_frame,
            text="🔄",
            command=self._load_audio_devices,
            bootstyle="secondary-outline",
            width=2
        )
        self.refresh_devices_button.pack(side=RIGHT)
        
        # Test Config Section
        config_frame = ttk.Labelframe(
            self.sidebar_frame,
            text="Test Configuration",
            padding=15,
            bootstyle="info"
        )
        config_frame.pack(fill=X, pady=(0, 10))
        
        self.right_ear_first_var = ttk.BooleanVar(value=True)
        right_ear_check = ttk.Checkbutton(
            config_frame,
            text="Test Right Ear First",
            variable=self.right_ear_first_var,
            bootstyle="success-round-toggle"
        )
        right_ear_check.pack(anchor=W, pady=(0, 10))

        # Windows-focused UI option: bring window to front and focus when test starts
        # Windows-focused UI option: bring window to front and focus when test starts
        self.win_focus_var = ttk.BooleanVar(value=_PREFERENCES.get('win_focus', sys.platform == 'win32'))
        win_focus_check = ttk.Checkbutton(
            config_frame,
            text="Windows Focus Mode",
            variable=self.win_focus_var,
            bootstyle="info-round-toggle",
            command=self._on_win_focus_toggle
        )
        win_focus_check.pack(anchor=W, pady=(0, 10))

        # Dark theme toggle (Windows default is dark)
        self.dark_theme_var = ttk.BooleanVar(value=(_PREFERENCES.get('theme', DEFAULT_THEME) == 'darkly'))
        dark_theme_check = ttk.Checkbutton(
            config_frame,
            text="Dark Theme",
            variable=self.dark_theme_var,
            bootstyle="info-round-toggle",
            command=self._on_dark_theme_toggle
        )
        dark_theme_check.pack(anchor=W, pady=(0, 10))

        # Accessibility: High-contrast option
        self.high_contrast_var = ttk.BooleanVar(value=_PREFERENCES.get('high_contrast', False))
        high_contrast_check = ttk.Checkbutton(
            config_frame,
            text="High Contrast (Accessibility)",
            variable=self.high_contrast_var,
            bootstyle="warning-round-toggle",
            command=self._on_high_contrast_toggle
        )
        high_contrast_check.pack(anchor=W, pady=(0, 10))

        # Quick vs Diagnostic mode toggle
        self.quick_mode_var = ttk.BooleanVar(value=_PREFERENCES.get('quick_mode', True))
        quick_mode_check = ttk.Checkbutton(
            config_frame,
            text="Quick Screening Mode (4 freqs)",
            variable=self.quick_mode_var,
            bootstyle="secondary-round-toggle",
            command=self._on_quick_mode_toggle
        )
        quick_mode_check.pack(anchor=W, pady=(0, 10))

        # Ultra Quick Mode: 2 frequencies per test (highest speed)
        self.mini_mode_var = ttk.BooleanVar(value=_PREFERENCES.get('mini_mode', False))
        mini_mode_check = ttk.Checkbutton(
            config_frame,
            text="Ultra Quick Mode (2 freqs)",
            variable=self.mini_mode_var,
            bootstyle="warning-round-toggle",
            command=self._on_mini_mode_toggle
        )
        mini_mode_check.pack(anchor=W, pady=(0, 10))
        # Action Button
        self.start_button = ttk.Button(
            self.sidebar_frame,
            text="START TEST",
            command=self._start_test,
            bootstyle="success",
            width=25,
            padding=10
        )
        self.start_button.pack(fill=X, pady=(10, 5))
        
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
        """Load audio devices with AGGRESSIVE error reporting."""
        try:
            # 1. Force PortAudio Refresh
            try:
                sd._terminate()
                sd._initialize()
            except Exception:
                pass # Ignore if already closed

            # 2. Query Devices
            devices = sd.query_devices()
            device_list = []
            default_device = None
            
            # 3. Filter Output Devices
            for i, d in enumerate(devices):
                if d.get('max_output_channels', 0) > 0:
                    name = d.get('name', 'Unknown Device')
                    device_str = f"{i}: {name}"
                    device_list.append(device_str)
                    if 'USB' in name and default_device is None:
                        default_device = device_str

            # 4. Update UI
            if device_list:
                self.device_combo['values'] = device_list
                if default_device:
                    self.device_var.set(default_device)
                else:
                    self.device_var.set(device_list[0])
                self.start_button.config(state=NORMAL)
                # Debug Success
                print(f"DEBUG: Loaded {len(device_list)} devices.")
            else:
                # CASE: Privacy Settings Blocking
                self.device_var.set("NO DEVICES FOUND")
                self.start_button.config(state=DISABLED)
                tk_messagebox.showwarning(
                    "No Audio Devices",
                    "PortAudio found 0 output devices.\n\n"
                    "POSSIBLE CAUSE: Windows Microphone Privacy Settings.\n"
                    "FIX: Go to Settings > Privacy > Microphone -> Turn ON 'Allow desktop apps'."
                )

        except Exception as e:
            # CASE: Missing DLL or Driver Crash
            import traceback
            error_trace = traceback.format_exc()
            self.device_var.set("DRIVER ERROR")
            self.start_button.config(state=DISABLED)
            
            tk_messagebox.showerror(
                "Critical Audio Error",
                f"Failed to load SoundDevice.\n\nError: {e}\n\n"
                f"Traceback:\n{error_trace}"
            )
            print(error_trace)
    
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
        
        # Validate Age (optional field - must be positive integer if provided)
        age_str = self.age_entry.get().strip()
        # Only validate if age is not empty (treat empty as optional)
        if age_str:  # Age is optional, but if provided must be valid
            if not age_str.isdigit():
                self._show_error("Age must be a positive integer (e.g., 25) or leave blank.")
                return
            age_value = int(age_str)
            if age_value <= 0:
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
            max_out = int(devinfo.get('max_output_channels', 2)) # type: ignore
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
        # Give the response button keyboard focus for immediate interaction
        try:
            self.patient_button.focus_set()
        except Exception:
            pass
        
        # Disable input controls during test
        self._set_test_controls_state(DISABLED)

        # Windows-focused behavior: bring window to front and focus
        if getattr(self, 'win_focus_var', None) and self.win_focus_var.get():
            try:
                self._ensure_windows_focus()
            except Exception as e:
                logging.debug(f"Could not ensure windows focus: {e}")
        
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
            
            # Capture UI preferences on the main thread to avoid cross-thread
            # access to Tkinter variables (which causes RuntimeError).
            quick_mode_flag = bool(self.quick_mode_var.get())
            mini_mode_flag = bool(self.mini_mode_var.get())

            # Launch test in separate thread (CRITICAL: prevents UI freezing)
            self.test_thread = threading.Thread(
                target=self._run_test_thread,
                args=(device_id, full_name, self._update_progress_bar, self._on_ear_change, self._on_freq_change, quick_mode_flag, mini_mode_flag),
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
    
    def _run_test_thread(self, device_id, subject_name, progress_callback, ear_change_callback, freq_change_callback, quick_mode_flag=False, mini_mode_flag=False):
        """Run the hearing test in background thread.

        Args:
            device_id: Audio device ID
            subject_name: Patient name
            progress_callback: Callback function for progress updates (receives float 0-100)
            ear_change_callback: Callback function for ear changes (receives 'left' or 'right')
            freq_change_callback: Callback function for frequency changes (receives frequency in Hz)
            quick_mode_flag: Boolean passed from UI main thread indicating quick mode
            mini_mode_flag: Boolean passed from UI main thread indicating mini mode (ultra-quick)
        """
        print("DEBUG: Thread started with device_id:", device_id)
        try:
            # CRITICAL FIX: Check stop flag BEFORE creating test instance (race condition prevention)
            if self.test_stop_requested:
                logging.info("Test stop requested before test creation. Aborting.")
                print("DEBUG: Test stop requested before test creation. Aborting.")
                self.after(0, self._on_test_stopped)
                return
            
            # Reset stop flag
            self.test_stop_requested = False
            print("DEBUG: Creating AscendingMethod instance...")
            
            # Create test instance with progress callback, ear change callback, and frequency change callback
            # Use flags captured from the main/UI thread to avoid cross-thread Tk calls
            test = AscendingMethod(
                device_id=device_id,
                subject_name=subject_name,
                progress_callback=progress_callback,
                ear_change_callback=ear_change_callback,
                freq_change_callback=freq_change_callback,
                quick_mode=bool(quick_mode_flag),
                mini_mode=bool(mini_mode_flag)
            )
            print("DEBUG: AscendingMethod instance created successfully")
            
            # CRITICAL FIX: Check stop flag AGAIN after creation (race condition window)
            if self.test_stop_requested:
                logging.info("Test stop requested immediately after test creation. Stopping.")
                print("DEBUG: Test stop requested immediately after test creation. Stopping.")
                test.stop_test()
                self.after(0, self._on_test_stopped)
                return
            
            with self.test_lock:
                self.current_test = test
            print("DEBUG: Test instance stored in current_test, calling test.run()...")
            
            # Run test
            test.run()
            print("DEBUG: test.run() completed")
            
            # Check if stop was requested
            if self.test_stop_requested or test.stop_event.is_set():
                print("DEBUG: Test stopped by user")
                # Ensure running flag is cleared so UI knows test has stopped
                self.is_running = False
                self.after(0, self._on_test_stopped)
            else:
                # Test completed successfully
                print("DEBUG: Test completed successfully")
                self.is_running = False
                self.after(0, self._on_test_completed, test)
            
        except Exception as e:
            print("DEBUG: EXCEPTION in _run_test_thread:", str(e))
            import traceback
            traceback.print_exc()  # CRITICAL: Print full traceback to console
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

            # Attempt to wait briefly for the background test thread to terminate so
            # the UI can be reset immediately and a restart can proceed without race.
            try:
                if self.test_thread and self.test_thread.is_alive():
                    # Join for a short time only to avoid blocking the UI too long
                    self.test_thread.join(timeout=0.5)
                # If the thread finished, ensure we reset UI state synchronously
                if not self.test_thread or not self.test_thread.is_alive():
                    try:
                        self._on_test_stopped()
                    except Exception:
                        pass
            except Exception as e:
                logging.debug(f"Error while waiting for test thread to stop: {e}")
    
    def _on_test_stopped(self):
        """Handle test stop."""
        try:
            self._set_test_controls_state(NORMAL)
            self.start_button.config(state=NORMAL)
            self.stop_button.config(state=DISABLED)
            self.patient_button.config(state=DISABLED, bootstyle="primary")
            # Ensure window is no longer forced topmost
            self._reset_ui_for_new_test()

            self.status_label.config(text="Test Stopped", bootstyle="warning")
            self.ear_indicator_label.config(text="", bootstyle="warning")
            try:
                self.attributes('-topmost', False)
            except Exception:
                pass
            # Return focus to Start button for quick restart
            try:
                self.start_button.focus_set()
            except Exception:
                pass

            # Ensure running flag is cleared
            self.is_running = False
            self.test_stop_requested = False

            # Clean up test reference
            with self.test_lock:
                self.current_test = None
        except Exception as e:
            logging.debug(f"_on_test_stopped UI update skipped due to error: {e}")
            # Ensure we clear running state and restore Start button where possible
            try:
                self.is_running = False
                self.test_stop_requested = False
                self.start_button.config(state=NORMAL)
                self.stop_button.config(state=DISABLED)
            except Exception:
                pass
            try:
                with self.test_lock:
                    self.current_test = None
            except Exception:
                pass
    
    def _on_test_completed(self, test):
        """Handle test completion."""
        try:
            self._reset_ui_for_new_test()

            self.status_label.config(text="Test Completed!", bootstyle="success")
            self.ear_indicator_label.config(text="", bootstyle="warning")
            # Ensure window is no longer forced topmost
            try:
                self.attributes('-topmost', False)
            except Exception:
                pass
            try:
                self.start_button.focus_set()
            except Exception:
                pass

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
        except Exception as e:
            logging.debug(f"_on_test_completed UI update skipped due to error: {e}")
            try:
                self.progress_var.set(100)
            except Exception:
                pass
    
    def _on_test_error(self, error_msg):
        """Handle test error."""
        self._reset_ui_for_new_test()
        try:
            self.attributes('-topmost', False)
        except Exception:
            pass
        try:
            self.start_button.focus_set()
        except Exception:
            pass
        
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
    
    def _on_freq_change(self, freq):
        """Handle frequency change callback.
        
        Called from test thread when frequency changes. Updates UI thread-safely.
        
        Args:
            freq: Frequency in Hz
        """
        self.after(0, lambda: self._on_freq_change_safe(freq))
    
    def _on_freq_change_safe(self, freq):
        """Thread-safe frequency indicator update."""
        # Frequency display removed from UI - method kept for API compatibility
        pass
    
    def _on_ear_change_safe(self, ear_name):
        """Update UI with Clinical Colors (Red/Blue)."""
        try:
            if ear_name.lower() == 'right':
                text = "TESTING: RIGHT EAR 🔴"
                style = "danger" # Red
            else:
                text = "TESTING: LEFT EAR 🔵"
                style = "info"   # Blue

            self.ear_indicator_label.config(text=text, bootstyle=style)
            self.status_label.config(text=f"Switched to {ear_name.upper()} Ear", bootstyle=style)
            
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
        """Poll for UI state updates (status is now event-driven via callbacks)."""
        if self.is_running and self.current_test:
            pass  # Polling is no longer needed for primary UI state updates.
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

    def _reset_ui_for_new_test(self):
        """Reset UI controls to their pre-test state."""
        self._set_test_controls_state(NORMAL)
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.patient_button.config(state=DISABLED, bootstyle="primary")
        self.feedback_label.config(
            text="Waiting for patient response...", bootstyle="secondary"
        )
    
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

    def _ensure_windows_focus(self):
        """Bring the application window to the foreground and give focus.

        Uses a combination of attributes('-topmost', True), focus_force(), and
        platform-specific calls on Windows (ShowWindow / SetForegroundWindow)
        to increase the chance the window becomes the active foreground window.
        """
        try:
            # Temporarily make the window topmost so it appears above others
            try:
                self.attributes('-topmost', True)
            except Exception:
                pass

            # Bring to front and focus
            try:
                self.update()
                self.focus_force()
                self.patient_button.focus_set()
            except Exception:
                pass

            # Try Windows-specific foreground calls if available
            if sys.platform == 'win32':
                try:
                    import ctypes
                    hwnd = self.winfo_id()
                    SW_SHOW = 5
                    ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                except Exception as e:
                    logging.debug(f"Windows focus call failed: {e}")

            # Remove topmost after a short delay so user can interact with other apps later
            try:
                # Only schedule delayed UI tasks when the mainloop is running to avoid
                # Tcl callbacks being invoked in test/headless environments.
                if getattr(self, '_mainloop_running', False):
                    self.after(300, self._safe_clear_topmost)
            except Exception:
                pass
        except Exception as e:
            logging.debug(f"_ensure_windows_focus() error: {e}")

    def _safe_clear_topmost(self):
        """Safely clear the topmost attribute; tolerates headless/test environments."""
        try:
            self.attributes('-topmost', False)
        except Exception:
            pass

    def _on_dark_theme_toggle(self):
        """Apply dark or light theme at runtime when user toggles the checkbox."""
        try:
            use_dark = bool(self.dark_theme_var.get())
            # Choose theme names - prefer 'darkly' for dark and 'litera' for light on Windows
            if use_dark:
                theme = 'darkly'
            else:
                theme = 'litera' if sys.platform == 'win32' else 'superhero'

            # Attempt to switch ttkbootstrap theme at runtime
            try:
                ttk.Style().theme_use(theme)
                # Refresh UI to apply theme changes
                self.update()
            except Exception as e:
                logging.debug(f"Could not switch theme at runtime: {e}")
        except Exception as e:
            logging.debug(f"_on_dark_theme_toggle error: {e}")
        # Persist preference
        try:
            self._save_ui_prefs()
        except Exception as e:
            logging.debug(f"Could not save prefs after theme toggle: {e}")

    def _on_win_focus_toggle(self):
        # Persist the changed value
        try:
            self._save_ui_prefs()
        except Exception as e:
            logging.debug(f"Could not save prefs after win_focus toggle: {e}")

    def _on_high_contrast_toggle(self):
        # Apply high contrast option (e.g., increase fonts)
        try:
            if self.high_contrast_var.get():
                # Increase some element fonts for accessibility
                self.status_label.config(font=("Helvetica", 18, "bold"))
                self.feedback_label.config(font=("Helvetica", 14))
            else:
                self.status_label.config(font=("Helvetica", 16, "bold"))
                self.feedback_label.config(font=("Helvetica", 12))
        except Exception as e:
            logging.debug(f"Could not apply high contrast: {e}")
        # Persist preference
        try:
            self._save_ui_prefs()
        except Exception as e:
            logging.debug(f"Could not save prefs after high_contrast toggle: {e}")

    def _save_ui_prefs(self):
        """Collect UI preference values and persist them to config file."""
        try:
            prefs = {
                'theme': 'darkly' if self.dark_theme_var.get() else ('litera' if sys.platform == 'win32' else 'superhero'),
                'win_focus': bool(self.win_focus_var.get()),
                'high_contrast': bool(self.high_contrast_var.get())
            }
            save_prefs(prefs)
        except Exception as e:
            logging.debug(f"Error saving UI prefs: {e}")

    def _on_quick_mode_toggle(self):
        try:
            # If quick mode is enabled, ensure mini mode is disabled to avoid
            # conflicting shortcuts. The UI persists both values but mini-mode
            # takes precedence during test creation.
            prefs = {'quick_mode': bool(self.quick_mode_var.get()), 'mini_mode': False}
            # Load existing prefs first to avoid overwriting other keys
            full = _PREFERENCES.copy()
            full.update(prefs)
            save_prefs(full)
        except Exception as e:
            logging.debug(f"Error saving quick mode pref: {e}")

    def _on_mini_mode_toggle(self):
        try:
            prefs = {'mini_mode': bool(self.mini_mode_var.get())}
            # If mini-mode is enabled, disable quick-mode to avoid ambiguity
            if prefs['mini_mode']:
                prefs['quick_mode'] = False
            full = _PREFERENCES.copy()
            full.update(prefs)
            save_prefs(full)
        except Exception as e:
            logging.debug(f"Error saving mini mode pref: {e}")


def main():
    """Main entry point."""
    try:
        app = AudiometerUI()
        # Mark that mainloop will be active so delayed UI tasks are scheduled
        app._mainloop_running = True
        try:
            app.mainloop()
        finally:
            app._mainloop_running = False
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
