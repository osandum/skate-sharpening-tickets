"""
Email notification utilities for sharpeners
"""
from email.utils import formataddr
from flask import current_app
from flask_mail import Message, Mail
from models import Sharpener


def notify_sharpeners_new_ticket(ticket):
    """
    Send email notification to all registered sharpeners about a new confirmed ticket.

    Args:
        ticket: The Ticket object that was just confirmed

    Returns:
        int: Number of emails sent successfully
    """
    from app import app

    # Get all active sharpeners
    sharpeners = Sharpener.query.all()

    if not sharpeners:
        print("[NOTIFICATION] No sharpeners to notify")
        return 0

    # Check if mail is configured
    if not current_app.config.get('MAIL_SERVER'):
        print("[NOTIFICATION] Email not configured - skipping notification")
        print(f"[NOTIFICATION] Would notify {len(sharpeners)} sharpeners about ticket {ticket.code}")
        return 0

    # Build list of recipients with proper name formatting
    recipients = []
    for sharpener in sharpeners:
        if sharpener.email:
            recipients.append(formataddr((sharpener.name, sharpener.email)))

    if not recipients:
        print("[NOTIFICATION] No sharpener email addresses configured")
        return 0

    mail = Mail(current_app)

    try:
        # Create single email message to all sharpeners
        msg = Message(
            subject=f"New Ticket: {ticket.code} – {ticket.customer_name}",
            recipients=recipients,  # Must be a list
            reply_to=', '.join(recipients),  # Must be a string
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )

        # Plain text body
        msg.body = f"""Hi sharpeners,

A new ticket is ready for sharpening:

Ticket Code: {ticket.code}
Customer: {ticket.customer_name}
Phone: {ticket.customer_phone}
Skates: {ticket.brand} {ticket.color} size {ticket.size}
{'Price: ' + str(ticket.price) + ' DKK' if ticket.price > 0 else 'Confirmation completed'}

Log in to claim this ticket:
{current_app.config.get('BASE_URL', 'http://localhost:5000')}/sharpener

Best regards,
SKK Skate Sharpening System
"""

        # HTML body
        msg.html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #2563eb;">New Ticket Ready for Sharpening</h2>

    <p>Hi sharpeners,</p>

    <p>A new ticket is ready for sharpening:</p>

    <div style="background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 15px; margin: 20px 0;">
        <p style="margin: 5px 0;"><strong>Ticket Code:</strong> {ticket.code}</p>
        <p style="margin: 5px 0;"><strong>Customer:</strong> {ticket.customer_name}</p>
        <p style="margin: 5px 0;"><strong>Phone:</strong> {ticket.customer_phone}</p>
        <p style="margin: 5px 0;"><strong>Skates:</strong> {ticket.brand} {ticket.color} size {ticket.size}</p>
        {'<p style="margin: 5px 0;"><strong>Price:</strong> ' + str(ticket.price) + ' DKK</p>' if ticket.price > 0 else '<p style="margin: 5px 0;">Confirmation completed</p>'}
    </div>

    <p>
        <a href="{current_app.config.get('BASE_URL', 'http://localhost:5000')}/sharpener"
           style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            Log in to claim this ticket
        </a>
    </p>

    <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
        SKK Skate Sharpening System
    </p>
</body>
</html>
"""

        # Send email
        mail.send(msg)
        print(f"[NOTIFICATION] Sent notification to {len(recipients)} sharpeners about ticket {ticket.code}")
        print(f"[NOTIFICATION] Recipients: {', '.join(recipients)}")
        return len(recipients)

    except Exception as e:
        print(f"[NOTIFICATION] Failed to send notification: {e}")
        return 0
