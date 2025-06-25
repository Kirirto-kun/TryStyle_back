import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint
import os
import random
import string
from datetime import datetime, timedelta

# --- In-memory storage for verification codes ---
# In a production environment, consider using a more persistent
# and scalable solution like Redis or Memcached.
verification_codes = {}

def generate_verification_code(length=6):
    """Generate a random alphanumeric verification code."""
    return ''.join(random.choices(string.digits, k=length))

def store_verification_code(email: str, code: str):
    """Stores the verification code with a timestamp."""
    # Store the code and the time it was created
    verification_codes[email] = {"code": code, "timestamp": datetime.utcnow()}

def get_verification_code(email: str):
    """Retrieves the verification code if it's still valid."""
    record = verification_codes.get(email)
    if record:
        # Check if the code is still valid (e.g., within 10 minutes)
        if datetime.utcnow() - record["timestamp"] < timedelta(minutes=10):
            return record["code"]
    return None

def delete_verification_code(email: str):
    """Deletes the verification code after it has been used."""
    if email in verification_codes:
        del verification_codes[email]

# --- Brevo (Sendinblue) API Configuration ---
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.environ.get("BREVO_API_KEY")

def send_verification_email(recipient_email: str, verification_code: str):
    """Sends a verification email using the Brevo API."""
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    subject = "Your Verification Code"
    html_content = f"<html><body><h1>Your verification code is: {verification_code}</h1></body></html>"
    sender = {"name": "TryStyle verification", "email": "no-reply@trystyle.live"}
    to = [{"email": recipient_email}]
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        html_content=html_content,
        sender=sender,
        subject=subject
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        pprint(api_response)
        return True
    except ApiException as e:
        print("Exception when calling TransactionalEmailsApi->send_transac_email: %s\n" % e)
        return False 