# Flask Skate Sharpening Ticket System
# Complete backend with database, auth, SMS, and payment integration

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import requests
import os
import yaml
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///skate_tickets.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Handle PostgreSQL URL format for SQLAlchemy 2.0+
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

db = SQLAlchemy(app)

# Configuration - set these as environment variables
GATEWAYAPI_TOKEN = os.environ.get('GATEWAYAPI_TOKEN', 'your-gatewayapi-token')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'your-stripe-publishable-key')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')

# Database Models
class Sharpener(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    tickets = db.relationship('Ticket', backref='sharpener', lazy=True)

class Ticket(db.Model):
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
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Internationalization
def load_translations():
    """Load translations from YAML files"""
    translations = {}
    for lang in ['da', 'en']:
        try:
            with open(f'translations/{lang}.yaml', 'r', encoding='utf-8') as f:
                translations[lang] = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Translation file translations/{lang}.yaml not found")
            translations[lang] = {}
    return translations

# Load translations once at startup
TRANSLATIONS = load_translations()

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
    translation = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS['en'].get(key, key))

    # Handle string formatting
    if args or kwargs:
        try:
            if kwargs:
                return translation.format(**kwargs)
            else:
                return translation.format(*args)
        except:
            return translation
    return translation

@app.context_processor
def inject_translate():
    """Make translation function available in all templates"""
    return dict(t=t, recaptcha_site_key=RECAPTCHA_SITE_KEY)

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
        response = requests.post("https://gatewayapi.eu/rest/mtsms", json=data, auth=(GATEWAYAPI_TOKEN, ''))

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
            data=verification_data
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
    # This is a stub - implement actual Stripe integration
    # In real implementation, create payment intent with MobilePay payment method

    if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY == 'your-stripe-secret-key':
        # Simulation mode
        return f"pi_simulation_{ticket.code}"

    # Real Stripe integration would go here
    # stripe.PaymentIntent.create(...)
    return "pi_simulation_" + ticket.code

def login_required(f):
    """Decorator to require sharpener login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'sharpener_id' not in session:
            return redirect(url_for('sharpener_login'))
        return f(*args, **kwargs)
    return decorated_function

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
    payment_id = create_stripe_payment_intent(25, ticket)  # 25 DKK
    ticket.payment_id = payment_id
    db.session.commit()

    # Send SMS with payment link
    payment_url = f"{BASE_URL}/pay/{ticket.code}"
    skate_details = f"{brand} {color} {size}"

    sms_message = t('sms_ticket_created', code=code, payment_url=payment_url)
    send_sms(phone, sms_message)

    flash(t('ticket_request_sent'))
    return redirect(url_for('index'))

@app.route('/pay/<ticket_code>')
def payment_page(ticket_code):
    """Payment page for tickets"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    if ticket.status != 'unpaid':
        return render_template('already_paid.html', ticket=ticket)

    return render_template('payment.html', ticket=ticket, stripe_key=STRIPE_PUBLISHABLE_KEY)

@app.route('/payment_success/<ticket_code>')
def payment_success(ticket_code):
    """Handle successful payment"""
    ticket = Ticket.query.filter_by(code=ticket_code).first_or_404()

    # In real implementation, verify payment with Stripe webhook
    # For now, simulate successful payment
    ticket.status = 'paid'
    ticket.paid_at = datetime.utcnow()
    db.session.commit()

    # Send confirmation SMS
    sms_message = t('sms_payment_confirmed', code=ticket.code, estimated_time="15-20 minutes")
    send_sms(ticket.customer_phone, sms_message)

    return render_template('payment_success.html', ticket=ticket)

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
    sharpener_name = session['sharpener_name']
    feedback_url = f"{BASE_URL}/feedback/{ticket.code}"

    sms_message = t('sms_ticket_completed', code=ticket.code, feedback_url=feedback_url)
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
            stars = '⭐' * rating
            sms_message = t('feedback_email_body', name=ticket.customer_name, code=ticket.code, rating=rating)

            if comment:
                sms_message += f"\n{t('comment')}: {comment}"

            send_sms(ticket.sharpener.phone, sms_message)

        return render_template('feedback_thanks.html', ticket=ticket, rating=rating)

    return render_template('feedback_form.html', ticket=ticket)

# Admin routes (for setup and testing)
@app.route('/admin/create_sharpener', methods=['GET', 'POST'])
def create_sharpener():
    """Create a new sharpener account (admin only)"""
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        if Sharpener.query.filter_by(username=username).first():
            flash(t('username_exists'))
        else:
            sharpener = Sharpener(
                name=name,
                phone=phone,
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(sharpener)
            db.session.commit()
            flash(t('sharpener_created', name))
            return redirect(url_for('create_sharpener'))

    sharpeners = Sharpener.query.all()
    return render_template('create_sharpener.html', sharpeners=sharpeners)

# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()

# Create tables on import (works with both 'python app.py' and 'flask run')
create_tables()

if __name__ == '__main__':
    # Bind to 0.0.0.0 for Docker compatibility
    app.run(host='0.0.0.0', port=5000, debug=True)
