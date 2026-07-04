import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'super_secure_fallback_key_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrms.db'

# ==========================================
# SECURITY: SECURE UPLOAD CONFIGURATION
# ==========================================
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'profile_pics')
app.config['ATTACHMENT_FOLDER'] = os.path.join(app.root_path, 'static', 'attachments')

# ANTI-HACKING: Hard limit upload size to 5 Megabytes to prevent DoS attacks
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  

# ANTI-HACKING: Restrict acceptable file types to prevent malicious script execution
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_DOC_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

def allowed_file(filename, allowed_set):
    """Verifies that the uploaded file has a safe extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

# ==========================================
# SMTP SETUP
# ==========================================
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
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(150), nullable=True)
    employees = db.relationship('User', backref='branch', lazy=True)

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    employees = db.relationship('User', backref='department', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(250), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True, default='default.png')
    
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    monthly_wage = db.Column(db.Float, default=0.0)
    
    @property
    def yearly_wage(self): return (self.monthly_wage or 0) * 12
    @property
    def basic_salary(self): return (self.monthly_wage or 0) * 0.50
    @property
    def hra(self): return self.basic_salary * 0.50
    
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=lambda: datetime.now().date())
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
    message = db.Column(db.Text, nullable=True)
    attachment = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('leave_requests', lazy=True))

class SalaryRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now())
    month_year = db.Column(db.String(50), nullable=False)
    gross_salary = db.Column(db.Float, nullable=False)
    deductions = db.Column(db.Float, default=0.0)
    deduction_reason = db.Column(db.String(255), nullable=True)
    net_paid = db.Column(db.Float, nullable=False)
    user = db.relationship('User', backref=db.backref('salary_records', order_by='desc(SalaryRecord.payment_date)', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ==========================================
# UTILS & AUTH ROUTES
# ==========================================
def send_otp_email(user):
    otp_code = f"{random.randint(100000, 999999)}"
    user.otp = otp_code
    user.otp_expiry = datetime.now() + timedelta(minutes=10)
    db.session.commit()
    
    msg = Message('Your HRMS Security Code', recipients=[user.email])
    current_year = datetime.now().year

    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f5; padding: 40px 15px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; max-width: 500px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                        <tr>
                            <td style="background-color: #b244d4; padding: 30px; text-align: center; color: #ffffff;">
                                <h1 style="margin: 0; font-size: 24px; letter-spacing: 1px; text-transform: uppercase;">HRMS Portal</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px 30px; text-align: center;">
                                <h2 style="margin-top: 0; color: #333333; font-size: 22px;">Authentication Required</h2>
                                <p style="color: #555555; font-size: 15px; line-height: 1.6; margin-bottom: 30px;">
                                    You are receiving this email because a request was made to access your HRMS account. Please use the following security code to complete your request.
                                </p>
                                <div style="background-color: #fbf5ff; border: 1px solid #e9d5ff; border-radius: 8px; padding: 20px; display: inline-block; margin-bottom: 30px;">
                                    <p style="margin: 0; font-size: 36px; font-weight: bold; color: #b244d4; letter-spacing: 12px; white-space: nowrap;">{otp_code}</p>
                                </div>
                                <p style="color: #888888; font-size: 14px; margin: 0;">
                                    This code will expire in <strong>10 minutes</strong>.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 30px 30px 30px; border-top: 1px solid #eeeeee;">
                                <p style="margin: 0; font-size: 12px; color: #999999; line-height: 1.6; text-align: center;">
                                    If you did not request this code, please ignore this email or contact your IT/HR administrator immediately. Your account password may be compromised.<br><br>
                                    &copy; {current_year} HR Management System. This is an automated message, please do not reply.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    msg.body = f"Your HRMS security code is: {otp_code}. This code will expire in 10 minutes."
    mail.send(msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    branches, departments = Branch.query.all(), Department.query.all()
    if request.method == 'POST':
        email = request.form.get('email')
        employee_id = request.form.get('employee_id')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
            
        if User.query.filter_by(employee_id=employee_id).first():
            flash('Employee ID is already in use. Please enter a unique ID.')
            return redirect(url_for('register'))
            
        new_user = User(
            name=request.form.get('name'),
            email=email, 
            employee_id=employee_id, 
            role=request.form.get('role'), 
            branch_id=request.form.get('branch_id'),
            department_id=request.form.get('department_id'),
            monthly_wage=request.form.get('monthly_wage', type=float, default=0.0),
            password_hash=generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        
        try:
            send_otp_email(new_user)
            flash('Registration successful! Check email for OTP.')
            return redirect(url_for('verify_otp', email=new_user.email))
        except Exception as e:
            flash(f'Error sending OTP: {str(e)}')
            return redirect(url_for('login'))
            
    return render_template('register.html', branches=branches, departments=departments)

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first_or_404()
    if request.method == 'POST':
        if user.otp != request.form.get('otp'):
            flash('Incorrect entry token.')
            return render_template('verify_otp.html', email=email)
        if datetime.now() > user.otp_expiry:
            flash('OTP expired.')
            return redirect(url_for('register'))
        user.is_verified, user.otp, user.otp_expiry = True, None, None
        db.session.commit()
        flash('Account verified! Please login.')
        return redirect(url_for('login'))
    return render_template('verify_otp.html', email=email)

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if not user or not check_password_hash(user.password_hash, request.form.get('password')):
            flash('Invalid credentials.')
            return redirect(url_for('login'))
        if not user.is_verified:
            flash('Please verify your email.')
            return redirect(url_for('verify_otp', email=user.email))
        login_user(user, remember=True if request.form.get('remember') else False)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ==========================================
# SINGLE PAGE FORGOT PASSWORD LOGIC (APIs)
# ==========================================
@app.route('/forgot-password', methods=['GET'])
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/api/send-reset-otp', methods=['POST'])
def api_send_reset_otp():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user:
        try:
            send_otp_email(user)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': 'Failed to send email. Check SMTP.'})
    return jsonify({'success': False, 'message': 'Email not found in our system.'})

@app.route('/api/verify-reset-otp', methods=['POST'])
def api_verify_reset_otp():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if not user or user.otp != data.get('otp'):
        return jsonify({'success': False, 'message': 'Incorrect OTP.'})
    
    if datetime.now() > user.otp_expiry:
        return jsonify({'success': False, 'message': 'OTP has expired. Please resend.'})
    
    return jsonify({'success': True})

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if not user:
        return jsonify({'success': False, 'message': 'System error. User not found.'})
    
    user.password_hash = generate_password_hash(data.get('new_password'), method='pbkdf2:sha256')
    user.otp = None
    db.session.commit()
    
    flash('Password successfully reset! You can now log in.')
    return jsonify({'success': True, 'redirect': url_for('login')})


# ==========================================
# DASHBOARD & PROFILE LOGIC
# ==========================================
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        employees = User.query.filter(
            User.role == 'Employee',
            User.branch_id == current_user.branch_id,
            User.department_id == current_user.department_id
        ).options(db.joinedload(User.branch), db.joinedload(User.department)).all()
        
        emp_ids = [emp.id for emp in employees]
        all_attendance = Attendance.query.filter(Attendance.user_id.in_(emp_ids)).all() if emp_ids else []
        pending_leaves = LeaveRequest.query.filter(LeaveRequest.user_id.in_(emp_ids)).all() if emp_ids else []
            
        branches, departments = Branch.query.all(), Department.query.all()
        return render_template('admin_dashboard.html', employees=employees, attendance=all_attendance, leaves=pending_leaves, branches=branches, departments=departments)
    
    else:
        # Data Isolation: Employees only see their peers
        peers = User.query.filter(
            User.id != current_user.id,
            User.branch_id == current_user.branch_id,
            User.department_id == current_user.department_id
        ).options(db.joinedload(User.branch), db.joinedload(User.department)).all()
        
        my_attendance = Attendance.query.filter_by(user_id=current_user.id).all()
        my_leaves = LeaveRequest.query.filter_by(user_id=current_user.id).all()
        return render_template('employee_dashboard.html', employees=peers, attendance=my_attendance, leaves=my_leaves)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    current_user.name = request.form.get('name') or current_user.name
    current_user.phone = request.form.get('phone') or current_user.phone
    current_user.address = request.form.get('address') or current_user.address
    
    new_password = request.form.get('password')
    if new_password:
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        
    # SECURITY & ANTI-HACKING: Profile Picture Upload
    pic = request.files.get('profile_picture')
    if pic and pic.filename != '':
        if allowed_file(pic.filename, ALLOWED_IMAGE_EXTENSIONS):
            # Safe Filename Generation avoids Directory Traversal Overwrites
            ext = pic.filename.rsplit('.', 1)[1].lower()
            safe_name = f"user_{current_user.id}_{int(datetime.now().timestamp())}.{ext}"
            pic.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
            current_user.profile_picture = safe_name
        else:
            flash("Security Alert: Invalid image format. Please upload JPG, PNG, or WEBP.", "error")
            return redirect(url_for('dashboard'))

    db.session.commit()
    flash("Your profile details have been successfully updated.")
    return redirect(url_for('dashboard'))

@app.route('/admin/employee/edit/<int:emp_id>', methods=['POST'])
@login_required
def edit_employee(emp_id):
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
        
    emp = User.query.get_or_404(emp_id)
    emp.name = request.form.get('name') or emp.name
    emp.role = request.form.get('role', emp.role)
    emp.branch_id = request.form.get('branch_id') or None
    emp.department_id = request.form.get('department_id') or None
    emp.monthly_wage = request.form.get('monthly_wage', type=float, default=emp.monthly_wage)
    
    db.session.commit()
    flash(f"Successfully updated records for {emp.email}.")
    return redirect(url_for('dashboard'))


# ==========================================
# SALARY DISBURSEMENT & INVOICE ENGINE
# ==========================================
@app.route('/admin/salary/pay/<int:emp_id>', methods=['POST'])
@login_required
def process_salary(emp_id):
    if current_user.role != 'Admin':
        return redirect(url_for('dashboard'))
        
    emp = User.query.get_or_404(emp_id)
    month_year = request.form.get('month_year')
    deductions = float(request.form.get('deductions', 0.0))
    deduction_reason = request.form.get('deduction_reason', '')
    hr_message = request.form.get('hr_message', '').strip()
    
    gross = emp.monthly_wage
    net_paid = gross - deductions
    
    record = SalaryRecord(
        user_id=emp.id, month_year=month_year, gross_salary=gross, 
        deductions=deductions, deduction_reason=deduction_reason, net_paid=net_paid
    )
    db.session.add(record)
    db.session.commit()
    
    try:
        msg = Message(f'Official Payslip & Salary Disbursement - {month_year}', recipients=[emp.email])
        
        deduction_block = ""
        if deductions > 0:
            deduction_block = f"""
            <div style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 15px; margin-bottom: 25px;">
                <p style="margin: 0; color: #c53030; font-size: 14px;"><strong>Reason for Deduction:</strong> {deduction_reason}</p>
            </div>
            """

        message_block = ""
        if hr_message:
            message_block = f"""
            <div style="background-color: #fbf5ff; border: 1px solid #e9d5ff; border-radius: 6px; padding: 20px; margin-bottom: 25px;">
                <p style="margin: 0 0 10px 0; color: #b244d4; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Message from HR / Admin</p>
                <p style="margin: 0; color: #555555; font-size: 15px; font-style: italic;">"{hr_message}"</p>
            </div>
            """
            
        current_year = datetime.now().year

        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f5; padding: 40px 15px;">
                <tr>
                    <td align="center">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; max-width: 600px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                            <tr>
                                <td style="background-color: #b244d4; padding: 35px 30px; text-align: center; color: #ffffff;">
                                    <h1 style="margin: 0; font-size: 24px; letter-spacing: 1px; text-transform: uppercase;">Salary Disbursement</h1>
                                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{month_year}</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <p style="margin-top: 0; font-size: 16px; color: #333333;">Hello <strong>{emp.employee_id}</strong>,</p>
                                    <p style="font-size: 15px; color: #555555; line-height: 1.6;">Your salary for <strong>{month_year}</strong> has been successfully processed by the HR department. Below is the summary of your official payslip.</p>
                                    <table width="100%" cellpadding="15" cellspacing="0" border="0" style="margin-top: 35px; margin-bottom: 30px; border: 1px solid #eeeeee; border-radius: 6px;">
                                        <tr>
                                            <td style="border-bottom: 1px solid #eeeeee; color: #555555;">Base Gross Salary</td>
                                            <td align="right" style="border-bottom: 1px solid #eeeeee; font-weight: bold; color: #333333;">&#8377; {gross:,.2f}</td>
                                        </tr>
                                        <tr>
                                            <td style="border-bottom: 1px solid #eeeeee; color: #e53e3e;">Total Deductions</td>
                                            <td align="right" style="border-bottom: 1px solid #eeeeee; font-weight: bold; color: #e53e3e;">- &#8377; {deductions:,.2f}</td>
                                        </tr>
                                        <tr>
                                            <td style="background-color: #fcfcfc; font-weight: bold; font-size: 15px; color: #111111;">NET PAID AMOUNT</td>
                                            <td align="right" style="background-color: #fcfcfc; font-weight: bold; font-size: 20px; color: #22c55e;">&#8377; {net_paid:,.2f}</td>
                                        </tr>
                                    </table>
                                    {deduction_block}
                                    {message_block}
                                    <p style="font-size: 13px; color: #888888; margin-top: 35px; line-height: 1.6; border-top: 1px solid #eeeeee; padding-top: 25px;">
                                        The funds should reflect in your registered bank account shortly. If you have any discrepancies or questions regarding this payslip, please contact your HR representative immediately.
                                    </p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: #f9f9f9; padding: 20px; text-align: center; color: #aaaaaa; font-size: 12px;">
                                    &copy; {current_year} HR Management System. All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        msg.body = f"Salary Processed: Gross: {gross}, Deductions: {deductions}, Net: {net_paid}."
        
        mail.send(msg)
        flash(f"Salary successfully processed and invoice emailed to {emp.email}.")
    except Exception as e:
        flash(f"Salary logged, but failed to send email invoice: {str(e)}")
        
    return redirect(url_for('dashboard'))

# ==========================================
# ATTENDANCE & LEAVE ROUTES
# ==========================================
@app.route('/attendance/check_in', methods=['POST'])
@login_required
def check_in():
    today = datetime.now().date()
    if not Attendance.query.filter_by(user_id=current_user.id, date=today).first():
        db.session.add(Attendance(user_id=current_user.id, check_in=datetime.now()))
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/attendance/check_out', methods=['POST'])
@login_required
def check_out():
    record = Attendance.query.filter_by(user_id=current_user.id, date=datetime.now().date()).first()
    if record and not record.check_out:
        record.check_out = datetime.now()
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/leave/apply', methods=['POST'])
@login_required
def apply_leave():
    file = request.files.get('attachment')
    filename = None
    
    # SECURITY & ANTI-HACKING: Attachment Extension Check
    if file and file.filename != '':
        if allowed_file(file.filename, ALLOWED_DOC_EXTENSIONS):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"doc_{current_user.id}_{int(datetime.now().timestamp())}.{ext}")
            file.save(os.path.join(app.config['ATTACHMENT_FOLDER'], filename))
        else:
            flash("Security Alert: Invalid attachment. Only PDF, DOC, or Images allowed.")
            return redirect(url_for('dashboard'))
            
    new_leave = LeaveRequest(
        user_id=current_user.id, 
        leave_type=request.form.get('leave_type'), 
        start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(), 
        end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date(),
        message=request.form.get('message'),
        attachment=filename
    )
    db.session.add(new_leave)
    db.session.commit()
    flash("Time off request submitted to HR.")
    return redirect(url_for('dashboard'))

@app.route('/admin/leave/action/<int:leave_id>', methods=['POST'])
@login_required
def leave_action(leave_id):
    if current_user.role == 'Admin':
        leave = LeaveRequest.query.get_or_404(leave_id)
        leave.status = request.form.get('status')
        db.session.commit()
    return redirect(url_for('dashboard'))

def seed_database():
    if not Branch.query.first():
        db.session.add_all([Branch(name='Main HQ', location='New York'), Branch(name='Europe', location='London'), Branch(name='Asia Hub', location='Singapore')])
    if not Department.query.first():
        db.session.add_all([Department(name='Engineering'), Department(name='HR'), Department(name='Sales')])
    db.session.commit()

def initialize():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ATTACHMENT_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()
        seed_database()

initialize()

if __name__ == '__main__':
    app.run(debug=True)