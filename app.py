from flask import Flask, render_template, request, flash
import json
import smtplib
from email.mime.text import MIMEText

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        users = load_users()
        for user in users.values():
            if user.get('email') == email:
                subject = "Obnova hesla – Krizový průvodce"
                message = f"Vaše heslo je: {user.get('password')}"
                send_email(email, subject, message)
                return "Heslo bylo odesláno na váš e-mail."
        return "E-mail nebyl nalezen."
    return render_template('forgot_password.html')

def send_email(to, subject, message):
    FROM = "tvuj@email.cz"
    PASSWORD = "tvé_heslo"  # lépe použít bezpečnější způsob!
    smtp_server = "smtp.seznam.cz"
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = FROM
    msg["To"] = to

    with smtplib.SMTP_SSL(smtp_server, 465) as server:
        server.login(FROM, PASSWORD)
        server.send_message(msg)
