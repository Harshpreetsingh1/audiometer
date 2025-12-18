# Stress Test & Verification Suite

This directory contains comprehensive stress tests and verification suites for the Audiometer project.

## Test Files Overview

### 1. `test_logic_stress.py` - Algorithm Logic Stress Tests
Tests the Hughson-Westlake algorithm under various patient response patterns.

**Test Classes:**
- `TestPerfectPatient`: Patient who always responds at 20dB - verifies quick completion
- `TestDeafPatient`: Patient who NEVER responds - verifies safety limit (80dB) handling
- `TestRandomPatient`: Erratic response pattern - verifies no infinite loops
- `TestEarSwitching`: Verifies both ears are tested and switching works correctly
- `TestProgressMath`: Verifies progress calculation is exactly 100% at completion

**Key Features:**
- Mocks audio and responder components
- Tests edge cases and boundary conditions
- Verifies algorithm robustness
- Prevents infinite loops

### 2. `test_ui_validation.py` - Input Validation & Thread Safety
Tests UI input validation and thread safety.

**Test Classes:**
- `TestInputValidation`: Tests empty/None/invalid patient IDs, character sanitization
- `TestThreadSafety`: Tests stop immediately after start, multiple stop calls
- `TestEdgeCases`: Tests minimal config, empty frequencies list

**Key Features:**
- Input sanitization verification
- Race condition detection
- Thread safety validation
- Edge case handling

### 3. `test_data_integrity.py` - File Saving & Data Integrity
Tests that data is never lost and files are created correctly.

**Test Classes:**
- `TestDirectoryCreation`: Verifies user folder structure creation
- `TestCSVFormat`: Verifies CSV headers match data columns
- `TestPartialResults`: Verifies partial results saved on mid-test stop

**Key Features:**
- Directory structure verification
- CSV format validation
- Data completeness checks
- Partial result handling

## Running the Tests

### Run All Tests
```bash
cd tests
python run_all_tests.py
```

### Run Specific Test File
```bash
python -m unittest tests.test_logic_stress
python -m unittest tests.test_ui_validation
python -m unittest tests.test_data_integrity
```

### Run Specific Test Class
```bash
python -m unittest tests.test_logic_stress.TestPerfectPatient
```

### Run with Verbose Output
```bash
python -m unittest -v tests.test_logic_stress
```

## Test Coverage

### Algorithm Logic
- ✅ Perfect patient (always responds)
- ✅ Deaf patient (never responds)
- ✅ Random patient (erratic responses)
- ✅ Ear switching (both ears tested)
- ✅ Progress calculation (exact 100%)

### Input Validation
- ✅ Empty patient ID
- ✅ None patient ID
- ✅ Invalid characters in patient ID
- ✅ Thread safety (stop immediately after start)
- ✅ Multiple stop calls
- ✅ Minimal configuration
- ✅ Empty frequencies list

### Data Integrity
- ✅ User folder creation
- ✅ CSV header format
- ✅ CSV data format
- ✅ Earside column validation
- ✅ Partial results on stop

## Manual Testing

See `QA_CHECKLIST.md` in the project root for comprehensive manual testing procedures.

## Mocking Strategy

All tests use `unittest.mock` to:
- Mock audio hardware (`AudioStream`)
- Mock patient input (`Responder`)
- Mock file system operations
- Mock configuration objects

This allows testing logic without requiring actual hardware.

## Expected Test Results

### Successful Run
```
Tests run: 15
Successes: 15
Failures: 0
Errors: 0
```

### Common Issues

1. **Import Errors**: Ensure parent directory is in Python path
2. **Mock Errors**: Verify mock setup matches actual implementation
3. **File System Errors**: Tests use temporary directories, should clean up automatically

## Adding New Tests

When adding new tests:

1. Follow existing test structure
2. Use `setUp()` and `tearDown()` for fixtures
3. Mock external dependencies
4. Use descriptive test names
5. Add docstrings explaining test purpose
6. Verify cleanup (temporary files, threads, etc.)

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No hardware required
- Fast execution (< 30 seconds)
- Deterministic results
- Comprehensive coverage

---

**Last Updated:** 2025-01-XX
**Maintainer:** QA Team

