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


app = Flask(__name__)
app.secret_key = "secret123"

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="otp_system1"
)
cursor = db.cursor()

# Send OTP Email
def send_otp(email, otp):
    sender_email = ""      # your gmail
    sender_password =""   # your gmail app password
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
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])

        cursor.execute("SELECT id, password FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and user[1] == password:
            otp = str(random.randint(100000, 999999))
            expires_at = datetime.now() + timedelta(minutes=5)

            cursor.execute("INSERT INTO otp_logs (user_id, otp_code, expires_at) VALUES (%s, %s, %s)",
                           (user[0], otp, expires_at))
            db.commit()

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
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', email=session['email'])


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
        database='otp_system1'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
    "SELECT id, username, email, mobileno, created_at FROM users WHERE email = %s",
    (user_email,)
)

    user = cursor.fetchone()
    conn.close()

    return render_template('profile.html', user=user)

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
        database='otp_system1'
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

    # Fetch account info
    cursor.execute("SELECT * FROM bank_accounts WHERE user_id = %s", (user_id,))
    account = cursor.fetchone()
    conn.close()

    return render_template('create_bank_account.html', account=account)

# #upi qr
@app.route('/upi_qr/<upi_id>')
def upi_qr(upi_id):
    upi_link = f"upi://pay?pa={upi_id}&pn=PayShield&cu=INR"
    qr = qrcode.make(upi_link)
    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

# 📤 Route to share QR + UPI link (this is the new one)
@app.route('/share_qr/<upi_id>')
def share_qr(upi_id):
    upi_link = f"upi://pay?pa={upi_id}&pn=PayShield&cu=INR"

    # Create base64 QR image to show in HTML
    qr = qrcode.make(upi_link)
    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    qr_base64 = base64.b64encode(img_io.read()).decode('utf-8')

    return render_template('share_qr.html', upi_link=upi_link, qr_base64=qr_base64)

#wallet email otp
def send_email(to_email, subject, otp):
    sender_email = ""
    sender_password = ""  # Use App Password (not your real one)

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
            <img src="https://github.com/dhrumildhameliya/PayShield/blob/main/static/logo.svg" alt="PayShield Logo" width="60" style="vertical-align: middle; margin-right: 8px;">
            <span style="font-size: 22px; font-weight: bold;">PayShield Security</span>
          </td>
        </tr>

        <tr>
          <td style="padding: 30px;">
            <h2 style="color: #333;">Wallet Verification OTP</h2>
            <p style="color: #555; font-size: 16px;">
              Dear User,<br><br>
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
    sender_email = ""  # change to your Gmail
    sender_password = ""  # use your App Password, not your login password

    msg = MIMEMultipart("alternative")
    msg["From"] = f"PayShield <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = "🎉 Wallet Created Successfully | PayShield"

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif; background-color:#f4f7fb; margin:0; padding:0;">
      <div style="max-width:600px;margin:30px auto;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);padding:20px;">
        <div style="text-align:center;">
          <img src="{{ url_for('static', filename='logo.svg') }}" alt="PayShield" style="width:120px;margin-bottom:10px;">
          <h2 style="color:#0066cc;">Your Wallet is Ready! 🎉</h2>
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
        host='localhost', user='root', password='', database='otp_system1'
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
                host='localhost', user='root', password='', database='otp_system1'
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
            return redirect(url_for('create_bank_account'))
        else:
            flash("Invalid OTP. Try again.", "danger")
            return redirect(url_for('wallet_verify'))

    return render_template('wallet_verify.html')


if __name__ == '__main__':
    app.run(debug=True)



