import hmac
from flask import Blueprint, abort, request
from models import db, Ticket
from models.ticket import SMS_FAILED_STATUSES
from services.sms import callback_token

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/sms/status/<token>', methods=['POST'])
def sms_status(token):
    """GatewayAPI delivery status callback"""
    if not hmac.compare_digest(token, callback_token()):
        abort(404)

    payload = request.get_json(silent=True) or {}
    status = payload.get('status')
    ref = payload.get('userref')
    error = payload.get('error')

    log = f"[SMS] Status {status} for message {payload.get('id')} (ref: {ref})"
    if status in SMS_FAILED_STATUSES:
        log += f" – {payload.get('code')}: {error}"
    print(log)

    ticket = Ticket.query.filter_by(code=ref).first() if ref else None
    if ticket and status:
        ticket.sms_status = status
        ticket.sms_error = error[:255] if error and status in SMS_FAILED_STATUSES else None
        db.session.commit()

    return '', 204
