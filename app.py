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

#ADMIN============================
from functools import wraps
import bcrypt

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Admin login required.", "warning")
            return redirect(url_for('admin_login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def get_db():
    return mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password', '').encode()

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM admin_users WHERE email=%s", (email,))
        admin = cur.fetchone()
        conn.close()

        if admin and bcrypt.checkpw(password, admin['password_hash'].encode()):
            session['admin_id'] = admin['id']
            session['admin_email'] = admin['email']
            session['admin_name'] = admin['username']
            session['is_super'] = bool(admin['is_super'])
            flash("Admin logged in.", "success")
            return redirect(request.args.get('next') or url_for('admin_dashboard'))
        flash("Invalid email or password.", "danger")
    return render_template('admin/login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    session.pop('admin_name', None)
    session.pop('is_super', None)
    flash("Admin logged out.", "info")
    return redirect(url_for('admin_login'))
# Dashboard
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS total FROM users"); users = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM transactions"); tx = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM risk_transactions"); risk = cur.fetchone()['total']
    conn.close()
    stats = {'users': users, 'transactions': tx, 'risk': risk}
    return render_template('admin/dashboard.html', stats=stats)

# Users list + actions
@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username, email, created_at FROM users ORDER BY id DESC LIMIT 500")
    rows = cur.fetchall(); conn.close()
    return render_template('admin/users.html', users=rows)

@app.route('/admin/user/toggle_block/<int:uid>', methods=['POST'])
@admin_required
def admin_user_toggle_block(uid):
    if not session.get('is_super'):
        flash("Only super admin allowed.", "danger")
        return redirect(url_for('admin_users'))
    conn = get_db(); cur = conn.cursor()
    # simple blocked flag: if column 'is_blocked' exists use it, else create soft block via update (safe approach below assumes column)
    try:
        cur.execute("UPDATE users SET is_blocked = NOT IFNULL(is_blocked,0) WHERE id=%s", (uid,))
    except Exception:
        # fallback: set a 'is_blocked' column if doesn't exist
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked TINYINT(1) DEFAULT 0")
        cur.execute("UPDATE users SET is_blocked = 1 WHERE id=%s", (uid,))
    conn.commit(); conn.close()
    flash("User block toggled.", "success")
    return redirect(url_for('admin_users'))

# Transactions list
@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
      SELECT t.tx_id, t.amount, t.status, t.created_at,
             s.username AS sender, r.username AS receiver, t.to_upi
      FROM transactions t
      LEFT JOIN users s ON t.from_user_id = s.id
      LEFT JOIN users r ON t.to_user_id = r.id
      ORDER BY t.created_at DESC LIMIT 500
    """)
    rows = cur.fetchall(); conn.close()
    return render_template('admin/transactions.html', txs=rows)

# Risk / Fraud list
@app.route('/admin/fraud')
@admin_required
def admin_fraud():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
      SELECT rt.id, rt.from_user_id, ru.username AS from_user, rt.to_user_id, tu.username AS to_user,
             rt.to_upi, rt.amount, rt.note, rt.status, rt.created_at
      FROM risk_transactions rt
      LEFT JOIN users ru ON rt.from_user_id = ru.id
      LEFT JOIN users tu ON rt.to_user_id = tu.id
      ORDER BY rt.created_at DESC LIMIT 200
    """)
    risk_txs = cur.fetchall()
    cur.execute("SELECT * FROM security_logs ORDER BY timestamp DESC LIMIT 200")
    logs = cur.fetchall()
    conn.close()
    return render_template('admin/fraud.html', risk_txs=risk_txs, logs=logs)

# View single risk tx
@app.route('/admin/fraud/view/<int:rt_id>')
@admin_required
def admin_view_risk(rt_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM risk_transactions WHERE id=%s", (rt_id,))
    rtx = cur.fetchone()
    cur.execute("SELECT id, username, email FROM users WHERE id IN (%s, %s)", (rtx['from_user_id'], rtx['to_user_id']))
    users = cur.fetchall()
    cur.execute("SELECT * FROM security_logs WHERE user_id IN (%s, %s) ORDER BY timestamp DESC LIMIT 50", (rtx['from_user_id'], rtx['to_user_id']))
    logs = cur.fetchall()
    conn.close()
    # fetch users separately to avoid mismatch
    conn2 = get_db(); cur2 = conn2.cursor(dictionary=True)
    cur2.execute("SELECT username,email FROM users WHERE id=%s", (rtx['from_user_id'],)); sender = cur2.fetchone()
    cur2.execute("SELECT username,email FROM users WHERE id=%s", (rtx['to_user_id'],)); receiver = cur2.fetchone()
    conn2.close()
    return render_template('admin/view_risk.html', rtx=rtx, sender=sender, receiver=receiver, logs=logs)

# Action on risk tx
@app.route('/admin/fraud/action/<int:rt_id>', methods=['POST'])
@admin_required
def admin_action_risk(rt_id):
    action = request.form.get('action')
    conn = get_db(); cur = conn.cursor()
    if action == 'approve':
        cur.execute("UPDATE risk_transactions SET status='APPROVED' WHERE id=%s", (rt_id,))
    elif action == 'block':
        cur.execute("UPDATE risk_transactions SET status='REJECTED' WHERE id=%s", (rt_id,))
        cur.execute("INSERT INTO fraud_checks (user_id, tx_id, reason, status) VALUES ((SELECT from_user_id FROM risk_transactions WHERE id=%s), %s, %s, 'BLOCKED')",
                    (rt_id, f"RT{rt_id}", "Admin blocked"))
    else:
        cur.execute("UPDATE risk_transactions SET status='PENDING' WHERE id=%s", (rt_id,))
    conn.commit(); conn.close()
    flash("Action applied.", "success")
    return redirect(url_for('admin_view_risk', rt_id=rt_id))

# Export risk csv
@app.route('/admin/fraud/export')
@admin_required
def admin_export_risk_csv():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
      SELECT rt.id, rt.from_user_id, ru.username AS from_user, ru.email AS from_email,
             rt.to_user_id, tu.username AS to_user, tu.email AS to_email,
             rt.to_upi, rt.amount, rt.note, rt.status, rt.created_at
      FROM risk_transactions rt
      LEFT JOIN users ru ON rt.from_user_id = ru.id
      LEFT JOIN users tu ON rt.to_user_id = tu.id
      ORDER BY rt.created_at DESC
    """)
    rows = cur.fetchall(); conn.close()
    from io import StringIO
    import csv
    si = StringIO(); cw = csv.writer(si)
    cw.writerow(['id','from_user_id','from_user','from_email','to_user_id','to_user','to_email','to_upi','amount','note','status','created_at'])
    for r in rows:
        cw.writerow([r.get(k) for k in ['id','from_user_id','from_user','from_email','to_user_id','to_user','to_email','to_upi','amount','note','status','created_at']])
    output = si.getvalue()
    from flask import Response
    return Response(output, mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=risk_transactions.csv"})

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
    
from datetime import datetime, timedelta, date

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

############################################
# SEND MONEY CONFIRM (with Fraud Detection)
############################################
@app.route('/send_money_confirm', methods=['GET', 'POST'])
def send_money_confirm():
    if 'user_id' not in session or 'pending_tx' not in session:
        flash("No pending transaction found.", "warning")
        return redirect(url_for('send_money'))

    user_id = session['user_id']
    pending = session['pending_tx']
    amount = Decimal(pending['amount'])

    # Fetch stored MPIN + balance
    conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT b.wallet_balance, b.mpin_hash FROM bank_accounts b WHERE b.user_id=%s", (user_id,))
    sender = cursor.fetchone()
    conn.close()

    if not sender or not sender.get('mpin_hash'):
        flash("Please set MPIN first.", "warning")
        return redirect(url_for('set_mpin'))

    if request.method == 'POST':

        # ---------- MPIN Validation ----------
        entered_mpin = request.form.get('mpin', '').strip()
        if not check_password_hash(sender['mpin_hash'], entered_mpin):
            flash("Incorrect MPIN!", "danger")
            return redirect(url_for('send_money_confirm'))

        # ---------- Balance Check ----------
        if sender['wallet_balance'] < amount:
            flash("Insufficient Wallet Balance.", "danger")
            session.pop('pending_tx', None)
            return redirect(url_for('send_money'))

        # ---------- FRAUD DETECTION ----------
        reasons = []
        risk_score = 0

        # Get true IP (proxy safe)
        def get_client_ip():
            if request.headers.get('X-Forwarded-For'):
                return request.headers.get('X-Forwarded-For').split(',')[0]
            return request.remote_addr

        user_ip = get_client_ip()
        user_device = request.user_agent.string

        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT last_login_ip, device_fingerprint FROM users WHERE id=%s", (user_id,))
        user_profile = cursor.fetchone()
        conn.close()

        # 1️⃣ New IP Detection
        if user_profile.get('last_login_ip') and user_profile['last_login_ip'] != user_ip:
            risk_score += 2
            reasons.append(f"New IP detected")

        # 2️⃣ New Device Detection
        if user_profile.get('device_fingerprint') and user_profile['device_fingerprint'] != user_device:
            risk_score += 3
            reasons.append("New Device detected")

        # 3️⃣ High Amount Flag
        if amount > Decimal("20000"):
            risk_score += 2
            reasons.append("High Value Transaction")

        # 4️⃣ Decision System
        if risk_score >= 3:
            session['risk_tx'] = pending
            generate_and_send_risk_otp(session['email'], session.get('username', "User"))
            flash(f"⚠ Security Verification Required: {', '.join(reasons)}", "warning")
            return redirect(url_for("verify_risk_otp"))

        # ---------- TRANSACTION PROCESS ----------
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        try:
            conn.start_transaction()
            cursor = conn.cursor()

            # Deduct from sender
            cursor.execute("UPDATE bank_accounts SET wallet_balance = wallet_balance - %s WHERE user_id=%s",
                           (str(amount), user_id))

            # Credit receiver
            cursor.execute("UPDATE bank_accounts SET wallet_balance = wallet_balance + %s WHERE user_id=%s",
                           (str(amount), pending['to_user_id']))

            # Save Tx ID
            tx_id = uuid.uuid4().hex[:20]
            cursor.execute("""
                INSERT INTO transactions (tx_id, from_user_id, to_user_id, to_upi, amount, note, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (tx_id, user_id, pending['to_user_id'], pending['to_upi'], str(amount), pending.get('note',''), 'SUCCESS'))

            conn.commit()

        except Exception as e:
            conn.rollback()
            flash("Transaction Failed! Try again later.", "danger")
            print("Error:", e)
            return redirect(url_for('send_money'))

        finally:
            conn.close()

        # ---------- UPDATE LAST DEVICE + IP ----------
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login_ip=%s, device_fingerprint=%s WHERE id=%s",
                       (user_ip, user_device, user_id))
        conn.commit()
        conn.close()

        # ---------- Send Email Notifications ----------
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT username, email FROM users WHERE id=%s", (user_id,))
        sender_info = cursor.fetchone()

        cursor.execute("SELECT username, email FROM users WHERE id=%s", (pending['to_user_id'],))
        receiver_info = cursor.fetchone()

        conn.close()

        send_payment_emails(
            sender_email=sender_info['email'],
            sender_name=sender_info['username'],
            sender_upi=pending['to_upi'],
            receiver_email=receiver_info['email'],
            receiver_name=receiver_info['username'],
            receiver_upi=pending['to_upi'],
            amount=amount,
            note=pending.get('note',''),
            tx_id=tx_id
        )

        session.pop('pending_tx', None)
        flash("Payment Successful 🎉", "success")

        return redirect(url_for('transaction_success', tx_id=tx_id))

    return render_template('send_money_confirm.html', pending=pending, amount=amount)


def log_security_event(user_id, event_type, ip=None, device=None, score=0):
    try:
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO security_logs (user_id, event_type, ip_address, device_info, risk_score)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, event_type, ip, device, score))
        conn.commit()
    except Exception as e:
        print("log_security_event error:", e)
    finally:
        try: conn.close()
        except: pass

