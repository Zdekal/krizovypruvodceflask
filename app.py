from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_wtf.csrf import CSRFProtect
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import secrets
import time
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'tajny_klic')
csrf = CSRFProtect(app)

DATABASE = 'users.db'
ADMIN_EMAIL = 'zdenekkalvach@gmail.com'
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.seznam.cz')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            organization TEXT,
            role TEXT,
            status TEXT,
            password TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS reset_tokens (
            email TEXT PRIMARY KEY,
            token TEXT,
            expiration REAL
        )''')
        c.execute('SELECT COUNT(*) FROM users')
        if c.fetchone()[0] == 0 and os.path.exists('users.json'):
            import json
            with open('users.json', 'r') as f:
                users = json.load(f)
            for user in users:
                c.execute('''INSERT INTO users 
                    (username, first_name, last_name, email, phone, organization, role, status, password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (user['username'], user['first_name'], user['last_name'], user['email'],
                     user['phone'], user['organization'], user['role'], user['status'], user['password']))
        conn.commit()

def get_user_by_email(email):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = c.fetchone()
        if row:
            return {
                'username': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'email': row[3],
                'phone': row[4],
                'organization': row[5],
                'role': row[6],
                'status': row[7],
                'password': row[8]
            }
    return None

def update_user_password(email, password):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET password = ? WHERE email = ?', (password, email))
        conn.commit()

def save_reset_token(email, token, expiration):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO reset_tokens (email, token, expiration) VALUES (?, ?, ?)',
                  (email, token, expiration))
        conn.commit()

def load_reset_token(email):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('SELECT token, expiration FROM reset_tokens WHERE email = ?', (email,))
        result = c.fetchone()
        return {'token': result[0], 'expiration': result[1]} if result else None

def delete_reset_token(email):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM reset_tokens WHERE email = ?', (email,))
        conn.commit()

def send_email(to, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/')
def index():
    # Automaticky přihlásí administrátora pro localhost
    if request.remote_addr == '127.0.0.1':
        session['user'] = 'zdenekkalvach@gmail.com'
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        organization = request.form['organization']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not validate_email(email):
            return render_template('register.html', error="Neplatný formát e-mailu.")
        if password != confirm_password:
            return render_template('register.html', error="Hesla se neshodují.")
        if len(password) < 8:
            return render_template('register.html', error="Heslo musí mít alespoň 8 znaků.")

        user = get_user_by_email(email)
        if user:
            return render_template('register.html', error="Tento e-mail je již registrován.")

        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO users 
                (username, first_name, last_name, email, phone, organization, role, status, password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (email, fullname.split()[0], ' '.join(fullname.split()[1:]) if len(fullname.split()) > 1 else '',
                 email, request.form.get("phone", ""), organization, "user", "pending", generate_password_hash(password)))
            conn.commit()

        try:
            send_email(ADMIN_EMAIL, "Nová registrace", f"Nový uživatel čeká na schválení: {fullname}, {email}")
            return render_template('register.html', success="Registrace přijata. Po schválení administrátorem obdržíte přístup.")
        except Exception:
            return render_template('register.html', error="Chyba při odesílání e-mailu. Zkuste to znovu později.")

    return render_template('register.html', error=None, success=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_email(username)

        if not user:
            error = 'Uživatel nenalezen.'
        elif user['status'] != 'approved':
            error = 'Váš účet čeká na schválení. Kontaktujte administrátora: zdenekkalvach@gmail.com'
        elif not check_password_hash(user['password'], password):
            error = 'Nesprávné heslo.'
        else:
            session['user'] = username
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('dashboard'))

    return render_template('login.html', error=error, forgot_error=None, forgot_success=None, csrf_token=app.jinja_env.globals['csrf_token']())

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    forgot_error = None
    forgot_success = None
    if request.method == 'POST':
        email = request.form['email']
        user = get_user_by_email(email)

        if not user:
            forgot_error = 'E-mail nenalezen.'
        else:
            token = secrets.token_urlsafe(32)
            expiration = time.time() + 3600
            save_reset_token(email, token, expiration)

            try:
                reset_url = url_for('reset_password', token=token, _external=True)
                send_email(
                    email,
                    "Obnova hesla – Krizový průvodce",
                    f"Pro obnovu hesla klikněte na tento odkaz: {reset_url}\nOdkaz je platný 1 hodinu."
                )
                forgot_success = 'Odkaz pro obnovu hesla byl odeslán na váš e-mail.'
            except Exception:
                forgot_error = 'Chyba při odesílání e-mailu. Zkuste to znovu později.'

    return render_template('login.html', forgot_error=forgot_error, forgot_success=forgot_success, error=None, csrf_token=app.jinja_env.globals['csrf_token']())

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    error = None
    success = None
    email = None

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('SELECT email, expiration FROM reset_tokens WHERE token = ?', (token,))
        result = c.fetchone()
        if result and result[1] > time.time():
            email = result[0]
        else:
            error = 'Neplatný nebo vypršelý odkaz pro obnovu hesla.'

    if request.method == 'POST' and email:
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            error = 'Hesla se neshodují.'
        elif len(new_password) < 8:
            error = 'Heslo musí mít alespoň 8 znaků.'
        else:
            update_user_password(email, generate_password_hash(new_password))
            delete_reset_token(email)
            success = 'Heslo bylo úspěšně změněno. Přihlaste se.'

    return render_template('reset_password.html', error=error, success=success, token=token)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['user'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET'])
def admin():
    if 'user' not in session or get_user_by_email(session['user'])['role'] != 'admin':
        return "Přístup zamítnut.", 403
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        users = [
            {
                'username': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'email': row[3],
                'phone': row[4],
                'organization': row[5],
                'role': row[6],
                'status': row[7]
            } for row in c.fetchall()
        ]
    return render_template('admin.html', users=users)

@app.route('/admin/approve_user', methods=['POST'])
def approve_user():
    if 'user' not in session or get_user_by_email(session['user'])['role'] != 'admin':
        return "Přístup zamítnut.", 403
    username = request.form['username']
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET status = ? WHERE username = ?', ('approved', username))
        conn.commit()
        user = get_user_by_email(username)
        if user:
            send_email(user['email'], 'Registrace schválena', 'Váš účet byl aktivován. Nyní se můžete přihlásit.')
    return redirect(url_for('admin'))

@app.route('/admin/reject_user/<username>', methods=['POST'])
def reject_user(username):
    if 'user' not in session or get_user_by_email(session['user'])['role'] != 'admin':
        return "Přístup zamítnut.", 403
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
    return redirect(url_for('admin'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
