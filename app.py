from flask import Flask, render_template, request, redirect
import pandas as pd
import os

app = Flask(__name__)

# Načtení tabulky bez prázdných řádků
DATA_FILE = "KŠ.xlsx"
ks_df = pd.read_excel(DATA_FILE)
ks_df.dropna(how='all', inplace=True)
ks_df = ks_df.fillna("")

@app.route("/ks", methods=["GET"])
def krizovy_stab():
    ks_data = ks_df.to_dict(orient='records')
    return render_template("ks.html", ks_data=ks_data)

@app.route("/save", methods=["POST"])
def ulozit_zmeny():
    updated_data = {
        'Funkce v KŠ': request.form.getlist("funkce"),
        'Hlavní zodpovědnosti': request.form.getlist("zodpovednosti"),
        'Jméno': request.form.getlist("jmeno"),
        'Telefon': request.form.getlist("telefon"),
        'Email': request.form.getlist("email"),
    }
    df = pd.DataFrame(updated_data)
    df.to_excel(DATA_FILE, index=False)
    return redirect("/ks")

if __name__ == "__main__":
    app.run(debug=True)
