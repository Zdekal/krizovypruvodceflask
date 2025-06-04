from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import secrets
import time

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'tajny_klic')

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
        conn.commit()

def load_users():
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
                'status': row[7],
                'password': row[8]
            } for row in c.fetchall()
        ]
    return users

def save_users(users):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users')
        for user in users:
            c.execute('''INSERT OR REPLACE INTO users 
                (username, first_name, last_name, email, phone, organization, role, status, password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user['username'], user['first_name'], user['last_name'], user['email'],
                 user['phone'], user['organization'], user['role'], user['status'], user['password']))
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

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        organization = request.form['organization']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password or len(password) < 8 or '@' not in email:
            return "Hesla se neshodují nebo údaje nejsou platné."

        users = load_users()

        if any(u['email'] == email for u in users):
            return "Tento email je již registrován."

        user_data = {
            "username": email,
            "first_name": fullname.split()[0],
            "last_name": ' '.join(fullname.split()[1:]) if len(fullname.split()) > 1 else '',
            "email": email,
            "phone": request.form.get("phone", ""),
            "organization": organization,
            "role": "user",
            "status": "pending",
            "password": generate_password_hash(password)
        }
        users.append(user_data)
        save_users(users)

        send_email(ADMIN_EMAIL, "Nová registrace", f"Nový uživatel čeká na schválení: {fullname}, {email}")
        return "Registrace přijata. Po schválení administrátorem obdržíte přístup."

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        user = next((u for u in users if u['username'] == username), None)

        if not user:
            error = 'Uživatel nenalezen.'
        elif user['status'] != 'approved':
            error = 'Váš účet čeká na schválení. V případě potřeby kontaktujte administrátora: zdenekkalvach@gmail.com'
        elif not check_password_hash(user['password'], password):
            error = 'Nesprávné heslo.'
        else:
            session['user'] = username
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('dashboard'))

    return render_template('login.html', error=error)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    forgot_error = None
    forgot_success = None
    if request.method == 'POST':
        email = request.form['
