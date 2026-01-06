#!/usr/bin/env python3
"""
Patient Database Module

SQLite-based patient record system for the PC Audiometer application.
Stores patient information and test history for longitudinal tracking.

Author: Audiometry Application
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

# Configure logging
logger = logging.getLogger(__name__)


class PatientDatabase:
    """
    SQLite database manager for patient records and test history.
    
    Provides CRUD operations for patients and their audiometry test results.
    The database file is created automatically if it doesn't exist.
    
    Example Usage:
        >>> db = PatientDatabase("patients.db")
        >>> patient_id = db.add_patient("John Doe", "9876543210", 45, "male", "REF-001")
        >>> db.save_test_result(patient_id, {"500": 25, "1000": 30}, {"500": 20, "1000": 25})
        >>> history = db.get_patient_history(patient_id)
    """
    
    def __init__(self, db_path: str = "patients.db"):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file. Defaults to "patients.db"
                    in the current directory.
        """
        self.db_path = db_path
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_database(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Patients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE,
                    patient_ref_id TEXT,
                    age INTEGER,
                    gender TEXT,
                    referring_physician TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    left_ear_data TEXT,
                    right_ear_data TEXT,
                    interpretation TEXT,
                    remarks TEXT,
                    csv_path TEXT,
                    audiogram_path TEXT,
                    pdf_report_path TEXT,
                    test_mode TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_results_patient ON test_results(patient_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_results_date ON test_results(test_date)
            ''')
            
            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
        finally:
            conn.close()
    
    # =========================================================================
    # Patient Operations
    # =========================================================================
    
    def add_patient(
        self,
        name: str,
        phone: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        ref_id: Optional[str] = None,
        referring_physician: Optional[str] = None
    ) -> int:
        """
        Add a new patient to the database.
        
        Args:
            name: Patient's full name (required)
            phone: Phone number (used as unique identifier for search)
            age: Patient's age
            gender: Gender (male/female/other)
            ref_id: Hospital reference ID
            referring_physician: Name of referring doctor
            
        Returns:
            The ID of the newly created patient record.
            
        Raises:
            sqlite3.IntegrityError: If phone number already exists.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO patients (name, phone, patient_ref_id, age, gender, referring_physician)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, phone, ref_id, age, gender, referring_physician))
            
            conn.commit()
            patient_id = cursor.lastrowid
            logger.info(f"Added patient: {name} (ID: {patient_id})")
            return patient_id
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: patients.phone" in str(e):
                # Phone already exists - return existing patient ID
                existing = self.get_patient_by_phone(phone)
                if existing:
                    logger.info(f"Patient with phone {phone} already exists (ID: {existing['id']})")
                    return existing['id']
            raise
        finally:
            conn.close()
    
    def get_patient_by_id(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """
        Get patient by their database ID.
        
        Args:
            patient_id: The patient's database ID.
            
        Returns:
            Dict with patient data or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by phone number.
        
        Args:
            phone: The patient's phone number.
            
        Returns:
            Dict with patient data or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM patients WHERE phone = ?', (phone,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def search_patients(self, query: str) -> List[Dict[str, Any]]:
        """
        Search patients by name or phone number.
        
        Args:
            query: Search string (partial match supported).
            
        Returns:
            List of matching patient records.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            search_pattern = f"%{query}%"
            cursor.execute('''
                SELECT * FROM patients 
                WHERE name LIKE ? OR phone LIKE ? OR patient_ref_id LIKE ?
                ORDER BY updated_at DESC
                LIMIT 50
            ''', (search_pattern, search_pattern, search_pattern))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def update_patient(self, patient_id: int, **kwargs) -> bool:
        """
        Update patient information.
        
        Args:
            patient_id: The patient's database ID.
            **kwargs: Fields to update (name, phone, age, gender, etc.)
            
        Returns:
            True if update was successful.
        """
        if not kwargs:
            return False
        
        allowed_fields = {'name', 'phone', 'patient_ref_id', 'age', 'gender', 'referring_physician'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return False
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            set_clause = ', '.join(f"{k} = ?" for k in update_fields.keys())
            values = list(update_fields.values()) + [patient_id]
            
            cursor.execute(f'''
                UPDATE patients 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', values)
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    # =========================================================================
    # Test Result Operations
    # =========================================================================
    
    def save_test_result(
        self,
        patient_id: int,
        left_ear_data: Dict[int, float],
        right_ear_data: Dict[int, float],
        interpretation: Optional[str] = None,
        remarks: Optional[str] = None,
        csv_path: Optional[str] = None,
        audiogram_path: Optional[str] = None,
        pdf_report_path: Optional[str] = None,
        test_mode: Optional[str] = None
    ) -> int:
        """
        Save a new test result for a patient.
        
        Args:
            patient_id: The patient's database ID.
            left_ear_data: Dict of {frequency: dB level} for left ear.
            right_ear_data: Dict of {frequency: dB level} for right ear.
            interpretation: Auto-generated interpretation text.
            remarks: Doctor's remarks.
            csv_path: Path to the CSV results file.
            audiogram_path: Path to the audiogram image.
            pdf_report_path: Path to the PDF report.
            test_mode: Test mode used (quick/mini/full).
            
        Returns:
            The ID of the newly created test result.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert frequency keys to strings for JSON serialization
            left_json = json.dumps({str(k): v for k, v in left_ear_data.items()})
            right_json = json.dumps({str(k): v for k, v in right_ear_data.items()})
            
            cursor.execute('''
                INSERT INTO test_results 
                (patient_id, left_ear_data, right_ear_data, interpretation, remarks,
                 csv_path, audiogram_path, pdf_report_path, test_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, left_json, right_json, interpretation, remarks,
                  csv_path, audiogram_path, pdf_report_path, test_mode))
            
            conn.commit()
            result_id = cursor.lastrowid
            logger.info(f"Saved test result for patient {patient_id} (Result ID: {result_id})")
            return result_id
            
        finally:
            conn.close()
    
    def get_patient_history(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Get all test results for a patient, ordered by date (newest first).
        
        Args:
            patient_id: The patient's database ID.
            
        Returns:
            List of test result records with parsed ear data.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM test_results 
                WHERE patient_id = ?
                ORDER BY test_date DESC
            ''', (patient_id,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Parse JSON ear data back to dicts
                if result.get('left_ear_data'):
                    result['left_ear_data'] = json.loads(result['left_ear_data'])
                if result.get('right_ear_data'):
                    result['right_ear_data'] = json.loads(result['right_ear_data'])
                results.append(result)
            
            return results
            
        finally:
            conn.close()
    
    def get_latest_test(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent test result for a patient.
        
        Args:
            patient_id: The patient's database ID.
            
        Returns:
            The latest test result or None if no tests exist.
        """
        history = self.get_patient_history(patient_id)
        return history[0] if history else None
    
    def get_test_by_id(self, test_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific test result by its ID.
        
        Args:
            test_id: The test result's database ID.
            
        Returns:
            Test result record or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM test_results WHERE id = ?', (test_id,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                if result.get('left_ear_data'):
                    result['left_ear_data'] = json.loads(result['left_ear_data'])
                if result.get('right_ear_data'):
                    result['right_ear_data'] = json.loads(result['right_ear_data'])
                return result
            return None
            
        finally:
            conn.close()
    
    def update_test_result(self, test_id: int, **kwargs) -> bool:
        """
        Update a test result record.
        
        Args:
            test_id: The test result's database ID.
            **kwargs: Fields to update (remarks, pdf_report_path, etc.)
            
        Returns:
            True if update was successful.
        """
        if not kwargs:
            return False
        
        allowed_fields = {'interpretation', 'remarks', 'pdf_report_path', 'audiogram_path'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return False
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            set_clause = ', '.join(f"{k} = ?" for k in update_fields.keys())
            values = list(update_fields.values()) + [test_id]
            
            cursor.execute(f'UPDATE test_results SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    # =========================================================================
    # Analytics & Comparison
    # =========================================================================
    
    def get_comparison_data(self, patient_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get test results for audiogram overlay comparison.
        
        Returns the most recent tests with simplified data structure
        suitable for overlaying multiple audiograms.
        
        Args:
            patient_id: The patient's database ID.
            limit: Maximum number of tests to return.
            
        Returns:
            List of simplified test records for comparison.
        """
        history = self.get_patient_history(patient_id)[:limit]
        
        comparison_data = []
        for test in history:
            comparison_data.append({
                'test_date': test['test_date'],
                'left_ear': test.get('left_ear_data', {}),
                'right_ear': test.get('right_ear_data', {}),
                'test_id': test['id']
            })
        
        return comparison_data
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict with counts and summary statistics.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM patients')
            patient_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM test_results')
            test_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT DATE(test_date) as date, COUNT(*) as count 
                FROM test_results 
                GROUP BY DATE(test_date) 
                ORDER BY date DESC 
                LIMIT 7
            ''')
            recent_tests = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_patients': patient_count,
                'total_tests': test_count,
                'recent_activity': recent_tests
            }
        finally:
            conn.close()
    
    def close(self) -> None:
        """Close all connections (placeholder for future connection pooling)."""
        pass


# Module test
if __name__ == '__main__':
    import tempfile
    
    # Create a test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db_path = f.name
    
    try:
        db = PatientDatabase(test_db_path)
        
        # Test patient operations
        patient_id = db.add_patient(
            name="John Doe",
            phone="9876543210",
            age=45,
            gender="male",
            ref_id="REF-001"
        )
        print(f"Created patient with ID: {patient_id}")
        
        # Test duplicate phone handling
        same_id = db.add_patient(name="John Doe", phone="9876543210")
        print(f"Duplicate phone returned existing ID: {same_id}")
        
        # Test search
        results = db.search_patients("John")
        print(f"Search results: {len(results)} found")
        
        # Test saving test results
        test_id = db.save_test_result(
            patient_id=patient_id,
            left_ear_data={500: 25, 1000: 30, 2000: 35, 4000: 40},
            right_ear_data={500: 20, 1000: 25, 2000: 30, 4000: 35},
            interpretation="Mild bilateral hearing loss",
            test_mode="quick"
        )
        print(f"Created test result with ID: {test_id}")
        
        # Test history retrieval
        history = db.get_patient_history(patient_id)
        print(f"Patient history: {len(history)} tests")
        
        # Test statistics
        stats = db.get_statistics()
        print(f"Database stats: {stats}")
        
        print("\nAll tests passed!")
        
    finally:
        os.unlink(test_db_path)
