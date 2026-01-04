from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """Decorator to require sharpener login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'sharpener_id' not in session:
            return redirect(url_for('sharpener.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin sharpener login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'sharpener_id' not in session:
            return redirect(url_for('sharpener.login'))
        from models import Sharpener
        sharpener = Sharpener.query.get(session['sharpener_id'])
        if not sharpener or not sharpener.is_admin:
            flash('Admin access required')
            return redirect(url_for('sharpener.dashboard'))
        return f(*args, **kwargs)
    return decorated_function