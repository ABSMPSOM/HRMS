import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

# Load environment configuration from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrms.db'

# SMTP Setup securely parsed from environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ==========================================
# REVISED MODELS
# ==========================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False) # 'Admin' or 'Employee'
    address = db.Column(db.String(250), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Secure Verification Columns
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Present')
    user = db.relationship('User', backref=db.backref('attendance_records', lazy=True))

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('leave_requests', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# OTP UTILITY FUNCTION
# ==========================================
def send_otp_email(user):
    """Generates a secure numeric token and dispatches it over SMTP."""
    otp_code = f"{random.randint(100000, 999999)}"
    user.otp = otp_code
    # Token valid for a 10 minute window frame
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    msg = Message('Your HRMS Account OTP Verification Code', recipients=[user.email])
    msg.body = f'''Welcome to the HRMS System!
    
Your secure One-Time Password (OTP) validation key is: {otp_code}

This operational verification key will expire automatically in 10 minutes.
'''
    mail.send(msg)

# ==========================================
# SEAMLESS AUTH ROTATION ROUTES
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        employee_id = request.form.get('employee_id')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
            
        new_user = User(
            email=email, 
            employee_id=employee_id, 
            role=role, 
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        
        try:
            send_otp_email(new_user)
            flash('Registration successful! Please submit the OTP token dispatched to your inbox.')
            return redirect(url_for('verify_otp', email=new_user.email))
        except Exception as e:
            flash(f'Account initialized, but SMTP failed to send token: {str(e)}')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')
    if not email:
        flash('Invalid verification request parameter mapping.')
        return redirect(url_for('login'))
        
    user = User.query.filter_by(email=email).first_or_404()
    
    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        
        if user.otp != submitted_otp:
            flash('Incorrect entry token code value.')
            return render_template('verify_otp.html', email=email)
            
        if datetime.utcnow() > user.otp_expiry:
            flash('The verification code has expired. Use the register system to re-issue standard authorization tokens.')
            return redirect(url_for('register'))
            
        # Target verification criteria met smoothly
        user.is_verified = True
        user.otp = None 
        user.otp_expiry = None
        db.session.commit()
        
        flash('Email completely verified successfully! Access granted via core login system portal.')
        return redirect(url_for('login'))
        
    return render_template('verify_otp.html', email=email)

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid login authentication coordinates.')
            return redirect(url_for('login'))
            
        if not user.is_verified:
            flash('Your identity verification verification pipeline is incomplete. Check email or complete target authentication routing.')
            return redirect(url_for('verify_otp', email=user.email))
            
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==========================================
# CORE REDIRECT ROUTING DASHBOARD LOGIC
# ==========================================
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        employees = User.query.filter_by(role='Employee').all()
        all_attendance = Attendance.query.all()
        pending_leaves = LeaveRequest.query.all()
        return render_template('admin_dashboard.html', employees=employees, attendance=all_attendance, leaves=pending_leaves)
    else:
        my_attendance = Attendance.query.filter_by(user_id=current_user.id).all()
        my_leaves = LeaveRequest.query.filter_by(user_id=current_user.id).all()
        return render_template('employee_dashboard.html', attendance=my_attendance, leaves=my_leaves)

# (Remaining attendance/leave logic endpoints match folder structures cleanly...)
if __name__ == '__main__':
    with app.app_context():
        # NOTE: If columns structural conflict patterns occur, wipe instance/hrms.db completely to overwrite schema structural components safely.
        db.create_all()
    app.run(debug=True)