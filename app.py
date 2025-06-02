from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'tajny_klic'

USERS_FILE = 'users.json'
ADMIN_EMAIL = 'zdenekkalvach@gmail.com'


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def send_email(to, subject, message):
    FROM = 'tvuj@email.cz'
    PASSWORD = 'tvéheslo'
    smtp_server = 'smtp.seznam.cz'
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = FROM
    msg['To'] = to

    with smtplib.SMTP_SSL(smtp_server, 465) as server:
        server.login(FROM, PASSWORD)
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

        if password != confirm_password:
            return "Hesla se neshodují."

        users = load_users()
        username = email  # nebo generovat z jména

        if username in users:
            return "Tento email je již registrován."

        users[username] = {
            'fullname': fullname,
            'email': email,
            'organization': organization,
            'password': password,
            'approved': False
        }
        save_users(users)

        send_email(ADMIN_EMAIL, 'Nová registrace', f'Nový uživatel čeká na schválení: {fullname}, {email}')
        return "Registrace přijata. Po schválení administrátorem obdržíte přístup."

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        user = users.get(username)

        if not user:
            error = 'Uživatel nenalezen.'
        elif not user.get('approved'):
            error = 'Váš účet čeká na schválení. V případě potřeby kontaktujte administrátora: zdenekkalvach@gmail.com'
        elif user['password'] != password:
            error = 'Nesprávné heslo.'
        else:
            session['user'] = username
            return redirect(url_for('dashboard'))

    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return f"Vítejte, {session['user']}!"

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user' != 'admin@admin.cz':  # pevně daný admin účet, můžeš změnit
        return "Přístup zamítnut."

    users = load_users()

    if request.method == 'POST':
        username = request.form['approve']
        if username in users:
            users[username]['approved'] = True
            save_users(users)
            send_email(users[username]['email'], 'Registrace schválena', 'Váš účet byl aktivován. Nyní se můžete přihlásit.')

    return render_template('admin.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)
