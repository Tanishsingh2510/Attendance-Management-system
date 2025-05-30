"""
Database models and operations for attendance management system.
"""

import sqlite3
import hashlib
import datetime
import secrets
import json
from contextlib import contextmanager
from config import DATABASE_PATH

# Database connection helper
@contextmanager
def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        yield conn
    finally:
        conn.close()

# Helper function to convert date strings to Python date objects
def parse_date(date_str):
    """Parse a date string from SQLite into a Python date object."""
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

# Helper function to convert datetime strings to Python datetime objects
def parse_datetime(datetime_str):
    """Parse a datetime string from SQLite into a Python datetime object."""
    if not datetime_str:
        return None
    try:
        return datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None

# Helper to make DB rows JSON serializable
def dict_factory(cursor, row):
    """Convert a SQLite row to a dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        value = row[idx]
        
        # Convert date/datetime strings to Python objects
        if col[0] == 'date':
            value = parse_date(value)
        elif col[0] == 'login_time' or 'created_at' in col[0] or 'expires_at' in col[0]:
            value = parse_datetime(value)
            
        d[col[0]] = value
    return d

class Student:
    """Student model for authentication and profile management"""
    
    @staticmethod
    def get_by_id(student_id):
        """Retrieve a student by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_by_username(username):
        """Retrieve a student by username"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE username = ?", (username,))
            return cursor.fetchone()
    
    @staticmethod
    def verify_password(username, password):
        """Verify a student's password"""
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM students WHERE username = ? AND password = ?", 
                (username, hashed_password)
            )
            result = cursor.fetchone()
            return result['id'] if result else None
    
    @staticmethod
    def create(username, password, name, email):
        """Create a new student account"""
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO students (username, password, name, email) VALUES (?, ?, ?, ?)",
                    (username, hashed_password, name, email)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Username or email already exists
                return False

class Attendance:
    """Attendance model for tracking student attendance"""
    
    @staticmethod
    def mark_attendance(student_id):
        """Mark a student as present for today"""
        today = datetime.date.today()
        now = datetime.datetime.now()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if attendance already marked for today
            cursor.execute(
                "SELECT id FROM attendance WHERE student_id = ? AND date = ?",
                (student_id, today)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record if not already marked as logged in
                cursor.execute(
                    "UPDATE attendance SET logged_in = 1, login_time = ? WHERE id = ?",
                    (now, existing['id'])
                )
            else:
                # Create new attendance record
                cursor.execute(
                    "INSERT INTO attendance (student_id, date, logged_in, login_time) VALUES (?, ?, 1, ?)",
                    (student_id, today, now)
                )
            
            conn.commit()
            return True
    
    @staticmethod
    def get_attendance_percentage(student_id, days=30):
        """Calculate attendance percentage for a student over a period"""
        from config import ATTENDANCE_PERIOD_DAYS
        
        # Use config value if default is passed
        if days == 30:
            days = ATTENDANCE_PERIOD_DAYS
            
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days-1)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count days in the period (excluding future dates)
            days_in_period = min(days, (end_date - start_date).days + 1)
            
            # Check if there are any attendance records
            cursor.execute(
                """
                SELECT COUNT(*) as record_count FROM attendance 
                WHERE student_id = ? AND date BETWEEN ? AND ?
                """,
                (student_id, start_date, end_date)
            )
            record_count = cursor.fetchone()['record_count']
            
            # If no records exist but we're in the requested period
            if record_count == 0:
                # For missing days, create records marked as absent
                missing_days = []
                current_date = start_date
                while current_date <= end_date and current_date <= datetime.date.today():
                    # Skip weekends (5=Saturday, 6=Sunday)
                    if current_date.weekday() < 5:
                        missing_days.append((student_id, current_date, 0, None))
                    current_date += datetime.timedelta(days=1)
                    
                if missing_days:
                    cursor.executemany(
                        "INSERT INTO attendance (student_id, date, logged_in, login_time) VALUES (?, ?, ?, ?)",
                        missing_days
                    )
                    conn.commit()
                    
                    # Update the record count
                    record_count = len(missing_days)
            
            # Count days present (logged in)
            cursor.execute(
                """
                SELECT COUNT(*) as present_days FROM attendance 
                WHERE student_id = ? AND date BETWEEN ? AND ? AND logged_in = 1
                """,
                (student_id, start_date, end_date)
            )
            present_days = cursor.fetchone()['present_days']
            
            # Calculate total days (excluding weekends)
            total_days = record_count
            
            percentage = (present_days / total_days) * 100 if total_days > 0 else 0
            
            return {
                "percentage": round(percentage, 2),
                "present_days": present_days,
                "total_days": total_days,
                "start_date": start_date,
                "end_date": end_date
            }
    
    @staticmethod
    def get_attendance_history(student_id, days=30):
        """Get detailed attendance history for a student"""
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days-1)
        
        with get_db_connection() as conn:
            # Use dict_factory for better date handling
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT date, logged_in, login_time 
                FROM attendance 
                WHERE student_id = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
                """,
                (student_id, start_date, end_date)
            )
            
            attendance_records = cursor.fetchall()
            
            # Empty results check
            if not attendance_records:
                # For empty results, create a placeholder with today's date
                return [{
                    'date': end_date,
                    'logged_in': 0,
                    'login_time': None
                }]
                
            return attendance_records

class Session:
    """Session management for tracking logged-in users"""
    
    @staticmethod
    def create(student_id):
        """Create a new session for a student"""
        token = secrets.token_hex(16)
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (student_id, session_token, expires_at) VALUES (?, ?, ?)",
                (student_id, token, expires_at)
            )
            conn.commit()
            return token
    
    @staticmethod
    def validate(token):
        """Validate a session token and return student_id if valid"""
        now = datetime.datetime.now()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT student_id FROM sessions WHERE session_token = ? AND expires_at > ?",
                (token, now)
            )
            result = cursor.fetchone()
            return result['student_id'] if result else None
    
    @staticmethod
    def delete(token):
        """Delete a session (logout)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0