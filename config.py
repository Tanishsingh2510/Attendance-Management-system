"""
Configuration settings for the attendance management system.
"""

import os

# Flask settings
DEBUG = True
SECRET_KEY = 'your_secret_key_here'  # Change this in production!
SESSION_TYPE = 'filesystem'

# Database settings
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'attendance.db')

# Application settings
ATTENDANCE_THRESHOLD = 75  # Minimum attendance percentage required
ATTENDANCE_PERIOD_DAYS = 30  # Default period for attendance calculation

# Session settings
SESSION_LIFETIME = 24  # Session lifetime in hours