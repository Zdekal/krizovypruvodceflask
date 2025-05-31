from flask import Flask, render_template, request, redirect, url_for, session
import json
import os

app = Flask(__name__)
app.secret_key = 'tajny_klic'

USERS_FILE = 'users.json'
PROJECTS_FILE = 'projects.json'


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            # převod seznamu na slovník podle username
            return {u['username']: u for u in data}
        return data


def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        user = users.get(username)
        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Neplatné přihlašovací údaje'
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        if username in users:
            error = 'Uživatel již existuje'
        else:
            users[username] = {
                'password': request.form['password'],
                'first_name': request.form['first_name'],
                'last_name': request.form['last_name'],
                'email': request.form['email'],
                'phone': request.form['phone'],
                'organization': request.form.get('organization', ''),
                'is_approved': False,
                'is_admin': False
            }
            save_users(users)
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/dashboard')
def dashboa
