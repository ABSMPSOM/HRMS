import os
import random
from datetime import datetime, timedelta, timezone
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

# ==========================================
# FILE UPLOAD CONFIGURATION (PICTURE PATH)
# ==========================================
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'profile_pics')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB upload limit

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
# MODELS
# ==========================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False) # 'Admin' or 'Employee'
    address = db.Column(db.String(250), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Profile Picture Link
    profile_picture = db.Column(db.String(255), nullable=True, default='default.png')
    
    # Secure Verification Columns
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
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
    return db.session.get(User, int(user_id))

# ==========================================
# OTP UTILITY FUNCTION
# ==========================================
def send_otp_email(user):
    """Generates a secure numeric token and dispatches it over SMTP."""
    otp_code = f"{random.randint(100000, 999999)}"
    user.otp = otp_code
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()
    
    msg = Message('Your HRMS Account OTP Verification Code', recipients=[user.email])
    msg.body = f'''Welcome to the HRMS System!
    
Your secure One-Time Password (OTP) validation key is: {otp_code}

This operational verification key will expire automatically in 10 minutes.
'''
    mail.send(msg)

# ==========================================
# AUTHENTICATION ROUTES
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
            
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        if current_time > user.otp_expiry:
            flash('The verification code has expired. Use the register system to re-issue standard authorization tokens.')
            return redirect(url_for('register'))
            
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
        
        # Determine if the Remember Me checkbox was checked
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid login authentication coordinates.')
            return redirect(url_for('login'))
            
        if not user.is_verified:
            flash('Your identity verification pipeline is incomplete. Check email or complete target authentication routing.')
            return redirect(url_for('verify_otp', email=user.email))
            
        # Trigger the login session, passing the remember parameter to generate the persistent cookie
        login_user(user, remember=remember)
        return redirect(url_for('dashboard'))
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==========================================
# PASSWORD RESET ROUTES
# ==========================================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handles the request to send an OTP for password reset."""
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                send_otp_email(user)
                flash('A password reset OTP has been sent to your email.')
                return redirect(url_for('reset_password', email=user.email))
            except Exception as e:
                flash(f'Failed to send OTP email: {str(e)}')
        else:
            flash('No account found with that email address.')
            
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Verifies the OTP and updates the user's password."""
    email = request.args.get('email') or request.form.get('email')
    
    if not email:
        flash('Invalid request. Please start the password reset process again.')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('User not found.')
            return redirect(url_for('login'))
            
        if user.otp != submitted_otp:
            flash('Incorrect OTP code.')
            return render_template('reset_password.html', email=email)
            
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        if current_time > user.otp_expiry:
            flash('The OTP has expired. Please request a new one.')
            return redirect(url_for('forgot_password'))
            
        # Success - Hash the new password and clear the OTP fields
        user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        user.otp = None
        user.otp_expiry = None
        db.session.commit()
        
        flash('Your password has been successfully reset! You can now log in.')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', email=email)


# ==========================================
# CORE DASHBOARD & LOGIC ROUTES
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

@app.route('/attendance/check_in', methods=['POST'])
@login_required
def check_in():
    today = datetime.now(timezone.utc).date()
    record = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    if not record:
        new_record = Attendance(user_id=current_user.id, check_in=datetime.now(timezone.utc))
        db.session.add(new_record)
        db.session.commit()
        flash('Successfully Checked In.')
    else:
        flash('Already Checked In Today.')
    return redirect(url_for('dashboard'))

@app.route('/attendance/check_out', methods=['POST'])
@login_required
def check_out():
    today = datetime.now(timezone.utc).date()
    record = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    if record and not record.check_out:
        record.check_out = datetime.now(timezone.utc)
        db.session.commit()
        flash('Successfully Checked Out.')
    elif not record:
        flash('Please Check In first.')
    else:
        flash('Already Checked Out Today.')
    return redirect(url_for('dashboard'))

@app.route('/leave/apply', methods=['POST'])
@login_required
def apply_leave():
    leave_type = request.form.get('leave_type')
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
    
    new_leave = LeaveRequest(user_id=current_user.id, leave_type=leave_type, start_date=start_date, end_date=end_date)
    db.session.add(new_leave)
    db.session.commit()
    flash('Leave request submitted.')
    return redirect(url_for('dashboard'))

@app.route('/admin/leave/action/<int:leave_id>', methods=['POST'])
@login_required
def leave_action(leave_id):
    if current_user.role != 'Admin':
        return "Unauthorized", 403
    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = request.form.get('status') # 'Approved' or 'Rejected'
    db.session.commit()
    flash(f'Leave request {leave.status}.')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Ensure the upload folder exists before the app starts
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        db.create_all()
    app.run(debug=True)