import smtplib
import os
from email.message import EmailMessage
from email.utils import make_msgid
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")        # Your email
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")    # App password or actual password (if less secure app access enabled)
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")    # Recipient's email

def send_zip_via_email(zip_file_path, subject="Downloaded Data", body="Please find the attached zip file."):
    try:
        if not os.path.exists(zip_file_path):
            raise FileNotFoundError(f"{zip_file_path} does not exist.")

        # Setup Email
        msg = EmailMessage()
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = subject
        msg.set_content(body)

        # Add zip attachment
        with open(zip_file_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(zip_file_path)
            msg.add_attachment(file_data, maintype="application", subtype="zip", filename=file_name)

        # Connect and send
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print("✅ Email sent successfully.")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
