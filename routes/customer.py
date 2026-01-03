import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import stripe
from models import db, Ticket, Feedback
from services import send_sms, render_sms_template, create_stripe_payment_intent
from utils import generate_ticket_code, normalize_phone_number, t
from utils.notifications import notify_sharpeners_new_ticket
from flask import send_from_directory

customer_bp = Blueprint('customer', __name__)

# Configuration
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
SHARPENING_PRICE_DKK = int(os.environ.get('SHARPENING_PRICE_DKK', '80'))
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'your-stripe-publishable-key')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')

@customer_bp.route('/')
def index():
    # Brands as tuples (key, value) for translation
    brands = [
        ('jackson', 'Jackson'),
        ('edea', 'EDEA'),
        ('risport', 'Risport'),
        ('riedell', 'Riedell'),
        ('graf', 'Graf'),
        ('other', 'Other')
    ]
    # Colors as tuples (key, value) for translation
    colors = [
        ('white', 'White'),
        ('black', 'Black'),
        ('other', 'Other')
    ]
    # Standard EU sizes (24-46)
    sizes = list(range(24, 47))

    # EDEA sizes (185-310 in steps of 5)
    edea_sizes = list(range(185, 315, 5))

    return render_template('customer.html',
                         brands=brands,
                         colors=colors,
                         sizes=sizes,
                         edea_sizes=edea_sizes)

@customer_bp.route('/request_ticket', methods=['POST'])
def request_ticket():
    """Create a new ticket request"""
    # Get form data
    name = request.form['name'].strip()
    phone = request.form['phone'].strip()
    brand = request.form['brand'].strip()
    color = request.form['color'].strip()
    size = int(request.form['size'])

    # Store form data in session for potential retry
    session['ticket_form_data'] = {
        'name': name,
        'phone': phone,
        'brand': brand,
        'color': color,
        'size': size
    }

    # Validate inputs
    if not all([name, phone, brand, color]) or size <= 0:
        flash(t('error_all_fields_required'), 'error')
        return redirect(url_for('customer.index'))

    # Normalize phone
    phone = normalize_phone_number(phone)

    # Generate unique ticket code
    while True:
        code = generate_ticket_code()
        if not Ticket.query.filter_by(code=code).first():
            break

    # Create new ticket
    ticket = Ticket(
        code=code,
        customer_name=name,
        customer_phone=phone,
        brand=brand,
        color=color,
        size=size,
        price=SHARPENING_PRICE_DKK  # Stamp current price
    )

    db.session.add(ticket)
    db.session.commit()

    # Send SMS based on ticket price
    if ticket.price > 0:
        # Paid mode: send payment link
        payment_url = f"{BASE_URL}/pay/{ticket.code}"
        sms_message = render_sms_template('ticket_created', ticket=ticket, payment_url=payment_url)
        confirm_url = None
    else:
        # Free mode: send confirmation link
        confirm_url = f"{BASE_URL}/confirm/{ticket.code}"
        sms_message = render_sms_template('ticket_created', ticket=ticket, confirm_url=confirm_url)
        payment_url = None

    sms_success = send_sms(phone, sms_message)

    # Clear form data from session on success
    if 'ticket_form_data' in session:
        del session['ticket_form_data']

    # Store confirmation data in session for redirect
    session['ticket_confirmation'] = {
        'code': ticket.code,
        'customer_name': ticket.customer_name,
        'phone_number': ticket.customer_phone,
        'skate_brand': ticket.brand,
        'skate_color': ticket.color,
        'skate_size': ticket.size,
        'payment_url': payment_url,
        'confirm_url': confirm_url,
        'price': ticket.price,
        'sms_success': sms_success
    }

    # Redirect to confirmation page (PRG pattern to prevent duplicate submissions)
    return redirect(url_for('customer.ticket_created'))

