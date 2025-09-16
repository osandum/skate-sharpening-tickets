"""Flask Skate Sharpening Ticket System.

Complete backend with database, auth, SMS, and payment integration.
"""
from datetime import datetime, timedelta
from functools import wraps
import os
from pathlib import Path
import random

from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory, g)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import requests
import stripe
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
import yaml
import secrets

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///skate_tickets.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')

# Handle PostgreSQL URL format for SQLAlchemy 2.0+
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
    )

db = SQLAlchemy(app)
mail = Mail(app)

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key')

# Configuration - set these as environment variables
GATEWAYAPI_TOKEN = os.environ.get('GATEWAYAPI_TOKEN', 'your-gatewayapi-token')
SEND_PAYMENT_CONFIRMATION_SMS = os.environ.get('SEND_PAYMENT_CONFIRMATION_SMS', 'false').lower() == 'true'
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'your-stripe-publishable-key')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'your-stripe-webhook-secret')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')
SHARPENING_PRICE_DKK = int(os.environ.get('SHARPENING_PRICE_DKK', '80'))

# Database Models
class Sharpener(db.Model):
    """Database model for skate sharpener staff accounts."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    tickets = db.relationship('Ticket', backref='sharpener', lazy=True)

class Ticket(db.Model):
    """Database model for customer skate sharpening tickets."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)

    # Skate details
    brand = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    size = db.Column(db.Integer, nullable=False)

    # Status tracking
    status = db.Column(db.String(20), default='unpaid')  # unpaid, paid, in_progress, completed
    payment_id = db.Column(db.String(100))  # Stripe payment intent ID

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Sharpener tracking
    sharpened_by_id = db.Column(db.Integer, db.ForeignKey('sharpener.id'))

    # Relationships
    feedback = db.relationship('Feedback', backref='ticket', uselist=False)

