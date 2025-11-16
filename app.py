from flask import Flask, render_template, request, flash, redirect, url_for, session, flash, send_file
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
import mysql.connector
import hashlib
import string
import re
import qrcode
import io
import base64
import time
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from decimal import Decimal
import random, string
from datetime import datetime
from werkzeug.security import check_password_hash
import uuid


app = Flask(__name__)
app.secret_key = "secret123"

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="payshield"
)
cursor = db.cursor()

# Send OTP Email
def send_otp(email, otp):
    sender_email = "payshield77@gmail.com"      # your gmail
    sender_password ="jevapqmlljxqkjyj"   # your gmail app password
    msg = MIMEText(f"Your OTP is: {otp}\nIt will expire in 5 minutes.")
    msg['Subject'] = "Login OTP Verification"
    msg['From'] = sender_email
    msg['To'] = email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


# Hashing passwords for security
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def home():
    return render_template('index.html')


# Register page (optional, for testing)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobileno = request.form['mobileno']
        password = hash_password(request.form['password'])
        confirm = request.form['confirm']

        # Password match check
        if request.form['password'] != confirm:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))

        # Simple phone validation
        if not re.match(r'^[0-9]{10}$', mobileno):
            flash("Invalid phone number! Must be 10 digits.", "danger")
            return redirect(url_for('register'))

        try:
            cursor.execute("""
                INSERT INTO users (username, email, mobileno, password)
                VALUES (%s, %s, %s, %s)
            """, (username, email, mobileno, password))
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')


# Step 1: Login with email+password
# @app.route('/', methods=['GET', 'POST'])
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = hash_password(request.form['password'])

#         cursor.execute("SELECT id, password FROM users WHERE email=%s", (email,))
#         user = cursor.fetchone()

#         if user and user[1] == password:
#             otp = str(random.randint(100000, 999999))
#             expires_at = datetime.now() + timedelta(minutes=5)

#             cursor.execute("INSERT INTO otp_logs (user_id, otp_code, expires_at) VALUES (%s, %s, %s)",
#                            (user[0], otp, expires_at))
#             db.commit()

#             if send_otp(email, otp):
#                 flash("OTP sent to your email!", "success")
#                 return render_template('verify.html', email=email)
#             else:
#                 flash("Failed to send OTP. Check email settings.", "danger")
#         else:
#             flash("Invalid email or password!", "danger")

#     return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])

        cursor.execute("SELECT id, username, password FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and user[2] == password:
            otp = str(random.randint(100000, 999999))
            expires_at = datetime.now() + timedelta(minutes=5)

            cursor.execute(
                "INSERT INTO otp_logs (user_id, otp_code, expires_at) VALUES (%s, %s, %s)",
                (user[0], otp, expires_at)
            )
            db.commit()

            # ✅ Store details in session
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = email

            if send_otp(email, otp):
                flash("OTP sent to your email!", "success")
                return render_template('verify.html', email=email)
            else:
                flash("Failed to send OTP. Check email settings.", "danger")
        else:
            flash("Invalid email or password!", "danger")

    return render_template('login.html')


# Step 2: Verify OTP
@app.route('/verify', methods=['POST'])
def verify():
    email = request.form['email']
    otp_input = request.form['otp']

    cursor.execute("""
        SELECT otp_logs.id, otp_logs.otp_code, otp_logs.expires_at, otp_logs.is_used, users.id 
        FROM otp_logs
        JOIN users ON otp_logs.user_id = users.id
        WHERE users.email = %s
        ORDER BY otp_logs.created_at DESC
        LIMIT 1
    """, (email,))
    
    result = cursor.fetchone()

    if result:
        otp_id, otp_code, expires_at, is_used, user_id = result
        if is_used:
            flash("OTP already used!", "danger")
        elif datetime.now() > expires_at:
            flash("OTP expired!", "danger")
        elif otp_input == otp_code:
            cursor.execute("UPDATE otp_logs SET is_used = TRUE WHERE id = %s", (otp_id,))
            db.commit()
            session['user_id'] = user_id
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid OTP!", "danger")
    else:
        flash("No OTP found for this email!", "danger")

    return render_template('verify.html', email=email)


# Dashboard (protected route)
# @app.route('/dashboard')
# def dashboard():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     return render_template('dashboard.html', email=session['email'])
  
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='payshield'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (user_id,))
    account = cursor.fetchone()
    conn.close()

    print("DEBUG => user_id:", user_id)
    print("DEBUG => account:", account)

    return render_template('dashboard.html', account=account,email=session['email'])

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))



