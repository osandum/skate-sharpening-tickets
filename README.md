# Ice Skate Sharpening Ticket System ⛸️

A bilingual Flask web application for managing ice skate sharpening services with SMS notifications and payment processing. Built specifically for Nordic skating clubs with automatic language detection.

## ✨ Features

### 🌍 **Bilingual Support**
- **Automatic language detection** based on browser Accept-Language headers
- **Danish interface** for Nordic users (Danish, Swedish, Norwegian)
- **English interface** for international users
- **Bilingual SMS notifications** in user's preferred language

### 📱 **Complete Workflow**
- **Customer ticket requests** with skate details (brand, color, size)
- **Unique 6-character ticket codes** for identification
- **SMS notifications** at every step of the process
- **MobilePay integration** via Stripe for payments
- **Sharpener dashboard** for managing work queue
- **Customer feedback system** with star ratings

### 🔧 **Technical Features**
- **Flask web framework** with SQLAlchemy ORM
- **SQLite database** for easy deployment
- **SMS integration** via GatewayAPI
- **Payment processing** via Stripe + MobilePay
- **Docker containerization** for production deployment
- **Responsive mobile-first design** with Tailwind CSS
- **reCAPTCHA v3** for bot protection
- **Borderless cards on mobile** for cleaner UX

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/osandum/skate-sharpening-tickets.git
cd skate-sharpening-tickets

# Start with docker-compose
docker-compose up -d

# Access the application
open http://localhost:8080
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Access the application
open http://localhost:5000
```

## 🏒 How It Works

### For Customers

1. **Submit Request**: Fill out skate details (brand, color, size) and phone number
2. **Receive SMS**: Get ticket code and payment link via SMS
3. **Label Skates**: Write ticket code on paper with your skates
4. **Make Payment**: Pay using MobilePay link (parents can pay too!)
5. **Get Notified**: Receive SMS when skates are ready for pickup
6. **Leave Feedback**: Rate the sharpening service

### For Sharpeners

1. **Login**: Access sharpener dashboard with credentials
2. **View Queue**: See paid tickets ready for sharpening
3. **Claim Tickets**: Take ownership of tickets to sharpen
4. **Complete Work**: Mark tickets as completed
5. **Customer Notification**: Customers automatically notified via SMS
6. **Track Performance**: View ratings and feedback

## 🛠️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# SMS Service (GatewayAPI)
GATEWAYAPI_TOKEN=your-gatewayapi-token

# Payment Processing (Stripe)
STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable-key

# Application Settings
BASE_URL=https://yourdomain.com
SECRET_KEY=your-very-secret-key-32-characters-minimum

# Optional: Database (defaults to SQLite)
DATABASE_URL=sqlite:///skate_tickets.db

# Optional: reCAPTCHA for bot protection
RECAPTCHA_SITE_KEY=your-recaptcha-site-key
RECAPTCHA_SECRET_KEY=your-recaptcha-secret-key
```

### First-Time Setup

1. **Create Sharpener Accounts**:
   - Visit `/admin/create_sharpener`
   - Create accounts for volunteer sharpeners
   - Each sharpener gets unique login credentials

2. **Configure Payment**:
   - Set up Stripe account with MobilePay integration
   - Add webhook endpoints for payment confirmation

3. **Test SMS**:
   - Verify GatewayAPI integration
   - Test with Danish mobile numbers (+45)
   - Verify language auto-detection works

4. **Configure reCAPTCHA** (Optional):
   - Set up Google reCAPTCHA v3
   - Add site and secret keys to environment

## 🐳 Docker Deployment

### Using Docker Compose (Production)

```yaml
# docker-compose.yml
version: '3.8'

services:
  skate-sharpening:
    build: .
    ports:
      - "80:5000"
    environment:
      - GATEWAYAPI_TOKEN=your-token
      - STRIPE_SECRET_KEY=your-key
      - STRIPE_PUBLISHABLE_KEY=your-publishable-key
      - BASE_URL=https://yourdomain.com
      - SECRET_KEY=your-secret-key
      - RECAPTCHA_SITE_KEY=your-recaptcha-site-key
      - RECAPTCHA_SECRET_KEY=your-recaptcha-secret-key
    volumes:
      - ./data:/app/instance
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Manual Docker Commands

```bash
# Build image
docker build -t skate-sharpening .

# Run container
docker run -p 8080:5000 \
  -e GATEWAYAPI_TOKEN=your-token \
  -e STRIPE_SECRET_KEY=your-key \
  -e STRIPE_PUBLISHABLE_KEY=your-publishable-key \
  -e BASE_URL=https://yourdomain.com \
  -e SECRET_KEY=your-secret-key \
  -v $(pwd)/data:/app/instance \
  skate-sharpening