class Feedback(db.Model):
    """Database model for customer feedback on completed tickets."""
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invitation(db.Model):
    """Database model for sharpener invitations."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    token = db.Column(db.String(100), nullable=False, unique=True)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

# Initialize token serializer for invitations
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Internationalization
_translations_cache = {}
_translation_file_times = {}

def load_translations():
    """Load translations from YAML files with hot-reloading in debug mode"""
    global _translations_cache

    # In production, use cached translations
    if not app.debug and _translations_cache:
        return _translations_cache

    # Check if any translation files have been modified
    reload_needed = False
    for lang in ['da', 'en']:
        file_path = f'translations/{lang}.yaml'
        try:
            current_mtime = Path(file_path).stat().st_mtime
            if (file_path not in _translation_file_times or
                    _translation_file_times[file_path] != current_mtime):
                _translation_file_times[file_path] = current_mtime
                reload_needed = True
        except FileNotFoundError:
            continue

    # Reload translations if files changed or cache is empty
    if reload_needed or not _translations_cache:
        print("[Translations] Reloading language files...")
        translations = {}
        for lang in ['da', 'en']:
            try:
                with open(f'translations/{lang}.yaml', 'r', encoding='utf-8') as f:
                    translations[lang] = yaml.safe_load(f)
            except FileNotFoundError:
                print(f"Warning: Translation file translations/{lang}.yaml not found")
                translations[lang] = {}
        _translations_cache = translations

    return _translations_cache

def get_translations():
    """Get current translations (with hot-reloading in debug mode)"""
    return load_translations()

def get_language():
    """Detect language from Accept-Language header"""
    if hasattr(g, 'language'):
        return g.language

    # Check Accept-Language header
    accept_lang = request.headers.get('Accept-Language', '').lower()

    # Nordic languages use Danish
    nordic_codes = ['da', 'dk', 'sv', 'se', 'no', 'nb', 'nn']
    if any(code in accept_lang for code in nordic_codes):
        g.language = 'da'
    else:
        g.language = 'en'

    return g.language

def t(key, *args, **kwargs):
    """Translate key to current language"""
    lang = get_language()
    translations = get_translations()
    translation = translations.get(lang, {}).get(key, translations.get('en', {}).get(key, key))

    # Handle string formatting
    if args or kwargs:
        try:
            if kwargs:
                return translation.format(**kwargs)
            else:
                return translation.format(*args)
        except Exception as e:
            print(f"Warning: Translation formatting error for key '{key}': {e}")
            return translation
    return translation

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

@app.context_processor
def inject_translate():
    """Make translation function available in all templates"""
    return {'t': t, 'recaptcha_site_key': RECAPTCHA_SITE_KEY, 'sharpening_price': SHARPENING_PRICE_DKK}

# Helper Functions
def generate_ticket_code():
    """Generate a 5-character ticket code using unambiguous characters"""
    # Exclude confusing characters: 0/O, 1/I/L, D (looks like 0)
    chars = "ABCEFGHJKMNPQRSTUVWXYZ23456789"
    return ''.join(random.choices(chars, k=5))

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

def verify_recaptcha(response_token, min_score=0.5):
    """Verify reCAPTCHA v3 response with Google"""
    # Skip reCAPTCHA verification in development mode (localhost)
    if app.debug and (request.host.startswith('localhost') or request.host.startswith('127.0.0.1')):
        print("[reCAPTCHA v3] Development mode - bypassing reCAPTCHA verification")
        return True

    if not RECAPTCHA_SECRET_KEY or RECAPTCHA_SECRET_KEY == '':
        # Skip verification in development if no key is set
        print("[reCAPTCHA v3] No secret key set, skipping verification")
        return True

    if not response_token:
        print("[reCAPTCHA v3] No response token provided")
        return False

    try:
        verification_data = {
            'secret': RECAPTCHA_SECRET_KEY,
            'response': response_token,
            'remoteip': request.environ.get('REMOTE_ADDR')
        }

        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=verification_data,
            timeout=10
        )

        result = response.json()
        success = result.get('success', False)
        score = result.get('score', 0.0)
        action = result.get('action', '')

        print(f"[reCAPTCHA v3] Score: {score}, Action: {action}, Success: {success}")

        if success and score >= min_score and action == 'ticket_request':
            print(f"[reCAPTCHA v3] Verification passed (score: {score})")
            return True
        else:
            print(f"[reCAPTCHA v3] Verification failed - Score: {score}, Min required: {min_score}")
            if not success:
                print(f"[reCAPTCHA v3] Error codes: {result.get('error-codes', [])}")
            return False

    except Exception as e:
        print(f"[reCAPTCHA v3] Error verifying: {str(e)}")
        return False

def create_stripe_payment_intent(amount, ticket):
    """Create Stripe payment intent for MobilePay"""
    if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY == 'your-stripe-secret-key':
        # Simulation mode
        print(f"[Stripe] Simulation mode - creating fake payment intent for ticket {ticket.code}")
        return f"pi_simulation_{ticket.code}"

    try:
        # Create real Stripe payment intent
        print(f"[Stripe] Creating payment intent for ticket {ticket.code}, amount: {amount} DKK")

        # Convert DKK to øre (smallest currency unit)
        amount_in_ore = int(amount * 100)

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_in_ore,
            currency='dkk',
            payment_method_types=['mobilepay'],  # Can add 'mobilepay' when available in Denmark
            metadata={
                'ticket_code': ticket.code,
                'customer_name': ticket.customer_name,
                'customer_phone': ticket.customer_phone,
                'skate_details': f"{ticket.brand} {ticket.color} {ticket.size}"
            },
            description=f"Skate sharpening - Ticket {ticket.code}"
        )

        print(f"[Stripe] Payment intent created: {payment_intent.id}")
        return payment_intent.id

    except Exception as e:
        print(f"[Stripe] Error creating payment intent: {e}")
        # Fallback to simulation mode on error
        return f"pi_simulation_{ticket.code}"

def login_required(f):
    """Decorator to require sharpener login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'sharpener_id' not in session:
            return redirect(url_for('sharpener_login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper functions for invitations
def generate_invitation_token(email):
    """Generate a secure invitation token"""
    return serializer.dumps(email, salt='invitation')

def verify_invitation_token(token, max_age=86400):  # 24 hours
    """Verify and decode invitation token"""
    try:
        email = serializer.loads(token, salt='invitation', max_age=max_age)
        return email
    except:
        return None

def send_invitation_email(email, token):
    """Send invitation email (simulation for now)"""
    invitation_url = url_for('accept_invitation', token=token, _external=True)
    print(f"[EMAIL SIMULATION] Invitation sent to {email}")
    print(f"Registration link: {invitation_url}")
    return True

# Routes

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon'
    )

@app.route('/')
def index():
    """Customer ticket request page"""
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
    sizes = list(range(24, 47))  # 24-46

    return render_template('customer.html', brands=brands, colors=colors, sizes=sizes)

@app.route('/request_ticket', methods=['POST'])
def request_ticket():
    """Process ticket request"""
    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        brand = request.form.get('brand', '')
        color = request.form.get('color', '')
        size_str = request.form.get('size', '')

        # Validate all required fields
        if not name or not phone or not brand or not color or not size_str:
            flash(t('all_fields_required'))
            return redirect(url_for('index'))

        # Validate size is a valid integer
        try:
            size = int(size_str)
            if size < 24 or size > 46:
                flash(t('invalid_size'))
                return redirect(url_for('index'))
        except ValueError:
            flash(t('invalid_size'))
            return redirect(url_for('index'))

    except Exception as e:
        print(f"[ERROR] Form validation error: {str(e)}")
        flash(t('form_error'))
        return redirect(url_for('index'))

    # Verify reCAPTCHA
    recaptcha_response = request.form.get('g-recaptcha-response')
    if not verify_recaptcha(recaptcha_response):
        flash(t('captcha_failed'))
        return redirect(url_for('index'))

    # Generate unique ticket code
    while True:
        code = generate_ticket_code()
        if not Ticket.query.filter_by(code=code).first():
            break

    # Create ticket
    ticket = Ticket(
        code=code,
        customer_name=name,
        customer_phone=phone,
        brand=brand,
        color=color,
        size=size
    )

    db.session.add(ticket)
    db.session.commit()

    # Create payment intent
    payment_id = create_stripe_payment_intent(SHARPENING_PRICE_DKK, ticket)
    ticket.payment_id = payment_id
    db.session.commit()

    # Send SMS with payment link
    payment_url = f"{BASE_URL}/pay/{ticket.code}"

    sms_message = render_sms_template('ticket_created', ticket=ticket, payment_url=payment_url)
    send_sms(phone, sms_message)

    # Store ticket info in session for confirmation page (without exposing ticket code in URL)
    session['ticket_confirmation'] = {
        'customer_name': ticket.customer_name,
        'phone_number': ticket.customer_phone,
        'skate_brand': ticket.brand,
        'skate_color': ticket.color,
        'skate_size': ticket.size,
        'created': True
    }

    return redirect(url_for('ticket_created_confirmation'))

@app.route('/ticket/created')
def ticket_created_confirmation():
    """Ticket creation confirmation page"""
    # Get ticket info from session
    ticket_info = session.get('ticket_confirmation')

    if not ticket_info or not ticket_info.get('created'):
        # No valid session data, redirect to home
        flash(t('session_expired'))
        return redirect(url_for('index'))

    # Clear the session data after displaying (one-time use)
    session.pop('ticket_confirmation', None)

    return render_template('ticket_created.html',
                         customer_name=ticket_info['customer_name'],
                         phone_number=ticket_info['phone_number'],
                         skate_brand=ticket_info['skate_brand'],
                         skate_color=ticket_info['skate_color'],
                         skate_size=ticket_info['skate_size'])

@app.route('/pay/<ticket_code>')
def payment_page(ticket_code):
    """Payment page for tickets"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    if ticket.status != 'unpaid':
        return render_template('already_paid.html', ticket=ticket)

    # Get client_secret for Stripe payment
    client_secret = None
    if ticket.payment_id and not ticket.payment_id.startswith('pi_simulation_'):
        try:
            # Retrieve the payment intent to get client_secret
            payment_intent = stripe.PaymentIntent.retrieve(ticket.payment_id)
            client_secret = payment_intent.client_secret
        except Exception as e:
            print(f"[Stripe] Error retrieving payment intent: {e}")

    return render_template('payment.html',
                         ticket=ticket,
                         stripe_key=STRIPE_PUBLISHABLE_KEY,
                         client_secret=client_secret)

@app.route('/payment_process/<ticket_code>', methods=['POST'])
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

        # Send confirmation SMS only if configured
        if SEND_PAYMENT_CONFIRMATION_SMS:
            sms_message = render_sms_template(
                'payment_confirmed',
                ticket=ticket
            )
            send_sms(ticket.customer_phone, sms_message)

    # Redirect to return page after processing
    return redirect(url_for('payment_return', ticket_code=ticket_code))

@app.route('/payment_return/<ticket_code>')
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
        if payment_intent and STRIPE_SECRET_KEY != 'your-stripe-secret-key':
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
                             payment_url=url_for('payment_page', ticket_code=ticket_code))

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe payment webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    # Skip webhook verification in development if secret not configured
    if STRIPE_WEBHOOK_SECRET == 'your-stripe-webhook-secret':
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
                payload, sig_header, STRIPE_WEBHOOK_SECRET
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
        if not ticket_code:
            print("[Stripe Webhook] No ticket_code in payment metadata")
            return 'Missing ticket_code', 400

        # Find and update ticket
        ticket = Ticket.query.filter_by(code=ticket_code).first()
        if not ticket:
            print(f"[Stripe Webhook] Ticket not found: {ticket_code}")
            return 'Ticket not found', 404

        # Only process if still unpaid (prevent duplicate processing)
        if ticket.status == 'unpaid':
            print(f"[Stripe Webhook] Processing payment for ticket {ticket_code}")

            # Update ticket status
            ticket.status = 'paid'
            ticket.paid_at = datetime.utcnow()
            ticket.payment_id = payment_intent['id']
            db.session.commit()

            # Send confirmation SMS only if configured
            if SEND_PAYMENT_CONFIRMATION_SMS:
                sms_message = render_sms_template(
                    'payment_confirmed',
                    ticket=ticket,
                    estimated_time="15-20 minutes"
                )
                send_sms(ticket.customer_phone, sms_message)
                print(f"[Stripe Webhook] Payment processed and SMS sent for ticket {ticket_code}")
            else:
                print(f"[Stripe Webhook] Payment processed for ticket {ticket_code} (SMS disabled)")
        else:
            print(f"[Stripe Webhook] Ticket {ticket_code} already processed (status: {ticket.status})")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        ticket_code = payment_intent.get('metadata', {}).get('ticket_code')
        print(f"[Stripe Webhook] Payment failed for ticket {ticket_code}")
        # Could add failed payment handling here if needed

    else:
        print(f"[Stripe Webhook] Unhandled event type: {event['type']}")

    return '', 200

@app.route('/sharpener/login', methods=['GET', 'POST'])
def sharpener_login():
    """Sharpener login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        sharpener = Sharpener.query.filter_by(username=username).first()

        if sharpener and check_password_hash(sharpener.password_hash, password):
            session['sharpener_id'] = sharpener.id
            session['sharpener_name'] = sharpener.name
            return redirect(url_for('sharpener_dashboard'))
        else:
            flash(t('invalid_login'))

    return render_template('sharpener_login.html')

@app.route('/sharpener/logout')
def sharpener_logout():
    """Logout sharpener"""
    session.pop('sharpener_id', None)
    session.pop('sharpener_name', None)
    return redirect(url_for('sharpener_login'))

@app.route('/sharpener')
@login_required
def sharpener_dashboard():
    """Sharpener dashboard"""
    unpaid_tickets = Ticket.query.filter_by(status='unpaid').all()
    ready_tickets = Ticket.query.filter_by(status='paid').all()
    in_progress_tickets = Ticket.query.filter_by(status='in_progress').all()
    completed_today = Ticket.query.filter(
        Ticket.status == 'completed',
        Ticket.completed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).all()

    # Get current sharpener's recent work and feedback
    sharpener_id = session['sharpener_id']
    my_recent_tickets = Ticket.query.filter_by(
        sharpened_by_id=sharpener_id,
        status='completed'
    ).order_by(Ticket.completed_at.desc()).limit(5).all()

    # Calculate average rating
    feedbacks = db.session.query(Feedback).join(Ticket).filter(
        Ticket.sharpened_by_id == sharpener_id
    ).all()
    avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks) if feedbacks else 0

    return render_template('sharpener_dashboard.html',
                         unpaid_count=len(unpaid_tickets),
                         ready_tickets=ready_tickets,
                         in_progress_tickets=in_progress_tickets,
                         completed_today=len(completed_today),
                         my_recent_tickets=my_recent_tickets,
                         avg_rating=round(avg_rating, 1),
                         feedback_count=len(feedbacks))