@app.route('/')
def index():
    # If user logged in, show dashboard; otherwise go to login page.
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

#Profile section code
@app.route('/profile')
def profile():
    import mysql.connector
    from flask import session, redirect, url_for

    # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('login'))  # redirect if not logged in

    user_email = session['email']

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',   # update if needed
        database='payshield'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
    "SELECT id, username, email, mobileno, created_at FROM users WHERE email = %s",
    (user_email,)
)

    user = cursor.fetchone()
    account = None
    if user:
        cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (user['id'],))
        account = cursor.fetchone()
    conn.close()

    return render_template('profile.html', user=user,account=account)

# create a bank sccount after upi id
@app.route('/create_bank_account', methods=['GET', 'POST'])
def create_bank_account():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='payshield'
    )
    cursor = conn.cursor(dictionary=True)

    # Handle bank account creation
    if request.method == 'POST' and 'create_account' in request.form:
        account_number = "AC" + ''.join(random.choices(string.digits, k=10))
        ifsc_code = "PYSD" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        debit_card_number = ''.join(random.choices(string.digits, k=16))

        cursor.execute("""
            INSERT INTO bank_accounts (user_id, account_number, ifsc_code, debit_card_number)
            VALUES (%s, %s, %s, %s)
        """, (user_id, account_number, ifsc_code, debit_card_number))
        conn.commit()
        flash("Bank account created successfully!", "success")
        return redirect(url_for('create_bank_account'))

    # Handle UPI creation
    if request.method == 'POST' and 'create_upi' in request.form:
        upi_id = f"user{user_id}@payshield"
        cursor.execute("UPDATE bank_accounts SET upi_id = %s WHERE user_id = %s", (upi_id, user_id))
        conn.commit()
        flash("UPI ID created successfully!", "success")
        return redirect(url_for('create_bank_account'))

    # Fetch current account data
    cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (user_id,))
    account = cursor.fetchone()
    conn.close()

    return render_template('create_bank_account.html', account=account)

# #upi qr
@app.route('/upi_qr/<upi_id>', methods=['GET', 'POST'])
def upi_qr(upi_id):
    upi_link = f"upi://pay?pa={upi_id}&pn=PayShield&cu=INR"
    qr = qrcode.make(upi_link)
    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

# 📤 Route to share QR + UPI link (this is the new one)
@app.route('/share_qr/<upi_id>', methods=['GET', 'POST'])
def share_qr(upi_id):
    upi_link = f"upi://pay?pa={upi_id}&pn=PayShield&cu=INR"

    # Create base64 QR image to show in HTML
    qr = qrcode.make(upi_link)
    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    qr_base64 = base64.b64encode(img_io.read()).decode('utf-8')

    return render_template('share_qr.html', upi_link=upi_link, upi_id=upi_id ,qr_base64=qr_base64)

