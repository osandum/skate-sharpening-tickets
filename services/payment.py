import os
import stripe

# Configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key')

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
            payment_method_types=['mobilepay'],
            payment_method_data={
                'type': 'mobilepay'
            },
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