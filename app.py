from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Úvodní stránka s informacemi o aplikaci
@app.route("/")
def homepage():
    return render_template("index.html")

# Registrace
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # TODO: Uložit nového uživatele do úložiště
        return redirect(url_for("login"))
    return render_template("register.html")

# Přihlášení
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # TODO: Ověřit uživatele z úložiště
        session["username"] = username
        return redirect(url_for("dashboard"))
    return render_template("login.html")

# Uživatelská domovská stránka
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["username"])

# Odhlášení
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("homepage"))

if __name__ == "__main__":
    app.run(debug=True)
