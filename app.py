from flask import Flask, render_template, request, redirect, session, url_for
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'tajny_klic'  # bezpečnostní klíč pro session

# Cesta k souboru s krizovým štábem
DATA_FILE = 'KŠ.xlsx'

# Cesta k "databázi" uživatelů
USERS_FILE = 'users.csv'
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username", "password"]).to_csv(USERS_FILE, index=False)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = pd.read_csv(USERS_FILE)
        username = request.form['username']
        password = request.form['password']
        if ((users['username'] == username) & (users['password'] == password)).any():
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Nesprávné údaje')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = pd.read_csv(USERS_FILE)
        username = request.form['username']
        password = request.form['password']
        if username in users['username'].values:
            return render_template('register.html', error='Uživatel již existuje')
        else:
            users.loc[len(users)] = [username, password]
            users.to_csv(USERS_FILE, index=False)
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])


@app.route('/ks')
def krizovy_stab():
    if 'username' not in session:
        return redirect(url_for('login'))
    ks_df = pd.read_excel(DATA_FILE)
    ks_df = ks_df[['Funkce v KŠ', 'Hlavní zodpovědnosti', 'Jméno', 'Telefon', 'Email']].dropna(how='all')
    return render_template('ks.html', ks_data=ks_df.to_dict(orient='records'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