@app.route('/sharpener/claim/<int:ticket_id>')
@login_required
def claim_ticket(ticket_id):
    """Claim a ticket for sharpening"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if ticket.status != 'paid':
        flash(t('ticket_not_available'))
        return redirect(url_for('sharpener_dashboard'))

    ticket.status = 'in_progress'
    ticket.started_at = datetime.utcnow()
    ticket.sharpened_by_id = session['sharpener_id']
    db.session.commit()

    flash(t('ticket_claimed', ticket.code))
    return redirect(url_for('sharpener_dashboard'))

@app.route('/sharpener/complete/<int:ticket_id>')
@login_required
def complete_ticket(ticket_id):
    """Mark ticket as completed"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if ticket.status != 'in_progress' or ticket.sharpened_by_id != session['sharpener_id']:
        flash(t('cannot_complete'))
        return redirect(url_for('sharpener_dashboard'))

    ticket.status = 'completed'
    ticket.completed_at = datetime.utcnow()
    db.session.commit()

    # Send pickup SMS with feedback link
    feedback_url = f"{BASE_URL}/feedback/{ticket.code}"

    sms_message = render_sms_template('ticket_completed', ticket=ticket, feedback_url=feedback_url)
    send_sms(ticket.customer_phone, sms_message)

    flash(t('ticket_completed', ticket.code))
    return redirect(url_for('sharpener_dashboard'))

