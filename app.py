from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)

# Cesta k datovému souboru
DATA_FILE = 'KŠ.xlsx'

@app.route("/")
def index():
    return "<h2>Aplikace běží. Pro přístup ke stránce krizového štábu přejděte na <a href='/ks'>/ks</a></h2>"

@app.route("/ks")
def krizovy_stab():
    ks_df = pd.read_excel(DATA_FILE, engine="openpyxl")
    ks_df = ks_df.dropna(subset=["Funkce v KŠ", "Hlavní zodpovědnosti"], how="all")
    ks_df = ks_df.fillna("")
    ks_data = ks_df.to_dict(orient="records")
    return render_template("ks.html", ks_data=ks_data)

if __name__ == "__main__":
    app.run(debug=True)