#wallet email otp
def send_email(to_email, subject, otp):
    sender_email = "payshield77@gmail.com"
    sender_password = "jevapqmlljxqkjyj"  # Use App Password (not your real one)
    # session.get('username', 'User')

    # msg = MIMEMultipart()
    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    html = f"""
     <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f8; padding: 0; margin: 0;">
      <table width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow: hidden;">
        <tr style="background-color: #0066cc;">
          <td style="padding: 20px; text-align: center; color: #fff;">
            
            <span style="font-size: 22px; font-weight: bold;">PayShield Security</span>
          </td>
        </tr>

        <tr>
          <td style="padding: 30px;">
            <h2 style="color: #333;">Wallet Verification OTP</h2>
            <p style="color: #555; font-size: 16px;">
              Dear User ,<br><br>
              To complete your PayShield Wallet setup, please verify using the OTP below.
            </p>

            <div style="text-align: center; margin: 25px 0;">
              <span style="display: inline-block; font-size: 12px; font-weight: bold; color: #0066cc; background: #f0f4ff; padding: 12px 12px; border-radius: 8px;">{otp}</span>
            </div>

            <p style="color: #555; font-size: 14px;">
              This OTP is valid for <strong>10 minutes</strong>. Please do not share this code with anyone.
            </p>

            <p style="color: #999; font-size: 13px; margin-top: 25px;">
              Thanks,<br>
              <strong>The PayShield Team</strong><br>
              Secure. Simple. Smart.
            </p>
          </td>
        </tr>

        <tr>
          <td style="background-color: #f0f0f0; text-align: center; padding: 15px; font-size: 12px; color: #777;">
            © {datetime.now().year} PayShield Technologies Pvt. Ltd. All rights reserved.
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html, "html"))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("✅ OTP sent to email:", to_email)
    except Exception as e:
        print("❌ Email error:", e)

#wallet message send after cretaed

def send_wallet_created_email(to_email, username, wallet_balance):
    sender_email = "payshield77@gmail.com"  # change to your Gmail
    sender_password = "jevapqmlljxqkjyj"  # use your App Password, not your login password

    msg = MIMEMultipart("alternative")
    msg["From"] = f"PayShield <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = "🎉 Wallet Created Successfully | PayShield"

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif; background-color:#f4f7fb; margin:0; padding:0;">
      <div style="max-width:600px;margin:30px auto;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);padding:20px;">
        <div style="text-align:center;">
        
          <h2 style="color:#0066cc;">Your Wallet is Ready! {username}🎉</h2>
        </div>
        <p style="font-size:16px;color:#333;">Welcome to <strong>PayShield</strong> — your secure digital wallet is now active.</p>
        <div style="background:#eaf3ff;padding:15px;border-left:5px solid #0066cc;margin:20px 0;border-radius:8px;">
          <h3 style="margin:0;">💰 Wallet Balance: <span style="color:#0066cc;">₹{wallet_balance}</span></h3>
        </div>
        <p style="font-size:15px;color:#555;">You can now send and receive payments instantly using your PayShield Wallet!</p>
        <div style="text-align:center;margin-top:25px;">
          <a href="#" style="background-color:#0066cc;color:#fff;padding:12px 30px;border-radius:8px;text-decoration:none;font-weight:bold;">Open My Wallet</a>
        </div>
        <hr style="margin:30px 0;border:none;border-top:1px solid #eee;">
        <p style="font-size:12px;color:#999;text-align:center;">© {datetime.now().year} PayShield Technologies Pvt. Ltd.<br>Secure • Simple • Instant</p>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Wallet creation email sent to {to_email}")
    except Exception as e:
        print("❌ Failed to send wallet email:", e)


#Wallet code
@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_email = session.get('email')

    conn = mysql.connector.connect(
        host='localhost', user='root', password='', database='payshield'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (user_id,))
    account = cursor.fetchone()

    if request.method == 'POST':
        last4 = request.form.get('last4', '').strip()
        if not account:
            flash("Please create a bank account first.", "danger")
            conn.close()
            return redirect(url_for('create_bank_account'))

        if account['debit_card_number'][-4:] != last4:
            flash("Incorrect last 4 digits of debit card.", "danger")
            conn.close()
            return redirect(url_for('wallet'))

        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        session['wallet_otp'] = otp
        session['wallet_otp_expires'] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        session['wallet_for_user_id'] = user_id

        # Send OTP to user's email
        email_body = f"Dear user,\n\nYour PayShield Wallet verification OTP is: {otp}\n\nIt will expire in 10 minutes.\n\n- PayShield Security Team"
        send_email(user_email, "PayShield Wallet OTP Verification", email_body)

        
        flash("OTP sent to your registered email. Please check and verify.", "info")
        conn.close()
        return redirect(url_for('wallet_verify'))

    conn.close()
    return render_template('wallet.html', account=account)

#Wallet verify
@app.route('/wallet_verify', methods=['GET', 'POST'])
def wallet_verify():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Validate OTP session data
    if 'wallet_otp' not in session or 'wallet_for_user_id' not in session:
        flash("No OTP session found. Please try again.", "warning")
        return redirect(url_for('wallet'))

    try:
        expires = datetime.fromisoformat(session['wallet_otp_expires'])
    except Exception:
        expires = datetime.utcnow() - timedelta(seconds=1)

    if datetime.utcnow() > expires:
        session.pop('wallet_otp', None)
        session.pop('wallet_otp_expires', None)
        session.pop('wallet_for_user_id', None)
        flash("OTP expired. Please request a new one.", "danger")
        return redirect(url_for('wallet'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        stored_otp = session.get('wallet_otp')

        if entered_otp == stored_otp and session.get('wallet_for_user_id') == user_id:
            conn = mysql.connector.connect(
                host='localhost', user='root', password='', database='payshield'
            )
            cursor = conn.cursor()

            # Mark wallet created + add ₹10,000 balance
            cursor.execute("""
                UPDATE bank_accounts 
                SET wallet_created = 1, 
                    wallet_balance = 10000, 
                    wallet_created_at = %s
                WHERE user_id = %s
            """, (datetime.utcnow(), user_id))
            conn.commit()
            
            send_wallet_created_email(session['email'], session.get('username', 'User'), 10000)

            conn.close()

            # Clear OTP session
            session.pop('wallet_otp', None)
            session.pop('wallet_otp_expires', None)
            session.pop('wallet_for_user_id', None)

            flash("🎉 Wallet created successfully! ₹10,000 credited to your wallet.", "success")
            flash("Please set MPIN to secure your wallet.", "info")
            return redirect(url_for('set_mpin'))
            # return redirect(url_for('create_bank_account'))
        else:
            flash("Invalid OTP. Try again.", "danger")
            return redirect(url_for('wallet_verify'))

    return render_template('wallet_verify.html')
# after committing wallet


@app.route('/add_bank', methods=['GET', 'POST'])
def add_bank():
    import mysql.connector
    import random
    from datetime import datetime, timedelta
    from flask import session, flash, redirect, url_for, render_template, request

    if 'email' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        bank_name = request.form['bank_name']
        account_number = request.form['account_number']
        ifsc_code = request.form['ifsc_code']
        debit_card_number = request.form['debit_card_number']
        user_id = session['user_id']

        # Generate OTP
        otp = random.randint(100000, 999999)
        expiry_time = datetime.now() + timedelta(minutes=2)

        # Store temporary data
        session['bank_otp'] = otp
        session['bank_otp_expiry'] = expiry_time.strftime("%Y-%m-%d %H:%M:%S")
        session['pending_bank'] = {
            'bank_name': bank_name,
            'account_number': account_number,
            'ifsc_code': ifsc_code,
            'debit_card_number': debit_card_number
        }

        try:
            conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='payshield'
            )
            cursor = conn.cursor(dictionary=True)

            # ✅ Check if this user already added a bank
            cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (user_id,))
            existing_user_bank = cursor.fetchone()
            if existing_user_bank:
                flash("You already have a bank account added.", "info")
                conn.close()
                return redirect(url_for('view_bank'))

            cursor.execute("SELECT * FROM bank_accounts WHERE account_number = %s", (account_number,))
            duplicate_account = cursor.fetchone()

            cursor.execute("SELECT * FROM bank_accounts WHERE debit_card_number = %s", (debit_card_number,))
            duplicate_debit = cursor.fetchone()

            # ✅ Handle each case properly
            if duplicate_account and duplicate_debit:
                flash("⚠️ Both account number and debit card number already exist.", "danger")
                conn.close()
                return redirect(url_for('add_bank'))
            elif duplicate_account:
                flash("⚠️ This account number already exists. Please use a different one.", "danger")
                conn.close()
                return redirect(url_for('add_bank'))
            elif duplicate_debit:
                flash("⚠️ This debit card number already exists. Please use a different one.", "danger")
                conn.close()
                return redirect(url_for('add_bank'))

            # ✅ Insert new bank account
            cursor.execute("""
                INSERT INTO bank_accounts (user_id, bank_name, account_number, ifsc_code, debit_card_number)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, bank_name, account_number, ifsc_code, debit_card_number))
            conn.commit()
            conn.close()

            # ✅ Send OTP email
            email_msg = f"""
            <h2>PayShield Bank Verification</h2>
            <p>Use the OTP below to confirm adding your bank account:</p>
            <h3>{otp}</h3>
            <p>This OTP will expire in <b>2 minutes</b>.</p>
            <p>If you did not request this, please ignore this email.</p>
            """
            send_email(session['email'], "Confirm Bank Account Addition", email_msg)

            flash("OTP sent to your registered email. Please verify within 2 minutes.", "info")
            return redirect(url_for('verify_bank_otp'))

        except mysql.connector.Error as err:
            flash(f"Database error: {err}", "danger")
            return redirect(url_for('add_bank'))

    return render_template('add_bank.html')

