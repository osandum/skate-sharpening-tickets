from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    """Decorator to require sharpener login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'sharpener_id' not in session:
            return redirect(url_for('sharpener.login'))
        return f(*args, **kwargs)
    return decorated_function