@app.route('/feedback/<ticket_code>', methods=['GET', 'POST'])
def feedback(ticket_code):
    """Customer feedback page"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    if ticket.status != 'completed':
        return "Ticket not completed yet", 400

    if ticket.feedback:
        return render_template('feedback_already_given.html', ticket=ticket)

    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form.get('comment', '').strip()

        feedback_obj = Feedback(
            ticket_id=ticket.id,
            rating=rating,
            comment=comment
        )
        db.session.add(feedback_obj)
        db.session.commit()

        # Notify sharpener about feedback
        if ticket.sharpener:
            sms_message = t(
                'feedback_email_body',
                name=ticket.customer_name,
                code=ticket.code,
                rating=rating
            )

            if comment:
                sms_message += f"\n{t('comment')}: {comment}"

            send_sms(ticket.sharpener.phone, sms_message)

        return render_template('feedback_thanks.html', ticket=ticket, rating=rating)

    return render_template('feedback_form.html', ticket=ticket)

# Admin routes (for setup and testing)
@app.route('/admin/invite_sharpener', methods=['GET', 'POST'])
def invite_sharpener():
    """Send invitation to new sharpener (admin only)"""
    if request.method == 'POST':
        email = request.form['email']

        # Check if user already exists
        if Sharpener.query.filter_by(email=email).first():
            flash(f'A sharpener with email {email} already exists.')
        elif Invitation.query.filter_by(email=email, used=False).first():
            flash(f'An invitation has already been sent to {email}.')
        else:
            # Create invitation
            token = generate_invitation_token(email)
            expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days to accept

            invitation = Invitation(
                email=email,
                token=token,
                expires_at=expires_at
            )
            db.session.add(invitation)
            db.session.commit()

            # Send invitation email
            if send_invitation_email(email, token):
                flash(f'Invitation sent to {email}. They have 7 days to accept.')
            else:
                flash(f'Failed to send invitation to {email}.')

    # Get existing sharpeners and pending invitations
    sharpeners = Sharpener.query.all()
    pending_invitations = Invitation.query.filter_by(used=False).all()

    return render_template('invite_sharpener.html',
                         sharpeners=sharpeners,
                         pending_invitations=pending_invitations,
                         now=datetime.utcnow())

@app.route('/invitation/<token>', methods=['GET', 'POST'])
def accept_invitation(token):
    """Accept invitation and create sharpener account"""
    # Verify token
    email = verify_invitation_token(token)
    if not email:
        flash('Invalid or expired invitation link.')
        return redirect(url_for('index'))

    # Check if invitation exists and is not used
    invitation = Invitation.query.filter_by(email=email, token=token, used=False).first()
    if not invitation or invitation.expires_at < datetime.utcnow():
        flash('Invitation has expired or been used.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        # Validate inputs
        if Sharpener.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.')
        elif Sharpener.query.filter_by(email=email).first():
            flash('Account already exists for this email.')
        else:
            # Create sharpener account
            sharpener = Sharpener(
                name=name,
                email=email,
                phone=phone,
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(sharpener)

            # Mark invitation as used
            invitation.used = True
            db.session.commit()

            flash('Account created successfully! You can now login.')
            return redirect(url_for('sharpener_login'))

    return render_template('accept_invitation.html', email=email)

# Keep old route for backward compatibility
@app.route('/admin/create_sharpener', methods=['GET', 'POST'])
def create_sharpener():
    """Redirect to new invitation-based system"""
    return redirect(url_for('invite_sharpener'))

# Initialize database
def create_tables():
    """Create database tables if they don't exist."""
    with app.app_context():
        db.create_all()

# Create tables on import (works with both 'python app.py' and 'flask run')
create_tables()

if __name__ == '__main__':
    # Bind to 0.0.0.0 for Docker compatibility
    app.run(host='0.0.0.0', port=5000, debug=True)
