# Flask Skate Sharpening Ticket System
# Complete backend with database, auth, SMS, and payment integration

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import string
import requests
import os
from functools import wraps

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
TRANSLATIONS = {
    'da': {
        # General
        'skate_sharpening': 'Skøjteslibning',
        'customer_form': 'Kundeformular',
        'sharpener_dashboard': 'Sliber Dashboard',
        'login': 'Log ind',
        'logout': 'Log ud',
        'name': 'Navn',
        'phone': 'Telefon',
        'username': 'Brugernavn',
        'password': 'Adgangskode',
        
        # Customer form
        'request_sharpening': 'Anmod om skøjteslibning',
        'your_name': 'Dit navn',
        'your_phone': 'Dit telefonnummer',
        'skate_brand': 'Skøjtemærke',
        'skate_color': 'Farve',
        'skate_size': 'Størrelse',
        'submit_request': 'Send anmodning',
        'select_brand': 'Vælg mærke',
        'select_color': 'Vælg farve',
        'select_size': 'Vælg størrelse',
        
        # Ticket status
        'unpaid': 'Ubetalt',
        'paid': 'Betalt',
        'in_progress': 'Under bearbejdning',
        'completed': 'Færdig',
        
        # Dashboard
        'tickets_awaiting_payment': 'Billetter venter på betaling',
        'ready_for_sharpening': 'Klar til slibning',
        'in_progress_tickets': 'Billetter under bearbejdning',
        'completed_today': 'Færdiggjort i dag',
        'claim_ticket': 'Påtag billet',
        'complete_ticket': 'Fuldfør billet',
        'ticket_code': 'Billetkode',
        'customer': 'Kunde',
        'skates': 'Skøjter',
        'created': 'Oprettet',
        'my_performance': 'Min præstation',
        'average_rating': 'Gennemsnitlig bedømmelse',
        'total_feedback': 'Total feedback',
        'recent_work': 'Seneste arbejde',
        
        # Payment
        'payment': 'Betaling',
        'pay_for_sharpening': 'Betal for slibning',
        'amount': 'Beløb',
        'pay_now': 'Betal nu',
        'payment_success': 'Betaling gennemført',
        'payment_received': 'Betaling modtaget!',
        'already_paid': 'Allerede betalt',
        
        # Feedback
        'feedback': 'Feedback',
        'rate_service': 'Bedøm servicen',
        'rating': 'Bedømmelse',
        'comment': 'Kommentar',
        'submit_feedback': 'Send feedback',
        'thank_you': 'Tak for din feedback!',
        'stars': 'stjerner',
        
        # Messages
        'ticket_request_sent': 'Billetanmodning sendt! Tjek din telefon for billetkode og betalingslink.',
        'name_phone_required': 'Navn og telefonnummer er påkrævet!',
        'invalid_login': 'Ugyldig brugernavn eller adgangskode',
        'ticket_claimed': 'Påtaget billet {}',
        'ticket_completed': 'Færdiggjort billet {}. Kunde underrettet!',
        'cannot_complete': 'Kan ikke fuldføre denne billet',
        'ticket_not_available': 'Billet er ikke tilgængelig til slibning',
        'username_exists': 'Brugernavn findes allerede',
        'sharpener_created': 'Sliber {} oprettet med succes!',
        
        # Admin
        'create_sharpener': 'Opret sliber',
        'existing_sharpeners': 'Eksisterende slibere',
        'create_account': 'Opret konto',
        
        # SMS Messages
        'sms_ticket_created': """Din skøjtebillet: {}

1. Skriv "{}" på papir med dine skøjter
2. Læg skøjter på "til slibning" hylde
3. BETAL FØR SLIBNING STARTER: {}

💡 Send dette betalingslink til dine forældre!
⚠️ Ingen betaling = ingen slibning

Dine skøjter: {}""",
        
        'sms_payment_received': """Betaling modtaget! ✅

Billet {} er nu i slibningskøen.
Du får en SMS når dine skøjter er klar.

Skøjter: {} {} {}""",
        
        'sms_skates_ready': """Dine skøjter er klar til afhentning! 🥅

Billet: {}
Slebet af: {}
Skøjter: {} {} {}

Hvordan gik det? Giv feedback: {}""",
        
        'sms_feedback_received': """Ny feedback modtaget! {}

Fra: {}
Billet: {}
Bedømmelse: {}/5 stjerner"""
    },
    'en': {
        # General
        'skate_sharpening': 'Skate Sharpening',
        'customer_form': 'Customer Form',
        'sharpener_dashboard': 'Sharpener Dashboard',
        'login': 'Login',
        'logout': 'Logout',
        'name': 'Name',
        'phone': 'Phone',
        'username': 'Username',
        'password': 'Password',
        
        # Customer form
        'request_sharpening': 'Request Skate Sharpening',
        'your_name': 'Your name',
        'your_phone': 'Your phone number',
        'skate_brand': 'Skate brand',
        'skate_color': 'Color',
        'skate_size': 'Size',
        'submit_request': 'Submit request',
        'select_brand': 'Select brand',
        'select_color': 'Select color',
        'select_size': 'Select size',
        
        # Ticket status
        'unpaid': 'Unpaid',
        'paid': 'Paid',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        
        # Dashboard
        'tickets_awaiting_payment': 'Tickets awaiting payment',
        'ready_for_sharpening': 'Ready for sharpening',
        'in_progress_tickets': 'Tickets in progress',
        'completed_today': 'Completed today',
        'claim_ticket': 'Claim ticket',
        'complete_ticket': 'Complete ticket',
        'ticket_code': 'Ticket code',
        'customer': 'Customer',
        'skates': 'Skates',
        'created': 'Created',
        'my_performance': 'My performance',
        'average_rating': 'Average rating',
        'total_feedback': 'Total feedback',
        'recent_work': 'Recent work',
        
        # Payment
        'payment': 'Payment',
        'pay_for_sharpening': 'Pay for sharpening',
        'amount': 'Amount',
        'pay_now': 'Pay now',
        'payment_success': 'Payment successful',
        'payment_received': 'Payment received!',
        'already_paid': 'Already paid',
        
        # Feedback
        'feedback': 'Feedback',
        'rate_service': 'Rate the service',
        'rating': 'Rating',
        'comment': 'Comment',
        'submit_feedback': 'Submit feedback',
        'thank_you': 'Thank you for your feedback!',
        'stars': 'stars',
        
        # Messages
        'ticket_request_sent': 'Ticket request sent! Check your phone for the ticket code and payment link.',
        'name_phone_required': 'Name and phone number are required!',
        'invalid_login': 'Invalid username or password',
        'ticket_claimed': 'Claimed ticket {}',
        'ticket_completed': 'Completed ticket {}. Customer notified!',
        'cannot_complete': 'Cannot complete this ticket',
        'ticket_not_available': 'Ticket is not available for sharpening',
        'username_exists': 'Username already exists',
        'sharpener_created': 'Sharpener {} created successfully!',
        
        # Admin
        'create_sharpener': 'Create sharpener',
        'existing_sharpeners': 'Existing sharpeners',
        'create_account': 'Create account',
        
        # SMS Messages
        'sms_ticket_created': """Your skate ticket: {}

1. Write "{}" on paper with your skates
2. Put skates on "to sharpen" shelf
3. PAY BEFORE SHARPENING STARTS: {}

💡 Send this payment link to your parents!
⚠️ No payment = no sharpening

Your skates: {}""",
        
        'sms_payment_received': """Payment received! ✅

Ticket {} is now in the sharpening queue.
You'll get an SMS when your skates are ready.

Skates: {} {} {}""",
        
        'sms_skates_ready': """Your skates are ready for pickup! 🥅

Ticket: {}
Sharpened by: {}
Skates: {} {} {}

How did we do? Leave feedback: {}""",
        
        'sms_feedback_received': """New feedback received! {}

From: {}
Ticket: {}
Rating: {}/5 stars"""
    }
}

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

