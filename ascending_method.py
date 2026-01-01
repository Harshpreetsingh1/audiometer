#!/usr/bin/env python3
"""Ascending method (Modified Hughson-Westlake).

For more details about the 'ascending method', have a look at
https://github.com/franzpl/audiometer/blob/master/docu/docu_audiometer.ipynb
The 'ascending method' is described in chapter 3.1.1

**WARNING**: If the hearing loss is too severe, this method will
not work! Please, consult an audiologist!

**WARNUNG**: Bei extremer Schwerhörigkeit ist dieses Verfahren nicht
anwendbar! Bitte suchen Sie einen Audiologen auf!

"""

import sys
import logging
import time
import threading
import random
from typing import Optional, Callable
from audiometer import controller
from audiometer import audiogram


logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s',
                    handlers=[logging.FileHandler("logfile.log", 'w'),
                              logging.StreamHandler()])


class AscendingMethod:
    """Implements the Modified Hughson-Westlake ascending method for hearing tests.
    
    Test Flow:
        1. Tests RIGHT ear first (all frequencies)
        2. Then tests LEFT ear (all frequencies)
        3. Each frequency uses the 10dB-down, 5dB-up Hughson-Westlake protocol
        4. Progress is tracked per completed frequency threshold determination
        
    State Management:
        - Each frequency/ear combination starts with a clean state
        - Responder is cleared before each test
        - Audio is properly stopped between tests
        - State is completely isolated between ears
    """
    
    def __init__(self, device_id=None, subject_name=None, progress_callback=None, ear_change_callback=None, freq_change_callback=None):
        """Initialize the ascending method test.
        
        Args:
            device_id: Optional audio device ID. If None, uses default device.
            subject_name: Optional subject/patient name for organizing results in user folders.
            progress_callback: Optional callback function that receives progress percentage (0-100).
            ear_change_callback: Optional callback function called when ear changes (receives ear name: 'left' or 'right').
            freq_change_callback: Optional callback function called when frequency changes (receives frequency in Hz).
        """
        self.ctrl = controller.Controller(device_id=device_id, subject_name=subject_name)
        
        # Test state (reset for each frequency)
        self.current_level = 0
        self.click = True
        self.freq = None
        self.earside = None
        
        # Progress tracking state
        # Calculate total steps: number of frequencies × number of ears
        self._total_steps = len(self.ctrl.config.earsides) * len(self.ctrl.config.freqs)
        self._completed_steps = 0
        self._current_step = 0  # Track current step for progress calculation
        self._current_freq = None
        self._current_earside = None
        self._progress_callback: Optional[Callable[[float], None]] = progress_callback
        self._ear_change_callback: Optional[Callable[[str], None]] = ear_change_callback
        self._freq_change_callback: Optional[Callable[[int], None]] = freq_change_callback
        
        # Stop event for graceful test termination
        self.stop_event = threading.Event()
        
        # Pass stop_event to controller so it can check during sleeps
        self.ctrl.stop_event = self.stop_event
        
        # Randomize ear order (Task 2) - shuffle to prevent patient prediction
        self._randomize_ear_order()
    
    def stop_test(self):
        """Stop the test gracefully by setting the stop event.
        
        This method can be called from the UI thread to request test termination.
        The test will check this event in its loops and exit cleanly.
        """
        self.stop_event.set()
        # Also stop audio immediately if possible
        try:
            if hasattr(self.ctrl, '_audio') and self.ctrl._audio:
                self.ctrl._audio.stop()
        except Exception:
            pass

    def _randomize_ear_order(self):
        """Randomize the order of ears to prevent patient prediction (Task 2).
        
        Shuffles the earsides list so the starting ear is random each time,
        while ensuring both ears are tested.
        """
        if len(self.ctrl.config.earsides) > 1:
            earsides_list = list(self.ctrl.config.earsides)
            random.shuffle(earsides_list)
            self.ctrl.config.earsides = earsides_list
            logging.info(f"Randomized ear order: {earsides_list}")

    def _reset_state_for_new_frequency(self):
        """Reset all state variables for a new frequency/ear test.
        
        This ensures clean state isolation between tests and prevents
        state leakage that could affect accuracy.
        """
        # Reset test state
        self.current_level = 0
        self.click = True
        
        # Clear responder state to ensure no button presses carry over
        try:
            self.ctrl._rpd.clear()
        except Exception:
            pass
        
        # Ensure audio is stopped
        try:
            if hasattr(self.ctrl._audio, '_target_gain') and self.ctrl._audio._target_gain != 0:
                self.ctrl._audio.stop()
                # Brief pause to ensure audio stops (check stop_event)
                self.ctrl._progress_sleep(0.1, self.stop_event)
        except Exception:
            pass
        
        logging.debug(f"State reset for {self.earside} ear at {self.freq} Hz")

    def decrement_click(self, level_decrement):
        """Decrement level and test tone.
        
        Args:
            level_decrement: Amount to decrease level in dBHL
            
        Returns:
            None (modifies self.click state)
        """
        # Check stop event before proceeding
        if self.stop_event.is_set():
            self.ctrl.stop_audio_immediately()
            return
        
        self.current_level -= level_decrement
        self.click = self.ctrl.clicktone(self.freq, self.current_level,
                                         self.earside, stop_event=self.stop_event)

    def increment_click(self, level_increment):
        """Increment level and test tone.
        
        Args:
            level_increment: Amount to increase level in dBHL
            
        Returns:
            None (modifies self.click state)
        """
        # Check stop event before proceeding
        if self.stop_event.is_set():
            self.ctrl.stop_audio_immediately()
            return
        
        self.current_level += level_increment
        self.click = self.ctrl.clicktone(self.freq, self.current_level,
                                         self.earside, stop_event=self.stop_event)

    def familiarization(self):
        """Familiarization phase: find initial audibility threshold.
        
        Plays tones at increasing volumes until patient responds,
        then establishes a baseline level for the main test.
        
        This phase:
        1. Uses audibletone() to find initial threshold
        2. Waits for user confirmation click
        3. Uses large steps to refine approximate threshold
        """
        print("DEBUG: Starting Familiarization...")
        logging.info("Begin Familiarization")
        
        print(f"\n{'='*60}")
        print(f"FAMILIARIZATION: {self.earside.upper()} ear at {self.freq} Hz")
        print(f"{'='*60}")
        print("Starting automatic tone familiarization...")
        print("Press the button when you hear the tone.\n")

        # Find initial audibility threshold using audibletone()
        # This returns the level where patient first responds
        print(f"DEBUG: Calling audibletone() with freq={self.freq}, level={self.ctrl.config.beginning_fam_level}, earside={self.earside}")
        self.current_level = self.ctrl.audibletone(
                             self.freq,
                             self.ctrl.config.beginning_fam_level,
                             self.earside,
                             stop_event=self.stop_event)
        print(f"DEBUG: audibletone() returned level: {self.current_level} dBHL")
        
        # Check stop event after audibletone
        if self.stop_event.is_set():
            self.ctrl.stop_audio_immediately()
            return

        print(f"\nInitial threshold found at {self.current_level} dBHL")
        print("To begin the hearing test, click once")
        print("DEBUG: Waiting for user response (wait_for_click_down_and_up)...")
        
        # Wait for click with timeout and stop_event checking
        # Use a timeout so we can check stop_event periodically
        if not self.stop_event.is_set():
            clicked = self.ctrl._rpd.wait_for_click_down_and_up(timeout=30.0)
            print(f"DEBUG: wait_for_click_down_and_up returned: {clicked}")
            if not clicked and self.stop_event.is_set():
                print("DEBUG: Timeout or stop requested, stopping audio")
                self.ctrl.stop_audio_immediately()
                return
            # Also check stop_event even if clicked
            if self.stop_event.is_set():
                print("DEBUG: Stop event set after click, stopping audio")
                self.ctrl.stop_audio_immediately()
                return
        else:
            print("DEBUG: Stop event already set, skipping wait for click")

        # Large steps to refine approximate threshold
        # Decrement (go quieter) if patient still responds
        while self.click:
            # Check stop event at start of loop
            if self.stop_event.is_set():
                self.ctrl.stop_audio_immediately()
                break
            
            logging.info("Familiarization: -%s dB", self.ctrl.config.large_level_decrement)
            self.decrement_click(self.ctrl.config.large_level_decrement)
            
            # Check stop event after decrement
            if self.stop_event.is_set():
                self.ctrl.stop_audio_immediately()
                break
            
            # Safety check: don't go below -10 dBHL (very quiet)
            if self.current_level < -10:
                logging.warning("Familiarization reached minimum level, stopping decrement")
                break

        # Increment (go louder) if patient doesn't respond
        while not self.click:
            # Check stop event at start of loop
            if self.stop_event.is_set():
                self.ctrl.stop_audio_immediately()
                break
            
            logging.info("Familiarization: +%s dB", self.ctrl.config.large_level_increment)
            self.increment_click(self.ctrl.config.large_level_increment)
            
            # Check stop event after increment
            if self.stop_event.is_set():
                self.ctrl.stop_audio_immediately()
                break
            
            # Safety check: don't exceed 100 dBHL (very loud)
            if self.current_level > 100:
                logging.warning("Familiarization reached maximum level, stopping increment")
                break
        
        logging.info(f"Familiarization complete. Starting level: {self.current_level} dBHL")

    def hearing_test(self):
        """Main hearing test using Modified Hughson-Westlake method.
        
        Protocol:
            - After familiarization, decrement by small_level_decrement (10dB)
            - Then use 10dB-down, 5dB-up steps until threshold is found
            - Threshold is confirmed when 3 out of 5 responses occur at same level
            
        This implements the standard Hughson-Westlake ascending method:
            - 10 dB down when patient responds
            - 5 dB up when patient doesn't respond
            - Threshold = level where 3 of 5 responses occur
        """
        # Start with familiarization phase
        self.familiarization()

        # Begin main test: decrement by small step (10dB down)
        # This ensures we start below threshold
        logging.info("End Familiarization: -%s dB", self.ctrl.config.small_level_decrement)
        self.decrement_click(self.ctrl.config.small_level_decrement)
        
        # Check stop event after decrement
        if self.stop_event.is_set():
            self.ctrl.stop_audio_immediately()
            return

        # 5dB up steps until patient responds (ascending to threshold)
        while not self.click:
            # Check stop event at start of loop
            if self.stop_event.is_set():
                logging.info("DEBUG: Stop event detected in ascending loop")
                self.ctrl.stop_audio_immediately()
                return
            
            logging.info("Ascending: +%s dB", self.ctrl.config.small_level_increment)
            self.increment_click(self.ctrl.config.small_level_increment)
            
            # Check stop event after increment
            if self.stop_event.is_set():
                logging.info("DEBUG: Stop event detected after increment in ascending loop")
                self.ctrl.stop_audio_immediately()
                return
            
            # Safety check
            if self.current_level > 100:
                logging.warning("Reached maximum level during ascending phase")
                break

        # Initialize level list with first response
        current_level_list = []
        current_level_list.append(self.current_level)
        logging.info(f"First response at {self.current_level} dBHL")

        # Modified Hughson-Westlake: find threshold where 3 of 5 responses occur
        three_answers = False
        iteration_count = 0
        max_iterations = 5  # Safety limit: 5 iterations per ear (10 total for both ears)
        
        while not three_answers and iteration_count < max_iterations:
            # Check stop event at start of outer loop
            if self.stop_event.is_set():
                self.ctrl.stop_audio_immediately()
                return
            
            iteration_count += 1
            logging.info("3of5 check: %s (iteration %d)", current_level_list, iteration_count)
            
            # Test up to 4 more times (total 5 responses)
            for x in range(4):
                # Check stop event at start of inner loop
                if self.stop_event.is_set():
                    self.ctrl.stop_audio_immediately()
                    return
                
                # 10dB down if patient responds (go quieter)
                while self.click:
                    # Check stop event in while loop
                    if self.stop_event.is_set():
                        logging.info("DEBUG: Stop event detected in descending loop")
                        self.ctrl.stop_audio_immediately()
                        return
                    
                    logging.info("Descending: -%s dB", self.ctrl.config.small_level_decrement)
                    self.decrement_click(self.ctrl.config.small_level_decrement)
                    
                    # Check stop event after decrement
                    if self.stop_event.is_set():
                        logging.info("DEBUG: Stop event detected after decrement in descending loop")
                        self.ctrl.stop_audio_immediately()
                        return
                    
                    # Safety check
                    if self.current_level < -10:
                        logging.warning("Reached minimum level during descending phase")
                        break

                # 5dB up if patient doesn't respond (go louder)
                while not self.click:
                    # Check stop event in while loop
                    if self.stop_event.is_set():
                        logging.info("DEBUG: Stop event detected in threshold-seeking ascending loop")
                        self.ctrl.stop_audio_immediately()
                        return
                    
                    logging.info("Ascending: +%s dB", self.ctrl.config.small_level_increment)
                    self.increment_click(self.ctrl.config.small_level_increment)
                    
                    # Check stop event after increment
                    if self.stop_event.is_set():
                        logging.info("DEBUG: Stop event detected after increment in threshold-seeking loop")
                        self.ctrl.stop_audio_immediately()
                        return
                    
                    # Safety check
                    if self.current_level > 100:
                        logging.warning("Reached maximum level during ascending phase")
                        break

                # Record this level
                current_level_list.append(self.current_level)
                logging.info("3of5 check: %s", current_level_list)
                
                # Check if we have 3 responses at the same level
                # http://stackoverflow.com/a/11236055
                matching_levels = [k for k in current_level_list
                                 if current_level_list.count(k) == 3]
                if matching_levels:
                    three_answers = True
                    threshold_level = matching_levels[0]
                    logging.info(f"3of5 threshold confirmed: {threshold_level} dBHL")
                    self.current_level = threshold_level
                    break
            
            # Check stop event before continuing outer loop
            if self.stop_event.is_set():
                self.ctrl.stop_audio_immediately()
                return
            
            # If no 3-of-5 match found, increase level and restart
            if not three_answers:
                logging.info("No 3-of-5 match. Restarting with +%s dB",
                             self.ctrl.config.large_level_increment)
                current_level_list = []
                self.increment_click(self.ctrl.config.large_level_increment)
                
                # Check stop event after increment
                if self.stop_event.is_set():
                    self.ctrl.stop_audio_immediately()
                    return
                
                # Add new starting level to list
                current_level_list.append(self.current_level)
                # Safety check
                if self.current_level > 100:
                    logging.warning("Reached maximum level, using current level as threshold")
                    three_answers = True
                    break
        
        if iteration_count >= max_iterations:
            logging.warning("Maximum iterations reached. Using last determined level.")
            # Use the most common level in the list as threshold
            if current_level_list:
                from collections import Counter
                most_common = Counter(current_level_list).most_common(1)
                if most_common:
                    self.current_level = most_common[0][0]
                    logging.info(f"Using most common level as threshold: {self.current_level} dBHL")

    def get_progress(self) -> tuple[int, int, int]:
        """Get current test progress.
        
        Returns:
            Tuple of (completed_steps, total_steps, percentage)
            - completed_steps: Number of frequency thresholds determined
            - total_steps: Total number of frequency/ear combinations
            - percentage: Progress percentage (0-100)
        """
        if self._total_steps == 0:
            return (0, 0, 0)
        
        # Use _current_step for accurate progress tracking
        percentage = int((self._current_step / self._total_steps) * 100)
        # Ensure percentage doesn't exceed 100%
        percentage = min(100, percentage)
        return (self._current_step, self._total_steps, percentage)

    def set_progress_callback(self, callback: Optional[Callable[[int], None]]):
        """Set a callback function to be called when progress updates.
        
        Args:
            callback: Function that takes an integer percentage (0-100) as argument.
                     Called whenever a frequency threshold is determined.
        """
        self._progress_callback = callback

    def _update_progress(self):
        """Update progress tracking and notify callback/UI."""
        self._completed_steps += 1
        
        # Calculate percentage based on current_step / total_steps
        if self._total_steps > 0:
            percentage = (self._current_step / self._total_steps) * 100.0
            # Ensure percentage doesn't exceed 100%
            percentage = min(100.0, percentage)
        else:
            percentage = 0.0
        
        # Call progress callback immediately (real-time update)
        if self._progress_callback:
            try:
                self._progress_callback(percentage)
            except Exception as e:
                logging.warning(f"Error calling progress callback: {e}")
            
            # Update UI window if available (for backward compatibility)
            try:
                if hasattr(self.ctrl, 'ui_window') and self.ctrl.ui_window is not None:
                    self.ctrl.ui_window.write_event_value('-PROGRESS-', int(percentage))
            except Exception as e:
                # Log but don't fail - this is backward compatibility code
                logging.debug(f"Error updating legacy UI window (non-critical): {e}")
            
            logging.info(
                f"Progress: {self._completed_steps}/{self._total_steps} "
                f"({percentage:.1f}%) - {self._current_earside.upper()} ear, {self._current_freq} Hz"
            )

    def run(self):
        """Run the complete hearing test.
        
        Test Flow:
            1. RIGHT ear: All frequencies (complete isolation)
            2. LEFT ear: All frequencies (complete isolation)
            3. Each frequency uses Hughson-Westlake method
            4. Progress updates after each frequency threshold is determined
            
        State Management:
            - Complete state reset between ears
            - Complete state reset between frequencies
            - Responder cleared before each test
            - Audio stopped between tests
        """
        print("DEBUG: Entering AscendingMethod.run()")
        if not self.ctrl.config.logging:
            logging.disable(logging.CRITICAL)
        
        # Calculate total steps: (Number of Frequencies) * (Number of Ears)
        ears = list(self.ctrl.config.earsides)
        freqs = list(self.ctrl.config.freqs)
        logging.info(f"DEBUG: Test Sequence Ears: {ears}")
        print(f"DEBUG: Ears: {ears}, Freqs: {freqs}")
        self._total_steps = len(ears) * len(freqs) if ears and freqs else 0
        self._completed_steps = 0
        
        if self._total_steps == 0:
            logging.warning("No frequencies or earsides configured. Cannot run test.")
            print("DEBUG: ERROR - No frequencies or earsides configured. Cannot run test.")
            return
        print(f"DEBUG: Total steps: {self._total_steps}")
        
        logging.info(f"\n{'='*70}")
        logging.info("HEARING TEST STARTING")
        logging.info(f"{'='*70}")
        logging.info(
            f"Configuration: {len(freqs)} frequencies × {len(ears)} ears = "
            f"{self._total_steps} total steps"
        )
        logging.info(f"Ear order: {ears}")
        logging.info(f"Frequency order: {freqs}")
        logging.info(f"{'='*70}\n")

        # Test each ear (order randomized in __init__)
        for ear_idx, self.earside in enumerate(ears):
            # CRITICAL: Notify UI of ear change IMMEDIATELY as first line of loop
            self._current_earside = self.earside
            if self._ear_change_callback:
                try:
                    self._ear_change_callback(self.earside)
                except Exception as e:
                    logging.warning(f"Error calling ear change callback: {e}")
            
            # Check for stop request (after callback to ensure UI is updated)
            if self.stop_event.is_set():
                logging.info("Test stop requested by user")
                # Stop audio and clean up
                try:
                    if hasattr(self.ctrl, '_audio') and self.ctrl._audio:
                        self.ctrl._audio.stop()
                except Exception:
                    pass
                return
            
            # Complete state reset when switching ears
            if ear_idx > 0:
                logging.info("\n" + "="*70)
                logging.info("SWITCHING EARS - Complete state reset")
                logging.info("="*70 + "\n")
                
                # Brief pause between ears (check stop_event)
                if not self.ctrl._progress_sleep(0.5, self.stop_event):
                    # Stop was requested during pause
                    return
                
                try:
                    self.ctrl._rpd.clear()
                    if hasattr(self.ctrl._audio, '_target_gain') and self.ctrl._audio._target_gain != 0:
                        self.ctrl._audio.stop()
                        # Brief pause after stopping audio (check stop_event)
                        if not self.ctrl._progress_sleep(0.2, self.stop_event):
                            return
                except Exception:
                    pass
            
            logging.info(f"\n{'='*70}")
            logging.info(f"TESTING {self.earside.upper()} EAR")
            logging.info(f"{'='*70}\n")
            
            # Test each frequency for this ear
            for freq_idx, self.freq in enumerate(freqs):
                # Check for stop request
                if self.stop_event.is_set():
                    logging.info("Test stop requested by user")
                    # Stop audio and clean up
                    try:
                        if hasattr(self.ctrl, '_audio') and self.ctrl._audio:
                            self.ctrl._audio.stop()
                    except Exception:
                        pass
                    return
                
                self._current_freq = self.freq
                
                # Notify UI of frequency change immediately
                if self._freq_change_callback:
                    try:
                        self._freq_change_callback(self.freq)
                    except Exception as e:
                        logging.warning(f"Error calling frequency change callback: {e}")
                
                logging.info(f"\n{'-'*70}")
                logging.info(f"Frequency: {self.freq} Hz | Ear: {self.earside.upper()}")
                logging.info(f"{'-'*70}")
                
                try:
                    # CRITICAL: Reset state BEFORE starting test
                    # This ensures clean isolation between frequencies
                    self._reset_state_for_new_frequency()
                    
                    # Run the hearing test for this frequency/ear combination
                    self.hearing_test()
                    
                    # CRITICAL FIX: Check if we stopped during the test
                    if self.stop_event.is_set():
                        logging.info("Test stopped. Aborting save for this frequency.")
                        return
                    
                    # Verify we have a valid threshold
                    if self.current_level is None:
                        raise ValueError("Threshold determination failed")
                    
                    # CRITICAL: Double-check stop event BEFORE saving to prevent junk data
                    if self.stop_event.is_set():
                        logging.info("Test stop requested before save_results(). Skipping save to prevent data corruption.")
                        return
                    
                    # Save the determined threshold (only if test completed successfully)
                    self.ctrl.save_results(self.current_level, self.freq,
                                           self.earside)
                    
                    # Increment step counter IMMEDIATELY after saving
                    self._current_step += 1
                    
                    # Update progress IMMEDIATELY (this calls the callback)
                    self._update_progress()
                    
                    # Log for debugging
                    logging.info(
                        f"Progress updated: {self._current_step}/{self._total_steps} = "
                        f"{(self._current_step/self._total_steps)*100:.1f}%"
                    )
                    
                    logging.info(
                        f"✓ Completed {self.earside.upper()} ear at {self.freq} Hz: "
                        f"{self.current_level} dBHL"
                    )
                    
                    # Brief pause between frequencies (check stop_event)
                    if not self.ctrl._progress_sleep(0.3, self.stop_event):
                        # Stop was requested during pause
                        return

                except OverflowError:
                    error_msg = (
                        f"The signal is distorted at {self.freq} Hz for {self.earside} ear. "
                        "Possible causes are an incorrect calibration or a severe hearing loss. "
                        "Skipping to next frequency."
                    )
                    print(error_msg)
                    logging.warning(error_msg)
                    self.current_level = None
                    # Still count as completed step (even if failed)
                    self._update_progress()
                    continue

                except Exception as e:
                    error_msg = (
                        f"Error testing {self.freq} Hz for {self.earside} ear: {e}"
                    )
                    print(error_msg)
                    logging.exception(error_msg)
                    self.current_level = None
                    # Still count as completed step (even if failed)
                    self._update_progress()
                    continue

                except KeyboardInterrupt:
                    # In a GUI context, calling sys.exit() will terminate the whole
                    # application. Re-raise the exception so the calling thread
                    # can handle it and report the error to the UI instead.
                    raise
        
        # Test complete
        logging.info(f"\n{'='*70}")
        logging.info("TEST COMPLETE")
        logging.info(f"{'='*70}")
        logging.info(f"Total steps completed: {self._completed_steps}/{self._total_steps}")
        
        # Final cleanup
        try:
            self.ctrl._rpd.clear()
            if hasattr(self.ctrl._audio, '_target_gain') and self.ctrl._audio._target_gain != 0:
                self.ctrl._audio.stop()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.ctrl.__exit__()
        audiogram.make_audiogram(self.ctrl.config.filename,
                                 self.ctrl.config.results_path)


if __name__ == '__main__':
    with AscendingMethod() as asc_method:
        asc_method.run()

    print("Finished!")