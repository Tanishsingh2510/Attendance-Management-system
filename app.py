"""
Main application for the attendance management system.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import datetime
import traceback
from functools import wraps

from models import Student, Attendance, Session
from config import SECRET_KEY, DEBUG, SESSION_TYPE, SESSION_LIFETIME

app = Flask(__name__)
app.secret_key = SECRET_KEY  # From config.py

# Session cookie settings
app.config['SESSION_TYPE'] = SESSION_TYPE
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=SESSION_LIFETIME)
app.config['DEBUG'] = True  # Enable debug mode for better error messages

# Context processor to make datetime available in all templates
@app.context_processor
def inject_now():
    """Make now variable available to all templates."""
    return {'now': datetime.datetime.now()}

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        
        # Validate session token
        student_id = Session.validate(session['session_token'])
        if not student_id:
            # Invalid or expired session
            session.pop('session_token', None)
            flash('Your session has expired. Please log in again', 'error')
            return redirect(url_for('login'))
        
        # Set current_user for the request
        kwargs['student_id'] = student_id
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/')
def index():
    """Home page"""
    if 'session_token' in session:
        student_id = Session.validate(session['session_token'])
        if student_id:
            return redirect(url_for('dashboard'))
    
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # Verify credentials
            student_id = Student.verify_password(username, password)
            
            if student_id:
                # Create session and mark attendance
                session_token = Session.create(student_id)
                session['session_token'] = session_token
                
                # Mark attendance for today
                Attendance.mark_attendance(student_id)
                
                flash('Login successful! Your attendance has been marked for today.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash(f"An error occurred during login. Please try again.", 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Validate input (simplified)
        if not all([username, password, name, email]):
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        try:
            # Create new student
            if Student.create(username, password, name, email):
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Username or email already exists', 'error')
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            flash(f"An error occurred during registration. Please try again.", 'error')
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard(student_id):
    """Student dashboard showing attendance statistics"""
    try:
        student = Student.get_by_id(student_id)
        if not student:
            session.pop('session_token', None)
            flash('Your account could not be found. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        # Get attendance statistics
        attendance_stats = Attendance.get_attendance_percentage(student_id)
        attendance_history = Attendance.get_attendance_history(student_id)
        
        return render_template(
            'dashboard.html',
            student=student,
            attendance_stats=attendance_stats,
            attendance_history=attendance_history
        )
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash(f"An error occurred while loading your dashboard. Please try again.", 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Logout user and invalidate session"""
    if 'session_token' in session:
        Session.delete(session['session_token'])
        session.pop('session_token', None)
    
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/api/attendance')
@login_required
def api_attendance(student_id):
    """API endpoint for attendance data (useful for AJAX updates)"""
    try:
        days = request.args.get('days', 30, type=int)
        attendance_stats = Attendance.get_attendance_percentage(student_id, days=days)
        attendance_history = Attendance.get_attendance_history(student_id, days=days)
        
        return jsonify({
            'stats': attendance_stats,
            'history': attendance_history
        })
    except Exception as e:
        app.logger.error(f"API error: {str(e)}")
        return jsonify({
            'error': 'An error occurred while fetching attendance data',
            'details': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 error: {str(e)}")
    app.logger.error(traceback.format_exc())
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)