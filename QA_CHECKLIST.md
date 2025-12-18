# Audiometer QA Manual Testing Checklist

This checklist covers manual testing scenarios that cannot be fully automated, particularly those involving hardware interaction and user experience.

## Pre-Test Setup

- [ ] USB headphones are connected and recognized by the system
- [ ] Audio device appears in the "USB Headset" dropdown
- [ ] System volume is set to a reasonable level (not muted)
- [ ] Application launches without errors
- [ ] GUI displays correctly with dark theme

---

## Test 1: Input Validation

### 1.1 Missing Audio Device
- [ ] Unplug USB headphones
- [ ] Try to start test without selecting device
- [ ] **Expected:** Error message "Please select an audio device first!"
- [ ] **Expected:** Test does NOT start

### 1.2 Missing Patient ID
- [ ] Leave "Patient ID" field empty
- [ ] Fill in Name and Age
- [ ] Click "START TEST"
- [ ] **Expected:** Error message "Please enter a Patient ID!"
- [ ] **Expected:** Test does NOT start

### 1.3 Invalid Age
- [ ] Enter negative age (e.g., "-5")
- [ ] Click "START TEST"
- [ ] **Expected:** Error message "Age must be a positive integer"
- [ ] **Expected:** Test does NOT start

- [ ] Enter non-numeric age (e.g., "abc")
- [ ] Click "START TEST"
- [ ] **Expected:** Error message "Age must be a positive integer"
- [ ] **Expected:** Test does NOT start

### 1.4 Missing Patient Name
- [ ] Leave "Name" field empty
- [ ] Fill in ID and Age
- [ ] Click "START TEST"
- [ ] **Expected:** Error message "Please enter patient name!"
- [ ] **Expected:** Test does NOT start

---

## Test 2: Button State Management

### 2.1 Start Button Double-Click Prevention
- [ ] Fill in all required fields
- [ ] Click "START TEST" button rapidly twice
- [ ] **Expected:** Button disables immediately after first click
- [ ] **Expected:** Second click is ignored
- [ ] **Expected:** Only one test thread starts

### 2.2 Response Button State
- [ ] Start a test
- [ ] **Expected:** "I HEAR IT" button becomes enabled (green)
- [ ] **Expected:** Button is clickable during test
- [ ] **Expected:** Button becomes disabled when test completes

### 2.3 Stop Button Functionality
- [ ] Start a test
- [ ] Click "STOP TEST" button mid-test
- [ ] **Expected:** Test stops gracefully
- [ ] **Expected:** UI resets to ready state
- [ ] **Expected:** Start button becomes enabled again
- [ ] **Expected:** No crash or error messages

---

## Test 3: Hardware Disconnection

### 3.1 Unplug Headphones During Test
- [ ] Start a test
- [ ] While test is running, unplug USB headphones
- [ ] **Expected:** Application does NOT crash
- [ ] **Expected:** Error is handled gracefully
- [ ] **Expected:** UI remains responsive
- [ ] **Expected:** User can stop test or restart

### 3.2 Plug Headphones Back In
- [ ] After unplugging, plug headphones back in
- [ ] **Expected:** Device appears in dropdown again
- [ ] **Expected:** User can start new test

---

## Test 4: Window Management

### 4.1 Close Window During Test
- [ ] Start a test
- [ ] While test is running, close the application window
- [ ] **Expected:** Application exits cleanly
- [ ] **Expected:** Test thread is killed (daemon thread)
- [ ] **Expected:** No zombie processes remain
- [ ] **Expected:** No error dialogs appear

### 4.2 Minimize/Restore Window
- [ ] Start a test
- [ ] Minimize window during test
- [ ] Restore window
- [ ] **Expected:** Progress bar continues updating
- [ ] **Expected:** Status label updates correctly
- [ ] **Expected:** Test continues normally

---

## Test 5: Audio Channel Separation

### 5.1 Left Ear Only
- [ ] Start test with headphones on
- [ ] When testing LEFT ear, listen carefully
- [ ] **Expected:** Sound plays ONLY in left ear
- [ ] **Expected:** Right ear hears NOTHING (complete silence)
- [ ] **Expected:** No audio leakage between ears

### 5.2 Right Ear Only
- [ ] When testing RIGHT ear, listen carefully
- [ ] **Expected:** Sound plays ONLY in right ear
- [ ] **Expected:** Left ear hears NOTHING (complete silence)
- [ ] **Expected:** No audio leakage between ears

### 5.3 Channel Switching
- [ ] Complete test for both ears
- [ ] **Expected:** Audio switches cleanly between left and right
- [ ] **Expected:** No overlap or mixing of channels

---

## Test 6: Response Button Functionality

### 6.1 On-Screen Button
- [ ] Start a test
- [ ] When you hear a tone, click "I HEAR IT" button
- [ ] **Expected:** Button click is registered
- [ ] **Expected:** Light bulb indicator flashes yellow
- [ ] **Expected:** Test progresses to next level/frequency
- [ ] **Expected:** Button remains responsive throughout test

