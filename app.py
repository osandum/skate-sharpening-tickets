#!/usr/bin/env python3
"""
Skate Sharpening Ticket System - Refactored Version
A Flask application for managing ice skate sharpening tickets with SMS notifications.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, g
from flask_mail import Mail
from flask_migrate import Migrate
import stripe
from itsdangerous import URLSafeTimedSerializer

# Import our modules
from models import db, Ticket, Sharpener, Feedback
from utils.i18n import t
from utils.banner import print_startup_banner
from routes import register_blueprints

# Load environment variables from .env file
load_dotenv()

def create_app():
    """Application factory pattern"""
    # Print startup banner (will show in both dev and production)
    print_startup_banner()

    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/skate_tickets.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Handle PostgreSQL URL format for SQLAlchemy 2.0+
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
        )

    # Initialize extensions
    db.init_app(app)
    mail = Mail(app)
    migrate = Migrate(app, db)

    # Configure Stripe
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key')

    # Register blueprints
    register_blueprints(app)

    # Context processor for templates
    @app.context_processor
    def inject_template_vars():
        """Make common variables available in all templates"""
        return {
            't': t,
            'recaptcha_site_key': os.environ.get('RECAPTCHA_SITE_KEY', ''),
            'sharpening_price': int(os.environ.get('SHARPENING_PRICE_DKK', '80'))
        }

    # Database migrations are handled by Flask-Migrate
    # Run: flask db upgrade (in production)

    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)