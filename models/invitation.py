from datetime import datetime
from .database import db

class Invitation(db.Model):
    """Database model for sharpener invitations."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    token = db.Column(db.String(100), nullable=False, unique=True)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)