### 6.2 USB Headset Buttons
- [ ] Start a test
- [ ] When you hear a tone, press USB headset "Volume Up" button
- [ ] **Expected:** Response is registered
- [ ] **Expected:** System volume does NOT change (suppressed)
- [ ] **Expected:** Test progresses correctly

- [ ] Press USB headset "Volume Down" button
- [ ] **Expected:** Response is registered (same as Volume Up)
- [ ] **Expected:** System volume does NOT change
- [ ] **Expected:** Test progresses correctly

### 6.3 Spacebar Alternative
- [ ] Start a test
- [ ] Press SPACEBAR when you hear a tone
- [ ] **Expected:** Response is registered (same as button click)
- [ ] **Expected:** Test progresses correctly

---

## Test 7: Progress Tracking

### 7.1 Progress Bar Updates
- [ ] Start a test
- [ ] Watch the progress bar during test
- [ ] **Expected:** Progress bar updates smoothly
- [ ] **Expected:** Percentage increases as frequencies complete
- [ ] **Expected:** Progress text shows "X% (completed/total)"
- [ ] **Expected:** Progress reaches exactly 100% at completion

### 7.2 Status Label Updates
- [ ] Start a test
- [ ] Watch the status label
- [ ] **Expected:** Shows "Testing RIGHT EAR - 1000Hz" (or current ear/freq)
- [ ] **Expected:** Updates when ear changes
- [ ] **Expected:** Updates when frequency changes
- [ ] **Expected:** Shows "Test Completed!" at end

### 7.3 Ear Indicator
- [ ] Start a test
- [ ] Watch the "Testing: X EAR" indicator
- [ ] **Expected:** Shows "Testing: RIGHT EAR" when testing right ear
- [ ] **Expected:** Shows "Testing: LEFT EAR" when testing left ear
- [ ] **Expected:** Updates immediately when ear switches
- [ ] **Expected:** Clears when test completes

---

## Test 8: Test Completion

### 8.1 Full Test Completion
- [ ] Complete a full test (both ears, all frequencies)
- [ ] **Expected:** Progress reaches 100%
- [ ] **Expected:** Status shows "Test Completed!"
- [ ] **Expected:** Audiogram PDF opens automatically
- [ ] **Expected:** Results saved to user folder
- [ ] **Expected:** CSV file contains all data points
- [ ] **Expected:** Both ears are represented in results

### 8.2 Results File Verification
- [ ] After test completes, check results folder
- [ ] **Expected:** Folder structure: `audiometer/results/{PatientName}/`
- [ ] **Expected:** CSV file exists with timestamp
- [ ] **Expected:** PDF audiogram exists (same name as CSV + .pdf)
- [ ] **Expected:** CSV contains headers: Level/dB, Frequency/Hz, Earside
- [ ] **Expected:** CSV contains data for both 'left' and 'right' ears
- [ ] **Expected:** All frequencies are represented

### 8.3 Audiogram Visualization
- [ ] Open the generated PDF audiogram
- [ ] **Expected:** Red line/circles for RIGHT ear
- [ ] **Expected:** Blue line/X markers for LEFT ear
- [ ] **Expected:** Both ears displayed side-by-side (if both tested)
- [ ] **Expected:** Graph is readable and properly formatted
- [ ] **Expected:** Frequencies are labeled correctly
- [ ] **Expected:** dB levels are on Y-axis (inverted)

---

## Test 9: Error Recovery

### 9.1 Test Error Handling
- [ ] Intentionally cause an error (e.g., unplug device mid-test)
- [ ] **Expected:** Error message is displayed
- [ ] **Expected:** UI resets to ready state
- [ ] **Expected:** Start button becomes enabled
- [ ] **Expected:** User can start new test

### 9.2 Partial Results on Error
- [ ] Start a test
- [ ] Stop test mid-way (or cause error)
- [ ] Check results folder
- [ ] **Expected:** CSV file exists (even if partial)
- [ ] **Expected:** CSV file is not corrupted
- [ ] **Expected:** Headers are intact
- [ ] **Expected:** Partial data is valid

---

## Test 10: Stress Testing

### 10.1 Rapid Start/Stop Cycles
- [ ] Start test → Stop immediately → Start again → Stop
- [ ] Repeat 5 times rapidly
- [ ] **Expected:** No crashes
- [ ] **Expected:** No memory leaks
- [ ] **Expected:** UI remains responsive
- [ ] **Expected:** Threads are cleaned up properly

### 10.2 Long-Running Test
- [ ] Start a full test with all frequencies
- [ ] Let it run to completion (10-15 minutes)
- [ ] **Expected:** No memory leaks
- [ ] **Expected:** Progress continues updating
- [ ] **Expected:** UI remains responsive
- [ ] **Expected:** Test completes successfully

