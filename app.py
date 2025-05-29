from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)
KS_FILE = "ks.json"

def load_ks():
    if os.path.exists(KS_FILE):
        with open(KS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_ks(ks_data):
    with open(KS_FILE, "w", encoding="utf-8") as f:
        json.dump(ks_data, f, indent=2, ensure_ascii=False)

@app.route("/")
def index():
    return redirect(url_for("krizovy_stab"))

@app.route("/ks", methods=["GET", "POST"])
def krizovy_stab():
    ks_data = load_ks()
    if request.method == "POST":
        new_member = {
            "jmeno": request.form["jmeno"],
            "telefon": request.form["telefon"],
            "email": request.form["email"],
            "funkce": request.form["funkce"],
            "zodpovednost": request.form["zodpovednost"]
        }
        ks_data.append(new_member)
        save_ks(ks_data)
        return redirect(url_for("krizovy_stab"))
    return render_template("ks.html", ks_data=ks_data)

@app.route("/ks/delete/<int:index>")
def delete_member(index):
    ks_data = load_ks()
    if 0 <= index < len(ks_data):
        ks_data.pop(index)
        save_ks(ks_data)
    return redirect(url_for("krizovy_stab"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
