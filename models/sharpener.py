from datetime import datetime
from .database import db

class Sharpener(db.Model):
    """Database model for skate sharpener staff accounts."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship - explicitly specify foreign_key since Ticket has multiple FKs to Sharpener
    tickets = db.relationship('Ticket', backref='sharpener', lazy=True,
                              foreign_keys='Ticket.sharpened_by_id')