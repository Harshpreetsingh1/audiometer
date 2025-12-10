"""The responder module processes the reaction to acoustic signals."""

import threading
import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    # Fallback for non-Raspberry Pi systems (testing/development)
    GPIO = None


class Responder:

    def __init__(self, tone_duration):
        """Initialize GPIO responder for Raspberry Pi.
        
        Args:
            tone_duration: Duration of the tone in seconds (used for timeout calculations)
        """
        self._timeout = tone_duration
        self._button_pin = 17  # GPIO Pin 17 for the push button
        self._button_pressed = threading.Event()
        self._button_released = threading.Event()
        self._button_released.set()  # Button starts in released state
        
        if GPIO is not None:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # Add event detection for button press and release
            GPIO.add_event_detect(self._button_pin, GPIO.BOTH, 
                                callback=self._button_callback, bouncetime=20)

    def _button_callback(self, channel):
        """Internal callback for GPIO button state changes."""
        if GPIO is None:
            return
        
        # GPIO.LOW means button is pressed (ground switching with pull-up)
        if GPIO.input(self._button_pin) == GPIO.LOW:
            self._button_released.clear()
            self._button_pressed.set()
        else:
            self._button_pressed.clear()
            self._button_released.set()

    def close(self):
        """Clean up GPIO resources."""
        if GPIO is not None:
            GPIO.cleanup(self._button_pin)

    def click_down(self):
        """Return True if the button is currently pressed."""
        if GPIO is None:
            return False
        return GPIO.input(self._button_pin) == GPIO.LOW

    def click_up(self):
        """Return True if the button is currently released."""
        if GPIO is None:
            return True
        return GPIO.input(self._button_pin) == GPIO.HIGH

    def clear(self):
        """Clear button state events."""
        self._button_pressed.clear()
        self._button_released.clear()

    def wait_for_click_up(self, timeout=None):
        """Block until the button is released.
        
        Args:
            timeout: Maximum time to wait in seconds. If None, waits indefinitely.
        """
        self._button_released.wait(timeout=timeout)

    def wait_for_click_down_and_up(self, timeout=None):
        """Block until the button is pressed and then released.
        
        Args:
            timeout: Maximum time to wait in seconds. If None, waits indefinitely.
        
        Returns:
            True if button was pressed and released within timeout, False otherwise.
        """
        if timeout is None:
            timeout = self._timeout
        
        # Wait for button press
        pressed = self._button_pressed.wait(timeout=timeout)
        if not pressed:
            return False
        
        # Wait for button release
        released = self._button_released.wait(timeout=timeout)
        return released

    def __exit__(self, *args):
        self.close()

    def __enter__(self):
        return self