```

## 🌐 API Endpoints

### Customer Endpoints
- `GET /` - Customer ticket request form
- `POST /request_ticket` - Submit new ticket request
- `GET /pay/<ticket_code>` - Payment page
- `GET /payment_success/<ticket_code>` - Payment confirmation
- `GET /feedback/<ticket_code>` - Feedback form
- `POST /feedback/<ticket_code>` - Submit feedback

### Sharpener Endpoints
- `GET /sharpener/login` - Login page
- `POST /sharpener/login` - Authenticate sharpener
- `GET /sharpener` - Dashboard (requires authentication)
- `GET /sharpener/claim/<ticket_id>` - Claim ticket
- `GET /sharpener/complete/<ticket_id>` - Complete ticket
- `GET /sharpener/logout` - Logout

### Admin Endpoints
- `GET /admin/create_sharpener` - Create sharpener accounts
- `POST /admin/create_sharpener` - Process account creation

## 🗄️ Database Schema

### Tables

**Sharpener**
- `id`, `name`, `phone`, `username`, `password_hash`, `created_at`

**Ticket**
- `id`, `code`, `customer_name`, `customer_phone`
- `brand`, `color`, `size` (skate details)
- `status`, `payment_id`, `sharpened_by_id`
- `created_at`, `paid_at`, `started_at`, `completed_at`

**Feedback**
- `id`, `ticket_id`, `rating` (1-5 stars), `comment`, `created_at`

## 📱 SMS Integration

The system sends SMS notifications at key points:

1. **Ticket Created**: Instructions and payment link
2. **Payment Received**: Confirmation and queue status
3. **Skates Ready**: Pickup notification with feedback link
4. **Feedback Received**: Notification to sharpener

### SMS Languages

Messages are automatically sent in the appropriate language based on the user's browser settings:

**Danish** (for da, dk, sv, se, no, nb, nn):
```
Din skøjtebillet: ABC123

1. Skriv "ABC123" på papir med dine skøjter
2. Læg skøjter på "til slibning" hylde
3. BETAL FØR SLIBNING STARTER: https://...

💡 Send dette betalingslink til dine forældre!
⚠️ Ingen betaling = ingen slibning
```

**English** (for all other languages):
```
Your skate ticket: ABC123

1. Write "ABC123" on paper with your skates
2. Put skates on "to sharpen" shelf
3. PAY BEFORE SHARPENING STARTS: https://...

💡 Send this payment link to your parents!
⚠️ No payment = no sharpening
```

## 🌨️ Responsive Design

### Mobile Optimizations

- **Borderless cards on small screens** (<640px) for cleaner mobile UX
- **Full card styling on larger screens** with shadows and rounded corners
- **Touch-optimized buttons** with appropriate sizing
- **Mobile-first form layouts** that adapt to screen size
- **Cyan-themed background** for better visual contrast

### CSS Implementation

```css
/* Responsive card wrapper classes */
@media (max-width: 640px) {
    .card-wrapper {
        @apply rounded-none shadow-none p-4 bg-transparent;
    }
}
@media (min-width: 641px) {
    .card-wrapper {
        @apply rounded-lg shadow-lg p-8 bg-white;
    }
}
```

## 🔒 Security Features

- **Password hashing** with Werkzeug
- **Session management** with Flask sessions
- **Non-root Docker container** for security
- **Environment variable secrets** (no hardcoded keys)
- **Input validation** and SQL injection prevention
- **HTTPS support** (configure reverse proxy)
- **reCAPTCHA v3 integration** for bot protection
- **CSRF protection** via Flask sessions

## 🧪 Development

### Quick Commands

The project includes a `Justfile` for common tasks:

```bash
# Install just (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash

# List available commands
just

# Run development server
just dev

# Build Docker image
just build

# Release and deploy to staging
just release v1.0.0

# Test SMS functionality
just test-sms
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run the application in debug mode
python app.py

# Test language detection
curl -H "Accept-Language: da-DK" http://localhost:5000/
curl -H "Accept-Language: en-US" http://localhost:5000/

# Test SMS sending (requires GATEWAYAPI_TOKEN)
python test_sms.py
```

### Project Structure

```
skate-sharpening-tickets/
├── app.py                 # Main Flask application (all-in-one)
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container definition
├── docker-compose.yml    # Orchestration
├── .dockerignore         # Build context exclusions
├── .env.example          # Environment variable template
├── CLAUDE.md             # AI assistant instructions
├── templates/            # Jinja2 templates
│   ├── base.html         # Base layout with responsive CSS
│   ├── customer.html     # Ticket request form
│   ├── sharpener_login.html
│   ├── sharpener_dashboard.html
│   ├── create_sharpener.html
│   ├── payment.html      # Stripe/MobilePay integration
│   ├── payment_success.html
│   ├── payment_failed.html
│   ├── ticket_created.html
│   ├── already_paid.html
│   └── feedback_form.html
├── static/               # Static assets
│   └── favicon.ico
└── instance/             # Database directory (created automatically)
    └── skate_tickets.db  # SQLite database
```

## 📚 API Response Formats

### Ticket Status Values
- `unpaid` - Ticket created, awaiting payment
- `paid` - Payment received, ready for sharpening
- `in_progress` - Sharpener has claimed the ticket
- `completed` - Sharpening finished, customer notified

### Language Detection

The system automatically detects language from the `Accept-Language` header:
- Danish UI: `da`, `dk`, `sv`, `se`, `no`, `nb`, `nn`
- English UI: All other language codes

## 🌟 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- **Single file architecture**: All backend logic in `app.py`
- **Responsive design**: Test on mobile and desktop
- **Bilingual support**: Update both Danish and English translations
- **Database migrations**: Handle schema changes carefully
- **SMS testing**: Use simulation mode for development

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ for Nordic skating communities
- SMS integration via [GatewayAPI](https://gatewayapi.eu/)
- Payment processing via [Stripe](https://stripe.com/)
- UI styling with [Tailwind CSS](https://tailwindcss.com/)

---

**⛸️ Ready to sharpen some skates!**

For support or questions, please open an issue on GitHub.
