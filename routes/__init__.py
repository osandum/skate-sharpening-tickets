from .customer import customer_bp
from .sharpener import sharpener_bp
from .admin import admin_bp, invitation_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(customer_bp)
    app.register_blueprint(sharpener_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(invitation_bp)