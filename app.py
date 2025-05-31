
from flask import Flask, render_template, request, redirect, session, url_for
import json
import os

app = Flask(__name__)
app.secret_key = 'tajnyklic'

USERS_FILE = 'users.json'
PROJECTS_FILE = 'projects.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and user['password'] == password:
            session['user'] = username
            return redirect(url_for('dashboard'))
        return 'Neplatné přihlašovací údaje'
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        if username in users:
            return 'Uživatel již existuje'
        users[username] = {
            'password': request.form['password'],
            'name': request.form['name'],
            'surname': request.form['surname'],
            'email': request.form['email'],
            'phone': request.form.get('phone', ''),
            'organization': request.form.get('organization', ''),
            'approved': False
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/admin/users')
def admin_users():
    if session.get('user') != 'admin':
        return 'Přístup zamítnut'
    users = load_users()
    return render_template('admin_users.html', users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
