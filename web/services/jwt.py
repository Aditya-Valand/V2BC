import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app  # Import this


def create_token(email):
    # Use timezone-aware UTC objects
    now = datetime.now(timezone.utc)

    payload = {
        'email': email,
        'exp': now + timedelta(hours=24), # Expires in 24h
        'iat': now,                       # Issued at
        'nbf': now                        # Not before
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    try:
        # PyJWT handles the expiry check automatically
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
