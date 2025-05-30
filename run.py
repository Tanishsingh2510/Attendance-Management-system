#!/usr/bin/env python3
"""
Startup script for the attendance management system.
Initializes the database if it doesn't exist and starts the application.
"""

import os
import subprocess
from app import app
from config import DATABASE_PATH

def main():
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print("Database not found. Running initialization script...")
        try:
            subprocess.run(["python", "db_init.py"], check=True)
            print("Database initialized successfully.")
        except subprocess.CalledProcessError:
            print("Error initializing database. Please run db_init.py manually.")
            return
    
    # Start the Flask application
    print("Starting Attendance Management System...")
    app.run(debug=app.config.get('DEBUG', False))

if __name__ == "__main__":
    main()