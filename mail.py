"""SMTP over SSL, using environment-provided GitHub secrets."""
import os
import smtplib
from email.message import EmailMessage


def send_mail(html, subject):
    keys = ('SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'EMAIL_TO')
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        raise ValueError(f'Missing SMTP environment variables: {", ".join(missing)}')
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = os.getenv('EMAIL_FROM') or os.environ['SMTP_USER']
    message['To'] = os.environ['EMAIL_TO']
    message.set_content('Daily screener report is available in the HTML portion of this message.')
    message.add_alternative(html, subtype='html')
    with smtplib.SMTP_SSL(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT']), timeout=30) as server:
        server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        server.send_message(message)
