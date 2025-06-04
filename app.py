from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import secrets
import time
from functools import wraps
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'vygenerujte_silny_tajny_klic_pro_produkci')

DATABASE = 'users.db'
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.example.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))

# --- Dekorátory ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Pro přístup k této stránce se musíte přihlásit.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Pro přístup k této stránce se musíte přihlásit.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Pro přístup k této stránce nemáte dostatečná oprávnění.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Databázové funkce ---
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        first_name TEXT,
                        last_name TEXT,
                        email TEXT UNIQUE NOT NULL,
                        phone TEXT,
                        organization TEXT,
                        role TEXT DEFAULT 'user',
                        status TEXT DEFAULT 'pending',
                        password TEXT NOT NULL
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS reset_tokens (
                        email TEXT PRIMARY KEY,
                        token TEXT NOT NULL,
                        expiration REAL NOT NULL
                    )''')

        c.execute('SELECT COUNT(*) FROM users')
        if c.fetchone()[0] == 0 and os.path.exists('users.json'):
            try:
                with open('users.json', 'r', encoding='utf-8') as f:
                    users_data_from_json = json.load(f)
                    for user_json in users_data_from_json:
                        password_to_store = user_json.get('password')
                        if not password_to_store:
                            print(f"Chybí heslo pro uživatele {user_json.get('username')} v users.json, přeskočeno.")
                            continue
                        if not password_to_store.startswith(('pbkdf2:sha256:', 'scrypt:')):
                            print(f"VAROVÁNÍ: Heslo pro {user_json.get('username')} v users.json nevypadá jako hashované.")
                        c.execute('''INSERT INTO users
                                     (username, first_name, last_name, email, phone, organization, role, status, password)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (user_json.get('username'),
                                   user_json.get('first_name'),
                                   user_json.get('last_name'),
                                   user_json.get('email'),
                                   user_json.get('phone'),
                                   user_json.get('organization'),
                                   user_json.get('role', 'user'),
                                   user_json.get('status', 'pending'),
                                   password_to_store))
                conn.commit()
                print("Data z users.json byla importována.")
            except json.JSONDecodeError:
                print("Chyba při dekódování users.json.")
            except Exception as e:
                print(f"Nastala chyba při importu z users.json: {e}")
        conn.commit()

