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

def detect_optimal_encoding(message):
    """Detect the cheapest encoding that can handle the message"""
    # GSM 7-bit character set (most common Danish/European chars)
    gsm_basic = set(
        "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
        "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
    )
    # Extended GSM characters (count as 2 chars each)
    gsm_extended = set("^{}\\[~]|€")

    # Check if message can use GSM7
    for char in message:
        if char not in gsm_basic and char not in gsm_extended:
            # Character not in GSM7, must use UCS2
            return "UCS2"

    return "GSM0338"

def send_sms(phone, message):
    """Send SMS using GatewayAPI with automatic encoding detection"""
    if not GATEWAYAPI_TOKEN or GATEWAYAPI_TOKEN == 'your-gatewayapi-token':
        # Simulation mode for development
        encoding = detect_optimal_encoding(message)
        print(f"[SMS SIMULATION] To: {phone}")
        print(f"[SMS SIMULATION] Encoding: {encoding}")
        print(f"[SMS SIMULATION] Length: {len(message)} chars")
        print(f"[SMS SIMULATION] Message: {message}")
        print("-" * 50)
        return True

    # Normalize phone number
    msisdn = normalize_phone_number(phone)

    # Automatically detect optimal encoding
    encoding = detect_optimal_encoding(message)

    data = {
        "sender":     "SKK Ticket",         # Sender name (max 11 chars)
        "message":    message,              # Message content
        "recipients": [{"msisdn": msisdn}]  # Recipient list
    }

    # Only set encoding if UCS2 is needed (GSM-7 is default)
    if encoding == "UCS2":
        data["encoding"] = "UCS2"

    print(f"[SMS] Using {encoding} encoding for {len(message)} chars")

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