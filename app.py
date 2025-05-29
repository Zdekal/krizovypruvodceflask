# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)

# Cesta k souboru s projekty
PROJECTS_FILE = "projects.json"

# Funkce pro načtení projektů ze souboru
def load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    return []

# Funkce pro uložení projektů do souboru
def save_projects(projects):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)

@app.route("/")
def index():
    projects = load_projects()
    return render_template("index.html", projects=projects)

@app.route("/new", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        project = {"name": name, "description": description}
        projects = load_projects()
        projects.append(project)
        save_projects(projects)
        return redirect(url_for("index"))
    return render_template("new.html")

@app.route("/api/projects")
def api_projects():
    projects = load_projects()
    return jsonify(projects)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
