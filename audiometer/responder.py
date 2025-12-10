import threading
import time


class Responder:
    """
    Handles button input for PC-based audiometer with UI controls.
    Thread-safe state management for GUI button events.
    """
    
    def __init__(self, tone_duration):
        self._timeout = tone_duration
        self._lock = threading.Lock()
        
        # Track button state: True = pressed, False = released
        self._button_state = False
        
        # Events for waiting
        self._button_pressed_event = threading.Event()
        self._button_released_event = threading.Event()
        self._button_released_event.set()  # Start in released state
        
        # Track if button was pressed during a test cycle
        self._pressed_during_tone = False

    # --- Methods called by the GUI ---
    def ui_button_pressed(self):
        """Call this when the user presses the UI button."""
        with self._lock:
            self._button_state = True
            self._pressed_during_tone = True
            self._button_released_event.clear()
            self._button_pressed_event.set()

    def ui_button_released(self):
        """Call this when the user releases the UI button."""
        with self._lock:
            self._button_state = False
            self._button_pressed_event.clear()
            self._button_released_event.set()

    # --- Methods called by the Logic (Controller) ---
    def clear(self):
        """Reset button state for a new test cycle."""
        with self._lock:
            self._pressed_during_tone = False
            self._button_pressed_event.clear()
            self._button_released_event.set()

    def click_down(self):
        """Return True if button was pressed during the current tone."""
        with self._lock:
            return self._pressed_during_tone

    def click_up(self):
        """Return True if button is currently released."""
        with self._lock:
            return not self._button_state

    def wait_for_click_up(self, timeout=None):
        """Block until the button is released."""
        self._button_released_event.wait(timeout=timeout)

    def wait_for_click_down_and_up(self, timeout=None):
        """Block until button is pressed and then released."""
        if timeout is None:
            timeout = self._timeout
        
        # Wait for button press
        pressed = self._button_pressed_event.wait(timeout=timeout)
        if not pressed:
            return False
        
        # Wait for button release
        released = self._button_released_event.wait(timeout=timeout + 1.0)
        return released

    def close(self):
        """Clean up resources."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()