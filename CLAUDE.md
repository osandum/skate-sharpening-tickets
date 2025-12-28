# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Setup

This is a Flask application for managing ice skate sharpening tickets with SMS notifications, payment integration, and internationalization support.

### Virtual Environment
- Project uses Python virtual environment in `venv/` directory
- Activate with: `source venv/bin/activate`
- Dependencies in `requirements.txt`: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Mail, Werkzeug, requests, stripe, psycopg2-binary, PyYAML, python-dotenv, gunicorn

### Running the Application
- Development: `python app.py` or `flask run`
- Database migrations: `flask db upgrade` (required on first run and after schema changes)
- SQLite database: `instance/skate_tickets.db` (or PostgreSQL via `DATABASE_URL`)
- Admin interface for inviting sharpeners: `/admin/invite_sharpener`

### Environment Variables
Required for production (simulation mode for development):
- `GATEWAYAPI_TOKEN` - SMS service integration
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` - Payment processing (MobilePay)
- `BASE_URL` - Public URL for SMS links and invitation emails
- `SECRET_KEY` - Flask session security (required for production)
- `DATABASE_URL` - PostgreSQL connection string (optional, defaults to SQLite)
- `SHARPENING_PRICE_DKK` - Price in DKK (default: 80)
- `RECAPTCHA_SECRET_KEY` / `RECAPTCHA_SITE_KEY` - Optional reCAPTCHA integration
- `BUILD_TIME` / `GIT_HASH` - Set during Docker builds for version tracking

## Architecture Overview

### Core Components

**Modular Architecture**: Application uses Flask's application factory pattern with modular organization:

- `app.py` - Application factory and configuration (72 lines)
- `models/` - SQLAlchemy database models
  - `database.py` - Database instance
  - `ticket.py` - Ticket model
  - `sharpener.py` - Sharpener model
  - `feedback.py` - Feedback model
  - `invitation.py` - Invitation model
- `routes/` - Flask blueprints for routing
  - `customer.py` - Customer-facing routes (ticket creation, payment, feedback)
  - `sharpener.py` - Sharpener dashboard and workflow
  - `admin.py` - Admin routes (sharpener invitations)
- `services/` - Business logic services
  - `sms.py` - GatewayAPI SMS integration with encoding detection
  - `payment.py` - Stripe payment intent creation
  - `auth.py` - Authentication decorator
- `utils/` - Utility functions
  - `helpers.py` - Ticket code generation, phone number normalization
  - `i18n.py` - Internationalization with YAML translations
  - `banner.py` - Startup banner with git version info
- `templates/` - Jinja2 HTML templates
- `translations/` - YAML translation files (da.yaml, en.yaml)
- `migrations/` - Flask-Migrate database migrations

**Database Models**:
- `Sharpener` - Staff accounts with authentication (username, password_hash, email, phone)
- `Ticket` - Customer skate sharpening requests with status tracking and timestamps
- `Feedback` - Customer ratings (1-5 stars) and comments
- `Invitation` - Time-limited invitation tokens for onboarding new sharpeners

**Ticket Status Flow**: unpaid → paid → in_progress → completed

### Key Business Logic

**Ticket Creation Flow** (`routes/customer.py: request_ticket()`):
1. Customer submits skate details (brand, color, size) via web form
2. Generates unique 6-character ticket code (utils/helpers.py)
3. Creates ticket in database with 'unpaid' status
4. Creates Stripe payment intent for MobilePay (simulation in dev)
5. Sends SMS with ticket code and payment link (language-aware)
6. Implements PRG pattern (Post-Redirect-Get) to prevent duplicate submissions

**Sharpener Dashboard** (`routes/sharpener.py: dashboard()`):
- View unpaid tickets (awaiting payment confirmation)
- View paid tickets (ready for sharpening)
- Claim tickets (moves to in_progress, assigns to sharpener)
- Complete tickets (sends pickup SMS with feedback link)
- Track personal performance metrics (average rating, feedback count)
- View recent completed work

**Sharpener Invitation System** (`routes/admin.py: invite_sharpener()`):
- Admin sends invitation email with time-limited token (7 days)
- Token verification using itsdangerous URLSafeTimedSerializer
- New sharpeners create account via invitation link
- Prevents duplicate invitations and accounts

**Internationalization** (`utils/i18n.py`):
- Language detection from Accept-Language header
- Danish (da) for Nordic languages (da, dk, sv, se, no, nb, nn)
- English (en) as fallback
- YAML-based translations with hot-reloading in debug mode
- SMS templates in language-specific subdirectories

### Template Structure
- `templates/base.html` - Base layout with language-aware content
- Customer-facing:
  - `customer.html` - Ticket request form with dynamic EDEA size switching
  - `payment.html`, `payment_success.html`, `payment_failed.html` - Payment flow
  - `ticket_created.html`, `already_paid.html` - Ticket status pages
  - `feedback_form.html`, `feedback_thanks.html`, `feedback_already_given.html` - Feedback collection
- Sharpener interface:
  - `sharpener_login.html` - Login page
  - `sharpener_dashboard.html` - Main dashboard with ticket queues
  - `unpaid_tickets.html` - View all unpaid tickets
- Admin:
  - `invite_sharpener.html` - Send invitations to new sharpeners
  - `accept_invitation.html` - Invitation acceptance form
- SMS templates:
  - `templates/sms/da/*.j2` - Danish SMS templates
  - `templates/sms/en/*.j2` - English SMS templates

### Security & Authentication
- Sharpener authentication via Flask sessions
- Password hashing with Werkzeug (generate_password_hash, check_password_hash)
- `@login_required` decorator (services/auth.py) for protected routes
- No customer authentication (tickets accessed via unique codes)
- Secure invitation tokens using itsdangerous URLSafeTimedSerializer
- reCAPTCHA support (optional, configured via environment variables)

## Key Integration Points

### SMS Service (GatewayAPI)
- Implementation: `services/sms.py: send_sms()`
- Automatic encoding detection (GSM7 vs UCS2) for cost optimization
- Language-aware template rendering via `render_sms_template()`
- Sends ticket creation, payment confirmation, and pickup notifications
- Danish mobile number normalization (utils/helpers.py)
- Simulation mode in development (prints to console)

### Payment Processing (Stripe + MobilePay)
- Implementation: `services/payment.py: create_stripe_payment_intent()`
- Default pricing: 80 DKK (configurable via SHARPENING_PRICE_DKK)
- MobilePay payment method type
- Stores ticket metadata in payment intent
- Payment confirmation via routes in customer.py
- Simulation mode in development (generates fake payment intent IDs)

### Database Operations
- SQLite for development (instance/skate_tickets.db)
- PostgreSQL support for production (via DATABASE_URL environment variable)
- Flask-Migrate for schema migrations (migrations/ directory)
- Models defined in models/ directory with proper relationships
- Database initialization via `flask db upgrade` command

## Docker Deployment

### Building and Running
```bash
# Build image with version info
docker build \
  --build-arg BUILD_TIME="$(date -u +'%Y-%m-%d %H:%M:%S UTC')" \
  --build-arg GIT_HASH="$(git rev-parse HEAD)" \
  -t skate-sharpening .

# Run container
docker run -p 8080:5000 \
  -e GATEWAYAPI_TOKEN=your-token \
  -e STRIPE_SECRET_KEY=your-key \
  -e STRIPE_PUBLISHABLE_KEY=your-key \
  -e BASE_URL=https://yourdomain.com \
  -e SECRET_KEY=your-secret-key \
  -v ./data:/app/instance \
  skate-sharpening

# Using docker-compose (recommended)
docker-compose up -d
```

### Environment Variables
All variables from "Development Environment Setup" section apply. Key production variables:
- `FLASK_ENV` - Set to 'production' for gunicorn, or 'development' for Flask dev server
- `GATEWAYAPI_TOKEN` - SMS service token (required for SMS sending)
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` - Payment processing (required for payments)
- `BASE_URL` - Public URL for SMS links and invitation emails (required)
- `SECRET_KEY` - Flask session security (generate random 32+ chars, required)
- `DATABASE_URL` - PostgreSQL connection string (optional, defaults to SQLite)
- `SHARPENING_PRICE_DKK` - Price in DKK (default: 80)

### Production Notes
- App runs on port 5000 inside container (mapped to 8080 in docker-compose)
- Database persisted in `./data` volume when using docker-compose
- Health checks included for container orchestration (30s interval, 10s timeout)
- Non-root user 'app' for security
- Gunicorn WSGI server with 2 workers in production mode
- Automatic database migrations on container start (`flask db upgrade`)
- Startup banner displays build time and git commit hash
- OpenContainer labels for metadata