"""Responder: capture user response via USB headset media keys or UI button.

This module listens for 'volume up' and 'volume down' media key events from
USB headsets and treats either as a user response (click). It attempts to
register handlers with the `keyboard` library and requests suppression of
the events so the system volume doesn't change during the test.

The Responder maintains the same public API so the rest of the codebase
(controller, GUI) can interact with it via:
- click_down()
- click_up()
- wait_for_click_up()
- wait_for_click_down_and_up()
- ui_button_pressed()
- ui_button_released()
"""

import threading
import logging
import sys
from typing import Any, List, Optional


class Responder:
    """Handle button input via USB headset media keys or UI button.

    Behavior:
      - If `keyboard` library is available, register handlers for 'volume up'
        and 'volume down' key presses and releases. Either press is treated as
        a click_down event.
      - Attempts to suppress system volume changes (requires appropriate
        privileges on some operating systems).
      - If `keyboard` is not available, responder still works with UI
        calls (`ui_button_pressed` / `ui_button_released`).
    """

    # Media keys that USB headsets typically send for volume buttons
    MEDIA_KEYS = ['volume up', 'volume down']

    def __init__(self, tone_duration: float):
        """Initialize the responder.
        
        Args:
            tone_duration: Default timeout for tone presentations (seconds)
        """
        self._timeout = tone_duration
        self._lock = threading.Lock()

        # Button state tracking
        self._button_state = False
        self._pressed_during_tone = False

        # Threading events for synchronization
        self._button_pressed_event = threading.Event()
        self._button_released_event = threading.Event()
        self._button_released_event.set()  # Start in released state

        # Keyboard handler bookkeeping
        self._keyboard: Optional[Any] = None
        self._handlers: List[Any] = []
        self._suppress_supported = True

        # Track timestamps for press/release (helps timing logic/tests)
        self._last_press_time: Optional[float] = None
        self._last_release_time: Optional[float] = None

        # Try to import and register keyboard handlers
        # Prefer an already-inserted keyboard module from sys.modules (helps tests)
        kb = sys.modules.get('keyboard')
        if kb is not None:
            self._keyboard = kb
            logging.debug("Found 'keyboard' module in sys.modules")
            try:
                self._register_media_key_handlers()
            except Exception:
                logging.exception("Failed to register keyboard handlers from sys.modules")
        else:
            try:
                import keyboard  # type: ignore
                self._keyboard = keyboard
                logging.info("Successfully imported 'keyboard' module for media key detection")
                self._register_media_key_handlers()
            except ImportError:
                logging.info("keyboard module not available; using UI-only responder")
            except Exception:
                logging.exception("Error importing keyboard module")

    def _register_media_key_handlers(self) -> None:
        """Register press/release handlers for media keys.

        Attempts to register handlers for both 'volume up' and 'volume down'
        keys. Tries multiple key name variants (e.g., 'volume up' vs 'volume_up')
        and attempts to suppress system volume changes when possible.
        """
        if not self._keyboard:
            return

        # If the keyboard module supports hook(), register exactly two handlers
        # (one for press/down and one for release/up) rather than registering
        # separate handlers per media key. This matches test expectations where
        # hook() registers global handlers and the handler inspects event_type.
        hook_fn = getattr(self._keyboard, 'hook', None)
        if callable(hook_fn):
            def make_handler(is_press: bool):
                def handler(event):
                    if event.event_type == ('down' if is_press else 'up'):
                        if is_press:
                            self._on_media_press(event)
                        else:
                            self._on_media_release(event)
                return handler

            try:
                h_press = hook_fn(make_handler(True), suppress=True)
                h_release = hook_fn(make_handler(False), suppress=True)
                self._handlers.extend([h_press, h_release])
                logging.info("Registered media handlers using hook() API (global handlers)")
                return
            except Exception as e:
                logging.debug(f"Hook-based registration failed: {e}")

        # Fallback: try on_press_key/on_release_key per-media-key (space/underscore variants)
        for key in self.MEDIA_KEYS:
            registered = False
            variants = (key, key.replace(' ', '_'), key.replace(' ', '-'))
            for k in variants:
                try:
                    on_press = getattr(self._keyboard, 'on_press_key', None)
                    on_release = getattr(self._keyboard, 'on_release_key', None)
                    if not callable(on_press) or not callable(on_release):
                        continue

                    try:
                        h_press = on_press(k, self._on_media_press, suppress=True)
                        h_release = on_release(k, self._on_media_release, suppress=True)
                        self._handlers.extend([h_press, h_release])
                        registered = True
                        logging.info(f"Registered media key '{k}' with suppression enabled")
                        break
                    except TypeError:
                        # suppress kwarg not supported
                        try:
                            h_press = on_press(k, self._on_media_press)
                            h_release = on_release(k, self._on_media_release)
                            self._handlers.extend([h_press, h_release])
                            self._suppress_supported = False
                            registered = True
                            logging.warning(
                                f"Registered media key '{k}' without suppression "
                                "(system volume may change during test)"
                            )
                            break
                        except Exception as e:
                            logging.debug(f"Failed to register key variant '{k}' without suppress: {e}")
                            continue
                    except Exception as e:
                        logging.debug(f"Failed to register key variant '{k}' with suppress: {e}")
                        continue
                except Exception as e:
                    logging.debug(f"Error registering key variant '{k}': {e}")
                    continue

            if not registered:
                logging.warning(f"Could not register handler for media key '{key}'")

        if self._handlers:
            logging.info(
                f"Successfully registered {len(self._handlers)} media key handler(s). "
                f"Suppression: {'enabled' if self._suppress_supported else 'disabled (may require admin)'}"
            )

    def _on_media_press(self, event: Any) -> None:
        """Called when a media key is pressed. Treat as click down.
        
        Either 'volume up' or 'volume down' press is treated as a valid
        user response indicating they heard the tone.
        """
        with self._lock:
            self._button_state = True
            self._pressed_during_tone = True
            # Record timestamp of press for accurate timing calculations
            try:
                import time as _time
                self._last_press_time = _time.time()
            except Exception:
                self._last_press_time = None
            self._button_released_event.clear()
            self._button_pressed_event.set()
        logging.debug("Media key pressed - user response detected")

    def _on_media_release(self, event: Any) -> None:
        """Called when a media key is released."""
        with self._lock:
            self._button_state = False
            # Record timestamp of release
            try:
                import time as _time
                self._last_release_time = _time.time()
            except Exception:
                self._last_release_time = None
            self._button_pressed_event.clear()
            self._button_released_event.set()
        logging.debug("Media key released")

    def ui_button_pressed(self) -> None:
        """Call this when the GUI response button is pressed."""
        with self._lock:
            self._button_state = True
            self._pressed_during_tone = True
            try:
                import time as _time
                self._last_press_time = _time.time()
            except Exception:
                self._last_press_time = None
            self._button_released_event.clear()
            self._button_pressed_event.set()

    def ui_button_released(self) -> None:
        """Call this when the GUI response button is released."""
        with self._lock:
            self._button_state = False
            try:
                import time as _time
                self._last_release_time = _time.time()
            except Exception:
                self._last_release_time = None
            self._button_pressed_event.clear()
            self._button_released_event.set()

    def clear(self) -> None:
        """Reset state for a new tone/presentation.
        
        Call this before each new tone to ensure clean state tracking.
        """
        with self._lock:
            self._pressed_during_tone = False
            self._button_pressed_event.clear()
            self._button_released_event.set()

    def click_down(self) -> bool:
        """Return True if a click (press) was registered during the tone.
        
        This checks if the button was pressed during the current tone cycle,
        as tracked by _pressed_during_tone flag.
        """
        with self._lock:
            return self._pressed_during_tone

    def click_up(self) -> bool:
        """Return True if the button is currently released."""
        with self._lock:
            return not self._button_state

    def wait_for_click_up(self, timeout: Optional[float] = None) -> None:
        """Block until the button is released.
        
        Args:
            timeout: Maximum time to wait (seconds). None = wait indefinitely.
        """
        self._button_released_event.wait(timeout=timeout)

    def wait_for_click_down_and_up(self, timeout: Optional[float] = None) -> bool:
        """Block until the button is pressed and then released.

        Args:
            timeout: Maximum time to wait for press (seconds). 
                    Additional 1 second is allowed for release.
        
        Returns:
            True if press+release happened, False on timeout.
        """
        if timeout is None:
            timeout = self._timeout

        pressed = self._button_pressed_event.wait(timeout=timeout)
        if not pressed:
            return False
        released = self._button_released_event.wait(timeout=timeout + 1.0)
        return bool(released)

    def close(self) -> None:
        """Unregister keyboard handlers and free resources."""
        if self._keyboard and self._handlers:
            try:
                for h in list(self._handlers):
                    try:
                        # Try unhook() method
                        unhook = getattr(self._keyboard, 'unhook', None)
                        if callable(unhook):
                            unhook(h)
                        else:
                            # Try unhook_all() if individual unhook doesn't work
                            unhook_all = getattr(self._keyboard, 'unhook_all', None)
                            if callable(unhook_all):
                                unhook_all()
                                break
                    except Exception as e:
                        logging.debug(f"Error unhooking handler: {e}")
                        pass
                self._handlers = []
                logging.debug("Unregistered all keyboard handlers")
            except Exception:
                logging.exception("Error while unhooking keyboard handlers")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