init_db()  # ZDE OPRAVA: inicializace DB při startu aplikace

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_username(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_email(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_user(user_data):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO users
                        (username, first_name, last_name, email, phone, organization, role, status, password)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (user_data['username'],
                       user_data['first_name'],
                       user_data['last_name'],
                       user_data['email'],
                       user_data.get('phone'),
                       user_data['organization'],
                       user_data['role'],
                       user_data['status'],
                       user_data['password']))
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise e

def update_user(user_data):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''UPDATE users SET
                     first_name = ?, last_name = ?, email = ?, phone = ?,
                     organization = ?, role = ?, status = ?, password = ?
                     WHERE username = ?''',
                  (user_data['first_name'],
                   user_data['last_name'],
                   user_data['email'],
                   user_data.get('phone'),
                   user_data['organization'],
                   user_data['role'],
                   user_data['status'],
                   user_data['password'],
                   user_data['username']))
        conn.commit()

# --- Funkce pro e-maily ---
def send_email(to, subject, message_body):
    if not all([EMAIL_USER, EMAIL_PASS, SMTP_SERVER, SMTP_PORT]):
        print("Chyba: E-mailové údaje nejsou plně nakonfigurovány v .env souboru.")
        flash("Systém odesílání e-mailů není správně nakonfigurován. Kontaktujte administrátora.", "danger")
        return False
    msg = MIMEText(message_body, 'html')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"E-mail odeslán na {to} s předmětem: {subject}")
        return True
    except Exception as e:
        print(f"Chyba při odesílání e-mailu na {to}: {e}")
        flash(f"Došlo k chybě při odesílání e-mailu. Zkuste to prosím později. ({e})", "danger")
        return False

# --- Routy ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email'].lower()
        organization = request.form['organization']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form.get("phone", "")

        parts = fullname.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        if password != confirm_password:
            flash("Hesla se neshodují.", "danger")
            return render_template('register.html',
                                   fullname=fullname,
                                   email=email,
                                   organization=organization,
                                   phone=phone)
        if len(password) < 8:
            flash("Heslo musí mít alespoň 8 znaků.", "danger")
            return render_template('register.html',
                                   fullname=fullname,
                                   email=email,
                                   organization=organization,
                                   phone=phone)
        if '@' not in email or '.' not in email.split('@')[-1]:
            flash("Zadejte platný e-mail.", "danger")
            return render_template('register.html',
                                   fullname=fullname,
                                   organization=organization,
                                   phone=phone)

        existing_user_email = get_user_by_email(email)
        if existing_user_email:
            flash("Tento e-mail je již registrován.", "warning")
            return render_template('register.html',
                                   fullname=fullname,
                                   organization=organization,
                                   phone=phone)

        existing_user_username = get_user_by_username(email)
        if existing_user_username:
            flash("Toto uživatelské jméno (e-mail) je již použito.", "warning")
            return render_template('register.html',
                                   fullname=fullname,
                                   organization=organization,
                                   phone=phone)

        user_data = {
            "username": email,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "organization": organization,
            "role": "user",
            "status": "pending",
            "password": generate_password_hash(password)
        }

        try:
            add_user(user_data)
            message_to_admin = (f"Nový uživatel {fullname} ({email}) čeká na schválení.<br>"
                                f"Můžete jej schválit v <a href='{url_for('admin', _external=True)}'>administraci</a>.")
            send_email(ADMIN_EMAIL, "Nová registrace čeká na schválení", message_to_admin)
            flash("Registrace byla úspěšně přijata. Váš účet čeká na schválení.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Chyba při registraci (duplicitní data). Zkuste to znovu.", "danger")
            return render_template('register.html',
                                   fullname=fullname,
                                   organization=organization,
                                   phone=phone)

    # GET
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        if user and check_password_hash(user['password'], password):
            if user.get('status') == 'approved':
                session['user'] = user['username']
                session['role'] = user.get('role', 'user')
                if session['role'] == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                error = 'Účet čeká na schválení administrátorem.'
        else:
            error = 'Neplatné přihlašovací údaje.'
    return render_template('login.html', error=error, forgot_error=None, forgot_success=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session.get('user'))

@app.route('/admin')
@admin_required
def admin():
    users = load_users()
    return render_template('admin.html', users=users)

@app.route('/admin/approve_user', methods=['POST'])
@admin_required
def approve_user():
    username = request.form['username']
    users = load_users()
    for user in users:
        if user['username'] == username:
            user['status'] = 'approved'
            save_users(users)
            send_email(user['email'],
                       'Registrace schválena',
                       'Váš účet byl aktivován. Nyní se můžete přihlásit.')
            break
    return redirect(url_for('admin'))

@app.route('/reject_user/<username>', methods=['POST'])
@admin_required
def reject_user(username):
    users = load_users()
    users = [u for u in users if u['username'] != username]
    save_users(users)
    return redirect(url_for('admin'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form['email'].lower()
        user = get_user_by_email(email)
        if not user:
            error = 'Takový e-mail není zaregistrován.'
            return render_template('login.html',
                                   error=None,
                                   forgot_error=error,
                                   forgot_success=None)
        token = secrets.token_urlsafe(16)
        expiration = time.time() + 3600  # platnost 1 hodina
        save_reset_token(email, token, expiration)
        reset_link = url_for('reset_password', token=token, _external=True)
        message_body = f"Klikněte na odkaz pro reset hesla: <a href='{reset_link}'>{reset_link}</a>"
        send_email(email, 'Reset hesla', message_body)
        success = 'Odkaz pro reset hesla byl odeslán na váš e-mail.'
        return render_template('login.html',
                               error=None,
                               forgot_error=None,
                               forgot_success=success)
    return redirect(url_for('login'))

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    token_data = load_reset_token_data(token)
    if not token_data or token_data.get('expiration', 0) < time.time():
        flash('Token pro reset hesla je neplatný nebo expiroval.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash('Hesla se neshodují.', 'danger')
            return render_template('reset_password.html', token=token)
        if len(new_password) < 8:
            flash('Heslo musí mít alespoň 8 znaků.', 'danger')
            return render_template('reset_password.html', token=token)
        email = token_data['email']
        user = get_user_by_email(email)
        user['password'] = generate_password_hash(new_password)
        update_user(user)
        delete_reset_token(email)
        flash('Heslo bylo úspěšně změněno. Přihlaste se prosím.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(debug=True)