@customer_bp.route('/pay/<ticket_code>')
def payment_page(ticket_code):
    """Payment page for tickets"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # Redirect free tickets to confirmation page
    if ticket.price == 0:
        return redirect(url_for('customer.confirm_ticket', ticket_code=ticket_code))

    if ticket.status != 'unpaid':
        return render_template('already_paid.html', ticket=ticket)

    # Create or retrieve payment intent on-demand
    client_secret = None

    # Check if we have a valid existing payment intent
    if ticket.payment_id and not ticket.payment_id.startswith('pi_simulation_'):
        try:
            # Try to retrieve the existing payment intent
            payment_intent = stripe.PaymentIntent.retrieve(ticket.payment_id)
            # Check if the intent is still usable (not expired/canceled)
            if payment_intent.status in ['requires_confirmation', 'requires_action']:
                client_secret = payment_intent.client_secret
                print(f"[Stripe] Reusing existing payment intent {ticket.payment_id} for ticket {ticket.code}")
            else:
                # Intent is no longer usable, create a new one
                print(f"[Stripe] Payment intent {ticket.payment_id} status is {payment_intent.status}, creating new one")
                ticket.payment_id = None
        except Exception as e:
            print(f"[Stripe] Error retrieving payment intent: {e}")
            ticket.payment_id = None

    # Create a new payment intent if needed
    if not ticket.payment_id:
        payment_id = create_stripe_payment_intent(SHARPENING_PRICE_DKK, ticket)
        ticket.payment_id = payment_id
        db.session.commit()
        print(f"[Stripe] Created new payment intent {payment_id} for ticket {ticket.code}")

        if not payment_id.startswith('pi_simulation_'):
            try:
                payment_intent = stripe.PaymentIntent.retrieve(payment_id)
                client_secret = payment_intent.client_secret
            except Exception as e:
                print(f"[Stripe] Error retrieving new payment intent: {e}")

    return render_template('payment.html',
                         ticket=ticket,
                         stripe_key=STRIPE_PUBLISHABLE_KEY,
                         client_secret=client_secret)

@customer_bp.route('/ticket/created')
def ticket_created():
    """Show ticket creation confirmation page"""
    # Retrieve confirmation data from session
    confirmation = session.pop('ticket_confirmation', None)

    if not confirmation:
        # If no confirmation data, redirect to home
        flash(t('session_expired'), 'error')
        return redirect(url_for('customer.index'))

    # Show SMS confirmation as flash message
    if confirmation['sms_success']:
        flash(f"{t('sms_sent_to')}: {confirmation['phone_number']}", 'success')

    # Prepare ticket info for template
    ticket_info = {
        'code': confirmation['code'],
        'customer_name': confirmation['customer_name'],
        'skate_brand': confirmation['skate_brand'],
        'skate_color': confirmation['skate_color'],
        'skate_size': confirmation['skate_size']
    }

    return render_template('ticket_created.html',
                         ticket=ticket_info,
                         payment_url=confirmation.get('payment_url'),
                         confirm_url=confirmation.get('confirm_url'),
                         price=confirmation.get('price'),
                         customer_name=confirmation['customer_name'],
                         phone_number=confirmation['phone_number'],
                         skate_brand=confirmation['skate_brand'],
                         skate_color=confirmation['skate_color'],
                         skate_size=confirmation['skate_size'],
                         sms_success=confirmation['sms_success'])

@customer_bp.route('/payment_process/<ticket_code>', methods=['POST'])
def payment_process(ticket_code):
    """Process payment confirmation (should be called by payment provider webhook)"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # Only process payment if ticket is still unpaid
    if ticket.status == 'unpaid':
        # In real implementation, verify payment with Stripe webhook
        # For now, simulate successful payment
        ticket.status = 'paid'
        ticket.paid_at = datetime.utcnow()
        db.session.commit()

        # Notify all sharpeners about new ticket
        notify_sharpeners_new_ticket(ticket)

        # Send confirmation SMS only if configured
        send_payment_confirmation_sms = os.environ.get('SEND_PAYMENT_CONFIRMATION_SMS', 'false').lower() == 'true'
        if send_payment_confirmation_sms:
            sms_message = render_sms_template(
                'payment_confirmed',
                ticket=ticket
            )
            send_sms(ticket.customer_phone, sms_message)

    # Redirect to return page after processing
    return redirect(url_for('customer.payment_return', ticket_code=ticket_code))