@app.route('/view_bank', methods=['GET','POST'])
def view_bank():
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='payshield'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (session['user_id'],))
    bank = cursor.fetchone()
    conn.close()

    return render_template('view_bank.html', bank=bank)
from datetime import datetime

@app.route('/verify_bank_otp', methods=['GET', 'POST'])
def verify_bank_otp():
    if 'email' not in session or 'bank_otp' not in session:
        flash("Session expired or invalid access.", "danger")
        return redirect(url_for('add_bank'))

    if request.method == 'POST':
        entered_otp = request.form['otp']
        saved_otp = str(session['bank_otp'])
        expiry_str = session.get('bank_otp_expiry')
        expiry_time = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")

        # Check expiry
        if datetime.now() > expiry_time:
            session.pop('bank_otp', None)
            session.pop('pending_bank', None)
            session.pop('bank_otp_expiry', None)
            flash("⏰ OTP expired! Please try again.", "danger")
            return redirect(url_for('add_bank'))

        # Check OTP
        if entered_otp == saved_otp:
            bank_data = session['pending_bank']
            user_id = session['user_id']

            # Save to database
            conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='payshield'
            )
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bank_accounts (user_id, bank_name, account_number, ifsc_code, debit_card_number)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, bank_data['bank_name'], bank_data['account_number'], bank_data['ifsc_code'], bank_data['debit_card_number']))
            conn.commit()
            conn.close()

            # Cleanup
            session.pop('bank_otp', None)
            session.pop('pending_bank', None)
            session.pop('bank_otp_expiry', None)

            # Send confirmation email
            email_msg = f"""
            <h2>✅ Bank Account Added Successfully</h2>
            <p>Your bank account ending with <b>{bank_data['account_number'][-4:]}</b> 
            has been successfully added to your PayShield wallet.</p>
            """
            send_email(session['email'], "Bank Account Added Successfully", email_msg)

            flash("✅ Bank account added successfully!", "success")
            return redirect(url_for('view_bank'))
        else:
            flash("❌ Invalid OTP, please try again.", "danger")
            return redirect(url_for('verify_bank_otp'))

    return render_template('verify_bank_otp.html')


