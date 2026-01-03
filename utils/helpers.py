import os
import random

# Configuration for LL-NNN format ticket codes
# Unambiguous letters: excludes I, Z, A, S, B, O, Q, D, G, L
TICKET_LETTERS = 'CEFHJKMNPRTUVWXY'
# Unambiguous digits: excludes 0, 1, 2, 4, 5, 8
TICKET_DIGITS = '3679'

def generate_ticket_code():
    """
    Generate a ticket code in format LL-NNN.
    Two unique uppercase letters + hyphen + three unique digits.
    Uses reduced character sets to prevent ambiguities in handwriting.
    """
    # Generate 2 unique letters
    letters = random.sample(TICKET_LETTERS, 2)
    # Generate 3 unique digits
    digits = random.sample(TICKET_DIGITS, 3)

    return f"{''.join(letters)}-{''.join(digits)}"

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

def mask_phone_number(phone):
    """
    Mask middle digits of phone number for privacy while keeping it recognizable.
    Always keeps last 2 digits visible, masks up to 4 digits before them.
    Examples: 4526882377 -> 4526xxxx77, 12345678 -> 12xxxx78, 12345 -> xxx45
    """
    if not phone:
        return phone

    # Extract only digits
    digits = ''.join(filter(str.isdigit, phone))
    n = len(digits)

    # Calculate how many digits to mask (up to 4, leaving at least 2 at end)
    digits_to_mask = min(4, n - 2)

    # If 2 or fewer digits total, return as-is
    if digits_to_mask <= 0:
        return digits

    # Calculate positions
    start = n - 2 - digits_to_mask
    end = n - 2

    return digits[:start] + 'x' * digits_to_mask + digits[end:]
