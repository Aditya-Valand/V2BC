from functools import wraps
from flask import request, redirect, url_for, make_response
from services.jwt import decode_token
from database.user import get_user_by_email

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')

        if not token:
            return redirect(url_for('auth.signin'))

        data = decode_token(token)

        # If token is invalid/expired, data will be None
        if not data:
            response = make_response(redirect(url_for('auth.signin')))
            response.set_cookie('auth_token', '', expires=0) # Clear bad token
            return response

        user = get_user_by_email(data['email'])
        if not user:
            response = make_response(redirect(url_for('auth.signin')))
            response.set_cookie('auth_token', '', expires=0)
            return response

        if user['profile'] == 0 and request.endpoint != 'dashboard.profile':
            return redirect(url_for('dashboard.profile'))

        return f(dict(user), *args, **kwargs)
    return decorated


def guest(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')

        if token:
            data = decode_token(token)
            if data:
                # Valid token found, user shouldn't be here
                return redirect(url_for('dashboard.dashboard'))
            else:
                # Token exists but is INVALID/EXPIRED
                # We must clear the cookie, otherwise the browser keeps sending it
                response = make_response(redirect(request.url))
                response.set_cookie('auth_token', '', expires=0)
                return response

        return f(*args, **kwargs)
    return decorated
