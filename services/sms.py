import os
import requests
from flask import render_template
from utils.helpers import normalize_phone_number
from utils.i18n import get_language

# Configuration
GATEWAYAPI_TOKEN = os.environ.get('GATEWAYAPI_TOKEN', 'your-gatewayapi-token')

def render_sms_template(template_name, **context):
    """Render SMS template with language detection"""
    lang = get_language()
    template_path = f"sms/{lang}/{template_name}.j2"

    try:
        return render_template(template_path, **context)
    except Exception as e:
        print(f"Warning: SMS template error for {template_path}: {e}")
        # Fallback to English if language-specific template fails
        if lang != 'en':
            try:
                return render_template(f"sms/en/{template_name}.j2", **context)
            except Exception as e2:
                print(f"Error: English SMS template fallback failed: {e2}")
                return f"SMS template error: {template_name}"
        return f"SMS template error: {template_name}"

def send_sms(phone, message):
    """Send SMS using GatewayAPI"""
    if not GATEWAYAPI_TOKEN or GATEWAYAPI_TOKEN == 'your-gatewayapi-token':
        # Simulation mode for development
        print(f"[SMS SIMULATION] To: {phone}")
        print(f"[SMS SIMULATION] Message: {message}")
        print("-" * 50)
        return True

    # Normalize phone number
    msisdn = normalize_phone_number(phone)

    data = {
        "sender":     "SKK Ticket",         # Sender name (max 11 chars)
        "message":    message,              # Message content
        "encoding":   "UCS2",               # Use UCS2 for special characters
        "recipients": [{"msisdn": msisdn}]  # Recipient list
    }

    try:
        print(f"[SMS] Sending to {msisdn}...")
        response = requests.post(
            "https://gatewayapi.eu/rest/mtsms",
            json=data,
            auth=(GATEWAYAPI_TOKEN, ''),
            timeout=30
        )

        if response.status_code == 200:
            print(f"[SMS] Successfully sent to {msisdn}")
            return True
        else:
            print(f"[SMS] Failed to send. Status: {response.status_code}")
            print(f"[SMS] Response: {response.text}")
            return False

    except Exception as e:
        print(f"[SMS] Error sending SMS: {str(e)}")
        return False