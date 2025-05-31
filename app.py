from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
app.secret_key = 'tajny_klic'

USERS_FILE = 'users.json'
PROJECTS_FILE = 'projects.json'


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)


def load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_projects(projects):
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects, f, indent=4)


@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        if username in users:
            flash('Uživatelské jméno je již obsazené.')
            return redirect(url_for('register'))

        users[username] = {
            'password': generate_password_hash(password),
            'projects': []
        }
        save_users(users)
        flash('Registrace úspěšná. Nyní se přihlaste.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()
        user = users.get(username)

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Neplatné přihlašovací údaje.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    users = load_users()
    user_projects = users[username].get('projects', [])
    all_projects = load_projects()
    projects = [all_projects[pid] for pid in user_projects if pid in all_projects]
    return render_template('dashboard.html', username=username, projects=projects)


@app.route('/create_project', methods=['POST'])
def create_project():
    if 'username' not in session:
        return redirect(url_for('login'))
    title = request.form['title']
    project_id = f"prj_{len(os.urandom(4))}_{title.replace(' ', '_')}"
    username = session['username']

    projects = load_projects()
    projects[project_id] = {
        'title': title,
        'owner': username,
        'shared_with': [],
        'data': {}
    }
    save_projects(projects)

    users = load_users()
    users[username]['projects'].append(project_id)
    save_users(users)

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
