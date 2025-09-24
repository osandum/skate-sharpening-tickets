from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from models import db, Ticket, Sharpener, Feedback
from services import send_sms, render_sms_template, login_required
from utils import t

sharpener_bp = Blueprint('sharpener', __name__, url_prefix='/sharpener')

@sharpener_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Sharpener login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        sharpener = Sharpener.query.filter_by(username=username).first()

        if sharpener and check_password_hash(sharpener.password_hash, password):
            session['sharpener_id'] = sharpener.id
            session['sharpener_name'] = sharpener.name
            return redirect(url_for('sharpener.dashboard'))
        else:
            flash(t('invalid_login'))

    return render_template('sharpener_login.html')

@sharpener_bp.route('/logout')
def logout():
    """Logout sharpener"""
    session.pop('sharpener_id', None)
    session.pop('sharpener_name', None)
    return redirect(url_for('sharpener.login'))

@sharpener_bp.route('/')
@login_required
def dashboard():
    """Sharpener dashboard"""
    unpaid_tickets = Ticket.query.filter_by(status='unpaid').all()
    ready_tickets = Ticket.query.filter_by(status='paid').all()
    in_progress_tickets = Ticket.query.filter_by(status='in_progress').all()
    completed_today = Ticket.query.filter(
        Ticket.status == 'completed',
        Ticket.completed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).all()

    # Get current sharpener's recent work and feedback
    sharpener_id = session['sharpener_id']
    my_recent_tickets = Ticket.query.filter_by(
        sharpened_by_id=sharpener_id,
        status='completed'
    ).order_by(Ticket.completed_at.desc()).limit(5).all()

    # Calculate average rating
    feedbacks = db.session.query(Feedback).join(Ticket).filter(
        Ticket.sharpened_by_id == sharpener_id
    ).all()
    avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks) if feedbacks else 0

    return render_template('sharpener_dashboard.html',
                         unpaid_count=len(unpaid_tickets),
                         ready_tickets=ready_tickets,
                         in_progress_tickets=in_progress_tickets,
                         completed_today=len(completed_today),
                         my_recent_tickets=my_recent_tickets,
                         avg_rating=round(avg_rating, 1),
                         feedback_count=len(feedbacks))

@sharpener_bp.route('/unpaid')
@login_required
def unpaid_tickets():
    """View all unpaid tickets"""
    unpaid_tickets = Ticket.query.filter_by(status='unpaid').order_by(Ticket.created_at.desc()).all()
    return render_template('unpaid_tickets.html', unpaid_tickets=unpaid_tickets, now=datetime.utcnow())

@sharpener_bp.route('/claim/<int:ticket_id>')
@login_required
def claim_ticket(ticket_id):
    """Claim a ticket for sharpening"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if ticket.status == 'unpaid':
        # Promote unpaid ticket to paid status (claimed for processing)
        ticket.status = 'paid'
        db.session.commit()
        flash(t('unpaid_ticket_claimed', ticket.code))
        return redirect(request.referrer or url_for('sharpener.dashboard'))
    elif ticket.status == 'paid':
        # Normal claim: move to in_progress
        ticket.status = 'in_progress'
        ticket.started_at = datetime.utcnow()
        ticket.sharpened_by_id = session['sharpener_id']
        db.session.commit()
        flash(t('ticket_claimed', ticket.code))
        return redirect(url_for('sharpener.dashboard'))
    else:
        flash(t('ticket_not_available'))
        return redirect(request.referrer or url_for('sharpener.dashboard'))

@sharpener_bp.route('/unclaim/<int:ticket_id>')
@login_required
def unclaim_ticket(ticket_id):
    """Unclaim a ticket and return it to previous status"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if ticket.status == 'in_progress' and ticket.sharpened_by_id == session['sharpener_id']:
        # Return in_progress ticket to paid status
        ticket.status = 'paid'
        ticket.started_at = None
        ticket.sharpened_by_id = None
        db.session.commit()
        flash(t('ticket_unclaimed', ticket.code))
    elif ticket.status == 'paid' and not ticket.sharpened_by_id:
        # Return claimed unpaid ticket back to unpaid status
        ticket.status = 'unpaid'
        db.session.commit()
        flash(t('ticket_unclaimed', ticket.code))
    else:
        flash(t('cannot_unclaim'))

    return redirect(request.referrer or url_for('sharpener.dashboard'))

@sharpener_bp.route('/complete/<int:ticket_id>')
@login_required
def complete_ticket(ticket_id):
    """Mark a ticket as completed"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if ticket.status != 'in_progress' or ticket.sharpened_by_id != session['sharpener_id']:
        flash(t('ticket_not_available'))
        return redirect(url_for('sharpener.dashboard'))

    ticket.status = 'completed'
    ticket.completed_at = datetime.utcnow()
    db.session.commit()

    # Send pickup SMS with feedback link
    import os
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    feedback_url = f"{base_url}/feedback/{ticket.code}"

    sms_message = render_sms_template(
        'pickup_ready',
        ticket=ticket,
        feedback_url=feedback_url
    )
    send_sms(ticket.customer_phone, sms_message)

    flash(t('ticket_completed', ticket.code))
    return redirect(url_for('sharpener.dashboard'))