@customer_bp.route('/payment_return/<ticket_code>')
def payment_return(ticket_code):
    """Handle payment return - displays success or failure based on payment status"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # Check payment status from query parameters (Stripe typically adds payment_intent parameters)
    payment_intent = request.args.get('payment_intent')
    payment_intent_client_secret = request.args.get('payment_intent_client_secret')
    redirect_status = request.args.get('redirect_status')

    # Determine if payment was successful
    payment_successful = False
    error_message = None

    if redirect_status == 'succeeded' or ticket.status == 'paid':
        payment_successful = True
    elif redirect_status == 'failed':
        error_message = t('payment_failed')
    elif redirect_status == 'canceled':
        error_message = t('payment_canceled')
    else:
        # If no clear status, check with Stripe API if we have payment_intent
        stripe_secret_key = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key')
        if payment_intent and stripe_secret_key != 'your-stripe-secret-key':
            try:
                intent = stripe.PaymentIntent.retrieve(payment_intent)
                if intent.status == 'succeeded':
                    payment_successful = True
                elif intent.status == 'canceled':
                    error_message = t('payment_canceled')
                else:
                    error_message = t('payment_failed')
            except Exception as e:
                print(f"[Payment Return] Error checking payment status: {e}")
                error_message = t('payment_status_unknown')

    if payment_successful:
        return render_template('payment_success.html', ticket=ticket)
    else:
        return render_template('payment_failed.html',
                             ticket=ticket,
                             error_message=error_message,
                             payment_url=url_for('customer.payment_page', ticket_code=ticket_code))

@customer_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe payment webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    stripe_webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', 'your-stripe-webhook-secret')

    # Skip webhook verification in development if secret not configured
    if stripe_webhook_secret == 'your-stripe-webhook-secret':
        print("[Stripe Webhook] Development mode - skipping signature verification")
        try:
            event = stripe.Event.construct_from(request.get_json(), stripe.api_key)
        except Exception as e:
            print(f"[Stripe Webhook] Error parsing webhook: {e}")
            return 'Invalid payload', 400
    else:
        # Verify webhook signature in production
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, stripe_webhook_secret
            )
        except ValueError:
            print("[Stripe Webhook] Invalid payload")
            return 'Invalid payload', 400
        except stripe.error.SignatureVerificationError:
            print("[Stripe Webhook] Invalid signature")
            return 'Invalid signature', 400

    # Handle payment success event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']

        # Get ticket code from payment metadata
        ticket_code = payment_intent.get('metadata', {}).get('ticket_code')

        if ticket_code:
            ticket = Ticket.query.filter_by(code=ticket_code).first()
            if ticket and ticket.status == 'unpaid':
                # Update ticket status to paid
                ticket.status = 'paid'
                ticket.paid_at = datetime.utcnow()
                db.session.commit()

                print(f"[Stripe Webhook] Payment confirmed for ticket {ticket_code}")

                # Notify all sharpeners about new ticket
                notify_sharpeners_new_ticket(ticket)

                # Send confirmation SMS only if configured
                send_payment_confirmation_sms = os.environ.get('SEND_PAYMENT_CONFIRMATION_SMS', 'false').lower() == 'true'
                if send_payment_confirmation_sms:
                    sms_message = render_sms_template(
                        'payment_confirmed',
                        ticket=ticket
                    )
                    send_sms(ticket.customer_phone, sms_message)
            else:
                print(f"[Stripe Webhook] Ticket {ticket_code} not found or already paid")
        else:
            print("[Stripe Webhook] No ticket_code in payment metadata")

    return '', 200

@customer_bp.route('/confirm/<ticket_code>')
def confirm_ticket(ticket_code):
    """Confirmation page for free tickets (no payment required)"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # Redirect paid tickets to payment page
    if ticket.price > 0:
        return redirect(url_for('customer.payment_page', ticket_code=ticket_code))

    # Check if already confirmed
    if ticket.status != 'unpaid':
        return render_template('ticket_confirmed.html', ticket=ticket)

    return render_template('confirm_free_ticket.html', ticket=ticket)

@customer_bp.route('/confirm/<ticket_code>/process', methods=['POST'])
def confirm_ticket_process(ticket_code):
    """Process free ticket confirmation"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # Verify this is a free ticket
    if ticket.price > 0:
        flash(t('error_not_free_ticket'), 'error')
        return redirect(url_for('customer.payment_page', ticket_code=ticket_code))

    if ticket.status == 'unpaid':
        # Mark as 'paid' (ready for sharpening)
        ticket.status = 'paid'
        ticket.paid_at = datetime.utcnow()
        db.session.commit()

        # Notify all sharpeners about new ticket
        notify_sharpeners_new_ticket(ticket)

    return render_template('ticket_confirmed.html', ticket=ticket)

@customer_bp.route('/feedback/<ticket_code>', methods=['GET', 'POST'])
def feedback(ticket_code):
    """Customer feedback form for completed tickets"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # Only allow feedback for completed tickets
    if ticket.status != 'completed':
        return render_template('feedback_unavailable.html', ticket=ticket)

    # Check if feedback already exists
    if ticket.feedback:
        return render_template('feedback_already_given.html', ticket=ticket, feedback=ticket.feedback)

    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form.get('comment', '').strip()

        # Create feedback record
        feedback_record = Feedback(
            ticket_id=ticket.id,
            rating=rating,
            comment=comment
        )

        db.session.add(feedback_record)
        db.session.commit()

        return render_template('feedback_thanks.html', ticket=ticket, feedback=feedback_record)

    return render_template('feedback_form.html', ticket=ticket)

@customer_bp.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('static', 'favicon.ico')
