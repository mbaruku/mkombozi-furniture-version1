# utils.py
import smtplib
from email.mime.text import MIMEText


def send_email(to, subject, body):
    sender_email = "mbarouktechcreation@gmail.com"
    sender_password = (
        "guyh frqc xqnw krfy"  # tumia password ya application si password ya kawaida
    )
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print("Failed to send email:", str(e))
