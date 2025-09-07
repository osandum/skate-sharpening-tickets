# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Setup

This is a Flask application for managing ice skate sharpening tickets with SMS notifications and payment integration.

### Virtual Environment
- Project uses Python virtual environment in `venv/` directory
- Activate with: `source venv/bin/activate`
- Dependencies in `requirements.txt`: Flask, Flask-SQLAlchemy, Werkzeug, requests

### Running the Application
- Development: `python app.py` or `flask run`
- Database is automatically created on first run (SQLite: `instance/skate_tickets.db`)
- Admin interface for creating sharpener accounts: `/admin/create_sharpener`

### Environment Variables
Required for production (simulation mode for development):
- `GATEWAYAPI_TOKEN` - SMS service integration
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` - Payment processing
- `BASE_URL` - For SMS payment links
- `SECRET_KEY` - Flask session security

## Architecture Overview

### Core Components

**Single File Architecture (`app.py`)**: Complete Flask application with all routes, models, and business logic in one file.

**Database Models**:
- `Sharpener` - Staff accounts with authentication
- `Ticket` - Customer skate sharpening requests with status tracking
- `Feedback` - Customer ratings and comments

**Status Flow**: unpaid → paid → in_progress → completed

### Key Business Logic

**Ticket Creation Flow** (`/request_ticket`):
1. Customer submits skate details (brand, color, size)
2. Generates unique 6-character ticket code
3. Creates Stripe payment intent (simulation in dev)
4. Sends SMS with ticket code and payment link

**Sharpener Dashboard** (`/sharpener`):
- View unpaid tickets (awaiting payment)
- Claim paid tickets (moves to in_progress)
- Complete tickets (sends pickup SMS with feedback link)
- Track personal performance metrics

**Payment & SMS Integration**:
- `send_sms()` function handles GatewayAPI integration (prints to console in dev)
- `create_stripe_payment_intent()` for MobilePay processing (simulation in dev)
- SMS templates include payment links and pickup notifications

### Template Structure
- `templates/base.html` - Base layout
- Customer-facing: `customer.html`, `payment.html`, `feedback_form.html`
- Sharpener interface: `sharpener_login.html`, `sharpener_dashboard.html`
- Admin: `create_sharpener.html`

### Security & Authentication
- Sharpener authentication via Flask sessions
- Password hashing with Werkzeug
- `@login_required` decorator for protected routes
- No customer authentication (tickets accessed via unique codes)

## Key Integration Points

### SMS Service (GatewayAPI)
- Functions in app.py:78 (`send_sms`)
- Sends ticket creation, payment confirmation, and pickup notifications
- Danish mobile number format handling

### Payment Processing (Stripe + MobilePay)
- Functions in app.py:102 (`create_stripe_payment_intent`)
- 25 DKK fixed pricing for sharpening service
- Payment confirmation via `/payment_success/<code>` route

### Database Operations
- SQLite for development (auto-created in `instance/` directory)
- All models defined in app.py:28-71
- Database initialization in `create_tables()` function

## Docker Deployment

### Building and Running
```bash
# Build image
docker build -t skate-sharpening .

# Run container
docker run -p 8080:5000 \
  -e GATEWAYAPI_TOKEN=your-token \
  -e STRIPE_SECRET_KEY=your-key \
  -e BASE_URL=https://yourdomain.com \
  skate-sharpening

# Using docker-compose (recommended)
docker-compose up -d
```

### Environment Variables
- `GATEWAYAPI_TOKEN` - SMS service token
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` - Payment processing
- `BASE_URL` - Public URL for SMS links  
- `SECRET_KEY` - Flask session security (generate random 32+ chars)

### Production Notes
- App runs on port 5000 inside container
- Database persisted in `./data` volume when using docker-compose
- Health checks included for container orchestration
- Non-root user for security