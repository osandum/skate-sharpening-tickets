from datetime import datetime
from .database import db

# GatewayAPI statuses meaning the message will never reach the recipient
SMS_FAILED_STATUSES = {'REJECTED', 'UNDELIVERABLE', 'EXPIRED', 'DELETED', 'SKIPPED'}

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
    price = db.Column(db.Integer, nullable=False)  # Price in DKK

    # Status tracking
    status = db.Column(db.String(20), default='unpaid')  # unpaid, paid, in_progress, completed, cancelled
    payment_id = db.Column(db.String(100))  # Stripe payment intent ID

    # Delivery status of the latest SMS, reported by the GatewayAPI status callback
    sms_status = db.Column(db.String(20))
    sms_error = db.Column(db.String(255))

    @property
    def sms_failed(self):
        return self.sms_status in SMS_FAILED_STATUSES

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)

    # Sharpener tracking
    sharpened_by_id = db.Column(db.Integer, db.ForeignKey('sharpener.id'))
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey('sharpener.id'))

    # Relationships
    feedback = db.relationship('Feedback', backref='ticket', uselist=False)