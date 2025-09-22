from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_mail import Message, Mail
from werkzeug.security import generate_password_hash
from itsdangerous import URLSafeTimedSerializer
from models import db, Sharpener, Invitation

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize token serializer for invitations (this should come from app config)
import os
from flask import current_app

def get_serializer():
    """Get the token serializer"""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_invitation_token(email):
    """Generate a secure invitation token"""
    serializer = get_serializer()
    return serializer.dumps(email, salt='invitation')

def verify_invitation_token(token, max_age=86400*7):  # 7 days
    """Verify and decode invitation token"""
    try:
        serializer = get_serializer()
        email = serializer.loads(token, salt='invitation', max_age=max_age)
        return email
    except:
        return None

def send_invitation_email(email, token):
    """Send invitation email (mock implementation for now)"""
    # In a real app, this would send an actual email
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    invitation_url = f"{base_url}/invitation/{token}"

    print(f"[EMAIL SIMULATION] Invitation sent to {email}")
    print(f"[EMAIL SIMULATION] Invitation URL: {invitation_url}")
    print("-" * 50)

    return True

@admin_bp.route('/invite_sharpener', methods=['GET', 'POST'])
def invite_sharpener():
    """Send invitation to new sharpener (admin only)"""
    if request.method == 'POST':
        email = request.form['email']

        # Check if user already exists
        if Sharpener.query.filter_by(email=email).first():
            flash(f'A sharpener with email {email} already exists.')
        elif Invitation.query.filter_by(email=email, used=False).first():
            flash(f'An invitation has already been sent to {email}.')
        else:
            # Create invitation
            token = generate_invitation_token(email)
            expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days to accept

            invitation = Invitation(
                email=email,
                token=token,
                expires_at=expires_at
            )
            db.session.add(invitation)
            db.session.commit()

            # Send invitation email
            if send_invitation_email(email, token):
                flash(f'Invitation sent to {email}. They have 7 days to accept.')
            else:
                flash(f'Failed to send invitation to {email}.')

    # Get existing sharpeners and pending invitations
    sharpeners = Sharpener.query.all()
    pending_invitations = Invitation.query.filter_by(used=False).all()

    return render_template('invite_sharpener.html',
                         sharpeners=sharpeners,
                         pending_invitations=pending_invitations,
                         now=datetime.utcnow())

@admin_bp.route('/invitation/<token>', methods=['GET', 'POST'])
def accept_invitation(token):
    """Accept invitation and create sharpener account"""
    # Verify token
    email = verify_invitation_token(token)
    if not email:
        flash('Invalid or expired invitation link.')
        return redirect(url_for('customer.index'))

    # Check if invitation exists and is not used
    invitation = Invitation.query.filter_by(email=email, token=token, used=False).first()
    if not invitation or invitation.expires_at < datetime.utcnow():
        flash('Invitation has expired or been used.')
        return redirect(url_for('customer.index'))

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        # Validate inputs
        if Sharpener.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.')
        elif Sharpener.query.filter_by(email=email).first():
            flash('Account already exists for this email.')
        else:
            # Create sharpener account
            sharpener = Sharpener(
                name=name,
                email=email,
                phone=phone,
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(sharpener)

            # Mark invitation as used
            invitation.used = True
            db.session.commit()

            flash('Account created successfully! You can now login.')
            return redirect(url_for('sharpener.login'))

    return render_template('accept_invitation.html', email=email)

# Keep old route for backward compatibility
@admin_bp.route('/create_sharpener', methods=['GET', 'POST'])
def create_sharpener():
    """Redirect to new invitation-based system"""
    return redirect(url_for('admin.invite_sharpener'))

# Add the invitation route to main routes (not admin prefix)
from flask import Blueprint as MainBlueprint
invitation_bp = MainBlueprint('invitation', __name__)

@invitation_bp.route('/invitation/<token>', methods=['GET', 'POST'])
def invitation_route(token):
    """Handle invitation acceptance at root level"""
    return accept_invitation(token)