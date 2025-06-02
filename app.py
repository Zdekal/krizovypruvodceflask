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
        return []
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

        if any(u['email'] == email for u in users):
            return "Tento email je již registrován."

        user_data = {
            'username': email,
            'first_name': fullname.split()[0],
            'last_name': ' '.join(fullname.split()[1:]) if len(fullname.split()) > 1 else '',
            'email': email,
            'phone': request.form.get('phone', ''),
            'organization': organization,
            'role': 'user',
            'status': 'pending',
            'password': password
        }
        users.append(user_data)
        save_users(users)

        send_email(ADMIN_EMAIL, 'Nová registrace', f"Nový uživatel čeká na schválení: {fullname}, {email}")
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

@app.route('/admin', methods=['GET'])
def admin():
    if session.get('user') != 'admin@admin.cz':
        return "Přístup zamítnut."
    users = load_users()
    return render_template('admin_users.html', users=users)

@app.route('/admin/approve_user', methods=['POST'])
def approve_user():
    if session.get('user') != 'admin@admin.cz':
        return "Přístup zamítnut."
    username = request.form['username']
    users = load_users()
    for user in users:
        if user['username'] == username:
            user['status'] = 'approved'
            save_users(users)
            send_email(user['email'], 'Registrace schválena', 'Váš účet byl aktivován. Nyní se můžete přihlásit.')
            break
    return redirect(url_for('admin'))

@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    if session.get('user') != 'admin@admin.cz':
        return "Přístup zamítnut."
    username = request.form['username']
    users = load_users()
    users = [u for u in users if u['username'] != username]
    save_users(users)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