def t(key, *args):
    """Translate key to current language"""
    lang = get_language()
    translation = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS['en'].get(key, key))
    
    # Handle string formatting
    if args:
        try:
            return translation.format(*args)
        except:
            return translation
    return translation

@app.context_processor
def inject_translate():
    """Make translation function available in all templates"""
    return dict(t=t)

# Helper Functions
def generate_ticket_code():
    """Generate a 6-character ticket code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def send_sms(phone, message):
    """Send SMS using GatewayAPI"""
    if not GATEWAYAPI_TOKEN or GATEWAYAPI_TOKEN == 'your-gatewayapi-token':
        # Simulation mode for development
        print(f"SMS to {phone}: {message}")
        return True

    url = "https://gatewayapi.com/rest/mtsms"
    headers = {
        "Authorization": f"Bearer {GATEWAYAPI_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "sender": "SkateSharp",
        "message": message,
        "recipients": [{"msisdn": phone.replace("+", "").replace(" ", "")}]
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        return response.status_code == 200
    except:
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
    brands = ['Jackson', 'EDEA', 'Risport', 'Riedell', 'Graf', 'Other']
    colors = ['White', 'Black', 'Other']
    sizes = list(range(24, 47))  # 24-46

    return render_template('customer.html', brands=brands, colors=colors, sizes=sizes)

@app.route('/request_ticket', methods=['POST'])
def request_ticket():
    """Process ticket request"""
    name = request.form['name'].strip()
    phone = request.form['phone'].strip()
    brand = request.form['brand']
    color = request.form['color']
    size = int(request.form['size'])

    if not name or not phone:
        flash(t('name_phone_required'))
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

    sms_message = t('sms_ticket_created', code, code, payment_url, skate_details)
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
    sms_message = t('sms_payment_received', ticket.code, ticket.brand, ticket.color, ticket.size)
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

    sms_message = t('sms_skates_ready', ticket.code, sharpener_name, ticket.brand, ticket.color, ticket.size, feedback_url)
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
            sms_message = t('sms_feedback_received', stars, ticket.customer_name, ticket.code, rating)
            
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

if __name__ == '__main__':
    create_tables()  # Create tables on startup
    # Bind to 0.0.0.0 for Docker compatibility
    app.run(host='0.0.0.0', port=5000, debug=True)