@app.route('/set_mpin', methods=['GET', 'POST'])
def set_mpin():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # If you want to require OTP before setting MPIN, you can check session flag here.
    # e.g. if not session.get('bank_verified'): redirect to wallet flow.

    if request.method == 'POST':
        mpin = request.form.get('mpin', '').strip()
        mpin_confirm = request.form.get('mpin_confirm', '').strip()

        if mpin != mpin_confirm:
            flash("MPIN and confirmation do not match.", "danger")
            return redirect(url_for('set_mpin'))

        if not mpin.isdigit() or len(mpin) != 4:
            flash("MPIN must be exactly 4 digits.", "danger")
            return redirect(url_for('set_mpin'))

        mpin_hash = generate_password_hash(mpin)  # PBKDF2

        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bank_accounts 
            SET mpin_hash = %s, mpin_set_at = %s
            WHERE user_id = %s
        """, (mpin_hash, datetime.utcnow(), user_id))
        conn.commit()
        conn.close()
        send_mpin_created_email(session['email'], session.get('username', 'User'))
        flash("🔐 MPIN set successfully.", "success")
        return redirect(url_for('create_bank_account'))  # or wallet dashboard

    # GET
    return render_template('set_mpin.html')

# optional global attempt tracking (in session) to prevent brute force
MAX_MPIN_ATTEMPTS = 5

def send_mpin_created_email(to_email, username):
    import smtplib
    from email.mime.text import MIMEText

    
    subject = "MPIN Created Successfully - PayShield"
    body = f"""
    Hello {username},

    Your MPIN has been created successfully. 
    Your PayShield wallet is now protected and ready to use.

    🔒 Please keep your MPIN confidential and do not share it with anyone.

    Regards,  
    PayShield Security Team
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "payshield77@gmail.com"
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("payshield77@gmail.com", "jevapqmlljxqkjyj")
            server.send_message(msg)
    except Exception as e:
        print("Error sending MPIN creation email:", e)