### 10.3 Multiple Tests in Sequence
- [ ] Complete test for Patient A
- [ ] Start new test for Patient B (different name/ID)
- [ ] Complete test for Patient B
- [ ] **Expected:** Results saved to separate folders
- [ ] **Expected:** No data mixing between patients
- [ ] **Expected:** Both tests complete successfully

---

## Test 11: Edge Cases

### 11.1 Very Long Patient Names
- [ ] Enter patient name with 200+ characters
- [ ] Start test
- [ ] **Expected:** Name is sanitized for folder name
- [ ] **Expected:** Folder is created successfully
- [ ] **Expected:** Results save correctly

### 11.2 Special Characters in Patient ID
- [ ] Enter patient ID with special chars: `Patient/Name\With|Invalid*Chars?`
- [ ] Start test
- [ ] **Expected:** Invalid characters are sanitized
- [ ] **Expected:** Folder name is valid
- [ ] **Expected:** Results save correctly

### 11.3 Empty Fields
- [ ] Try various combinations of empty fields
- [ ] **Expected:** Appropriate error messages
- [ ] **Expected:** Test does not start with invalid input

---

## Test 12: Randomization Verification

### 12.1 Ear Order Randomization
- [ ] Start test 1
- [ ] Note which ear is tested first
- [ ] Start test 2 (same patient, new test)
- [ ] Note which ear is tested first
- [ ] **Expected:** Ear order may be different (randomized)
- [ ] **Expected:** Both ears are eventually tested
- [ ] **Expected:** No ear is skipped

---

## Test 13: Performance

### 13.1 UI Responsiveness
- [ ] Start a test
- [ ] While test is running, try clicking buttons
- [ ] **Expected:** UI remains responsive
- [ ] **Expected:** No freezing or lag
- [ ] **Expected:** Progress updates smoothly

### 13.2 Memory Usage
- [ ] Monitor memory usage during test
- [ ] **Expected:** Memory usage is reasonable
- [ ] **Expected:** No memory leaks over time
- [ ] **Expected:** Memory is freed after test completion

---

## Test 14: Data Integrity

### 14.1 CSV File Validation
- [ ] Complete a test
- [ ] Open CSV file in Excel/text editor
- [ ] **Expected:** File opens without errors
- [ ] **Expected:** Headers are on rows 1-3
- [ ] **Expected:** Data starts on row 4
- [ ] **Expected:** All rows have 3 columns
- [ ] **Expected:** Earside column contains only 'left' or 'right'
- [ ] **Expected:** Frequency column contains valid numbers
- [ ] **Expected:** Level column contains valid numbers

### 14.2 Data Completeness
- [ ] Count data rows in CSV
- [ ] **Expected:** Number of rows = (frequencies × ears)
- [ ] **Expected:** Each frequency appears for each ear
- [ ] **Expected:** No duplicate entries
- [ ] **Expected:** No missing data

---

## Test 15: User Experience

### 15.1 Visual Feedback
- [ ] Start a test
- [ ] **Expected:** Status messages are clear
- [ ] **Expected:** Progress bar is visible
- [ ] **Expected:** Ear indicator is prominent
- [ ] **Expected:** Button states are obvious
- [ ] **Expected:** Color coding is consistent (green=go, red=stop, etc.)

### 15.2 Error Messages
- [ ] Trigger various error conditions
- [ ] **Expected:** Error messages are clear and helpful
- [ ] **Expected:** Messages explain what went wrong
- [ ] **Expected:** Messages suggest how to fix the issue

### 15.3 Accessibility
- [ ] Test with keyboard only (no mouse)
- [ ] **Expected:** Tab navigation works
- [ ] **Expected:** Spacebar works for response
- [ ] **Expected:** Enter key works for buttons
- [ ] **Expected:** All functions accessible via keyboard

---

## Sign-Off

**Tester Name:** _________________________

**Date:** _________________________

**Test Environment:**
- OS: _________________________
- Python Version: _________________________
- Audio Device: _________________________

**Overall Result:**
- [ ] All tests passed
- [ ] Some tests failed (see notes below)
- [ ] Critical issues found

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

## Quick Reference: Expected Behaviors

| Action | Expected Result |
|--------|----------------|
| Start without device | Error: "Please select an audio device first!" |
| Start without Patient ID | Error: "Please enter a Patient ID!" |
| Start without Name | Error: "Please enter patient name!" |
| Invalid age | Error: "Age must be a positive integer" |
| Double-click Start | Second click ignored, only one test starts |
| Unplug headphones | App doesn't crash, error handled gracefully |
| Close window during test | App exits cleanly, threads killed |
| Stop mid-test | Test stops, UI resets, partial results saved |
| Complete test | Progress = 100%, PDF opens, results saved |
| Left ear test | Sound ONLY in left ear, right is silent |
| Right ear test | Sound ONLY in right ear, left is silent |

---

**Last Updated:** 2025-01-XX
**Version:** 1.0

