#!/usr/bin/env python3
"""
Database initialization script for attendance management system.
This script creates the database tables and populates with sample data.
"""

import sqlite3
import os
import hashlib
import datetime

# Import database path from config
from config import DATABASE_PATH

# Check if database file exists, and remove it if it does
if os.path.exists(DATABASE_PATH):
    os.remove(DATABASE_PATH)

# Connect to database (will create it if it doesn't exist)
conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

# Create students table
cursor.execute('''
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create attendance table
cursor.execute('''
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date DATE NOT NULL,
    logged_in BOOLEAN DEFAULT 0,
    login_time TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students (id),
    UNIQUE (student_id, date)
)
''')

# Create sessions table to track active sessions
cursor.execute('''
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    session_token TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id)
)
''')

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Insert sample students
sample_students = [
    ('john_doe', hash_password('password123'), 'John Doe', 'john.doe@example.com'),
    ('jane_smith', hash_password('password123'), 'Jane Smith', 'jane.smith@example.com'),
    ('bob_johnson', hash_password('password123'), 'Bob Johnson', 'bob.johnson@example.com'),
    ('alice_williams', hash_password('password123'), 'Alice Williams', 'alice.williams@example.com'),
    ('charlie_brown', hash_password('password123'), 'Charlie Brown', 'charlie.brown@example.com'),
]

cursor.executemany('''
INSERT INTO students (username, password, name, email)
VALUES (?, ?, ?, ?)
''', sample_students)

# Generate sample attendance data for the past 30 days
today = datetime.date.today()
for student_id in range(1, 6):  # 5 students with IDs 1-5
    for days_ago in range(30):
        date = today - datetime.timedelta(days=days_ago)
        
        # Randomly mark some days as absent (not logged in)
        # For simplicity, students are present on most days
        logged_in = 1
        login_time = None
        
        # Students are less likely to be present on weekends
        if date.weekday() >= 5:  # Saturday or Sunday
            logged_in = 0 if days_ago % 3 == 0 else 1
        elif days_ago % 7 == 0:  # Occasional absence on weekdays
            logged_in = 0
            
        if logged_in:
            # Generate a random login time between 8:00 AM and 9:30 AM
            hour = 8
            minute = (days_ago * 7 + student_id * 11) % 60  # Ensure minutes are between 0-59
            login_time = datetime.datetime.combine(
                date, 
                datetime.time(hour, minute)
            )
        
        cursor.execute('''
        INSERT INTO attendance (student_id, date, logged_in, login_time)
        VALUES (?, ?, ?, ?)
        ''', (student_id, date, logged_in, login_time))

# Commit changes and close connection
conn.commit()
conn.close()

print("Database initialized successfully with sample data.")