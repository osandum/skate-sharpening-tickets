import os
import random

# Configuration
TICKET_CODE_LENGTH = int(os.environ.get('TICKET_CODE_LENGTH', '5'))
TICKET_CODE_ALPHABET = os.environ.get('TICKET_CODE_ALPHABET', 'CEFHJKMNPQRTUVWXY379')

def generate_ticket_code():
    """Generate a ticket code using configurable length and alphabet"""
    # Use configurable alphabet and length (defaults: unambiguous chars, 5 chars)
    # Default excludes confusing characters: 0/O, 1/I/L, D (looks like 0)
    return ''.join(random.choices(TICKET_CODE_ALPHABET, k=TICKET_CODE_LENGTH))

def normalize_phone_number(phone):
    """Normalize Danish phone number to international format"""
    # Remove all non-digit characters
    phone_digits = ''.join(filter(str.isdigit, phone))

    # Handle Danish mobile numbers
    if phone_digits.startswith('45'):  # Already has country code
        return phone_digits
    elif len(phone_digits) == 8:  # Danish number without country code
        return '45' + phone_digits
    else:
        return phone_digits  # Return as-is if unclear format