@app.route('/verify_risk_otp', methods=['GET', 'POST'])
def verify_risk_otp():
    # check risk_tx_id in session
    risk_tx_id = session.get('risk_tx_id')
    if not risk_tx_id:
        flash("No pending risky transaction found.", "warning")
        return redirect(url_for('send_money'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        # verify against otp_logs table
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM otp_logs WHERE action_type='RISK_TX' AND is_used=0 ORDER BY id DESC LIMIT 1")
        otp_row = cur.fetchone()
        conn.close()

        if not otp_row:
            flash("OTP not found. Request a new one.", "danger")
            return redirect(url_for('send_money'))

        expires = otp_row['expires_at']
        if datetime.utcnow() > expires:
            flash("OTP expired. Please start the transfer again.", "danger")
            # mark expired and cleanup risk tx
            conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
            cur = conn.cursor()
            cur.execute("UPDATE otp_logs SET is_used=1 WHERE id = %s", (otp_row['id'],))
            cur.execute("UPDATE risk_transactions SET status='EXPIRED' WHERE id = %s", (risk_tx_id,))
            conn.commit()
            conn.close()
            session.pop('risk_tx_id', None)
            session.pop('pending_tx', None)
            return redirect(url_for('send_money'))

        if entered != otp_row['otp_code']:
            # increment attempts? simple feedback
            flash("Incorrect OTP. Try again.", "danger")
            return redirect(url_for('verify_risk_otp'))

        # OTP correct: mark used and complete the pending risk transaction
        try:
            conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
            cur = conn.cursor(dictionary=True)
            # get risk tx
            cur.execute("SELECT * FROM risk_transactions WHERE id = %s AND status='PENDING'", (risk_tx_id,))
            rtx = cur.fetchone()
            if not rtx:
                flash("Pending transaction not found.", "danger")
                conn.close()
                session.pop('risk_tx_id', None)
                return redirect(url_for('send_money'))

            # perform atomic tx (deduct/credit and insert into transactions)
            conn2 = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
            cur2 = conn2.cursor()
            conn2.start_transaction()
            # deduct
            cur2.execute("UPDATE bank_accounts SET wallet_balance = wallet_balance - %s, daily_spent = daily_spent + %s WHERE user_id = %s", (str(rtx['amount']), str(rtx['amount']), rtx['from_user_id']))
            # credit
            cur2.execute("UPDATE bank_accounts SET wallet_balance = wallet_balance + %s WHERE user_id = %s", (str(rtx['amount']), rtx['to_user_id']))
            tx_id = uuid.uuid4().hex[:20]
            cur2.execute("""INSERT INTO transactions (tx_id, from_user_id, to_user_id, to_upi, amount, note, status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'SUCCESS')""", (tx_id, rtx['from_user_id'], rtx['to_user_id'], rtx['to_upi'], str(rtx['amount']), rtx['note']))
            # update risk_transactions to APPROVED
            cur2.execute("UPDATE risk_transactions SET status='APPROVED' WHERE id = %s", (risk_tx_id,))
            conn2.commit()
            conn2.close()

            # mark otp used
            cur.execute("UPDATE otp_logs SET is_used=1 WHERE id = %s", (otp_row['id'],))
            conn.commit()
            conn.close()
        except Exception as e:
            print("verify_risk_otp error:", e)
            try:
                conn2.rollback()
                conn2.close()
            except:
                pass
            flash("Transaction failed during verification. Try again.", "danger")
            return redirect(url_for('send_money'))
        finally:
            # cleanup session
            session.pop('risk_tx_id', None)
            session.pop('pending_tx', None)

        # fetch s/rec and upis and send email (same as above)
        conn3 = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cur3 = conn3.cursor(dictionary=True)
        cur3.execute("SELECT username, email FROM users WHERE id = %s", (rtx['from_user_id'],))
        s = cur3.fetchone()
        cur3.execute("SELECT username, email FROM users WHERE id = %s", (rtx['to_user_id'],))
        rec = cur3.fetchone()
        cur3.execute("SELECT upi_id FROM bank_accounts WHERE user_id = %s", (rtx['from_user_id'],))
        s_upi = cur3.fetchone()
        cur3.execute("SELECT upi_id FROM bank_accounts WHERE user_id = %s", (rtx['to_user_id'],))
        r_upi = cur3.fetchone()
        conn3.close()

        sender_upi = s_upi['upi_id'] if s_upi else 'N/A'
        receiver_upi = r_upi['upi_id'] if r_upi else 'N/A'

        send_payment_emails(
            sender_email=s.get('email'),
            sender_name=s.get('username'),
            sender_upi=sender_upi,
            receiver_email=rec.get('email'),
            receiver_name=rec.get('username'),
            receiver_upi=receiver_upi,
            amount=rtx['amount'],
            note=rtx.get('note',''),
            tx_id=tx_id
        )

        flash("Transaction completed after verification.", "success")
        return redirect(url_for('transaction_success', tx_id=tx_id))

    # GET
    return render_template('verify_risk_otp.html')

def generate_and_send_risk_otp(user_id, user_email, username):
    otp = f"{random.randint(100000, 999999):06d}"
    expires = datetime.utcnow() + timedelta(minutes=3)
    # persist OTP in otp_logs table (safer than session)
    try:
        conn = mysql.connector.connect(host='localhost', user='root', password='', database='payshield')
        cur = conn.cursor()
        cur.execute("INSERT INTO otp_logs (user_id, otp_code, action_type, is_used, expires_at) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, otp, 'RISK_TX', False, expires))
        conn.commit()
    except Exception as e:
        print("generate_and_send_risk_otp db error:", e)
    finally:
        try: conn.close()
        except: pass

    subject = "PayShield — OTP to confirm your transaction"
    body = f"""Hello {username},

We detected a transaction that requires additional verification.

Your OTP is: {otp}
It will expire in 3 minutes.

If you didn't request this, contact support.

— PayShield Security
"""
    return send_email_transaction(user_email, subject, body)


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