@app.route('/verify_mpin', methods=['GET', 'POST'])
def verify_mpin():
    if 'user_id' not in session:
        flash("Please login.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # fetch mpin_hash
    conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT mpin_hash FROM bank_accounts WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row.get('mpin_hash'):
        flash("No MPIN set. Please set MPIN first.", "warning")
        return redirect(url_for('set_mpin'))

    if request.method == 'POST':
        entered = request.form.get('mpin', '').strip()
        # rate limiting attempts stored in session
        attempts = session.get('mpin_attempts', 0)
        if attempts >= MAX_MPIN_ATTEMPTS:
            flash("Too many incorrect attempts. Try again later.", "danger")
            return redirect(url_for('create_bank_account'))

        if check_password_hash(row['mpin_hash'], entered):
            # success: reset attempts
            session.pop('mpin_attempts', None)
            # proceed with the sensitive action, e.g. send money, confirm wallet top-up
            flash("MPIN verified.", "success")
            # Example: redirect to actual action page / perform action
            return redirect(url_for('wallet_dashboard'))
        else:
            session['mpin_attempts'] = attempts + 1
            flash(f"Incorrect MPIN. Attempts left: {MAX_MPIN_ATTEMPTS - session['mpin_attempts']}", "danger")
            return redirect(url_for('verify_mpin'))

    return render_template('verify_mpin.html')
#SEND MONEY
@app.route('/send_money', methods=['GET', 'POST'])
def send_money():
    if 'user_id' not in session:
        flash("Please log in to send money.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        to_upi = request.form.get('to_upi', '').strip()
        amount_str = request.form.get('amount', '').strip()
        note = request.form.get('note', '').strip()

        # basic validation
        try:
            amount = Decimal(amount_str)
        except:
            flash("Enter a valid amount.", "danger")
            return redirect(url_for('send_money'))

        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for('send_money'))

        # lookup receiver by upi_id
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT u.id AS user_id, u.email, b.wallet_balance, b.wallet_created, b.mpin_hash FROM users u JOIN bank_accounts b ON b.user_id = u.id WHERE b.upi_id = %s", (to_upi,))
        receiver = cursor.fetchone()

        # fetch sender wallet
        cursor.execute("SELECT b.user_id, b.wallet_balance, b.wallet_created FROM bank_accounts b WHERE b.user_id = %s", (user_id,))
        sender = cursor.fetchone()
        conn.close()

        if not sender or not sender.get('wallet_created'):
            flash("Your wallet is not created. Please create wallet first.", "danger")
            return redirect(url_for('create_bank_account'))

        if not receiver:
            flash("Recipient UPI not found on PayShield.", "danger")
            return redirect(url_for('send_money'))

        if sender['wallet_balance'] < amount:
            flash("Insufficient balance.", "danger")
            return redirect(url_for('send_money'))

        # Show confirmation screen asking for MPIN (pass data via session temporary)
        session['pending_tx'] = {
            'to_user_id': receiver['user_id'],
            'to_upi': to_upi,
            'amount': str(amount),
            'note': note
        }
        return redirect(url_for('send_money_confirm'))

    # GET -> show form
    return render_template('send_money.html')

#send email for transaction
def send_email_transaction(to_email, subject, body):
    sender_email = "payshield77@gmail.com"
    sender_password = "jevapqmlljxqkjyj"  # Use App Password from Google

    # Create email
    msg = MIMEMultipart("alternative")
    msg["From"] = "PayShield <payshield77@gmail.com>"
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add message body
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

#email send for money transaction
# def send_payment_emails(sender_email, sender_name, receiver_email, receiver_name, amount, note, tx_id):
#     """Send transaction success emails to both sender and receiver."""

#     # 1️⃣ Email to sender
#     subject_sender = "💸 Payment Sent Successfully - PayShield"
#     message_sender = f"""
#     Hello {sender_name},

#     ✅ Your payment of ₹{amount:.2f} has been sent successfully to.

#     📎 Transaction ID: {tx_id}
#     🧾 Note: {note or 'No note provided'}

#     Thank you for using PayShield!
#     - PayShield Security Team
#     """
#     send_email_transaction(sender_email, subject_sender, message_sender)

#     # 2️⃣ Email to receiver
#     subject_receiver = "💰 Payment Received - PayShield"
#     message_receiver = f"""
#     Hello,

#     🎉 You have received ₹{amount:.2f} from {sender_name} (UPI: {sender_email}).

#     📎 Transaction ID: {tx_id}
#     🧾 Note: {note or 'No note provided'}

#     Enjoy your secure payments with PayShield!
#     - PayShield Security Team
#     """
#     send_email_transaction(receiver_email, subject_receiver, message_receiver)
def send_payment_emails(sender_email, sender_name, sender_upi,receiver_email, receiver_name, receiver_upi,amount, note, tx_id):
    sender_app_email = "payshield77@gmail.com"
    sender_password = "jevapqmlljxqkjyj"  # App Password

    # --- Email for sender ---
    sender_subject = "💸 Payment Sent Successfully - PayShield"
    sender_body = f"""
Hello {sender_name},

You have successfully sent ₹{amount} to {receiver_name}.
-----------------------------------
Transaction ID: {tx_id}
To UPI ID: {receiver_upi}
Note: {note or 'No note added'}
-----------------------------------

Thank you for using PayShield!
"""

    # --- Email for receiver ---
    receiver_subject = "💰 Payment Received - PayShield"
    receiver_body = f"""
Hello {receiver_name},

You have received ₹{amount} from {sender_name}.
-----------------------------------
Transaction ID: {tx_id}
From UPI ID: {sender_upi}
Note: {note or 'No note added'}
-----------------------------------

Thank you for using PayShield!
"""

    try:
        import smtplib
        from email.mime.text import MIMEText

        # Send to sender
        msg1 = MIMEText(sender_body)
        msg1["Subject"] = sender_subject
        msg1["From"] = sender_app_email
        msg1["To"] = sender_email

        # Send to receiver
        msg2 = MIMEText(receiver_body)
        msg2["Subject"] = receiver_subject
        msg2["From"] = sender_app_email
        msg2["To"] = receiver_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_app_email, sender_password)
            server.send_message(msg1)
            server.send_message(msg2)

        print("✅ Payment emails sent successfully to sender and receiver.")
        return True

    except Exception as e:
        print(f"❌ Failed to send payment emails: {e}")
        return False

#SEND MONEY CONFIRM
@app.route('/send_money_confirm', methods=['GET', 'POST'])
def send_money_confirm():
    if 'user_id' not in session or 'pending_tx' not in session:
        flash("No pending transaction found.", "warning")
        return redirect(url_for('send_money'))

    user_id = session['user_id']
    pending = session['pending_tx']
    amount = Decimal(pending['amount'])

    # fetch sender mpin hash & balance for final checks
    conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT b.wallet_balance, b.mpin_hash FROM bank_accounts b WHERE b.user_id = %s", (user_id,))
    sender = cursor.fetchone()
    conn.close()

    if not sender or not sender.get('mpin_hash'):
        flash("Set MPIN first to complete transactions.", "warning")
        return redirect(url_for('set_mpin'))

    if request.method == 'POST':
        entered_mpin = request.form.get('mpin', '').strip()
        if not entered_mpin:
            flash("Enter MPIN.", "danger")
            return redirect(url_for('send_money_confirm'))

        # verify mpin
        if not check_password_hash(sender['mpin_hash'], entered_mpin):
            flash("Incorrect MPIN.", "danger")
            return redirect(url_for('send_money_confirm'))

        # Double-check balance
        if sender['wallet_balance'] < amount:
            flash("Insufficient balance.", "danger")
            session.pop('pending_tx', None)
            return redirect(url_for('send_money'))

        # Perform atomic DB transaction (deduct + credit + insert tx record)
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        try:
            conn.start_transaction()
            cursor = conn.cursor()

            # Deduct from sender
            cursor.execute("UPDATE bank_accounts SET wallet_balance = wallet_balance - %s WHERE user_id = %s", (str(amount), user_id))
            # Credit receiver
            cursor.execute("UPDATE bank_accounts SET wallet_balance = wallet_balance + %s WHERE user_id = %s", (str(amount), pending['to_user_id']))

            # Create tx id
            tx_id = uuid.uuid4().hex[:20]
            cursor.execute("""
              INSERT INTO transactions (tx_id, from_user_id, to_user_id, to_upi, amount, note, status)
              VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (tx_id, user_id, pending['to_user_id'], pending['to_upi'], str(amount), pending.get('note',''), 'SUCCESS'))

            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.close()
            flash("Transaction failed. Please try again.", "danger")
            print("TX ERROR:", e)
            return redirect(url_for('send_money'))
        finally:
            conn.close()

        # send emails: sender and receiver
        # fetch receiver email and sender username
        conn2 = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cur2 = conn2.cursor(dictionary=True)
        cur2.execute("SELECT email FROM users WHERE id = %s", (pending['to_user_id'],))
        rec = cur2.fetchone()
        cur2.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        s = cur2.fetchone()
        conn2.close()

        # prepare email content (use your send_email function)
        # send_email_transaction(s['email'], "Payment Sent - PayShield",
        #            f"Hello {s['username']},\n\nYou have sent ₹{amount} to {pending['to_upi']} (tx: {tx_id}).\nNote: {pending.get('note','')}\n\n- PayShield")
        # if rec:
        #     send_email_transaction(rec['email'], "Payment Received - PayShield",
        #                f"Hello,\n\nYou have received ₹{amount} from {s['username']} (UPI: {s['email']}).\nNote: {pending.get('note','')}\n\n- PayShield")
        send_payment_emails(
        sender_email=s.get('email'),
        sender_name=s.get('username'),
        sender_upi=s.get('upi_id'),
        receiver_email=rec.get('email'),
        receiver_name=rec.get('username'),
        receiver_upi=rec.get('to_upi'),
        amount=amount,
        note=pending.get('note', ''),
        tx_id=tx_id
    )
        # clear pending_tx
        session.pop('pending_tx', None)

        flash(f"₹{amount} sent successfully (Tx ID: {tx_id}).", "success")
        return redirect(url_for('transaction_success', tx_id=tx_id))


    # GET -> render confirm page
    return render_template('send_money_confirm.html', pending=pending, amount=amount)


@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    uid = session['user_id']
    conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions WHERE from_user_id = %s OR to_user_id = %s ORDER BY created_at DESC LIMIT 50", (uid, uid))
    txs = cursor.fetchall()
    conn.close()
    return render_template('transactions.html', txs=txs)

#transaction history
@app.route('/transaction_history')
def transaction_history():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = mysql.connector.connect(
        host='localhost', user='root', password='', database='payshield'
    )
    cursor = conn.cursor(dictionary=True)

    # Fetch transactions where the user is sender or receiver
    cursor.execute("""
        SELECT 
            t.id, 
            t.amount, 
            t.note, 
            t.status, 
            t.created_at,
            u1.username AS from_user_id,
            u2.username AS to_user_id
        FROM transactions t
        JOIN users u1 ON t.from_user_id = u1.id
        JOIN users u2 ON t.to_user_id = u2.id
        WHERE t.from_user_id = %s OR t.to_user_id = %s
        ORDER BY t.created_at DESC
    """, (user_id, user_id))

    transactions = cursor.fetchall()
    conn.close()

    return render_template('transaction_history.html', transactions=transactions)

@app.route('/transaction_success/<tx_id>')
def transaction_success(tx_id):
    conn = mysql.connector.connect(
        host='localhost', user='root', password='', database='payshield'
    )
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        t.tx_id, 
        t.amount, 
        t.note, 
        t.created_at, 

        s.username AS sender_name, 
        s.email AS sender_email,
        sb.upi_id AS sender_upi,

        r.username AS receiver_name, 
        r.email AS receiver_email,
        rb.upi_id AS receiver_upi

    FROM transactions t
    JOIN users s ON t.from_user_id = s.id
    JOIN users r ON t.to_user_id = r.id
    JOIN bank_accounts sb ON s.id = sb.user_id
    JOIN bank_accounts rb ON r.id = rb.user_id
    WHERE t.tx_id = %s
""", (tx_id,))
    tx = cursor.fetchone()
    conn.close()

    if not tx:
        flash("Transaction not found!", "danger")
        return redirect(url_for('dashboard'))

    return render_template('transaction_success.html', tx=tx)

if __name__ == '__main__':
    app.run(debug=True)



